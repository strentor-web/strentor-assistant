"""Regenerates docs/architecture.png.   python scripts/make_diagram.py"""
from __future__ import annotations

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parent.parent / "docs" / "architecture.png"
BG, INK, MUTED, GOLD = "#0A0A0A", "#ECE8DF", "#ADADAD", "#C99C53"
C = {"ingest": "#1B2430", "store": "#3A2F17", "agent": "#17301F", "guard": "#3A1B1B", "ui": "#2A2236", "out": "#1C1C1C"}

fig, ax = plt.subplots(figsize=(15, 8.4), dpi=150, facecolor=BG)
ax.set_facecolor(BG)
ax.set_xlim(0, 15)
ax.set_ylim(0, 8.4)
ax.axis("off")


def box(x, y, w, h, title, sub, color, task=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc=color, ec=GOLD, lw=1.2))
    ax.text(x + w / 2, y + h * 0.66, title, ha="center", va="center", fontsize=10.5, weight="bold", color=INK)
    ax.text(x + w / 2, y + h * 0.30, sub, ha="center", va="center", fontsize=8, color=MUTED)
    if task:
        ax.text(x + w - 0.08, y + h - 0.1, task, ha="right", va="top", fontsize=7.5, color=INK, weight="bold")


def arrow(x1, y1, x2, y2, label=None, style="-|>", rad=0.0, color=INK):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=1.3, connectionstyle=f"arc3,rad={rad}"))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.17, label, ha="center", fontsize=7.5, color=MUTED, style="italic")


ax.text(0.2, 8.05, "STRENTOR Assistant: architecture", fontsize=15, weight="bold", color=INK)
ax.text(0.2, 7.7, "Streamlit UI  >  service layer  >  agents  >  ChromaDB.  Task numbers (T1-T10) refer to the capstone brief.",
        fontsize=9, color=MUTED)

# Lane 1: ingestion
ax.text(0.2, 7.2, "A. Ingestion (team mode or data/kb at start-up)", fontsize=10.5, weight="bold", color=INK)
y, h, w = 5.9, 1.05, 2.05
xs = [0.2, 2.65, 5.1, 7.55, 10.0]
box(xs[0], y, w, h, "Upload / URL", "PDF, TXT, MD, CSV, Excel", C["ingest"], "T2 T3")
box(xs[1], y, w, h, "Validate", "type, size, empty, corrupt", C["guard"], "T9")
box(xs[2], y, w, h, "Parse", "pages, sheets, CSV rows", C["ingest"], "T3")
box(xs[3], y, w, h, "Chunk", "1000 chars, 150 overlap", C["ingest"], "T4")
box(xs[4], y, w, h, "Embed", "MiniLM, runs locally", C["ingest"], "T5")
box(12.45, y, 2.3, h, "ChromaDB", "visibility: public | internal", C["store"], "T5")
for i in range(4):
    arrow(xs[i] + w, y + h / 2, xs[i + 1], y + h / 2)
arrow(xs[4] + w, y + h / 2, 12.45, y + h / 2)

# Lane 2: query
ax.text(0.2, 5.35, "B. Question answering (every chat message)", fontsize=10.5, weight="bold", color=INK)
y2 = 3.95
box(0.2, y2, 1.75, h, "Question", "chat input", C["out"], "T2")
box(2.2, y2, 2.1, h, "Guardrails", "length, injection, medical", C["guard"], "T9")
box(4.55, y2, 1.75, h, "1. Planner", "split into sub-queries", C["agent"], "T8")
box(6.55, y2, 2.1, h, "2. Retriever", "search_documents tool", C["agent"], "T6 T8")
box(8.9, y2, 2.05, h, "3. Reasoner", "LLM or extractive", C["agent"], "T7 T8")
box(11.2, y2, 1.9, h, "4. Validator", "check_grounding tool", C["agent"], "T8 T9")
box(13.3, y2, 1.5, h, "Answer", "sources + CTA", C["out"], "T7")
pairs = [(0.2 + 1.75, 2.2), (2.2 + 2.1, 4.55), (4.55 + 1.75, 6.55), (6.55 + 2.1, 8.9), (8.9 + 2.05, 11.2), (11.2 + 1.9, 13.3)]
for a, b in pairs:
    arrow(a, y2 + h / 2, b, y2 + h / 2)


def elbow(points, color=INK, label=None, lx=None, ly=None):
    xs_, ys_ = zip(*points)
    ax.plot(xs_[:-1], ys_[:-1], color=color, lw=1.3, solid_capstyle="round")
    arrow(points[-2][0], points[-2][1], points[-1][0], points[-1][1], color=color)
    if label:
        ax.text(lx, ly, label, fontsize=7.5, color=color if color != INK else MUTED, style="italic")


# chroma -> retriever (audience filter): down, across the gap, down into the retriever
mid = (y + y2 + h) / 2
elbow([(13.6, y), (13.6, mid), (7.6, mid), (7.6, y2 + h)], label="top-k similarity search; client mode sees public chunks only",
      lx=7.8, ly=mid + 0.08)
# retry loop (below the agents)
elbow([(12.15, y2), (12.15, y2 - 0.3), (9.9, y2 - 0.3), (9.9, y2)], label="ungrounded: retry once, else safe fallback",
      lx=9.95, ly=y2 - 0.52)
# medical short-circuit (below the retry loop)
elbow([(3.25, y2), (3.25, y2 - 0.85), (14.05, y2 - 0.85), (14.05, y2)], color="#EF7B7B",
      label="medical question: skips retrieval, redirects to the person's clinician", lx=3.4, ly=y2 - 0.78)

# Lane 3: UI, leads, ops
ax.text(0.2, 2.75, "C. Interface, leads and operations", fontsize=10.5, weight="bold", color=INK)
y3 = 1.5
box(0.2, y3, 3.4, h, "Streamlit UI (app.py)", "Chat | Evaluator guide | Leads | Self-test", C["ui"], "T1 T2")
box(3.9, y3, 2.8, h, "Lead form", "consent, validation, upsert", C["ui"])
box(7.0, y3, 2.5, h, "leads/leads.csv", "formula-safe, atomic write", C["store"])
box(9.8, y3, 2.4, h, "logs/app.log", "asks, blocks, errors", C["out"], "T9")
box(12.5, y3, 2.3, h, "Self-test + tests/", "14 live checks, 33 tests", C["agent"], "T9")
arrow(3.6, y3 + h / 2, 3.9, y3 + h / 2)
arrow(6.7, y3 + h / 2, 7.0, y3 + h / 2)

ax.text(0.2, 0.75, "T10: Docker image, run.sh / run.bat, Streamlit Cloud steps and documentation.",
        fontsize=9, color=INK)
ax.text(0.2, 0.4, "No LLM needed: with no Ollama or API key the same four agents run in extractive mode (rule-based plan, verbatim answers, sentence-level grounding check).",
        fontsize=9, color=MUTED)
LOGO = OUT.parent.parent / "assets" / "logo_small.png"
if LOGO.exists():
    ax.imshow(plt.imread(LOGO), extent=(13.45, 14.75, 6.95, 8.35), aspect="auto", zorder=5)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 8.4)
fig.savefig(OUT, bbox_inches="tight", facecolor=BG)
print("wrote", OUT)
