@echo off
REM Gambit AI - double-click to set up (first run) and launch.
cd /d "%~dp0"
title Gambit AI
echo.
echo   GAMBIT AI  -  personal chess coach
echo   ----------------------------------
echo.

REM 1. Find Python (the "py" launcher first, then "python")
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY (
    echo [!] Python 3.10 or newer is required.
    echo     Install it from https://www.python.org/downloads/
    echo     and tick "Add python.exe to PATH" during setup, then run this file again.
    echo.
    pause
    exit /b 1
)

REM 2. First run: create a private environment for the app
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating the app environment...
    %PY% -m venv .venv || goto :fail
)

REM 3. Install or update packages (quick when already installed)
echo [2/3] Checking packages. The first run takes a few minutes...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt || goto :fail

REM 4. Launch; the browser opens automatically
echo [3/3] Starting Gambit AI. Your browser will open in a moment.
echo       Keep this window open while using the app. Close it to stop.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless false --browser.gatherUsageStats false
goto :eof

:fail
echo.
echo [!] Setup failed. See the message above.
echo     Check your internet connection and run this file again.
pause
exit /b 1
