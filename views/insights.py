import streamlit as st

import theme
from eda import (plot_correlation_heatmap, plot_move_time_distribution, plot_repertoire, plot_opponent_scatter,
                 plot_radar_chart, plot_termination_pie, plot_time_heatmap)


def _personality(risk, pacing, analysis):
    """Five 0-10 traits; neutral 5 where data is missing."""
    phases = (analysis or {}).get('phases', {})
    accuracy = max(0, min(10, 10 - analysis['avg_acpl'] / 10)) if analysis else 5
    return {
        'categories': ['Aggression', 'Speed', 'Accuracy', 'Opening prep', 'Endgame skill'],
        'values': [risk['score'], pacing['score'], accuracy,
                   phases.get('Opening', {}).get('score', 5), phases.get('Endgame', {}).get('score', 5)],
    }


def _chart(col, fig, fallback):
    if fig:
        theme.chart(fig, col)
    else:
        col.info(fallback)


def render(df, risk, pacing, analysis, time_stats):
    theme.section("Style profile")
    c1, c2 = st.columns(2)
    _chart(c1, plot_radar_chart(_personality(risk, pacing, analysis)), "Not enough data.")
    _chart(c2, plot_move_time_distribution((time_stats or {}).get('raw_times')), "No clock data.")

    theme.section("Repertoire")
    st.caption("Your most played openings, with win rate.")
    c1, c2 = st.columns(2)
    _chart(c1, plot_repertoire(df, 'white'), "No games as White.")
    _chart(c2, plot_repertoire(df, 'black'), "No games as Black.")

    theme.section("Patterns")
    c1, c2 = st.columns(2)
    _chart(c1, plot_time_heatmap(df), "No activity data.")
    _chart(c2, plot_opponent_scatter(df), "No opponent data.")
    c1, c2 = st.columns(2)
    _chart(c1, plot_termination_pie(df), "No termination data.")
    _chart(c2, plot_correlation_heatmap(df), "Not enough data.")
