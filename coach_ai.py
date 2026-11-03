"""Picks the AI provider, builds coaching prompts and streams replies."""
import json
import os
import time

import requests

from groq_client import GroqClient
from llm_client import LLMClient

FREE = "Free AI (Default)"
OFFLINE = "Built-in coach (offline)"
GEMINI = "Google Gemini"
GROQ = "Groq (Llama 3)"
PROVIDERS = {
    FREE: None,
    OFFLINE: None,
    GEMINI: "GOOGLE_API_KEY",
    GROQ: "GROQ_API_KEY",
}


def missing_key(provider):
    """Return the env var a provider still needs, or None if it is ready."""
    key = PROVIDERS.get(provider)
    return key if key and not os.getenv(key) else None


def _sse(url, payload, headers=None):
    """Yield text deltas from an OpenAI-style server-sent-event stream."""
    # 10s to connect, then the reply must keep flowing (20s max between chunks)
    with requests.post(url, json={**payload, "stream": True}, headers=headers, stream=True, timeout=(10, 20)) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            choices = json.loads(data).get("choices") or []  # some chunks carry only metadata
            delta = choices[0].get("delta", {}).get("content") if choices else None
            if delta:
                yield delta


FALLBACK_NOTE = "*Built-in coach (the AI service didn't respond).*"


def _typewriter(text, delay=0.003):
    """Yield prepared text word by word so it reads like a live reply."""
    for word in text.split(" "):
        yield word + " "
        time.sleep(delay)


BUSY = "The AI coach is busy right now. Try again in a minute, or pick the built-in coach in the sidebar."


def stream(provider, messages, context=None, fallback=None):
    """Stream a reply token by token. If the AI fails or is slow, stream `fallback` (or a short notice) instead."""
    system = "You are a concise, practical chess coach."
    if context:
        system += f"\n\nPLAYER DATA:\n{context}"
    convo = [{"role": "system", "content": system}] + [m for m in messages if m["role"] != "system"]
    if provider == OFFLINE:
        yield from _typewriter(fallback or BUSY)
        return
    started = False
    try:
        if provider == GEMINI and not missing_key(GEMINI):
            text = "\n\n".join(f"{m['role']}: {m['content']}" for m in convo)
            chunks = (c.text for c in LLMClient().model.generate_content(text, stream=True))
        elif provider == GROQ and not missing_key(GROQ):
            client = GroqClient()
            chunks = _sse(client.url, {"model": client.model, "messages": convo},
                          {"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"})
        else:
            chunks = _sse("https://text.pollinations.ai/openai", {"model": "openai", "messages": convo})
        for chunk in chunks:
            started = True
            yield chunk
        if started:
            return
    except Exception as e:
        print(f"AI coach unavailable ({e})")
        if started:  # reply was cut off part-way; end it cleanly
            yield " …"
            return
    if fallback:
        yield FALLBACK_NOTE + "\n\n"
        yield from _typewriter(fallback)
    else:
        yield BUSY


