import streamlit as st

import coach_ai
import local_coach
import theme
from data_processing import get_opening_stats


def render(df, speed, provider, stats, risk, pacing, time_stats, analysis):
    theme.takeaway("Your plan: one verdict, three fixes, one drill.")
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
            prompt = coach_ai.report_prompt(stats, risk, pacing, time_stats, analysis,
                                            get_opening_stats(df, color="white"), get_opening_stats(df, color="black"))
            backup = local_coach.report(stats, risk, pacing, analysis, time_stats, get_opening_stats(df))
            reports[key] = st.write_stream(
                coach_ai.stream(provider, [{"role": "user", "content": prompt}], fallback=backup))
            st.rerun()  # redraw with the Regenerate label
        elif key in reports:
            st.markdown(reports[key])
        else:
            st.caption("Ready in seconds. Works offline too.")
