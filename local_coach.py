"""Built-in coach: writes the full coaching report and training plan from the graded stats (no internet needed)."""
import grades
from coach_ai import opening_perspective
from theme import plain

# Detailed drill for each weakness: name, why it helps, steps, how to measure, daily focus label
DRILLS = {
    'blunder_rate': dict(
        name="Blunder-check routine",
        why="Big mistakes decide most club games; cutting them is the fastest way to gain rating.",
        steps=["Before every move, ask: what does my opponent's last move threaten?",
               "Check all checks, captures and threats for both sides.",
               "Do 15 Lichess Puzzles a day, solving each fully before moving a piece.",
               "In each game review, mark every move that lost 3+ pawns and write why it happened."],
        measure="Blunders under {target}% of moves in your next 20 analysed games.",
        focus="Tactics"),
    'acpl': dict(
        name="Slow, accurate calculation",
        why="Your average accuracy loss shows value slipping away move by move, not just in blunders.",
        steps=["Play 3 longer games this week (15+10 or slower).",
               "On every non-obvious move, list two candidate moves and compare them.",
               "After each game, run the Lichess Analysis board and study the 3 biggest evaluation drops.",
               "Rewrite each of those moments as a 'what I should have played and why' note."],
        measure="Accuracy loss (ACPL) at or below {target} in longer games.",
        focus="Calculation"),
    'mistake_rate': dict(
        name="Candidate-move training",
        why="Medium mistakes come from picking the first decent move instead of the best one.",
        steps=["Set up 5 middlegame positions from your own games on the Analysis board.",
               "For each, write down three candidate moves before calculating.",
               "Compare your choice with the engine's and note the idea you missed."],
        measure="Mistakes under {target}% of moves.",
        focus="Calculation"),
    'win_rate': dict(
        name="Converting good positions",
        why="Turning better positions into wins is where results improve most.",
        steps=["Review your last 5 losses and find the move where the game turned.",
               "Practise winning endgames from Lichess Practice (basic and rook endgames).",
               "When ahead, trade pieces, not pawns, and avoid unnecessary risks."],
        measure="Win rate up 5 points over your next 50 games.",
        focus="Conversion"),
    'time': dict(
        name="Clock discipline",
        why="Time spent in the wrong phase leads to rushed or flagged positions later.",
        steps=["Play 5 games aiming for at least 10 seconds on every move from 5 to 15.",
               "Play simple recaptures and forced moves quickly to bank time.",
               "Review the clock in each game and mark where you were too fast or too slow."],
        measure="All three game stages 'On Target' on the Performance step.",
        focus="Time use"),
    'opening': dict(
        name="Repair a weak opening",
        why="An opening with a low win rate keeps handing your opponents easy games.",
        steps=["Open a Lichess Study for that opening and add the main line to move 10.",
               "Write one sentence on the plan for each side after the opening.",
               "Play it in 3 practice games, then review where you left the main line."],
        measure="That opening's win rate back above 45%.",
        focus="Openings"),
    'phase': dict(
        name="Weakest-phase workout",
        why="One stage of your game is clearly behind the others.",
        steps=["Middlegame: 20 minutes of themed puzzles (forks, pins, attacking the king).",
               "Endgame: Lichess Practice endgames until you can win them twice in a row.",
               "Opening: review the first 10 moves of your last 5 games against the main lines."],
        measure="That phase scoring 6/10 or better.",
        focus="Weak phase"),
}


def _weaknesses(stats, analysis, time_stats, opening_stats):
    """Ranked list of (severity, key, detail); higher severity = more urgent."""
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
            found.append((1.8, 'phase', phase))  # a clearly weak stage outranks clock habits
    return sorted(found, key=lambda t: -t[0])


