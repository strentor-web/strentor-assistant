from __future__ import annotations
import csv
import os
import re
from datetime import datetime, timezone
from . import config

FIELDS = ["timestamp", "name", "email", "phone", "country", "need", "pathway", "last_question", "consent"]
COUNTRIES = ["India", "UAE", "Singapore", "Other"]
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LeadError(Exception):
    pass


def recommend_pathway(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("company", "corporate", "organi", "employee", "csr", "institution", "dei", "ngo")):
        return "Corporate & Institutional"
    if any(k in t for k in ("one hour", "one-off", "single session", "review my training", "strategy")):
        return "Strategy Session"
    if any(k in t for k in ("after my program", "continue", "community", "circle", "membership")):
        return "STRENTOR Circle"
    if any(k in t for k in ("try", "trial", "not sure", "just looking", "explore", "starter")):
        return "STRENTOR Assessment (free)"
    return "STRENTOR Flagship: Founding Cohort"


def _safe(v: str) -> str:
    """Neutralize CSV/Excel formula injection."""
    v = (v or "").strip()
    return "'" + v if v[:1] in ("=", "+", "-", "@") else v


def read_leads() -> list[dict]:
    if not config.LEADS_CSV.exists():
        return []
    with config.LEADS_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_lead(name: str, email: str, country: str, need: str, phone: str = "",
              last_question: str = "", consent: bool = False) -> dict:
    """Validate and upsert (by email) a lead into the CSV."""
    name, email = (name or "").strip(), (email or "").strip().lower()
    if not consent:
        raise LeadError("Consent is required to contact you.")
    if not name:
        raise LeadError("Name is required.")
    if not _EMAIL.match(email):
        raise LeadError("Enter a valid email.")
    if country not in COUNTRIES:
        raise LeadError("Pick a country.")
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "name": _safe(name)[:100], "email": email, "phone": _safe(phone)[:30],
        "country": country, "need": _safe(need)[:500],
        "pathway": recommend_pathway(f"{need} {last_question}"),
        "last_question": _safe(last_question)[:300], "consent": "yes",
    }
    rows = [r for r in read_leads() if r["email"] != email] + [row]
    config.LEADS_CSV.parent.mkdir(parents=True, exist_ok=True)
    tmp = config.LEADS_CSV.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, config.LEADS_CSV)
    return row
