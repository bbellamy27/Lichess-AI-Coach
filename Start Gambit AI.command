#!/bin/bash
# Gambit AI - double-click (macOS) or run in a terminal (Linux) to set up and launch.
cd "$(dirname "$0")" || exit 1
echo
echo "  GAMBIT AI  -  personal chess coach"
echo "  ----------------------------------"
echo

if ! command -v python3 >/dev/null 2>&1; then
    echo "[!] Python 3.10 or newer is required: https://www.python.org/downloads/"
    read -r -p "Press Enter to close."
    exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
    echo "[1/3] Creating the app environment..."
    python3 -m venv .venv || { echo "[!] Could not create the environment."; exit 1; }
fi

echo "[2/3] Checking packages. The first run takes a few minutes..."
.venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt \
    || { echo "[!] Package install failed. Check your internet connection and try again."; exit 1; }

if ! command -v stockfish >/dev/null 2>&1; then
    echo "      (Optional) Game reviews need Stockfish: 'brew install stockfish' on macOS."
fi

echo "[3/3] Starting Gambit AI. Your browser will open in a moment."
echo "      Keep this window open while using the app. Close it to stop."
echo
.venv/bin/python -m streamlit run app.py --server.headless false --browser.gatherUsageStats false
