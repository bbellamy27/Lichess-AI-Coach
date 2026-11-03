"""Built-in coach: a personal training plan built from the player's games (no internet needed).

Everything here is derived from the data: where games are lost, which mistakes happen in which phase,
how the player does against stronger opponents. The AI (when online) writes the narrative analysis;
the profile, tactics, sparring and plan sections below are always produced from the numbers.
"""
import grades
from coach_ai import opening_perspective
from theme import plain

LICHESS = "https://lichess.org/training/"

# Rating milestones and what typically separates a player from the next one
MILESTONES = [
    (1000, "1000", "stop leaving pieces undefended and spot one-move threats"),
    (1200, "1200", "finish development before attacking and avoid needless trades"),
    (1400, "1400", "respect pawn structure and make a plan in quiet positions"),
    (1600, "1600", "know when to attack and when to improve your pieces"),
    (1800, "1800", "calculate 2-3 moves deep calmly and play prophylactic moves"),
    (2000, "2000", "convert rook endgames and stop impulsive moves under time pressure"),
    (2200, "2200 (candidate-master level)", "punish small positional errors and manage the clock in sharp games"),
    (2400, "2400 (master level)", "refine calculation depth and conversion of small advantages"),
    (2600, "2600", "deep opening preparation and flawless technique"),
]

# Lichess puzzle themes: slug -> display name
THEMES = {
    'fork': "Forks", 'pin': "Pins", 'skewer': "Skewers", 'discoveredAttack': "Discovered attacks",
    'hangingPiece': "Hanging pieces", 'mateIn2': "Mate in 2", 'backRankMate': "Back-rank mates",
    'defensiveMove': "Defensive moves", 'quietMove': "Quiet moves", 'sacrifice': "Sacrifices",
    'kingsideAttack': "Kingside attacks", 'rookEndgame': "Rook endgames", 'pawnEndgame': "Pawn endgames",
    'zugzwang': "Zugzwang", 'opening': "Opening tactics", 'trappedPiece': "Trapped pieces",
}

# Drill for each weakness: name, why it helps, steps, how to measure, daily focus label
DRILLS = {
    'blunder_rate': dict(
        name="Blunder-check routine",
        why="Big mistakes decide most games at every level; cutting them is the fastest way to gain rating.",
        steps=["Before every move, ask: what does my opponent's last move threaten?",
               "Check all checks, captures and threats for both sides.",
               "In each game review, mark every move that lost 3+ pawns and write why it happened."],
        measure="Big mistakes under {target}% of moves in your next 20 analysed games.",
        focus="Tactics"),
    'acpl': dict(
        name="Slow, accurate calculation",
        why="Your accuracy loss shows value slipping away move by move, not just in big blunders.",
        steps=["On every non-obvious move, list two candidate moves and compare them.",
               "After each game, open the Lichess Analysis board and study the 3 biggest evaluation drops.",
               "Rewrite each of those moments as a 'what I should have played and why' note."],
        measure="Accuracy loss (ACPL) at or below {target} in longer games.",
        focus="Calculation"),
    'mistake_rate': dict(
        name="Candidate-move training",
        why="Medium mistakes come from picking the first decent move instead of the best one.",
        steps=["Set up 5 middlegame positions from your own games on the Analysis board.",
               "Write down three candidate moves before calculating any of them.",
               "Compare your choice with the engine's and note the idea you missed."],
        measure="Medium mistakes under {target}% of moves.",
        focus="Calculation"),
    'win_rate': dict(
        name="Converting good positions",
        why="Turning better positions into wins is where results improve most.",
        steps=["Review your last 5 losses and find the move where the game turned.",
               "Practise winning endgames in Lichess Practice (basic and rook endgames).",
               "When ahead, trade pieces, not pawns, and avoid unnecessary risks."],
        measure="Win rate up 5 points over your next 50 games.",
        focus="Conversion"),
    'time': dict(
        name="Clock discipline",
        why="Losing on time throws away positions you have already played well.",
        steps=["Play your normal games with increment (e.g. 3+2 instead of 3+0) for two weeks.",
               "Play forced moves and simple recaptures instantly to bank time.",
               "Set a personal rule: when under 30 seconds, play safe, simple moves only."],
        measure="No more than 1 loss on time in your next 20 games.",
        focus="Clock"),
    'level_up': dict(
        name="Beat players at your level",
        why="Your results come mostly from weaker opponents; rating rises by beating equals and stronger players.",
        steps=["Play sparring games against opponents 100-200 points above you (see the sparring plan).",
               "Choose solid openings you know, not tricks that only work against weaker players.",
               "After each sparring loss, find the first moment the stronger player took over."],
        measure="Score 45%+ against opponents rated within 100 points of you.",
        focus="Sparring"),
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
        steps=["Middlegame: 20 minutes of themed tactics (see Tactics to train).",
               "Endgame: Lichess Practice endgames until you can win each one twice in a row.",
               "Opening: review the first 10 moves of your last 5 games against the main lines."],
        measure="That phase scoring 6/10 or better.",
        focus="Weak phase"),
}