def _strengths(stats, analysis, time_stats, opening_stats):
    out = []
    if grades.grade('win_rate', stats['win_rate']) != grades.BAD:
        out.append(f"**Results:** you win {stats['win_rate']:.0%} of your games, "
                   f"{'well above' if stats['win_rate'] >= 0.55 else 'around'} the 50% expected against equal opponents.")
    if analysis and analysis.get('phases'):
        phase, data = max(analysis['phases'].items(), key=lambda kv: kv[1].get('score', 0))
        out.append(f"**{phase}:** your best stage, scoring {data.get('score')}/10 "
                   f"with {data.get('accuracy_percent')}% accuracy.")
    if opening_stats is not None and not opening_stats.empty:
        good = opening_stats[opening_stats['games'] >= 5].sort_values('win_rate', ascending=False)
        if not good.empty:
            best = good.iloc[0]
            out.append(f"**Opening weapon:** the {best['opening_name']} scores {best['win_rate']:.0%} "
                       f"over {int(best['games'])} games.")
    if time_stats:
        on = [p for p in ('opening', 'middlegame', 'endgame') if time_stats[f'{p}_feedback'].startswith("On Target")]
        if on:
            out.append(f"**Clock:** your pace is on target in the {', '.join(on)}.")
    return out[:3] or ["**Experience:** you have a solid base of games to learn from."]


def _phase_paragraphs(analysis, time_stats):
    paras = []
    phases = (analysis or {}).get('phases', {})
    for phase in ("Opening", "Middlegame", "Endgame"):
        data = phases.get(phase)
        tempo = ""
        if time_stats:
            tempo = (f" You spend {time_stats[f'{phase.lower()}_avg']}s per move here "
                     f"({time_stats[f'{phase.lower()}_feedback'].split('. ')[0].lower()}).")
        if data:
            score = data.get('score', 0)
            verdict = "a real strength" if score >= 8 else "solid but improvable" if score >= 5 else "where most points leak"
            paras.append(f"**{phase}** ({score}/10, {verdict}): accuracy {data.get('accuracy_percent')}% with "
                         f"big mistakes on {data.get('blunder_rate')}% of moves.{tempo} {data.get('advice', '')}")
        elif tempo:
            paras.append(f"**{phase}:**{tempo}")
    if time_stats:
        off = [p for p in ('opening', 'middlegame', 'endgame') if not time_stats[f'{p}_feedback'].startswith("On Target")]
        paras.append("**Time management:** " + (
            f"your pace is off target in the {', '.join(off)}, which leads to rushed decisions or time trouble later."
            if off else "your clock use is on target in every stage of the game."))
    return paras or ["Run **Review** on a few games in the Games step to unlock a phase-by-phase breakdown."]


def _plan(fixes):
    """7-day plan cycling through the top weaknesses, with play and review days."""
    picks = [(k, d) for _, k, d in fixes] or [('blunder_rate', None)]

    def slot(i):
        key, detail = picks[i % len(picks)]
        steps = DRILLS[key]['steps']
        # For the weak-phase drill, use the step written for that phase
        step = next((s for s in steps if isinstance(detail, str) and s.startswith(detail)), steps[0])
        return DRILLS[key]['focus'], step

    rows = [
        ("Mon", *slot(0), "30 min"),
        ("Tue", "Endgames", "Lichess Practice: basic and rook endgames", "25 min"),
        ("Wed", *slot(1), "30 min"),
        ("Thu", "Openings", "Review the first 10 moves of your last 5 games", "20 min"),
        ("Fri", "Play", "3 longer games (15+10), using your blunder-check routine", "45 min"),
        ("Sat", *slot(2), "30 min"),
        ("Sun", "Review", "Analyse Friday's games and update your notes", "30 min"),
    ]
    table = ["| Day | Focus | What to do | Time |", "|---|---|---|---|"]
    table += [f"| {d} | {f} | {w} | {t} |" for d, f, w, t in rows]
    return table


def _repertoire(white_stats, black_stats):
    lines = []
    for color, table in (("White", white_stats), ("Black", black_stats)):
        if table is None or table.empty:
            continue
        solid = table[table['games'] >= 5]

        def phrase(names, mine, theirs):
            # Openings the opponent chose are "faced", not part of your repertoire
            own = [n for n in names if opening_perspective(color.lower(), n) == "my_choice"]
            faced = [n for n in names if n not in own]
            out = [f"{mine} the {' and '.join(own)}"] if own else []
            out += [f"{theirs} the {' and '.join(faced)}"] if faced else []
            return out

        parts = phrase(solid[solid['win_rate'] >= 0.55]['opening_name'].head(2).tolist(),
                       "keep playing", "you score well against")
        parts += phrase(solid[solid['win_rate'] < 0.45]['opening_name'].head(2).tolist(),
                        "fix or replace", "prepare a better answer to")
        if not parts:
            parts.append("play more games in your main lines to build a reliable sample")
        lines.append(f"- **As {color}:** {'; '.join(parts)}.")
    return lines or ["- Play more games to build up opening data."]


