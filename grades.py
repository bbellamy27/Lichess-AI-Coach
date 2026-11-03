"""Chess-standard benchmarks: grade each stat as good / ok / bad so the UI can colour it."""
GOOD, OK, BAD, NEUTRAL = "good", "ok", "bad", "neutral"
LABELS = {GOOD: "✅ Good", OK: "⚠️ OK", BAD: "🔻 Needs work", NEUTRAL: "Small sample"}

# (good_limit, ok_limit, lower_is_better, benchmark hint shown under the number)
BENCHMARKS = {
    # Average centipawn loss: ~15-25 master, ~35-45 around 2000, ~55-70 club, 80+ beginner
    'acpl': (40, 65, True, "Master <25 · club 55-70"),
    # Share of moves losing 3+ pawns: strong players ~1-2%, club 3-6%
    'blunder_rate': (3, 6, True, "Strong <2% · club 3-6%"),
    # Share of moves losing 1-3 pawns
    'mistake_rate': (5, 10, True, "Good <5%"),
    # Share of moves losing 0.5-1 pawn
    'inaccuracy_rate': (10, 18, True, "Good <10%"),
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
