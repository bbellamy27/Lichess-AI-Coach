import streamlit as st

import coach_ai
import local_coach
import theme
from data_processing import get_opening_stats


def render(df, speed, provider, stats, risk, pacing, time_stats, analysis):
    theme.takeaway("Your personal training plan: strengths, leaks, drills and a 7-day schedule.")
    theme.section("Coaching report")
    if coach_ai.missing_key(provider):
        st.warning(f"Add a {provider} key in the sidebar.")
        return

    # Reports are generated on demand and cached per player / filter / model
    reports = st.session_state.setdefault('coach_reports', {})
    key = (stats['username'], speed, provider, stats['total_games'])
    clicked = st.button("Regenerate" if key in reports else "Generate report", type="primary",
                        icon=":material/auto_awesome:")

    with st.container(border=True, key="report"):
        if clicked:
            openings = get_opening_stats(df)
            white, black = get_opening_stats(df, color="white"), get_opening_stats(df, color="black")
            prof = local_coach.profile(df)
            # 1) At a glance, instantly  2) the AI's analysis (built-in if the AI is down)  3) the training plan
            glance = local_coach.at_a_glance(stats, analysis, time_stats, openings, prof)
            st.markdown(glance)
            prompt = coach_ai.report_prompt(stats, risk, pacing, time_stats, analysis, white, black, prof)
            backup = local_coach.analysis_sections(stats, risk, pacing, analysis, time_stats, openings, prof)
            written = st.write_stream(coach_ai.stream(provider, [{"role": "user", "content": prompt}], fallback=backup))
            plan = local_coach.plan_sections(stats, risk, df, analysis, time_stats, openings, white, black)
            planned = st.write_stream(coach_ai.stream(coach_ai.OFFLINE, [], fallback=plan))
            reports[key] = "\n\n".join([glance, written, planned])
            st.rerun()  # redraw with the Regenerate label
        elif key in reports:
            st.markdown(reports[key])
        else:
            st.caption("A full report with a week of training. Works offline too.")