def _targets(stats, analysis):
    rows = [f"- **Win rate:** {stats['win_rate']:.0%} today → aim for {min(stats['win_rate'] + 0.05, 0.95):.0%}."]
    if analysis:
        rows.append(f"- **Big mistakes:** {analysis['blunder_rate']}% of moves → aim for "
                    f"{max(1.0, round(analysis['blunder_rate'] * 0.7, 1))}%.")
        rows.append(f"- **Accuracy loss (ACPL):** {analysis['avg_acpl']} → aim for "
                    f"{max(20, round(analysis['avg_acpl'] - 10))}.")
    return rows


def _fixes(stats, analysis, time_stats, opening_stats):
    weak = _weaknesses(stats, analysis, time_stats, opening_stats)
    defaults = [(0, k, None) for k in ('blunder_rate', 'acpl', 'win_rate') if k not in {w[1] for w in weak}]
    return (weak + defaults)[:3]


def analysis_sections(stats, risk, pacing, analysis=None, time_stats=None, opening_stats=None):
    """Summary, strengths, where points are lost, and the one thing (the part the AI writes when online)."""
    fixes = _fixes(stats, analysis, time_stats, opening_stats)
    top_key, top_detail = fixes[0][1], fixes[0][2]
    risk_word = plain(risk['label']).lower()
    article = "an" if risk_word[:1] in "aeiou" else "a"
    lines = [
        "## Summary",
        f"You're a {stats['current_rating']}-rated {plain(pacing['label']).lower()} with {article} {risk_word} "
        f"streak, winning {stats['win_rate']:.0%} of {stats['total_games']} games. "
        f"Your biggest opportunity is **{DRILLS[top_key]['name'].lower()}**: fix that and the rating points follow.",
        "", "## Strengths", *[f"- {s}" for s in _strengths(stats, analysis, time_stats, opening_stats)],
        "", "## Where you lose points", *[p + "\n" for p in _phase_paragraphs(analysis, time_stats)],
        "## The one thing",
        f"**{DRILLS[top_key]['name']}.** {DRILLS[top_key]['why']}"
        + (f" (Here: {top_detail}.)" if isinstance(top_detail, str) else ""),
    ]
    return "\n".join(lines)


def plan_sections(stats, analysis=None, time_stats=None, opening_stats=None, white_stats=None, black_stats=None):
    """7-day plan, drills, opening advice and targets: always built from the data."""
    fixes = _fixes(stats, analysis, time_stats, opening_stats)
    lines = ["## 7-day training plan", *_plan(fixes), "", "## Drills"]
    for _, key, value in fixes:
        d = DRILLS[key]
        target = (max(1.0, round(value * 0.7, 1)) if key == 'blunder_rate'
                  else max(20, round(value - 10)) if key == 'acpl'
                  else 5 if key == 'mistake_rate' else "")
        lines += [f"**{d['name']}**: {d['why']}", *[f"{i}. {s}" for i, s in enumerate(d['steps'], 1)],
                  "", f"*Measure it:* {d['measure'].format(target=target)}", ""]
    lines += ["## Opening repertoire", *_repertoire(white_stats, black_stats),
              "", "## Targets for next month", *_targets(stats, analysis)]
    return "\n".join(lines)


def report(stats, risk, pacing, analysis=None, time_stats=None, opening_stats=None, white_stats=None, black_stats=None):
    """Full markdown report: analysis followed by the training plan."""
    return (analysis_sections(stats, risk, pacing, analysis, time_stats, opening_stats) + "\n\n"
            + plan_sections(stats, analysis, time_stats, opening_stats, white_stats, black_stats))
