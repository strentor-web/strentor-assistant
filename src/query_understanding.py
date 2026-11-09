"""Query understanding: map how a visitor words a question onto how the knowledge base words it.

Three steps, all deterministic (no LLM needed), recorded in the agent trace:
  1. normalise  - spelling variants (program/programme) and typo repair against the KB vocabulary
  2. canonicalise - slang / paraphrase -> STRENTOR's own terms (e.g. "how much" -> price per session)
  3. suggest    - when nothing is found, offer the closest questions the knowledge base can answer
"""
from __future__ import annotations

import difflib
import re
from functools import lru_cache
from pathlib import Path

KB_FILE = Path(__file__).resolve().parent.parent / "data" / "kb" / "strentor_public.md"

# phrase/word patterns -> the terms the knowledge base actually uses
CANONICAL = [
    (r"\b(how much|cost|costs|price|prices|pricing|fee|fees|charge|charges|rate|rates|pay|afford\w*|expens\w*|cheap\w*|budget)\b",
     "price per session rupees pricing"),
    (r"\b(program|programme|programmes|programs|course|courses|package|plan|plans|training|coaching|offer|offers|offering\w*|service|services|product|products)\b",
     "Flagship programme coaching"),
    (r"\b(dubai|abu dhabi|emirates|emirati|gulf|uae)\b", "UAE"),
    (r"\b(sg|singapore\w*)\b", "Singapore"),
    (r"\b(indian?|rupees?|inr|mumbai|delhi|bangalore|bengaluru|chennai|hyderabad|pune)\b", "India"),
    (r"\b(abroad|overseas|outside india|other countries|worldwide|international|global)\b", "countries international"),
    (r"\b(company|companies|business|businesses|organi[sz]ations?|office|workplace|employees?|staff|hr|csr|ngo|b2b|institution\w*|school|college|university|team building)\b",
     "corporate institutional programmes"),
    (r"\b(online|remote|virtual|zoom|video( call)?|from home|distance)\b", "Trainer-Led Self-Paced online"),
    (r"\b(in person|in-person|gym|offline|face to face)\b", "Trainer-Led live"),
    (r"\b(live|1[: ]?1|one on one|one-on-one|personal trainer|private)\b", "Trainer-Led live coaching"),
    (r"\b(own pace|self paced|self-paced|recorded|asynchronous|anytime|flexible|whenever)\b", "Self-Paced"),
    (r"\b(free|trial|test|quiz|evaluat\w*|check|where do i start|where to start|not sure|which one|what suits|suit me|recommend\w*)\b",
     "Assessment pathway"),
    (r"\b(one off|one-off|single session|consult\w*|advice|review my|second opinion|call with)\b", "Strategy Session"),
    (r"\b(community|membership|member|after (the )?(programme|program)|alumni|continue|ongoing)\b", "Circle"),
    (r"\b(starter|7 day|seven day|elite|old|discontinued|retired)\b", "no longer sold retired"),
    (r"\b(aditya|founder|owner|who runs|who is behind|your coach|trainer|coach)\b", "founder Aditya Mandan"),
    (r"\b(how long|duration|weeks?|months?|timeline|time commitment|how many (sessions|days))\b", "12 weeks duration sessions per week"),
    (r"\b(wheelchair|disabled|disability|paraplegi\w*|spinal|spina bifida|sci|mobility|special needs|handicap\w*)\b",
     "wheelchair users adaptive"),
    (r"\b(beginner|new to|never trained|first time|no experience|start from scratch)\b", "who is it for ambitious beginners"),
    (r"\b(results?|guarantee\w*|promise|outcome)\b", "results guarantee"),
    (r"\b(book|sign up|signup|join|enrol\w*|enroll\w*|register|apply|get started|start)\b", "join enrol book"),
]
_SPELL = {"programme": "program", "programmes": "programs", "organisation": "organization",
          "organisations": "organizations", "centre": "center", "colour": "color"}


@lru_cache(maxsize=1)
def _kb_text() -> str:
    try:
        return KB_FILE.read_text(encoding="utf-8")
    except OSError:
        return ""


@lru_cache(maxsize=1)
def _vocab() -> tuple:
    words = set(re.findall(r"[a-z]{5,}", _kb_text().lower()))
    for pat, _ in CANONICAL:  # also repair typos of the trigger words themselves
        words |= {w for w in re.findall(r"[a-z]{5,}", re.sub(r"\\w\*|\\b", " ", pat)) if len(w) >= 6}
    return tuple(sorted(words))


def fix_typos(q: str) -> str:
    """Repair likely typos ('prgram', 'coachng', 'singapor') against words the KB really uses."""
    vocab = set(_vocab())
    out = []
    for tok in re.findall(r"[A-Za-z0-9']+|[^A-Za-z0-9']+", q):
        low = tok.lower()
        if len(low) >= 5 and low.isalpha() and low not in vocab:
            m = [w for w in difflib.get_close_matches(low, _vocab(), n=3, cutoff=0.8)
                 if abs(len(w) - len(low)) <= 1 and w[0] == low[0]][:1]  # real typos only: write != written
            if m:
                tok = m[0]
        out.append(tok)
    return "".join(out)


def canonical_terms(q: str) -> list:
    low = q.lower()
    for a, b in _SPELL.items():
        low = low.replace(a, b)
    seen, terms = set(), []
    for pat, canon in CANONICAL:
        if re.search(pat, low) and canon not in seen:
            seen.add(canon)
            terms.append(canon)
    return terms


def understand(q: str) -> dict:
    """-> {'original', 'corrected', 'terms', 'rewritten'} ; 'rewritten' is the extra retrieval query."""
    corrected = fix_typos(q)
    terms = canonical_terms(corrected)
    rewritten = (corrected.rstrip("?. ") + " " + " ".join(terms)).strip() if terms else corrected
    return {"original": q, "corrected": corrected, "terms": terms, "rewritten": rewritten}


def faq_questions() -> list:
    """Question lines of the public KB (single source for sample buttons and suggestions)."""
    text = _kb_text()
    section = text.split("## Frequently asked questions", 1)[-1] if "## Frequently asked questions" in text else ""
    return [ln.strip() for ln in section.splitlines() if ln.strip().endswith("?")]


def _tokens(s: str) -> set:
    return {w.rstrip("s") for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 2}


def suggest(q: str, n: int = 3) -> list:
    """Closest known questions to what the visitor typed (after typo repair and canonicalisation)."""
    u = understand(q)
    qt = _tokens(u["corrected"] + " " + " ".join(u["terms"]))
    scored = []
    for fq in faq_questions():
        ft = _tokens(fq)
        if not ft:
            continue
        ov = len(qt & ft)
        if ov:
            scored.append((ov / (len(ft) ** 0.5), fq))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [fq for _, fq in scored[:n]]
