# Gambit AI

Personal AI chess coach for Lichess players.
Masters of Data Science, Programming for Data Science Capstone.

## What it does
1. Fetches a player's recent games from Lichess.
2. Analyzes openings, time controls, pace, risk and engine accuracy by game phase.
3. Visualizes their style (personality radar, repertoire, activity and result patterns).
4. Coaches them with an AI model: a verdict, three fixes and one drill, built from their own games.

## Team
* Brian Bellamy (GitHub: https://github.com/bbellamy27)
* Harold Gonzalez (GitHub: https://github.com/Ruptzy)

## Setup
Requires Python 3.8+. MongoDB is optional; without it the app uses a local SQLite database.

```bash
pip install -r requirements.txt
```

Optional `.env` file in the project folder:

```
LICHESS_TOKEN=...      # needed if Lichess blocks anonymous game downloads (lichess.org/account/oauth/token, no scopes)
GOOGLE_API_KEY=...     # only for the Google Gemini model
GROQ_API_KEY=...       # only for the Groq model
```

The default AI model is free and needs no key. Keys can also be entered in the sidebar.

## Run
```bash
streamlit run app.py
```
Or double-click `run_app.bat` on Windows. The app opens at http://localhost:8501.
Click **Try the demo** to explore it offline with a bundled sample dataset.

## Data sources
* **Lichess API**: `https://lichess.org/api/games/user/{username}` (NDJSON).
* **AI models**: a free hosted model by default, or Google Gemini / Groq with your own key.

See `CODE_DOCUMENTATION.md` for the code structure.

Created for the Data Science Capstone, Fall 2025.
