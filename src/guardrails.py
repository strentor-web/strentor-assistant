from __future__ import annotations
import re
from . import config

_INJECTION = re.compile(
    r"(ignore (all )?(previous|prior|above) instructions|disregard (the )?system prompt|"
    r"you are now|reveal (your )?(system )?prompt)", re.I)


class GuardrailError(Exception):
    pass


def validate_question(q: str) -> str:
    q = (q or "").strip()
    if not q:
        raise GuardrailError("Question is empty.")
    if len(q) > config.MAX_QUESTION_CHARS:
        raise GuardrailError(f"Question exceeds {config.MAX_QUESTION_CHARS} characters.")
    if _INJECTION.search(q):
        raise GuardrailError("Question looks like a prompt-injection attempt.")
    return q


def sanitize_context(text: str) -> str:
    """Neutralize instruction-like text embedded in uploaded documents."""
    return _INJECTION.sub("[removed]", text)


_MEDICAL = re.compile(
    r"(diagnos|prescri|dosage|medication|pressure (sore|ulcer)|autonomic dysreflexia|"
    r"shunt|injur(y|ed)|pain in my|should i (stop|take)|is it safe (for me|to))", re.I)

MEDICAL_REDIRECT = (
    "This is a medical question. STRENTOR coaching does not replace your clinician. "
    "Please check with your doctor or therapist, then your STRENTOR coach can adapt training to their guidance.")


def is_medical(q: str) -> bool:
    return bool(_MEDICAL.search(q))
