# Gambit AI

Personal AI chess coach for Lichess players.
Masters of Data Science, Programming for Data Science Capstone.

## Quick start (about 3 minutes)
1. Install **Python 3.10 or newer** from [python.org](https://www.python.org/downloads/). On Windows, tick **"Add python.exe to PATH"**.
2. Download this project (green **Code** button → **Download ZIP**) and unzip it.
3. Double-click **`Run Gambit AI.bat`** (Windows) or **`Run Gambit AI.command`** (macOS).
   The first run installs packages (a few minutes); later runs start in seconds.
4. Your browser opens Gambit AI. Click **Try the demo** to explore without an account or internet.

To stop the app, close the black terminal window.
On macOS, if the launcher is blocked the first time, right-click it → **Open**.

## What it does
1. Fetches a player's recent games from Lichess.
2. Analyzes openings, time controls, pace, risk and engine accuracy by game phase.
3. Visualizes their style (personality radar, repertoire, activity and result patterns).
4. Coaches them with an AI model: a verdict, three fixes and one drill, built from their own games.

## Team
* Brian Bellamy (GitHub: https://github.com/bbellamy27)
* Harold Gonzalez (GitHub: https://github.com/Ruptzy)

## Manual setup
Requires Python 3.10+. MongoDB is optional; without it the app uses a local SQLite database.

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
Double-click the **Run Gambit AI** launcher (see Quick start), or from a terminal:
```bash
streamlit run app.py
```
The app opens at http://localhost:8501. **Try the demo** works offline with a bundled sample dataset.
Game reviews use Stockfish: bundled for Windows; on macOS run `brew install stockfish`.

## Data sources
* **Lichess API**: `https://lichess.org/api/games/user/{username}` (NDJSON).
* **AI models**: a free hosted model by default, or Google Gemini / Groq with your own key.

See `CODE_DOCUMENTATION.md` for the code structure.

Created for the Data Science Capstone, Fall 2025.