# --- Profile: everything personal comes from here ----------------------------------

def profile(df):
    """Where games are won and lost, from the player's own games."""
    played = df[~df['termination'].isin(['noStart', 'aborted'])]
    losses = played[played['result'] == 'Loss']
    diff = played['opponent_rating'] - played['user_rating']

    def record(mask):
        games = played[mask]
        return dict(games=len(games), win_rate=(games['result'] == 'Win').mean() if len(games) else None)

    by_color = {c: (played[played['user_color'] == c]['result'] == 'Win').mean()
                for c in ('white', 'black') if (played['user_color'] == c).any()}
    return dict(
        losses=len(losses),
        time_losses=int(losses['termination'].isin(['outoftime', 'timeout']).sum()),
        mate_losses=int((losses['termination'] == 'mate').sum()),
        resign_losses=int((losses['termination'] == 'resign').sum()),
        stronger=record(diff >= 100), similar=record(diff.abs() < 100), weaker=record(diff <= -100),
        by_color=by_color,
        speed=played['speed'].mode().iloc[0] if not played.empty else 'blitz',
    )


def _share(part, whole):
    return part / whole if whole else 0


def _weaknesses(stats, analysis, time_stats, opening_stats, prof):
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

    if prof:
        time_share = _share(prof['time_losses'], prof['losses'])
        if time_share >= 0.25:
            found.append((2.4 + time_share, 'time', f"{prof['time_losses']} of {prof['losses']} losses were on time"))
        equals = prof['similar']
        if equals['games'] >= 5 and equals['win_rate'] < 0.45:
            found.append((1.9, 'level_up', f"{equals['win_rate']:.0%} against similar-rated opponents"))
    if time_stats and not any(k == 'time' for _, k, _ in found):
        off = [p for p in ('opening', 'middlegame', 'endgame') if not time_stats[f'{p}_feedback'].startswith("On Target")]
        if off:
            found.append((1 + 0.2 * len(off), 'time', f"pace off target in the {', '.join(off)}"))

    if opening_stats is not None and not opening_stats.empty:
        weak = opening_stats[opening_stats['games'] >= 5].sort_values('win_rate')
        if not weak.empty and weak.iloc[0]['win_rate'] < 0.45:
            found.append((1.5, 'opening', weak.iloc[0]['opening_name']))

    if analysis and analysis.get('phases'):
        phase, data = min(analysis['phases'].items(), key=lambda kv: kv[1].get('score', 10))
        if data.get('score', 10) < 5:
            found.append((1.8, 'phase', phase))  # a clearly weak stage outranks general accuracy
    return sorted(found, key=lambda t: -t[0])


def _fixes(stats, analysis, time_stats, opening_stats, prof=None):
    weak = _weaknesses(stats, analysis, time_stats, opening_stats, prof)
    defaults = [(0, k, None) for k in ('blunder_rate', 'acpl', 'win_rate') if k not in {w[1] for w in weak}]
    return (weak + defaults)[:3]


# --- At a glance ----------------------------------------------------------------------

