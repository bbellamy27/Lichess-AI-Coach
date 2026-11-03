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
            plan = local_coach.plan_sections(stats, analysis, time_stats, openings, white, black)
            full_backup = (local_coach.analysis_sections(stats, risk, pacing, analysis, time_stats, openings)
                           + "\n\n" + plan)
            # The AI writes the analysis; the training plan is always built from the data and added after it
            prompt = coach_ai.report_prompt(stats, risk, pacing, time_stats, analysis, white, black)
            text = st.write_stream(coach_ai.stream(provider, [{"role": "user", "content": prompt}],
                                                   fallback=full_backup))
            if not text.startswith(coach_ai.FALLBACK_NOTE):
                text += "\n\n" + st.write_stream(coach_ai.stream(coach_ai.OFFLINE, [], fallback=plan))
            reports[key] = text
            st.rerun()  # redraw with the Regenerate label
        elif key in reports:
            st.markdown(reports[key])
        else:
            st.caption("A full report with a week of training. Works offline too.")
