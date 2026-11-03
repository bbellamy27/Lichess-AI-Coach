import pandas as pd
import streamlit as st

import coach_ai
import grades
import theme
from local_engine import LocalEngine


RESULT_ICONS = {'Win': '✓ Win', 'Loss': '✕ Loss', 'Draw': '= Draw'}
SIDE_ICONS = {'white': '♔', 'black': '♚'}
RESULT_TONE = {'Win': grades.GOOD, 'Loss': grades.BAD, 'Draw': grades.NEUTRAL}


def _color(grade):
    return f"color: {theme.TONE[grade]}; font-weight: 600" if grade != grades.NEUTRAL else ""


def _acpl_color(value):
    return "" if value in ("—", None) else _color(grades.grade('acpl', float(value)))


def _opponent(row):
    name = row['black_user'] if row['user_color'] == 'white' else row['white_user']
    rating = row['opponent_rating']
    return f"{SIDE_ICONS.get(row['user_color'], '')} {name}" + ("" if pd.isna(rating) else f" · {int(rating)}")


def render(df, opening_stats, provider, db):
    counts = df['result'].value_counts()
    theme.takeaway(f"{len(df)} games · {counts.get('Win', 0)} wins · {counts.get('Loss', 0)} losses. "
                   "Tick one for an AI review.")
    theme.section("♟️ Games")
    table = pd.DataFrame({
        'Result': df['result'].map(RESULT_ICONS) + " · " + df['speed'].fillna('').str.title(),
        'Opponent': df.apply(_opponent, axis=1),
        'Opening': df['opening_name'].fillna("—"),
        'ACPL': pd.to_numeric(df.get('acpl', pd.Series(index=df.index)), errors='coerce')
                  .map(lambda v: "—" if pd.isna(v) else f"{v:.0f}"),
        'Date': df['date'],
        'Link': "https://lichess.org/" + df['game_id'].astype(str),
    })
    styled = (table.style
              .apply(lambda col: [_color(RESULT_TONE[r]) for r in df['result']], subset=['Result'])
              .map(_acpl_color, subset=['ACPL']))
    event = st.dataframe(
        styled, hide_index=True, width="stretch", height=420,
        on_select="rerun", selection_mode="multi-row", key="games_table",
        column_config={
            'Result': st.column_config.TextColumn(width=110),
            'Opponent': st.column_config.TextColumn(width=160, help="♔ you had White · ♚ you had Black · opponent rating"),
            'Opening': st.column_config.TextColumn(width=240),
            'ACPL': st.column_config.TextColumn(width=50, help="Accuracy loss: value given away per move. Lower is better."),
            'Date': st.column_config.DatetimeColumn(width=62, format="MMM D"),
            'Link': st.column_config.LinkColumn(width=54, display_text="Open ↗"),
        },
    )
    selected = df.iloc[event.selection.rows]['game_id'].tolist()
    if selected:
        c1, c2 = st.columns([1, 1])
        if c1.button(f"Review {len(selected)}", type="primary",
                     icon=":material/neurology:", width="stretch"):
            _review_games(df, selected, provider)
        with c2.popover("Save", icon=":material/bookmark_add:", width="stretch"):
            _save_to_study(db, df, selected)

    theme.section("📖 Openings", "Your first moves and win rates.")
    if opening_stats.empty:
        st.info("No openings yet.")
        return
    openings = opening_stats[['opening_name', 'eco', 'games', 'wins', 'draws', 'losses', 'win_rate']].fillna({'eco': "—"})
    win_colors = [_color(grades.win_rate_grade(r.win_rate, r.games)) for r in openings.itertuples()]
    styled = openings.style.format({'win_rate': '{:.0%}'}).apply(lambda col: win_colors, subset=['win_rate'])
    st.dataframe(
        styled,
        hide_index=True, width="stretch", height=min(38 + 35 * len(opening_stats), 460),
        column_config={
            'opening_name': st.column_config.TextColumn("Opening", width=280),
            'eco': st.column_config.TextColumn("ECO", width=56, help="Standard opening code"),
            'games': st.column_config.NumberColumn("Games", width=64),
            'wins': st.column_config.NumberColumn("W", width=44),
            'draws': st.column_config.NumberColumn("D", width=44),
            'losses': st.column_config.NumberColumn("L", width=44),
            'win_rate': st.column_config.Column("Win rate", width=90, help="Coloured once an opening has 5+ games"),
        },
    )


