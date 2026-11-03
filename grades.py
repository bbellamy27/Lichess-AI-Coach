"""Chess-standard benchmarks: grade each stat as good / ok / bad so the UI can colour it."""
GOOD, OK, BAD, NEUTRAL = "good", "ok", "bad", "neutral"
LABELS = {GOOD: "✅ Good", OK: "⚠️ OK", BAD: "🔻 Needs work", NEUTRAL: "Small sample"}

# (good_limit, ok_limit, lower_is_better, benchmark hint shown under the number)
BENCHMARKS = {
    # Average centipawn loss: ~15-25 master, ~35-45 around 2000, ~55-70 club, 80+ beginner
    'acpl': (40, 65, True, "Lower is better · masters <25, club 55-70"),
    # Share of moves losing 3+ pawns: strong players ~1-2%, club 3-6%
    'blunder_rate': (3, 6, True, "Strong players <2% · club 3-6%"),
    # Share of moves losing 1-3 pawns
    'mistake_rate': (5, 10, True, "Good: under 5% of moves"),
    # Share of moves losing 0.5-1 pawn
    'inaccuracy_rate': (10, 18, True, "Good: under 10% of moves"),
    # Score vs. similar-rated opponents should be ~50%
    'win_rate': (0.55, 0.45, False, "50% = even with opponents"),
}


def grade(metric, value):
    """Return GOOD / OK / BAD for a metric value, or NEUTRAL when there is no value."""
    if value is None:
        return NEUTRAL
    good, ok, lower_better, _ = BENCHMARKS[metric]
    if lower_better:
        return GOOD if value <= good else OK if value <= ok else BAD
    return GOOD if value >= good else OK if value >= ok else BAD


def hint(metric):
    return BENCHMARKS[metric][3]


def win_rate_grade(win_rate, games, min_games=5):
    """Opening/colour win rates only count once there are enough games."""
    return NEUTRAL if games < min_games else grade('win_rate', win_rate)


def score_grade(score):
    """Phase scores are 0-10."""
    return GOOD if score >= 8 else OK if score >= 5 else BAD


def time_grade(status):
    """Time-management status from data_processing: 'On Target', 'Too Fast', 'Too Slow'."""
    return GOOD if status.startswith("On Target") else OK


# --- Overall Gambit Score -------------------------------------------------

def _scale(value, worst, best):
    """Map value onto 0-100 where `worst` -> 0 and `best` -> 100 (works for either direction)."""
    return max(0.0, min(100.0, (value - worst) / (best - worst) * 100))


def gambit_score(win_rate, analysis=None, time_stats=None):
    """0-100 score and letter from results, accuracy and time use (whatever is available)."""
    parts = [(_scale(win_rate, 0.30, 0.70), 3)]                      # results matter most
    if analysis:
        parts.append((_scale(analysis['avg_acpl'], 100, 25), 2))    # accuracy (fast games run higher)
        parts.append((_scale(analysis['blunder_rate'], 15, 2), 1))  # big mistakes
    if time_stats:
        on_target = sum(time_stats[f'{p}_feedback'].startswith("On Target") for p in ('opening', 'middlegame', 'endgame'))
        parts.append((on_target / 3 * 100, 0.5))                     # time use: a light touch
    score = round(sum(v * w for v, w in parts) / sum(w for _, w in parts))
    letter = next(l for cut, l in ((85, "A"), (70, "B"), (55, "C"), (40, "D"), (0, "F")) if score >= cut)
    return score, letter


# Plain-English findings, used for "strength" and "biggest leak"
FINDINGS = {
    'win_rate': ("You win {v:.0%} of your games", "You win only {v:.0%} of your games"),
    'acpl': ("Your moves are accurate (lose {v:.0f} points/move)", "You give away {v:.0f} points per move on average"),
    'blunder_rate': ("You rarely make big mistakes ({v}% of moves)", "Big mistakes on {v}% of your moves"),
    'mistake_rate': ("Few medium mistakes ({v}% of moves)", "Medium mistakes on {v}% of your moves"),
}


def findings(win_rate, analysis=None):
    """Return (best, worst) plain-English findings as (grade, sentence) tuples."""
    values = {'win_rate': win_rate}
    if analysis:
        # Ordered by importance: on ties, the last bad item is reported as the biggest leak
        values.update(mistake_rate=analysis['mistake_rate'], acpl=analysis['avg_acpl'],
                      blunder_rate=analysis['blunder_rate'])
    rank = {GOOD: 0, OK: 1, BAD: 2}
    graded = sorted(((rank[grade(k, v)], k, v) for k, v in values.items()), key=lambda t: t[0])
    best, worst = graded[0], graded[-1]
    good_text = FINDINGS[best[1]][0].format(v=best[2])
    bad_text = FINDINGS[worst[1]][1 if worst[0] > 0 else 0].format(v=worst[2])
    return (grade(best[1], best[2]), good_text), (grade(worst[1], worst[2]), bad_text)
