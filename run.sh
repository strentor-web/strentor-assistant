#!/usr/bin/env bash
# One-command start for macOS / Linux.   ./run.sh
set -e
cd "$(dirname "$0")"
PY=""
for c in python3.12 python3.11 python3.13 python3.10 python3.9 python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 9) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "Python 3.9 or newer is required: https://www.python.org/downloads/"; exit 1; }
echo "Using $("$PY" --version)"
[ -d .venv ] || "$PY" -m venv .venv
source .venv/bin/activate
echo "Installing dependencies (first run only takes a minute)..."
pip install -q -r requirements.txt
[ -f .env ] || cp .env.example .env
echo "Preparing the local embedding model (one-time download, needs internet)..."
python scripts/warmup.py
if command -v ollama >/dev/null 2>&1 && ollama list 2>/dev/null | grep -q "llama3.2"; then
  echo "Ollama model found: using LLM mode."
else
  echo "No local LLM: running in extractive mode. All four agents still run. Optional: install Ollama or set ANTHROPIC_API_KEY in .env."
fi
echo "Starting the app. Your browser opens at http://localhost:8501  (team password: see .env, default 'evaluator')"
streamlit run app.py
