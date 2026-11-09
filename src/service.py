from __future__ import annotations
import logging
from pathlib import Path
from . import config, ingestion, vectorstore, agents, leads
from .guardrails import validate_question, GuardrailError

logging.basicConfig(filename=str(config.LOG_FILE), level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("strentor")


def ingest_file(path: Path, visibility: str = "internal") -> int:
    records = ingestion.load_file(path)
    n = vectorstore.add_chunks(ingestion.chunk_records(records), visibility)
    log.info("ingested %s (%s): %d chunks", path.name, visibility, n)
    return n


def ingest_url(url: str, visibility: str = "public") -> int:
    records = ingestion.load_url(url)
    n = vectorstore.add_chunks(ingestion.chunk_records(records), visibility)
    log.info("ingested url %s (%s): %d chunks", url, visibility, n)
    return n


def _ingest_dir(folder: Path, visibility: str) -> int:
    n = 0
    for p in sorted(folder.glob("*")):
        if p.suffix.lower() in config.ALLOWED_EXT:
            n += ingest_file(p, visibility)
    return n


def seed_public_kb() -> int:
    """Index data/kb/* as client-visible. Safe to re-run (upsert)."""
    return _ingest_dir(config.KB_DIR, "public")


def load_samples() -> int:
    """Index the evaluator demo files in sample_docs/ as public. Safe to re-run."""
    return _ingest_dir(config.SAMPLE_DIR, "public")


def ask(question: str, audience: str = "client") -> dict:
    try:
        q = validate_question(question)
        res = agents.run(q, audience)
        t = res["trace"]
        log.info("ask audience=%s route=%s chunks=%s grounded=%s ms=%s",
                 audience, t.get("route"), t.get("chunks"), t.get("validation", {}).get("grounded"), t.get("total_ms"))
        return res
    except GuardrailError as e:
        log.warning("blocked question: %s", e)
        return {"answer": f"Blocked: {e}", "sources": [], "trace": {"route": "blocked"}, "cta": None}
    except Exception as e:
        log.exception("ask failed")
        hint = ""
        if any(k in str(e).lower() for k in ("connect", "proxy", "download", "resolve", "timeout")):
            hint = " (The embedding model downloads once on first use; check your internet connection and retry.)"
        return {"answer": f"Error: {e}{hint}", "sources": [], "trace": {"route": "error"}, "cta": None}


def submit_lead(**kw) -> dict:
    row = leads.save_lead(**kw)
    log.info("lead saved: pathway=%s country=%s", row["pathway"], row["country"])
    return row