def _save_to_study(db, df, game_ids):
    if not db.connected:
        st.warning("Database not connected.")
        return
    from DataBases.chess_parser import OptimizedPGNParser

    studies = db.get_studies()
    choice = st.selectbox("Study", ["New study…"] + [s['name'] for s in studies])
    name = st.text_input("Name") if choice == "New study…" else choice
    if not st.button("Save", type="primary", disabled=not name):
        return
    study_id = (db.create_study(name) if choice == "New study…"
                else next(s['_id'] for s in studies if s['name'] == choice))
    parser, added = OptimizedPGNParser(db), []
    for _, row in df[df['game_id'].isin(game_ids)].iterrows():
        pgn = "\n".join([
            '[Event "Lichess Game"]', f'[Site "https://lichess.org/{row["game_id"]}"]',
            f'[Date "{row["date"]:%Y.%m.%d}"]', f'[White "{row["white_user"]}"]', f'[Black "{row["black_user"]}"]',
            f'[Result "{row["result"]}"]', f'[WhiteElo "{row["white_rating"]}"]', f'[BlackElo "{row["black_rating"]}"]',
            f'[ECO "{row.get("eco") or "?"}"]', f'[Opening "{row["opening_name"]}"]', f'[TimeControl "{row["speed"]}"]',
            "", row['moves'], "",
        ])
        game = parser.parse_game(pgn)
        if game:
            added.append(db.insert_game(game).inserted_id)
    if added:
        st.success(f"Saved {db.add_games_to_study(study_id, added)} games to {name}.")
    else:
        st.warning("No games could be saved.")


def _review_games(df, game_ids, provider):
    """Analyse each game locally with Stockfish, then ask the AI for a short review."""
    engine = LocalEngine()
    raw = {g['id']: g for g in st.session_state.get('raw_games', []) if 'id' in g}
    full = st.session_state['game_data']
    bar = st.progress(0.0)
    for n, game_id in enumerate(game_ids, start=1):
        row = df[df['game_id'] == game_id].iloc[0]
        bar.progress((n - 1) / len(game_ids), f"Analysing game {n} of {len(game_ids)}…")
        if not row.get('moves'):
            continue
        try:
            result = engine.analyze_game(row['moves'].split())
            my_acpl = int(result[f"{row['user_color']}_acpl"])
            full.loc[full['game_id'] == game_id, 'acpl'] = my_acpl

            if game_id in raw:
                g = raw[game_id]
                g['analysis'] = result.get('analysis', [])
                for color in ('white', 'black'):
                    g['players'][color].setdefault('analysis', {})['acpl'] = int(result[f'{color}_acpl'])

            times = len(df[(df['opening_name'] == row['opening_name']) & (df['user_color'] == row['user_color'])])
            review = coach_ai.get_client(provider).chat(
                [{"role": "user", "content": coach_ai.game_review_prompt(row, my_acpl, times)}])
            st.session_state.setdefault('messages', []).append(
                {"role": "assistant", "content": f"**Game review: {row['opening_name']}**\n\n{review}"})
        except Exception as e:
            st.error(f"Couldn't analyse game {game_id}: {e}")
    bar.empty()
    st.session_state['game_data'] = full
    st.session_state['coach_reports'] = {}
    st.session_state['stats_cache'] = {}
    st.toast("Review ready in the coach chat", icon="🧠")
    st.rerun()
