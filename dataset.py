"""Loads games into session state and derives the stats every view shares."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from api_client import LichessClient
from data_processing import get_opening_stats, process_games
from local_engine import LocalEngine

DEMO_FILE = Path(__file__).parent / "data" / "demo_games.json"
SPEEDS = ["Overall", "Rapid", "Blitz", "Classical", "Bullet"]


# --- Loading ---

def store(df, raw_games, username):
    """Put a freshly loaded dataset into session state."""
    st.session_state.update(
        game_data=df,
        raw_games=raw_games,
        username=username,
        chat_context=build_chat_context(df, username),
        coach_reports={},
        stats_cache={},
    )
    st.session_state.pop('step', None)  # new player: start the guided path from the Overview


def cached(speed, compute):
    """Per-filter stats, computed once per dataset (cleared whenever games change)."""
    cache = st.session_state.setdefault('stats_cache', {})
    if speed not in cache:
        cache[speed] = compute()
    return cache[speed]


def load_from_lichess(username, max_games, db=None):
    """Fetch games from Lichess. Returns (games_loaded, error_message)."""
    client = LichessClient()
    games = client.get_user_games(username, max_games=max_games)
    if not games:
        return 0, client.last_error or "No rated games found for this player."
    df = process_games(games, username)
    if db is not None and db.connected:
        try:
            db.save_games(df)
        except Exception as e:
            print(f"DB save error: {e}")
    store(df, games, username)
    return len(df), None


def demo_available():
    return DEMO_FILE.exists()


def load_demo():
    """Load the bundled sample dataset (works offline)."""
    payload = json.loads(DEMO_FILE.read_text(encoding="utf-8"))
    df = process_games(payload["games"], payload["username"])
    store(df, payload["games"], payload["username"])
    return payload["username"], len(df)


def load_from_db(db, username, limit, progress=None):
    """Load saved games, then backfill clocks/analysis that older records lack."""
    df = db.load_games(username, limit=limit)
    if df.empty:
        return 0, 0
    df = df.drop_duplicates(subset=['game_id']).reset_index(drop=True)
    repaired = _backfill_from_lichess(db, df, progress) + _backfill_with_engine(db, df, progress)
    store(df, df.to_dict('records'), username)
    return len(df), repaired


def _has_items(value):
    return isinstance(value, list) and len(value) > 0


def _backfill_from_lichess(db, df, progress):
    missing = df.loc[~df['clocks'].apply(_has_items), 'game_id'].tolist()
    if not missing:
        return 0
    client, updated = LichessClient(), 0
    for i in range(0, len(missing), 200):
        for game in client.get_games_by_ids(missing[i:i + 200]):
            updates = {
                'clocks': game.get('clocks', []),
                'clock': game.get('clock', {}),
                'analysis': game.get('analysis', []),
                'white_analysis': game.get('players', {}).get('white', {}).get('analysis', {}),
                'black_analysis': game.get('players', {}).get('black', {}).get('analysis', {}),
            }
            if db.update_game(game['id'], updates):
                updated += 1
                idx = df.index[df['game_id'] == game['id']]
                for key in ('clocks', 'analysis', 'white_analysis', 'black_analysis'):
                    for j in idx:
                        df.at[j, key] = updates[key]
        if progress:
            progress(min((i + 200) / len(missing), 1.0), "Fetching missing clocks and analysis…")
    return updated


def _backfill_with_engine(db, df, progress, limit=5):
    """Run Stockfish locally on the most recent games that still have no analysis."""
    todo = df[~df['analysis'].apply(_has_items) & df['moves'].astype(bool)].head(limit)
    if todo.empty:
        return 0
    engine, done = LocalEngine(), 0
    for n, (idx, row) in enumerate(todo.iterrows(), start=1):
        try:
            result = engine.analyze_game(row['moves'].split())
        except Exception as e:
            print(f"Engine error for {row['game_id']}: {e}")
            continue
        updates = {
            'analysis': result.get('analysis', []),
            'white_analysis': {'acpl': int(result['white_acpl'])},
            'black_analysis': {'acpl': int(result['black_acpl'])},
        }
        if db.update_game(row['game_id'], updates):
            done += 1
            for key, value in updates.items():
                df.at[idx, key] = value
        if progress:
            progress(n / len(todo), "Running local engine analysis…")
    return done


# --- Derived stats ---

def filter_speed(df, raw_games, speed):
    """Restrict the dataset to one time control ('Overall' keeps everything)."""
    if speed == "Overall":
        return df, raw_games
    key = speed.lower()
    return df[df['speed'] == key], [g for g in raw_games if g.get('speed') == key]


def ensure_columns(df):
    """Older DB rows may lack derived columns; rebuild them if needed."""
    if 'ply_count' not in df.columns:
        df['ply_count'] = df['moves'].apply(lambda m: len(m.split()) if isinstance(m, str) else 0)
    if 'hour' not in df.columns:
        df['hour'] = df['date'].dt.hour
    if 'day_of_week' not in df.columns:
        df['day_of_week'] = df['date'].dt.day_name()
    return df


def summary(df):
    if df.empty:
        return dict(games=0, wins=0, draws=0, losses=0, win_rate=0.0, rating=None, rating_change=None)
    counts = df['result'].value_counts()
    ordered = df.sort_values('date')
    return dict(
        games=len(df),
        wins=int(counts.get('Win', 0)),
        draws=int(counts.get('Draw', 0)),
        losses=int(counts.get('Loss', 0)),
        win_rate=counts.get('Win', 0) / len(df),
        rating=ordered.iloc[-1]['user_rating'],
        rating_change=int(ordered.iloc[-1]['user_rating'] - ordered.iloc[0]['user_rating']) if len(df) > 1 else None,
    )


def best_opening(df, color, min_games=5):
    """Highest win-rate opening for a color (min_games, else all). Returns a row or None."""
    stats = get_opening_stats(df, color=color)
    if stats.empty:
        return None
    pool = stats[stats['games'] >= min_games]
    pool = pool if not pool.empty else stats
    return pool.sort_values(['win_rate', 'games'], ascending=False).iloc[0]


def build_chat_context(df, username):
    """Compact text summary of the player that the chat assistant can reference."""
    s = summary(df)

    def top_openings(color):
        stats = get_opening_stats(df, color=color)
        if stats.empty:
            return f"No {color} games played."
        return "\n".join(
            f"- {r.opening_name}: {r.games} games ({r.wins}W-{r.losses}L-{r.draws}D), win rate {r.win_rate:.1%}"
            for r in stats.head(3).itertuples()
        )

    speeds = []
    for speed in ('rapid', 'blitz', 'classical'):
        sub = summary(df[df['speed'] == speed])
        if sub['games']:
            speeds.append(f"{speed.title()}: rating {sub['rating']}, win rate {sub['win_rate']:.1%} ({sub['games']} games)")

    return (
        f"User: {username}\nOverall rating: {s['rating']}\nOverall win rate: {s['win_rate']:.1%}\n"
        f"Total games: {s['games']}\n" + "\n".join(speeds) +
        f"\n\nTOP OPENINGS AS WHITE:\n{top_openings('white')}\n\nTOP OPENINGS AS BLACK:\n{top_openings('black')}"
    )


def player_stats(df, username):
    s = summary(df)
    return {'username': username, 'total_games': s['games'], 'current_rating': s['rating'], 'win_rate': s['win_rate']}
