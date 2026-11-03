"""First tab: the story in plain English, so non-chess players get it in seconds."""
import streamlit as st

import grades
import theme

PART_OF_DAY = [(5, "🌅 Early bird", "morning"), (12, "☀️ Day player", "afternoon"),
               (18, "🌆 Evening player", "evening"), (22, "🦉 Night owl", "late night")]


def _part_of_day(hour):
    for start, label, when in reversed(PART_OF_DAY):
        if hour >= start:
            return label, when
    return PART_OF_DAY[-1][1:]  # 0-4am counts as late night


def _badges(df, summary):
    """Small, fun achievements computed from the games."""
    games = df.sort_values('date')
    badges = []

    streak = best = 0
    for result in games['result']:
        streak = streak + 1 if result == 'Win' else 0
        best = max(best, streak)
    if best >= 3:
        badges.append(("🔥", f"{best}-game win streak", "Longest run of wins in a row"))

    upsets = int(((games['result'] == 'Win') & (games['opponent_rating'] > games['user_rating'] + 100)).sum())
    if upsets:
        badges.append(("⚔️", f"Giant slayer ×{upsets}", "Wins against opponents rated 100+ higher"))

    if summary['rating_change'] and summary['rating_change'] > 0:
        badges.append(("📈", f"Climbing +{summary['rating_change']}", "Rating gained over these games"))

    family = games['opening_name'].dropna().str.split(':').str[0].value_counts()
    if not family.empty:
        badges.append(("📖", f"Loves the {family.index[0]}", f"Played in {family.iloc[0]} games"))

    label, when = _part_of_day(int(games['hour'].mode().iloc[0]))
    badges.append((label.split()[0], " ".join(label.split()[1:]), f"Plays most often in the {when}"))
    return badges[:5]


def render(df, summary, risk, pacing, analysis, time_stats):
    score, letter = grades.gambit_score(summary['win_rate'], analysis, time_stats)
    tone = theme.TONE[grades.GOOD if score >= 70 else grades.OK if score >= 55 else grades.BAD]
    (good_grade, strength), (bad_grade, leak) = grades.findings(summary['win_rate'], analysis)
    style = f"{theme.plain(pacing['label'])} · {theme.plain(risk['label'])}"

    theme.takeaway(f"Gambit Score {letter}: {strength.lower()}, but {leak[0].lower() + leak[1:]}."
                   if bad_grade == grades.BAD else f"Gambit Score {letter}: {strength.lower()}.")

    theme.story_cards(
        score=score, letter=letter, tone=tone, style=style,
        strength=strength, strength_tone=theme.TONE[good_grade],
        leak=leak, leak_tone=theme.TONE[bad_grade],
    )

    theme.section("Badges")
    theme.badges(_badges(df, summary))

    st.write("")
    theme.glossary()