def _good_at(stats, analysis, time_stats, opening_stats, prof):
    out = []
    if prof and prof['weaker']['games'] >= 5 and prof['weaker']['win_rate'] >= 0.6:
        out.append(f"Beating lower-rated players ({prof['weaker']['win_rate']:.0%} wins in {prof['weaker']['games']} games)")
    elif grades.grade('win_rate', stats['win_rate']) == grades.GOOD:
        out.append(f"Winning games ({stats['win_rate']:.0%} overall)")
    if analysis and analysis.get('phases'):
        phase, data = max(analysis['phases'].items(), key=lambda kv: kv[1].get('score', 0))
        if data.get('score', 0) >= 6:
            out.append(f"The {phase.lower()} ({data.get('score')}/10, {data.get('accuracy_percent')}% accuracy)")
    if opening_stats is not None and not opening_stats.empty:
        good = opening_stats[opening_stats['games'] >= 5].sort_values('win_rate', ascending=False)
        if not good.empty and good.iloc[0]['win_rate'] >= 0.6:
            best = good.iloc[0]
            out.append(f"The {best['opening_name']} ({best['win_rate']:.0%} over {int(best['games'])} games)")
    if prof and len(prof['by_color']) == 2:
        color = max(prof['by_color'], key=prof['by_color'].get)
        out.append(f"Playing {color.title()} ({prof['by_color'][color]:.0%} wins)")
    return out[:3] or ["Showing up and playing: you have a solid base of games to learn from"]


def _lacking(fixes):
    labels = {
        'blunder_rate': "Avoiding big mistakes ({v}% of moves)",
        'acpl': "Move-by-move accuracy (losing {v} points per move)",
        'mistake_rate': "Choosing the best move, not the first good one ({v}% medium mistakes)",
        'win_rate': "Converting games ({v:.0%} win rate)",
        'time': "Clock management ({v})",
        'level_up': "Results against equal opponents ({v})",
        'opening': "Your {v}",
        'phase': "Your {v} play",
    }
    out = []
    for _, key, value in fixes:
        if value is None:
            continue
        v = value.lower() if isinstance(value, str) and key == 'phase' else value
        out.append(labels[key].format(v=v))
    return out or ["No major leaks: keep stretching yourself against stronger opponents"]


def next_level(rating, fixes):
    target, label, typical = next(((m, lbl, t) for m, lbl, t in MILESTONES if m > (rating or 0)), MILESTONES[-1])
    personal = DRILLS[fixes[0][1]]['name'].lower() if fixes else "consistent practice"
    return target, (f"To reach **{label}**, players typically need to {typical}. "
                    f"For you specifically, that starts with **{personal}**.")


def at_a_glance(stats, analysis, time_stats, opening_stats, prof):
    fixes = _fixes(stats, analysis, time_stats, opening_stats, prof)
    _, nxt = next_level(stats.get('current_rating'), fixes)
    return "\n".join([
        "## At a glance",
        "**✅ What you're good at**", *[f"- {g}" for g in _good_at(stats, analysis, time_stats, opening_stats, prof)],
        "", "**🔻 What's holding you back**", *[f"- {l}" for l in _lacking(fixes)],
        "", "**🚀 Your next level**", nxt,
    ])


# --- Analysis (written by the AI when online) ----------------------------------------

def _phase_paragraphs(analysis, time_stats, prof):
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
    if prof and prof['losses']:
        paras.append(f"**How you lose:** of {prof['losses']} losses, {prof['time_losses']} were on time, "
                     f"{prof['resign_losses']} by resignation and {prof['mate_losses']} by checkmate.")
    return paras or ["Run **Review** on a few games in the Games step to unlock a phase-by-phase breakdown."]


