"""Four cooperating agents: Planner -> Retriever -> Reasoner -> Validator.

Each agent works with or without an LLM, so the full pipeline is demonstrable offline:
- With an LLM (Ollama / Claude): LLM planning, LLM answer, LLM fact-check.
- Without an LLM ("extractive" mode): rule-based planning, verbatim-sentence answers,
  and a real grounding check (every answer sentence must appear in the retrieved context).

Tools the agents call (recorded in the trace as `tool_calls`):
  search_documents  - vector similarity search (audience-filtered)
  sanitize_context  - strips instruction-like text from retrieved content
  check_grounding   - verifies answer sentences against the context
"""
from __future__ import annotations

import json
import re
import time
from . import config, vectorstore, query_understanding as qu
from .guardrails import is_medical, MEDICAL_REDIRECT, sanitize_context
from .rag import llm, answer_from_chunks, provider, _words

_LEAD_INTENT = re.compile(r"(price|pricing|cost|fee|join|enrol|enroll|sign up|start|book|call|corporate|csr|partner)", re.I)
LEAD_CTA = "Want Aditya to reach out? Leave your details in the sidebar form."
_SPLIT = re.compile(r"\?|;|\band also\b|\balso\b|\band\b", re.I)


def _rule_plan(question: str) -> list[str]:
    """No-LLM planner: split a compound question into focused sub-queries, plus one rewrite
    that restates the question in the knowledge base's own words (typos fixed, slang mapped)."""
    parts = [p.strip(" ,.") for p in _SPLIT.split(question) if len(p.strip(" ,.")) >= 8]
    subs = [question] if len(parts) <= 1 else ([question] + parts)
    rewritten = qu.understand(question)["rewritten"]
    if rewritten and rewritten not in subs:
        subs.insert(1, rewritten)
    return subs[:4]


def planner(question: str) -> list[str]:
    """Agent 1 (Plan): break the question into 1-3 retrieval sub-queries."""
    if provider() == "extractive":
        return _rule_plan(question)
    try:
        out = llm(
            "Break the user question into at most 3 short, self-contained search queries "
            "for a document search. Visitors word things loosely, so restate them in STRENTOR's own "
            "terms: STRENTOR Flagship programme (Trainer-Led or Self-Paced), price per session, "
            "Strategy Session, STRENTOR Circle, Assessment, corporate and institutional programmes, "
            "India / UAE / Singapore. Return ONLY a JSON array of strings.",
            question, max_tokens=200,
        )
        subs = json.loads(out[out.index("["): out.rindex("]") + 1])
        subs = [s for s in subs if isinstance(s, str) and s.strip()][:3]
        rewritten = qu.understand(question)["rewritten"]
        if rewritten not in subs:
            subs.append(rewritten)  # deterministic rewrite always joins the LLM's queries
        return subs or [question]
    except Exception:
        return _rule_plan(question)


def retriever(sub_queries: list[str], audience: str = "client", trace: dict | None = None) -> list[dict]:
    """Agent 2 (Retrieve): similarity search per sub-query (audience-filtered), dedupe, rank."""
    seen, merged = set(), []
    for q in sub_queries:
        hits = vectorstore.search(q, audience=audience)
        if trace is not None:
            trace.setdefault("tool_calls", []).append(
                {"tool": "search_documents", "query": q, "audience": audience, "hits": len(hits),
                 "top_scores": [h["score"] for h in hits[:3]]})
        for c in hits:
            key = (c["source"], c["page"], c["text"][:80])
            if key not in seen:
                seen.add(key)
                merged.append(c)
    merged.sort(key=lambda c: c["score"], reverse=True)
    return merged[: config.TOP_K * 2]


def reasoner(question: str, chunks: list[dict], audience: str = "client") -> str:
    """Agent 3 (Reason): draft a grounded answer from retrieved context only."""
    return answer_from_chunks(question, chunks, audience)


def _extractive_grounding(answer: str, chunks: list[dict]) -> dict:
    """Every '- sentence [source, page]' line must appear verbatim in the (sanitized) context."""
    ctx = [sanitize_context(c["text"]) for c in chunks]
    lines = [ln[2:] for ln in answer.splitlines() if ln.startswith("- ")]
    bad = []
    for ln in lines:
        sentence = re.sub(r"\s*\[[^\]]*\]\s*$", "", ln).strip()
        if not any(sentence in c for c in ctx):
            bad.append(sentence[:60])
    return {"grounded": not bad and bool(lines), "checked_sentences": len(lines),
            "issues": "; ".join(bad) if bad else ""}


def _lexical_grounding(answer: str, chunks: list[dict], min_support: float = 0.6) -> dict:
    """Deterministic support check for generated answers: each sentence must have most of its
    content words present in the retrieved context. Small local models are unreliable judges,
    so this check, not the model's opinion, decides when the provider is a small local LLM."""
    ctx_words: set[str] = set()
    for c in chunks:
        ctx_words |= _words(sanitize_context(c["text"]))
    body = re.sub(r"\[[^\]]*\]", " ", answer)
    sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+|\n+", body) if len(_words(x)) >= 4]
    bad = []
    for sent in sentences:
        w = _words(sent)
        if len(w & ctx_words) / len(w) < min_support:
            bad.append(sent[:60])
    return {"grounded": bool(sentences) and not bad, "checked_sentences": len(sentences),
            "issues": "; ".join(bad)}


