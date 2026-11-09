"""Rebuild docs/DOCUMENTATION.pdf from docs/DOCUMENTATION.md.   python scripts/make_pdfs.py
Needs: pandoc, and `pip install playwright && playwright install chromium`. Optional: the PDF is already included."""
from __future__ import annotations

import base64
import re
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
LOGO = "data:image/png;base64," + base64.b64encode((ROOT / "assets" / "logo_small.png").read_bytes()).decode()
DOCS = [("DOCUMENTATION", "STRENTOR Assistant: Documentation", "Concepts, setup, architecture, safety, testing, deployment and viva questions")]
DOCS_DIR = ROOT / "docs"
CSS = """
:root{--bg:#0A0A0A;--card:#1C1C1C;--text:#ECE8DF;--muted:#ADADAD;--gold:#C99C53;--line:#3a3a3a}
@page{size:A4;margin:14mm 0 22mm} tr,li,pre,img,blockquote{break-inside:avoid} thead{display:table-row-group} p{orphans:3;widows:3} h2,h3{break-after:avoid}
*{box-sizing:border-box}
html,body{background:var(--bg);color:var(--text);margin:0}
body{font-family:'Satoshi','Helvetica Neue',Helvetica,Arial,sans-serif;font-size:10.2pt;line-height:1.55}
.hero{padding:2mm 14mm 7mm;border-bottom:2px solid var(--gold);display:flex;align-items:center;gap:7mm}
.hero img{height:34mm;width:auto;flex:none}
.hero h1{margin:0 0 1.5mm;font-size:21pt;line-height:1.15;color:var(--text)}
.hero p{margin:0;color:var(--muted);font-size:9.5pt}
main{padding:7mm 14mm 4mm}
h2{color:var(--gold);font-size:14pt;margin:7mm 0 2.5mm;padding-bottom:1.5mm;border-bottom:1px solid var(--line);break-after:avoid}
h3{color:var(--text);font-size:11pt;break-after:avoid}
p,li{orphans:3;widows:3}
a{color:var(--gold)}
strong{color:#fff}
img{max-width:100%}
code{font-family:Menlo,Consolas,monospace;font-size:8.6pt;background:var(--card);color:var(--gold);padding:.2mm 1.2mm;border-radius:1mm}
pre{background:var(--card);border-left:3px solid var(--gold);padding:3mm;overflow:hidden;break-inside:avoid;white-space:pre-wrap}
pre code{background:none;padding:0;color:var(--text)}
table{border-collapse:collapse;width:100%;margin:3mm 0;font-size:9pt}
tr{break-inside:avoid}
th{background:var(--gold);color:#0A0A0A;text-align:left;padding:1.8mm 2.4mm}
td{background:var(--card);padding:1.8mm 2.4mm;border-bottom:1px solid var(--line);vertical-align:top}
"""
BAR = "background:#0A0A0A;width:100%;margin:0;-webkit-print-color-adjust:exact;print-color-adjust:exact;"
HEADER = "<div></div>"
FOOTER = (f'<div style="{BAR}height:22mm;font-size:7.5px;color:#ADADAD;text-align:center;padding-top:6mm;box-sizing:border-box">'
          '<span style="color:#C99C53;letter-spacing:2px">STRENTOR</span> &nbsp;·&nbsp; Break. Build. Become. &nbsp;·&nbsp; '
          'page <span class="pageNumber"></span> of <span class="totalPages"></span></div>')


def body_html(md: Path) -> str:
    text = re.sub(r'^<p align="center">.*?</p>\s*', "", md.read_text(encoding="utf-8"), flags=re.S)  # PDF has its own logo header
    html = subprocess.run(["pandoc", "-f", "markdown+lists_without_preceding_blankline", "-t", "html"],
                          input=text, capture_output=True, text=True, check=True).stdout
    return re.sub(r"^<h1[^>]*>.*?</h1>\s*", "", html, count=1, flags=re.S)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for stem, title, sub in DOCS:
            page_file = DOCS_DIR / f"_{stem}.html"  # next to the .md so relative image paths resolve
            page_file.write_text(
                f'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title><style>'
                f"@import url('https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700,800&display=swap');{CSS}</style></head><body>"
                f'<div class="hero"><img src="{LOGO}" alt="STRENTOR"><div><h1>{title}</h1><p>{sub}</p></div></div>'
                f"<main>{body_html(DOCS_DIR / (stem + '.md'))}</main></body></html>", encoding="utf-8")
            pg = browser.new_page()
            pg.goto(page_file.as_uri())
            pg.wait_for_timeout(800)
            pg.pdf(path=str(DOCS_DIR / f"{stem}.pdf"), format="A4", display_header_footer=True,
                   header_template=HEADER, footer_template=FOOTER, print_background=True)
            pg.close()
            page_file.unlink()
            _paint_background(DOCS_DIR / f"{stem}.pdf")
            print("wrote", f"{stem}.pdf")
        browser.close()


def _paint_background(path):
    """Put a solid brand-dark layer under every page so no margin shows white."""
    import io
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    reader, writer = PdfReader(str(path)), PdfWriter()
    for page in reader.pages:
        w, h = float(page.mediabox.width), float(page.mediabox.height)
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(w, h))
        c.setFillColorRGB(10 / 255, 10 / 255, 10 / 255)
        c.rect(0, 0, w, h, stroke=0, fill=1)
        c.save()
        bg = PdfReader(io.BytesIO(buf.getvalue())).pages[0]
        bg.merge_page(page)
        writer.add_page(bg)
    with open(path, "wb") as f:
        writer.write(f)


if __name__ == "__main__":
    main()