def analysis_sections(stats, risk, pacing, analysis=None, time_stats=None, opening_stats=None, prof=None):
    """Summary, strengths, where points are lost and the one thing (the part the AI writes when online)."""
    fixes = _fixes(stats, analysis, time_stats, opening_stats, prof)
    top_key, top_detail = fixes[0][1], fixes[0][2]
    risk_word = plain(risk['label']).lower()
    article = "an" if risk_word[:1] in "aeiou" else "a"
    lines = [
        "## Summary",
        f"You're a {stats['current_rating']}-rated {plain(pacing['label']).lower()} with {article} {risk_word} "
        f"streak, winning {stats['win_rate']:.0%} of {stats['total_games']} games. "
        f"Your biggest opportunity is **{DRILLS[top_key]['name'].lower()}**: fix that and the rating points follow.",
        "", "## Where you lose points", *[p + "\n" for p in _phase_paragraphs(analysis, time_stats, prof)],
        "## The one thing",
        f"**{DRILLS[top_key]['name']}.** {DRILLS[top_key]['why']}"
        + (f" (Here: {top_detail}.)" if isinstance(top_detail, str) else ""),
    ]
    return "\n".join(lines)


# --- Tactics, sparring and the plan ---------------------------------------------------

def tactics(analysis, risk, prof):
    """Puzzle themes picked from where this player's mistakes happen, with a reason for each."""
    picks = []  # (slug, reason)
    phases = (analysis or {}).get('phases', {})
    mid = phases.get('Middlegame', {})
    if mid.get('score', 10) < 6 or (analysis and analysis['blunder_rate'] >= 6):
        reason = f"middlegame big mistakes on {mid.get('blunder_rate', analysis['blunder_rate'] if analysis else '?')}% of moves"
        picks += [('hangingPiece', reason), ('fork', reason), ('discoveredAttack', reason)]
    end = phases.get('Endgame', {})
    if end and end.get('score', 10) < 7:
        reason = f"endgame score {end.get('score')}/10"
        picks += [('rookEndgame', reason), ('pawnEndgame', reason)]
    if phases.get('Opening', {}).get('score', 10) < 5:
        picks.append(('opening', f"opening score {phases['Opening'].get('score')}/10"))
    if prof and _share(prof['mate_losses'], prof['losses']) >= 0.2:
        picks += [('backRankMate', f"{prof['mate_losses']} of your losses ended in checkmate"),
                  ('defensiveMove', "you get mated more often than average")]
    if risk['score'] >= 7:
        picks.append(('defensiveMove', f"risk-taking {risk['score']}/10: you attack more than you defend"))
        picks.append(('quietMove', "aggressive players often miss the calm best move"))
    elif risk['score'] <= 3:
        picks += [('sacrifice', f"risk-taking {risk['score']}/10: practise seeing sacrifices"),
                  ('kingsideAttack', "turn safe positions into attacks")]
    if not picks:
        picks = [('fork', "core pattern at every level"), ('pin', "core pattern at every level")]
    seen, out = set(), []
    for slug, reason in picks:
        if slug not in seen:
            seen.add(slug)
            out.append((slug, reason))
    return out[:5]


def strategy(analysis, risk, prof):
    """Strategic themes in chess terms, chosen from the player's style and where games slip away."""
    phases = (analysis or {}).get('phases', {})
    themes = [
        ("Read the imbalances first",
         "Before choosing a plan, list the imbalances: minor pieces (bishop pair vs. knights), pawn structure "
         "(isolated, doubled, passed pawns), king safety, development and space. Your plan should exploit the "
         "imbalance that favours you, not just react to the last move."
         + (f" This matters most for you in the middlegame, which scores {phases['Middlegame'].get('score')}/10."
            if phases.get('Middlegame', {}).get('score', 10) < 6 else "")),
    ]
    if risk['score'] >= 6:
        themes.append((
            "Initiative: keep it, then cash in",
            f"Your risk-taking is {risk['score']}/10: you like to seize the initiative. Keep it by developing with "
            "tempo and making forcing moves, but the initiative is temporary. Once it has won material or a "
            "lasting edge (a weak king, a passed pawn), stop attacking and convert. Over-pressing is how strong "
            "attackers lose won games."))
    else:
        themes.append((
            "Use space and tighten the grip",
            f"Your risk-taking is {risk['score']}/10: you prefer control. With a space advantage, don't rush the "
            "pawn break. First restrict your opponent's counterplay (prophylaxis), improve your worst-placed "
            "piece and only open lines when every piece is ready. Squeeze before you strike."))
    endgame = phases.get('Endgame', {}).get('score', 10)
    time_share = _share(prof['time_losses'], prof['losses']) if prof else 0
    if endgame < 7 or time_share >= 0.2:
        why = (f"{prof['time_losses']} of your {prof['losses']} losses came on time" if time_share >= 0.2
               else f"your endgame scores {endgame}/10")
        themes.append((
            "Know when to convert",
            f"Since {why}, simplify once you're clearly ahead (about +2 pawns): trade pieces, not pawns, steer "
            "toward a technical endgame, activate your king and create a passed pawn. Simple winning positions "
            "need less clock and less calculation."))
    if risk['score'] >= 7 or (analysis and analysis['blunder_rate'] >= 6):
        themes.append((
            "Prophylaxis: ask what they want",
            "Before every committal move, ask what your opponent's best plan is and whether one quiet move stops it. "
            "Attacking players blunder most when they only look at their own threats."))
    return themes