def validator(question: str, answer: str, chunks: list[dict], trace: dict | None = None) -> dict:
    """Agent 4 (Validate): check the answer is fully supported by the context."""
    if answer.startswith("Not found"):
        return {"grounded": True, "issues": "", "method": "not-found fallback"}
    if trace is not None:
        trace.setdefault("tool_calls", []).append({"tool": "check_grounding", "provider": provider()})
    if provider() == "extractive":
        return {**_extractive_grounding(answer, chunks), "method": "verbatim-sentence check"}
    ctx = "\n\n".join(c["text"] for c in chunks)
    if provider() == "ollama":
        lex = _lexical_grounding(answer, chunks)
        opinion = "not asked"
        try:  # the small model's opinion is recorded for transparency but does not decide
            out = llm("You are a strict fact-checker. Is every claim in ANSWER supported by CONTEXT? "
                      'Return ONLY JSON: {"grounded": true|false}',
                      f"CONTEXT:\n{ctx}\n\nANSWER:\n{answer}", max_tokens=60)
            opinion = str(json.loads(out[out.index("{"): out.rindex("}") + 1]).get("grounded"))
        except Exception:
            opinion = "unparseable"
        return {**lex, "method": "lexical support check (local-model judge advisory)", "judge_opinion": opinion}
    try:
        out = llm(
            "You are a strict fact-checker. Decide if every claim in ANSWER is supported by CONTEXT, "
            "and that ANSWER gives no medical advice and promises no results. "
            'Return ONLY JSON: {"grounded": true|false, "issues": "<short>"}',
            f"CONTEXT:\n{ctx}\n\nANSWER:\n{answer}", max_tokens=200,
        )
        return {**json.loads(out[out.index("{"): out.rindex("}") + 1]), "method": "LLM fact-check"}
    except Exception:  # small local models often break JSON; fail open, flag it
        return {"grounded": True, "issues": "validator output unparseable (unchecked)", "method": "LLM fact-check"}


def _cited_sources(answer: str, chunks: list[dict]) -> list[str]:
    """Sources actually cited in the answer as [file, page]; falls back to the top 3 retrieved."""
    have = {(c["source"], str(c["page"])) for c in chunks}
    cited = {(m.group(1).strip(), m.group(2).strip())
             for m in re.finditer(r"\[([^\[\]]+?), ([^\[\]]+?)\]", answer)} & have
    pairs = cited or {(c["source"], str(c["page"])) for c in chunks[:3]}
    return sorted(f"{s} ({'p.' + p if p.isdigit() else p})" for s, p in pairs)


def run(question: str, audience: str = "client") -> dict:
    t0 = time.perf_counter()
    trace = {"provider": provider(), "audience": audience, "steps_ms": {}}

    def timed(name, fn, *a, **kw):
        s = time.perf_counter()
        r = fn(*a, **kw)
        trace["steps_ms"][name] = round((time.perf_counter() - s) * 1000)
        return r

    if is_medical(question):  # guardrail: never answer medical questions
        trace["route"] = "medical-redirect"
        return {"answer": MEDICAL_REDIRECT, "sources": [], "trace": trace, "cta": None}
    trace["route"] = "rag"
    subs = timed("plan", planner, question)
    trace["plan"] = subs
    trace["understood"] = {k: v for k, v in qu.understand(question).items() if k in ("corrected", "terms")}
    chunks = timed("retrieve", retriever, subs, audience, trace)
    trace["chunks"] = len(chunks)
    answer = timed("reason", reasoner, question, chunks, audience)
    verdict = timed("validate", validator, question, answer, chunks, trace)
    retries = 0
    while not verdict.get("grounded") and retries < config.MAX_RETRIES:
        retries += 1
        answer = reasoner(
            question + "\n(Previous draft had unsupported claims: "
            + str(verdict.get("issues")) + ". Use only the context.)", chunks, audience)
        verdict = validator(question, answer, chunks, trace)
    if not verdict.get("grounded"):
        answer = "I could not produce a fully grounded answer. Aditya can answer this directly."
    trace["validation"] = verdict
    trace["retries"] = retries
    sources = _cited_sources(answer, chunks)
    cta = LEAD_CTA if audience == "client" and _LEAD_INTENT.search(question) else None
    if audience == "client" and answer.startswith("Not found"):
        answer = "I don't have that on file. Aditya can answer it directly."
        cta = LEAD_CTA
        sources = []
    suggestions = []
    if answer.startswith(("I don't have that", "Not found", "I could not")):
        suggestions = qu.suggest(question)  # help the visitor re-ask in words the KB answers
    trace["total_ms"] = round((time.perf_counter() - t0) * 1000)
    return {"answer": answer, "sources": sources, "trace": trace, "cta": cta, "suggestions": suggestions}
