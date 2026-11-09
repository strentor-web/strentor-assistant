"""STRENTOR brand theme, read from strentor.com (CSS variables and computed styles).

Palette: near-black #0A0A0A background, card #1C1C1C, warm off-white text #ECE8DF,
gold accent #C99C53, muted text #ADADAD, border #616161, success green #2FA366.
Font: Satoshi (Fontshare), falling back to system fonts when offline.
The official logo is bundled in assets/ (works offline).
"""
from __future__ import annotations

import base64
from functools import lru_cache

import streamlit as st

from . import config

LOGO_FILE = config.ROOT / "assets" / "logo_small.png"
FAVICON_FILE = config.ROOT / "assets" / "favicon.png"


@lru_cache(maxsize=1)
def _logo_uri() -> str:
    try:
        return "data:image/png;base64," + base64.b64encode(LOGO_FILE.read_bytes()).decode()
    except OSError:
        return ""


def favicon():
    """PIL image for the browser-tab icon, or an emoji if the file is missing."""
    try:
        from PIL import Image
        return Image.open(FAVICON_FILE)
    except Exception:
        return "💪"

CSS = """
<style>
@import url('https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700,800&display=swap');
:root { --ink:#0A0A0A; --panel:#141414; --raise:#1C1C1C; --bone:#ECE8DF; --gold:#C99C53; --gold-dim:#7D6232;
        --muted:#ADADAD; --line:#2A2A2A; }
html, body, .stApp, p, li, label, h1, h2, h3, h4, a, button, input, textarea, select,
[data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"] {
  font-family: 'Satoshi', system-ui, -apple-system, 'Segoe UI', Arial, sans-serif;
}
[data-testid="stIconMaterial"], .material-icons, [class*="material-symbols"] {
  font-family: 'Material Symbols Rounded', 'Material Icons' !important;
}
.stApp { background: var(--ink); color: var(--bone); }
.stApp p, .stApp li { line-height: 1.6; }
[data-testid="stMainBlockContainer"], .block-container { max-width: 860px; padding-top: 4.2rem; }
h1, h2, h3, h4 { color: #FFFFFF; font-weight: 700; letter-spacing: -0.015em; }
h2, h3 { font-size: 1.05rem; }
a { color: var(--gold); }
.muted { color: var(--muted); }
:focus-visible { outline: 2px solid var(--gold) !important; outline-offset: 2px; }

/* sidebar: quiet, so the conversation stays the focus */
[data-testid="stSidebar"] { background: #0F0F0F; border-right: 1px solid var(--line); }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] li { font-size: 0.9rem; color: #D6D2C9; }

/* header */
.brand-row { display: flex; align-items: center; gap: 20px; margin: 0 0 1.4rem 0; }
.brand-row .logo { height: 64px; width: auto; flex: none; }
.brand-row h1 { margin: 0; padding: 0; font-size: 2.05rem; line-height: 1.12; }
.brand-row .tag { margin: 6px 0 0 0; max-width: 56ch; font-size: 0.98rem; }
.brand .wordmark { font-size: 1.5rem; font-weight: 800; letter-spacing: 0.04em; color: #FFFFFF; }

/* buttons: outlined pills for actions, plain hairline rows for the example questions */
.stButton > button, .stDownloadButton > button {
  border-radius: 9999px; border: 1px solid #3A3A3A; background: transparent; color: var(--bone); font-weight: 600;
}
.stButton > button:hover, .stDownloadButton > button:hover { border-color: var(--gold); color: var(--gold); background: transparent; }
.stFormSubmitButton > button, .stButton > button[kind="primary"] {
  background: var(--gold); color: #0A0A0A; border: 1px solid var(--gold); border-radius: 9999px; font-weight: 700;
}
.stFormSubmitButton > button:hover { background: #D8AE68; color: #0A0A0A; }
[class*="st-key-ex"] button {
  border: 0; border-bottom: 1px solid var(--line); border-radius: 0; justify-content: flex-start; text-align: left;
  padding: 0.9rem 0.1rem 0.5rem 0.1rem; font-size: 1rem; font-weight: 600; min-height: 0;
}
[class*="st-key-ex"] button:hover { border-bottom-color: var(--gold); color: var(--gold); }
[class*="st-key-ex"] button > div, [class*="st-key-ex"] button [data-testid="stMarkdownContainer"] { width: 100%; justify-content: flex-start; text-align: left; }
[class*="st-key-ex"] button p { text-align: left; white-space: normal; }

/* conversation: an answer carries a gold rule (the "grounded" signal); the visitor's question is a quiet panel */
[data-testid^="stChatMessageAvatar"] { display: none; }
[data-testid="stChatMessage"] { background: transparent; border: 0; padding: 0.2rem 0; margin: 0.7rem 0; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: var(--panel); border-radius: 10px; padding: 0.7rem 1rem; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
  border-left: 3px solid var(--gold); padding-left: 1.1rem; border-radius: 0; }
.sources { margin-top: 0.7rem; display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem; }
.sources .label { color: var(--muted); font-size: 0.8rem; margin-right: 0.2rem; }
.sources .chip { border: 1px solid var(--gold-dim); color: var(--gold); border-radius: 6px; padding: 0.08rem 0.55rem; font-size: 0.8rem; }
[data-testid="stChatInput"] { border: 1px solid #3A3A3A; border-radius: 12px; background: var(--panel); }
[data-testid="stChatInput"]:focus-within { border-color: var(--gold); }

/* tabs, forms, inputs, expanders */
.stTabs [data-baseweb="tab-list"] { border-bottom: 1px solid var(--line); gap: 0.4rem; }
.stTabs [data-baseweb="tab"] { font-weight: 600; }
[data-baseweb="tab-highlight"] { background-color: var(--gold) !important; }
.stTabs [aria-selected="true"] { color: var(--gold) !important; }
[data-testid="stForm"] { border: 1px solid var(--line); border-radius: 10px; background: var(--panel); }
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div { background: var(--ink); border-color: #333333; }
[data-testid="stExpander"] { border: 1px solid var(--line); border-radius: 10px; background: transparent; }
</style>
"""


def apply() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def header() -> None:
    logo = _logo_uri()
    mark = (f'<img class="logo" alt="STRENTOR: Break. Build. Become." src="{logo}">' if logo
            else '<span class="wordmark">STRENTOR</span>')
    st.markdown(
        f'<div class="brand-row">{mark}<div>'
        "<h1>Questions about STRENTOR coaching?</h1>"
        "<p class='muted tag'>Wheelchair-first strength, nutrition and mindset coaching. "
        "Every answer comes from STRENTOR's own documents and shows its source.</p></div></div>",
        unsafe_allow_html=True)