def _tactics_table(themes):
    rows = ["| Theme | Why you | Daily |", "|---|---|---|"]
    rows += [f"| [{THEMES[s]}]({LICHESS}{s}) | {reason} | 10 puzzles |" for s, reason in themes]
    return rows


def sparring(stats, prof):
    rating = int(stats.get('current_rating') or 1500)
    stronger = prof['stronger'] if prof else dict(games=0, win_rate=None)
    # Already holding up against stronger players? Stretch further.
    step = 200 if stronger['games'] >= 5 and (stronger['win_rate'] or 0) >= 0.4 else 150
    low, high = rating + 50, rating + step
    speed = (prof or {}).get('speed', 'blitz')
    slower = {'bullet': "3+2 blitz", 'blitz': "10+5 rapid", 'rapid': "15+10 rapid"}.get(speed, "15+10 rapid")
    record = (f"So far you score {stronger['win_rate']:.0%} in {stronger['games']} games against players 100+ above you."
              if stronger['games'] else "You have barely played stronger opponents yet, so this is where growth is.")
    return low, high, slower, [
        record,
        f"- **Who:** opponents rated **{low}-{high}**. In the Lichess lobby, create a game and set the rating range "
        f"to +50 / +{step}.",
        f"- **Time control:** **{slower}**. Slower than your usual {speed}, so you have time to use your routine.",
        "- **How many:** **4 games a week**, two sessions of two games.",
        f"- **Your focus in every game:** the one thing above. Before each move, run your blunder check.",
        "- **After each game (within 24h):** open it on the Analysis board, find the first big mistake, "
        "and write one line on what the stronger player did better.",
        "- **Win or lose, it counts:** losses against stronger players teach the most. Track how long you stay level.",
    ]


def _plan(fixes, themes, low, high, slower):
    t = lambda i: THEMES[themes[i % len(themes)][0]] if themes else "Mixed tactics"
    top = DRILLS[fixes[0][1]]
    rows = [
        ("Mon", "Tactics", f"10 {t(0)} + 10 {t(1)} puzzles", "25 min"),
        ("Tue", "Sparring", f"2 games ({slower}) vs {low}-{high}, then review both", "60 min"),
        ("Wed", top['focus'], top['steps'][0], "30 min"),
        ("Thu", "Tactics + endgame", f"10 {t(2)} puzzles, then 1 Lichess Practice endgame", "30 min"),
        ("Fri", "Sparring", f"2 games ({slower}) vs {low}-{high}, then review both", "60 min"),
        ("Sat", DRILLS[fixes[1][1]]['focus'] if len(fixes) > 1 else "Openings",
         DRILLS[fixes[1][1]]['steps'][0] if len(fixes) > 1 else "Review your main openings to move 10", "30 min"),
        ("Sun", "Review", "Re-read your week's notes, check your targets below, rest", "20 min"),
    ]
    table = ["| Day | Focus | Exactly what to do | Time |", "|---|---|---|---|"]
    table += [f"| {d} | {f} | {w} | {m} |" for d, f, w, m in rows]
    return table


