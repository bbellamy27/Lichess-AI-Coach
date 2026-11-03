from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

st.set_page_config(page_title="Gambit AI · Personal chess coach",
                   page_icon=str(Path(__file__).parent / "assets" / "favicon.png"),
                   layout="wide", initial_sidebar_state="auto")
load_dotenv()

import dataset  # noqa: E402
import grades  # noqa: E402  (imports below need page config set first)
import theme  # noqa: E402
from coach_ai import opening_perspective  # noqa: E402
from data_processing import (calculate_analysis_metrics, calculate_pacing_metrics, calculate_risk_metrics,  # noqa: E402
                             calculate_time_stats, get_opening_stats)
from DataBases.chess_database import ChessDatabaseManager  # noqa: E402
from DataBases.portable_database import PortableDatabaseManager  # noqa: E402
from views import coach, games, insights, overview, performance, sidebar, vault  # noqa: E402


@st.cache_resource
def get_db():
    """MongoDB if it's running locally, otherwise the bundled SQLite database."""
    try:
        mongo = ChessDatabaseManager()
        if mongo.connected:
            return mongo
    except Exception as e:
        print(f"MongoDB unavailable: {e}")
    return PortableDatabaseManager()


def best_opening_kpi(df, color):
    best = dataset.best_opening(df, color)
    if best is None:
        return dict(label=f"Best as {color.title()}", value="—", wide=True)
    theirs = opening_perspective(color, best['opening_name']) == "opponent_choice"
    n = int(best['games'])
    return dict(label=f"Best as {color.title()}" + (" (vs.)" if theirs else ""), value=best['opening_name'],
                foot=f"<b>{best['win_rate']:.0%}</b> · {n} game{'s' * (n != 1)}", wide=True)


theme.inject_css()
db = get_db()
provider = sidebar.render(db)

if 'game_data' not in st.session_state:
    theme.empty_state()
    if dataset.demo_available():
        _, mid, _ = st.columns([1, 1, 1])
        if mid.button("Try the demo", type="primary", icon=":material/play_arrow:", width="stretch"):
            dataset.load_demo()
            st.rerun()
    theme.empty_steps()
    st.stop()

username = st.session_state['username']
all_games = dataset.ensure_columns(st.session_state['game_data'])
speed = st.segmented_control("Time control", dataset.SPEEDS, default="Overall", key="speed",
                             label_visibility="collapsed") or "Overall"
df, raw_games = dataset.filter_speed(all_games, st.session_state.get('raw_games', []), speed)
s = dataset.summary(all_games)

theme.hero(
    f"{speed} · {len(all_games)} games", theme.esc(username),
    chips=[f"<b>{s['wins']}</b>W · <b>{s['draws']}</b>D · <b>{s['losses']}</b>L",
           f"Since <b>{all_games['date'].min():%b %d}</b>"],
)

if df.empty:
    st.info(f"No {speed.lower()} games here.")
    st.stop()

fs = dataset.summary(df)
theme.kpis([
    dict(label="Games", value=fs['games']),
    dict(label="Rating", value=fs['rating'], delta=fs['rating_change'], foot="1200 casual · 2000 strong"),
    dict(label="Win rate", value=f"{fs['win_rate']:.0%}", grade=grades.grade('win_rate', fs['win_rate']),
         foot=grades.hint('win_rate')),
    best_opening_kpi(df, 'white'),
    best_opening_kpi(df, 'black'),
])

def compute_stats():
    pacing = calculate_pacing_metrics(df, speed)
    return dict(
        opening_stats=get_opening_stats(df),
        risk=calculate_risk_metrics(df),
        pacing=pacing,
        analysis=calculate_analysis_metrics(raw_games, username, pacing_label=pacing['label']) if raw_games else None,
        time_stats=(calculate_time_stats(raw_games, username, time_control=speed, pacing_label=pacing['label'])
                    if raw_games else None),
    )


stats = dataset.cached(speed, compute_stats)
opening_stats, risk, pacing, analysis, time_stats = (
    stats[k] for k in ('opening_stats', 'risk', 'pacing', 'analysis', 'time_stats'))

theme.glossary()
tab_home, tab_games, tab_perf, tab_insights, tab_coach, tab_vault = st.tabs(
    ["🏠 Overview", "♟️ Games", "📊 Performance", "🧠 Insights", "🤖 AI Coach", "🗄️ Vault"])
with tab_home:
    overview.render(df, fs, risk, pacing, analysis, time_stats)
with tab_games:
    games.render(df, opening_stats, provider, db)
with tab_perf:
    performance.render(df, opening_stats, risk, pacing, analysis, time_stats)
with tab_insights:
    insights.render(df, risk, pacing, analysis, time_stats)
with tab_coach:
    coach.render(df, speed, provider, dataset.player_stats(df, username), risk, pacing, time_stats, analysis)
with tab_vault:
    vault.render(db)