def report_prompt(stats, risk, pacing, time_stats, analysis, white_stats, black_stats, prof=None):
    """Request for the analysis half of the report; the plan half comes from local_coach.plan_sections."""
    def openings(table):
        if table is None or table.empty:
            return "none"
        return "; ".join(f"{r.opening_name} ({r.games} games: {r.wins}W-{r.draws}D-{r.losses}L, {r.win_rate:.0%})"
                         for r in table.head(6).itertuples())

    lines = [
        f"Rating {stats['current_rating']}, {stats['total_games']} games, win rate {stats['win_rate']:.0%}.",
        f"Risk profile: {risk['label']} ({risk['score']}/10). {risk['feedback']}",
        f"Pace: {pacing['label']}, average game {pacing['avg_moves']} moves. {pacing['feedback']}",
        f"Openings as White: {openings(white_stats)}.",
        f"Openings as Black (names may include White's reply; the player chose the defense): {openings(black_stats)}.",
    ]
    if time_stats:
        for p in ('opening', 'middlegame', 'endgame'):
            lines.append(f"Time in the {p}: {time_stats[f'{p}_avg']}s per move ({time_stats[f'{p}_feedback']})")
    if analysis:
        lines.append(f"Engine accuracy over {analysis.get('games_analyzed', '?')} analysed games: ACPL "
                     f"{analysis['avg_acpl']}, blunders {analysis['blunder_rate']}% of moves, mistakes "
                     f"{analysis['mistake_rate']}%, inaccuracies {analysis['inaccuracy_rate']}%.")
        for phase, data in analysis.get('phases', {}).items():
            lines.append(f"{phase}: score {data.get('score')}/10, accuracy {data.get('accuracy_percent')}%, "
                         f"blunders {data.get('blunder_rate')}%.")
    if prof:
        lines.append(f"How games are lost: {prof['losses']} losses, of which {prof['time_losses']} on time, "
                     f"{prof['resign_losses']} by resignation, {prof['mate_losses']} by checkmate.")
        for label in ('stronger', 'similar', 'weaker'):
            rec = prof[label]
            if rec['games']:
                lines.append(f"Vs. {label} opponents (100+ points {'above' if label == 'stronger' else 'below' if label == 'weaker' else 'either side'}): "
                             f"{rec['win_rate']:.0%} wins in {rec['games']} games.")
        if prof['by_color']:
            lines.append("Win rate by colour: " + ", ".join(f"{c} {v:.0%}" for c, v in prof['by_color'].items()) + ".")

    return f"""You are a grandmaster-level chess coach writing a personal coaching report and training plan.
Use ONLY the player's data below. Quote their real numbers. Tailor every recommendation to their rating:
{ELO_BANDS}
Player data:
{chr(10).join('- ' + l for l in lines)}

Write the analysis part of their report in markdown (about 350-400 words; a training plan, drills and
targets are added separately, so do not write those). Be specific, explain the chess reasons behind
each number, and stay encouraging. Write like a strong coach: use precise chess terminology such as
imbalances (minor pieces, pawn structure, king safety, space, development), initiative and tempo,
prophylaxis, piece activity, converting an advantage (simplify, trade pieces not pawns), and using a
space advantage to tighten the grip before a pawn break. Add a short plain-English gloss the first time
you use a technical term. Use exactly these sections:

## Summary
3-4 sentences: who this player is, their style, and the single biggest opportunity.

## Strengths
2-3 bullets, each tied to a number from the data and what it says about their chess.

## Where you lose points
A short paragraph each for **Opening**, **Middlegame**, **Endgame** and **Time management**,
explaining what the numbers mean and why it costs games at this rating.

## The one thing
The single habit that would gain the most rating points, why it matters, and what it looks like in a game."""


ELO_BANDS = """
- 500-799: hanging pieces, simple threats, one-move thinking.
- 800-999: basic plans, converting material, simple endgames.
- 1000-1199: hanging pawns, incorrect trades, development.
- 1200-1399: pawn structure, piece activity, long-term plans.
- 1400-1599: decision consistency, when to attack vs improve pieces.
- 1600-1799: calculation depth, over-aggression, prophylaxis.
- 1800-1999: sharp lines, rook endgames, tempo.
- 2000-2199: subtle positional errors, exploiting weaknesses.
- 2200+: precision, novelties, conversion.
"""


def opening_perspective(color, opening_name, role=None):
    """Was this opening the player's choice, or the opponent's?"""
    if role == "i_play":
        return "my_choice"
    if role == "i_face":
        return "opponent_choice"
    defensive = any(x in (opening_name or "") for x in
                    ["Defense", "Defence", "Countergambit", "Counter-Gambit", "Counterattack", "Counter-Attack"])
    if color == "white":
        return "opponent_choice" if defensive else "my_choice"
    return "my_choice" if defensive else "opponent_choice"


def game_review_prompt(row, my_acpl, times_played):
    """Prompt for a short review of a single analysed game."""
    color = row['user_color']
    elo = row['white_rating'] if color == 'white' else row['black_rating']
    opening = row['opening_name']

    if opening_perspective(color, opening, row.get('opening_role')) == "my_choice":
        perspective = f"This was MY choice. Phrase as: 'In the {opening} as {color.title()}...'"
    else:
        perspective = f"This was my OPPONENT'S choice. Phrase as: 'Against the {opening} as {color.title()}...'"

    if times_played >= 5:
        repertoire = (f"This opening is part of my CORE REPERTOIRE (played {times_played} times). "
                      "You may call it 'a line I play' and treat it as a stable weapon.")
    else:
        repertoire = (f"This opening is INCIDENTAL (played only {times_played} times). Do NOT call it reliable or "
                      "part of my repertoire; treat good results here as tentative.")

    return f"""
Analyze this chess game summary and give me a brief coaching tip based on the accuracy and opening.

Perspective rules (non-negotiable):
1. I played as {color.upper()} (rating {elo}). Write only from my perspective, always saying "as White" or "as Black".
2. {perspective}
3. {repertoire}
4. Never treat my opponent's openings as my repertoire.

Elo guidance: start from my game data, then use my Elo ({elo}) to set priorities. Typical focus by band:
{ELO_BANDS}
Structure the answer as: "Based on your Elo range ({elo})...", "According to your personal game data...",
"Here's what to work on next...". Under 100 words, constructive, GM-style.

Game:
- {row['white_user']} ({row['white_rating']}) vs {row['black_user']} ({row['black_rating']})
- Result for me: {row['result']}
- Opening: {opening}
- Plies: {row['ply_count']}
- My accuracy (ACPL): {my_acpl}
"""