def _next_steps(fixes, themes, low, high, slower, target_rating):
    first = THEMES[themes[0][0]] if themes else "tactics"
    return [
        "**Today**",
        f"1. Solve 10 [{first}]({LICHESS}{themes[0][0] if themes else 'mix'}) puzzles slowly, checking every candidate.",
        f"2. Play 1 sparring game ({slower}) against someone rated {low}-{high}.",
        "3. Review it for 10 minutes: find your first big mistake and write one line about it.",
        "", "**This week**",
        "4. Follow the 7-day plan below, one row a day.",
        f"5. Practise your one thing in every game: **{DRILLS[fixes[0][1]]['name'].lower()}**.",
        "", "**This month**",
        "6. Play 16 sparring games and review every one.",
        f"7. Hit the targets at the bottom, then aim for **{target_rating}**.",
    ]


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


def _targets(stats, analysis, prof):
    rows = []
    if prof and prof['similar']['games']:
        rows.append(f"- **Vs. equal opponents:** {prof['similar']['win_rate']:.0%} today → aim for "
                    f"{min(prof['similar']['win_rate'] + 0.1, 0.6):.0%}.")
    if prof and prof['losses']:
        rows.append(f"- **Losses on time:** {prof['time_losses']} of {prof['losses']} → aim for 1 in your next 20 games.")
    if analysis:
        rows.append(f"- **Big mistakes:** {analysis['blunder_rate']}% of moves → aim for "
                    f"{max(1.0, round(analysis['blunder_rate'] * 0.7, 1))}%.")
        rows.append(f"- **Accuracy loss (ACPL):** {analysis['avg_acpl']} → aim for "
                    f"{max(20, round(analysis['avg_acpl'] - 10))}.")
    rows.append(f"- **Rating:** {stats.get('current_rating')} → aim for +50 this month.")
    return rows


def plan_sections(stats, risk, df, analysis=None, time_stats=None, opening_stats=None, white_stats=None,
                  black_stats=None):
    """Next steps, 7-day plan, tactics, sparring, drills, openings and targets: always built from the data."""
    prof = profile(df)
    fixes = _fixes(stats, analysis, time_stats, opening_stats, prof)
    themes = tactics(analysis, risk, prof)
    low, high, slower, spar = sparring(stats, prof)
    target_rating, _ = next_level(stats.get('current_rating'), fixes)

    lines = ["## Your next steps", *_next_steps(fixes, themes, low, high, slower, target_rating),
             "", "## 7-day training plan", *_plan(fixes, themes, low, high, slower),
             "", "## Tactics to train", "Picked from where your mistakes happen. Click a theme to start.",
             "", *_tactics_table(themes),
             "", "## Strategic themes", *[f"**{name}.** {text}\n" for name, text in strategy(analysis, risk, prof)],
             "## Sparring plan", *spar,
             "", "## Drills"]
    for _, key, value in fixes:
        d = DRILLS[key]
        target = (max(1.0, round(value * 0.7, 1)) if key == 'blunder_rate'
                  else max(20, round(value - 10)) if key == 'acpl'
                  else 5 if key == 'mistake_rate' else "")
        lines += [f"**{d['name']}**: {d['why']}", *[f"{i}. {s}" for i, s in enumerate(d['steps'], 1)],
                  "", f"*Measure it:* {d['measure'].format(target=target)}", ""]
    lines += ["## Opening repertoire", *_repertoire(white_stats, black_stats),
              "", "## Targets for next month", *_targets(stats, analysis, prof)]
    return "\n".join(lines)


def report(stats, risk, pacing, df, analysis=None, time_stats=None, opening_stats=None, white_stats=None,
           black_stats=None):
    """Full built-in report: at a glance, analysis, then the training plan."""
    prof = profile(df)
    return "\n\n".join([
        at_a_glance(stats, analysis, time_stats, opening_stats, prof),
        analysis_sections(stats, risk, pacing, analysis, time_stats, opening_stats, prof),
        plan_sections(stats, risk, df, analysis, time_stats, opening_stats, white_stats, black_stats),
    ])
