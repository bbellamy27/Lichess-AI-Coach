# Gambit AI - Code Documentation

**Gambit AI** is a Streamlit app that analyzes a player's Lichess games, visualizes their style and performance, and gives personalized coaching from an AI model.

## Module Breakdown

### `app.py` (Entry point)
Sets up the page, picks the database (MongoDB if running, otherwise SQLite), renders the sidebar, the player header and KPI row, computes stats once per time-control filter, and lays out the five tabs.

### `theme.py` (Design system)
- Color tokens (graphite neutrals, violet brand, color-blind-checked win/draw/loss colors).
- The `coach` Plotly template every chart inherits, and `chart()` to render figures with it.
- Global CSS and small HTML components: `hero`, `section`, `kpis`, `score_card`, `insight`, the knight logo.

### `dataset.py` (Data loading and shared stats)
- `load_from_lichess`, `load_from_db` (with clock/engine backfill), `load_demo` (bundled `data/demo_games.json`).
- `filter_speed`, `summary`, `best_opening`, `build_chat_context`, and `cached()` for per-filter stats.

### `coach_ai.py` (AI coaching)
- Provider selection (`Free Llama`, `Google Gemini`, `Groq`) and key checks.
- `stream()` yields replies token by token (falls back to a single response).
- `report_prompt()` builds the short, structured coaching report; `game_review_prompt()` reviews a single game.

### `views/` (One module per screen)
- `sidebar.py`: player input, data loading, AI settings, coach chat.
- `games.py`: selectable games table, Stockfish + AI review, save to study, opening stats.
- `performance.py`: style gauge, pace, phase accuracy, time per move, trend charts.
- `insights.py`: style radar, move times, repertoire, activity and result patterns.
- `coach.py`: on-demand streamed coaching report.
- `vault.py`: PGN import and study management.

### Backend
- `api_client.py`: Lichess API (`get_user_games`, `get_games_by_ids`); sends `LICHESS_TOKEN` when set.
- `data_processing.py`: turns raw games into a DataFrame and computes risk, pacing, time and accuracy metrics.
- `eda.py`: Plotly chart builders.
- `local_engine.py`: local Stockfish analysis (ACPL per side).
- `puter_client.py`, `groq_client.py`, `llm_client.py`: non-streaming chat clients per provider.
- `DataBases/`: MongoDB and portable SQLite storage, PGN parser and analytics CLI.

## Requirements
- **Python 3.10+**
- `pip install -r requirements.txt`

## How to Run
Double-click `Run Gambit AI.bat` (Windows) or `Run Gambit AI.command` (macOS), or run `streamlit run app.py`.
