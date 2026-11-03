"""Built-in coach: writes the coaching report from the graded stats, with no internet or AI service needed."""
import grades
from theme import plain

# Drill for each weakness, written for players of any level
DRILLS = {
    'blunder_rate': ("Stop the big mistakes", "Before every move, check what your opponent's last move threatens.",
                     "15 minutes a day of tactics puzzles, solving each one slowly before moving."),
    'mistake_rate': ("Cut the medium mistakes", "Compare two candidate moves before committing in sharp positions.",
                     "Replay 3 recent losses and find the first moment the evaluation dropped."),
    'acpl': ("Play more accurate moves", "Slow down in the middlegame, where most value is lost.",
             "Play 3 longer games (15+10) this week and review each with an engine."),
    'win_rate': ("Turn more games into wins", "Simplify when ahead and avoid risks you don't need.",
                 "Review your last 5 losses and note how each one turned."),
    'time': ("Use your clock better", "Spend more time early and on critical moves, less on obvious ones.",
             "Play 5 games aiming for at least 10 seconds on every move from 5 to 15."),
    'opening': ("Fix a weak opening", "One opening is costing you points.",
                "Study the main ideas of that opening for 20 minutes, then play it in 3 games."),
    'phase': ("Shore up your weakest phase", "One stage of the game is clearly behind the others.",
              "Spend 20 minutes on that stage: puzzles for the middlegame, basic endings for the endgame."),
}


def _weaknesses(stats, analysis, time_stats, opening_stats):
    """Ranked list of (severity, key, detail) where higher severity = more urgent."""
    found = []
    rank = {grades.BAD: 2, grades.OK: 1}
    values = {'win_rate': stats['win_rate']}
    if analysis:
        values.update(blunder_rate=analysis['blunder_rate'], acpl=analysis['avg_acpl'],
                      mistake_rate=analysis['mistake_rate'])
    for key, value in values.items():
        g = grades.grade(key, value)
        if g in rank:
            # Big mistakes first; medium mistakes overlap with accuracy, so they rank lower
            bump = {'blunder_rate': 0.5, 'mistake_rate': -0.6}.get(key, 0)
            found.append((rank[g] + bump, key, value))

    if time_stats:
        off = [p for p in ('opening', 'middlegame', 'endgame')
               if not time_stats[f'{p}_feedback'].startswith("On Target")]
        if off:
            found.append((1 + 0.2 * len(off), 'time', ", ".join(off)))

    if opening_stats is not None and not opening_stats.empty:
        weak = opening_stats[opening_stats['games'] >= 5].sort_values('win_rate')
        if not weak.empty and weak.iloc[0]['win_rate'] < 0.45:
            found.append((1.5, 'opening', weak.iloc[0]['opening_name']))

    if analysis and analysis.get('phases'):
        phase, data = min(analysis['phases'].items(), key=lambda kv: kv[1].get('score', 10))
        if data.get('score', 10) < 5:
            found.append((1.6, 'phase', phase))
    return sorted(found, key=lambda t: -t[0])


def report(stats, risk, pacing, analysis=None, time_stats=None, opening_stats=None):
    """Markdown report in the same format the AI coach uses."""
    rating = stats.get('current_rating')
    (_, strength), _ = grades.findings(stats['win_rate'], analysis)
    risk_word = plain(risk['label']).lower()
    article = "an" if risk_word[:1] in "aeiou" else "a"
    style = f"{plain(pacing['label']).lower()} with {article} {risk_word} streak"
    verdict = f"A {rating}-rated {style}: {strength[0].lower() + strength[1:]}."

    weak = _weaknesses(stats, analysis, time_stats, opening_stats)
    defaults = [(0, k, None) for k in ('blunder_rate', 'acpl', 'win_rate') if k not in {w[1] for w in weak}]
    fixes = (weak + defaults)[:3]

    lines = ["### Verdict", verdict, "", "### Fix these"]
    for i, (_, key, detail) in enumerate(fixes, start=1):
        title, why, _ = DRILLS[key]
        if key == 'opening':
            why = f"The {detail} is costing you points."
        elif key == 'phase':
            why = f"Your {detail.lower()} is your weakest stage."
        lines.append(f"{i}. **{title}**: {why}")
    lines += ["", "### This week", DRILLS[fixes[0][1]][2], "", "### Keep doing", f"{strength}."]
    return "\n".join(lines)
