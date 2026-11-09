@echo off
rem One-command start for Windows. Double-click this file.
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py -3
%PY% --version >nul 2>nul || (echo Python 3.9 or newer is required: https://www.python.org/downloads/ & pause & exit /b 1)
if not exist .venv %PY% -m venv .venv
call .venv\Scripts\activate
echo Installing dependencies (first run only takes a minute)...
pip install -q -r requirements.txt
if not exist .env copy .env.example .env >nul
echo Preparing the local embedding model (one-time download, needs internet)...
python scripts\warmup.py
where ollama >nul 2>nul
if %errorlevel%==0 (
  echo Ollama detected: it will be used if the llama3.2 model is installed.
) else (
  echo No local LLM: running in extractive mode. All four agents still run. Optional: install Ollama or set ANTHROPIC_API_KEY in .env.
)
echo Starting the app. Your browser opens at http://localhost:8501  (team password: see .env, default 'evaluator')
streamlit run app.py
