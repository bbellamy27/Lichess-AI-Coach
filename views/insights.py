import streamlit as st

import grades
import local_coach
import theme
from eda import (plot_correlation_heatmap, plot_move_time_distribution, plot_repertoire, plot_opponent_scatter,
                 plot_radar_chart, plot_termination_pie, plot_time_heatmap)


def _chart(col, fig, fallback):
    if fig:
        theme.chart(fig, col)
    else:
        col.info(fallback)


def render(df, risk, pacing, analysis, time_stats):
    family = df['opening_name'].dropna().str.split(':').str[0].value_counts()
    favourite = f" Favourite opening: {family.index[0]}." if not family.empty else ""
    style = theme.plain(risk['label']).lower()
    article = "an" if style[:1] in "aeiou" else "a"
    theme.takeaway(f"You play like a {theme.plain(pacing['label'])} with {article} {style} style.{favourite}")
    prof = local_coach.profile(df)
    rating = int(df.sort_values('date')['user_rating'].iloc[-1])
    band = f"Typical {rating // 100 * 100} {prof['speed']} player"
    analysed = (analysis or {}).get('games_analyzed', 0)
    theme.section("Skills", "Higher is better on every axis.")
    c1, c2 = st.columns([1.35, 1])
    _chart(c1, plot_radar_chart(grades.skills(analysis, prof, prof['speed']), grades.typical_skills(rating), band),
           "Not enough data.")
    with c2:
        theme.style_sliders([
            ("Solid", "Aggressive", risk['score'], f"Risk-taking {risk['score']}/10: {theme.plain(risk['label'])}"),
            ("Quick finishes", "Long grinds", pacing['score'],
             f"Average game {pacing['avg_moves']} moves: {theme.plain(pacing['label'])}"),
        ])
    st.caption(f"Based on {len(df)} games, {analysed} with engine analysis. "
               "Tactics and accuracy are adjusted for game speed.")

    theme.section("Time per move", "How long you think, move by move.")
    _chart(st, plot_move_time_distribution((time_stats or {}).get('raw_times')), "No clock data.")

    theme.section("Repertoire", "Wins and losses by opening.")
    c1, c2 = st.columns(2)
    _chart(c1, plot_repertoire(df, 'white'), "No games as White.")
    _chart(c2, plot_repertoire(df, 'black'), "No games as Black.")

    theme.section("Patterns", "When you play and who you beat.")
    c1, c2 = st.columns(2)
    _chart(c1, plot_time_heatmap(df), "No activity data.")
    _chart(c2, plot_opponent_scatter(df), "No opponent data.")
    c1, c2 = st.columns(2)
    _chart(c1, plot_termination_pie(df), "No termination data.")
    _chart(c2, plot_correlation_heatmap(df), "Not enough data.")
