import plotly.graph_objects as go
import streamlit as st

import grades
import theme
from eda import plot_rating_trend, plot_top_openings, plot_win_rate_by_color, plot_win_rate_by_opening
from theme import COLORS


def _gauge(risk):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=risk['score'],
        number=dict(font=dict(family=theme.DISPLAY, size=44, color=COLORS['text']), valueformat='.1f'),
        gauge=dict(
            axis=dict(range=[0, 10], tickcolor=COLORS['muted'], tickwidth=1),
            bar=dict(color=COLORS['text'], thickness=0.18),
            bgcolor='rgba(0,0,0,0)', borderwidth=0,
            steps=[dict(range=[0, 3], color='rgba(74,222,128,0.38)'),
                   dict(range=[3, 7], color='rgba(242,184,75,0.38)'),
                   dict(range=[7, 10], color='rgba(242,113,110,0.40)')],
        ),
    ))
    fig.update_layout(title=f"Risk-taking · {theme.plain(risk['label'])}", height=272, margin=dict(l=32, r=32, t=56, b=12))
    return fig


def render(df, opening_stats, risk, pacing, analysis, time_stats):
    win_rate = (df['result'] == 'Win').mean()
    (_, strength), (leak_grade, leak) = grades.findings(win_rate, analysis)
    theme.takeaway(f"Biggest leak: {leak[0].lower() + leak[1:]}." if leak_grade == grades.BAD
                   else f"Strongest area: {strength[0].lower() + strength[1:]}.")
    theme.section("🧭 Style", "Risk and speed.")
    c1, c2, c3 = st.columns([1.1, 1, 1.6])
    with c1:
        theme.chart(_gauge(risk))
    with c2:
        st.markdown(f"""<div class="card" style="text-align:center; display:flex; flex-direction:column; justify-content:center; min-height:272px;">
<div class="card-label">Pace</div>
<div style="font-family:var(--display); font-size:1.7rem; font-weight:800; color:{pacing['color']}; letter-spacing:-0.02em; line-height:1.15; margin:10px 0 14px;">{theme.esc(theme.plain(pacing['label']))}</div>
<div class="chip" style="margin:0 auto;">Avg <b>{pacing['avg_moves']}</b> moves</div>
</div>""", unsafe_allow_html=True)
    with c3:
        theme.insight(theme.ICONS["risk"], "Risk", risk['improvement'])
        theme.insight(theme.ICONS["pace"], "Pace", pacing['improvement'])
        with st.expander("Why?"):
            st.caption(risk['feedback'])
            st.caption(pacing['feedback'])

    theme.section("🎯 Accuracy", "Checked by a chess engine.")
    if analysis:
        theme.grade_legend()

        def graded(label, key, metric=None, suffix=""):
            metric, value = metric or key, analysis[key]
            return dict(label=label, value=f"{value}{suffix}", grade=grades.grade(metric, value),
                        foot=grades.hint(metric))

        theme.kpis([
            graded("Accuracy loss (ACPL)", 'avg_acpl', 'acpl'),
            graded("Big mistakes", 'blunder_rate', suffix="%"),
            graded("Medium mistakes", 'mistake_rate', suffix="%"),
            graded("Small slips", 'inaccuracy_rate', suffix="%"),
        ])
        st.write("")
        for col, phase in zip(st.columns(3), ("Opening", "Middlegame", "Endgame")):
            data = analysis.get('phases', {}).get(phase, {})
            with col:
                theme.score_card(
                    phase, data.get('score', 0),
                    {"Accuracy": f"{data.get('accuracy_percent', 0)}%", "Blunders": f"{data.get('blunder_rate', 0)}%"},
                    note=data.get('advice'),
                )
    else:
        st.info("No engine data yet. Pick games in **Games** → **Review**.", icon=":material/neurology:")

    if time_stats:
        theme.section("⏱️ Time per move", "Seconds per move, by game stage.")
        cards = []
        for label, key in [("Opening", 'opening'), ("Middlegame", 'middlegame'), ("Endgame", 'endgame')]:
            status, _, tip = time_stats[f'{key}_feedback'].partition('. ')
            cards.append(dict(label=label, value=f"{time_stats[f'{key}_avg']}s",
                              grade=grades.time_grade(status), foot=f"{status}. {tip}"))
        theme.kpis(cards)

    theme.section("📈 Trends", "Rating and best openings.")
    c1, c2 = st.columns(2)
    theme.chart(plot_rating_trend(df), c1)
    theme.chart(plot_win_rate_by_color(df), c2)
    c1, c2 = st.columns(2)
    theme.chart(plot_top_openings(df), c1)
    theme.chart(plot_win_rate_by_opening(opening_stats), c2)
