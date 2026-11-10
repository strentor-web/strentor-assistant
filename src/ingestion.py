from __future__ import annotations
import re
from pathlib import Path
import pandas as pd
from pypdf import PdfReader
from . import config


class IngestionError(Exception):
    pass


def validate_file(path: Path) -> None:
    if path.suffix.lower() not in config.ALLOWED_EXT:
        raise IngestionError(f"Unsupported file type: {path.suffix}")
    if path.stat().st_size > config.MAX_FILE_MB * 1024 * 1024:
        raise IngestionError(f"File exceeds {config.MAX_FILE_MB} MB")
    if path.stat().st_size == 0:
        raise IngestionError("File is empty")


def load_file(path: Path) -> list[dict]:
    """Return list of {text, source, page} records."""
    validate_file(path)
    ext = path.suffix.lower()
    name = path.name
    try:
        if ext == ".pdf":
            reader = PdfReader(str(path))
            # join PDF line-wraps inside a paragraph so sentences stay whole
            recs = [{"text": _join_wrapped(p.extract_text() or ""), "source": name, "page": i + 1}
                    for i, p in enumerate(reader.pages)]
        elif ext in (".txt", ".md"):
            recs = [{"text": path.read_text(errors="ignore"), "source": name, "page": 1}]
        elif ext == ".csv":
            recs = _df_to_records(pd.read_csv(path), name, "csv")
        else:
            sheets = pd.read_excel(path, sheet_name=None)
            recs = [r for s, df in sheets.items() for r in _df_to_records(df, name, s)]
    except IngestionError:
        raise
    except Exception as e:
        raise IngestionError(f"Could not parse {name}: {e}")
    recs = [r for r in recs if r["text"].strip()]
    if not recs:
        raise IngestionError(f"No extractable text in {name}")
    return recs


def _join_wrapped(text: str) -> str:
    """Re-join PDF line-wraps inside a paragraph (long line, no end punctuation) but keep short
    heading lines and sentence ends on their own line."""
    out = []
    for line in text.split("\n"):
        if out and out[-1] and len(out[-1]) >= 50 and out[-1][-1] not in ".!?:" and line.strip():
            out[-1] += " " + line.strip()
        else:
            out.append(line)
    return "\n".join(out)


def _df_to_records(df: pd.DataFrame, name: str, sheet: str) -> list[dict]:
    """Group rows into blocks of 20, each row rendered as 'col: val' pairs."""
    df = df.fillna("")
    rows = [", ".join(f"{c}: {v}" for c, v in r.items()) for _, r in df.iterrows()]
    return [{"text": "\n".join(rows[i:i + 20]), "source": name, "page": f"{sheet}:{i + 1}"}
            for i in range(0, len(rows), 20)]


def _split_long(text: str, source: str, page: str) -> list[dict]:
    """Hard-split one long block: sentence > hard cut, with overlap."""
    size, overlap = config.CHUNK_SIZE, config.CHUNK_OVERLAP
    out, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = max(text.rfind("\n\n", start, end), text.rfind(". ", start, end))
            if cut > start + size // 2:
                end = cut + 1
        piece = text[start:end].strip()
        if piece:
            out.append({"text": piece, "source": source, "page": page})
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return out


def chunk_records(records: list[dict]) -> list[dict]:
    """Recursive-style splitter: paragraph > sentence > hard cut, with overlap."""
    out = []
    for r in records:
        out.extend(_split_long(r["text"], r["source"], str(r["page"])))
    return out


def _join_stat_fragments(text: str) -> str:
    """Web pages often put a figure and its label in separate tags ("89" then "Regions With Real, Priced Coaching").
    Glue number-only fragments onto the line that follows so the figure stays with its label."""
    import re
    out, prefix = [], []
    for frag in (f.strip() for f in text.split("\n")):
        if not frag:
            continue
        if re.fullmatch(r"[\d+\-\u2013.,%x/ ]{1,8}", frag):
            prefix.append(frag)
            continue
        out.append(" ".join(prefix + [frag]))
        prefix = []
    if prefix:
        out.append(" ".join(prefix))
    return "\n\n".join(out).strip()


def load_url(url: str) -> list[dict]:
    """Fetch a web page (e.g. a strentor.com page) and return text records."""
    import re
    import urllib.request
    if not url.startswith(("http://", "https://")):
        raise IngestionError("URL must start with http:// or https://")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "StrentorAssistant/1.0"})
        html = urllib.request.urlopen(req, timeout=20).read(3_000_000).decode("utf-8", "ignore")
    except Exception as e:
        raise IngestionError(f"Could not fetch {url}: {e}")
    html = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", "\n", html)
    text = re.sub(r"&nbsp;|&amp;", " ", text)
    text = _join_stat_fragments(re.sub(r"[ \t]+", " ", text))
    if len(text) < 50:
        raise IngestionError("No extractable text at that URL")
    return [{"text": text, "source": url.split("//", 1)[1].rstrip("/"), "page": 1}]
