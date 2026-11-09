from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", ROOT / "data" / "uploads"))
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", ROOT / "chroma_db"))
LOG_FILE = Path(os.getenv("LOG_FILE", ROOT / "logs" / "app.log"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# LLM_PROVIDER: auto | ollama | anthropic | gemini | groq | openai | extractive
# gemini / groq / openai = any OpenAI-compatible chat API; set LLM_API_KEY (and LLM_MODEL, LLM_BASE_URL for 'openai').
# Gemini and Groq have free API tiers.
# auto = Ollama if running, else Anthropic if key set, else extractive (no LLM, no key).
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").lower()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
# Ollama defaults to a 2048-token window, which silently cuts off the system prompt and context.
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
OPENAI_COMPAT = {  # provider -> (base URL, default model); override the model with LLM_MODEL
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-flash-latest"),
    "groq": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    "openai": ("", ""),
}
MIN_SCORE = 0.25       # min similarity for extractive answers

COLLECTION = "enterprise_docs"
CHUNK_SIZE = 1000      # characters (~250 tokens)
CHUNK_OVERLAP = 150
TOP_K = 5
MAX_FILE_MB = 20
ALLOWED_EXT = {".pdf", ".txt", ".md", ".csv", ".xlsx", ".xls"}
KB_DIR = ROOT / "data" / "kb"            # public strentor.com content, seeded as client-visible
SAMPLE_DIR = ROOT / "sample_docs"        # demo files for evaluators (one click in team mode)
DOCS_DIR = ROOT / "docs"
LEADS_CSV = Path(os.getenv("LEADS_CSV", ROOT / "leads" / "leads.csv"))
TEAM_PASSWORD = os.getenv("TEAM_PASSWORD", "")   # empty = team mode disabled
MAX_QUESTION_CHARS = 1000
MAX_QUESTIONS_PER_SESSION = int(os.getenv("MAX_QUESTIONS_PER_SESSION", "40"))  # caps API spend on a public app
MAX_RETRIES = 1
