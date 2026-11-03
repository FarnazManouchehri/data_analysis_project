"""Markdown report -> HTML page -> PDF (headless Chrome).

    python tools/render_pdf.py writeup/phase1_fa.md reports/phase1.pdf

The Markdown may contain HTML blocks (cover, callouts, figure cards) with markdown="1".
Persian text is laid out right-to-left; numbers, code and Latin-only table cells stay left-to-right.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import markdown

FONTS = ("https://fonts.googleapis.com/css2?family=Noto+Naskh+Arabic:wght@400;600;700"
         "&family=Noto+Sans+Arabic:wght@500;700;800&family=JetBrains+Mono:wght@400&display=swap")

STYLE = """
:root { --ink:#1e293b; --muted:#64748b; --teal:#0f766e; --teal-soft:#e6f4f1; --amber:#d97706;
        --amber-soft:#fef6e7; --plum:#6d28d9; --line:#e2e8f0; }
@page { size: A4; margin: 18mm 17mm 18mm 17mm; }
@page :first { margin: 0; }
html { direction: rtl; }
body { font-family: "Noto Naskh Arabic", serif; font-size: 10.6pt; line-height: 1.85; color: var(--ink);
       counter-reset: sec fig tab; margin: 0; }
h1, h2, h3, .kpi b, th { font-family: "Noto Sans Arabic", sans-serif; }
p, li { text-align: justify; }

/* ---------- cover ---------- */
.cover { height: 297mm; box-sizing: border-box; padding: 0; display: flex; flex-direction: column;
         break-after: page; background: #0b3b37; color: white; position: relative; overflow: hidden; }
.cover .band { padding: 36mm 20mm 14mm; background: linear-gradient(160deg, #0f766e 0%, #0b3b37 70%); }
.cover .course { font-family: "Noto Sans Arabic"; font-size: 10pt; letter-spacing: .02em; opacity: .85; margin: 0; }
.cover h1 { font-size: 25pt; line-height: 1.45; margin: 10mm 0 4mm; color: white; border: none; }
.cover .en { direction: ltr; text-align: left; font-family: "Noto Sans Arabic"; font-size: 11pt; opacity: .8; margin: 0; }
.cover .rule { width: 34mm; height: 2.2mm; background: var(--amber); margin: 9mm 0 0; border-radius: 2px; }
.cover .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5mm; padding: 10mm 20mm; }
.kpi { background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.18); border-radius: 4mm;
       padding: 5mm 4mm; text-align: center; }
.kpi b { display: block; font-size: 17pt; color: #fcd34d; direction: ltr; }
.kpi span { font-size: 8.6pt; opacity: .9; line-height: 1.5; display: block; margin-top: 1.5mm; }
.cover .who { margin-top: auto; padding: 0 20mm 22mm; font-size: 10pt; line-height: 2; }
.cover .who p { margin: 0; text-align: right; }
.cover .who b { color: #fcd34d; font-family: "Noto Sans Arabic"; }
.cover code { background: rgba(255,255,255,.14); color: white; }

/* ---------- headings ---------- */
h2 { counter-increment: sec; font-size: 14.5pt; margin: 9mm 0 3mm; color: var(--teal);
     display: flex; align-items: center; gap: 3mm; break-after: avoid; }
h2::before { content: counter(sec, persian); display: inline-flex; align-items: center; justify-content: center;
             width: 9mm; height: 9mm; border-radius: 50%; background: var(--teal); color: white; font-size: 11pt; flex: none; }
h2::after { content: ""; flex: 1; height: 0; border-top: 1.5px dashed var(--amber); margin-right: 2mm; }
h3 { font-size: 11.2pt; color: var(--plum); margin: 5mm 0 1.5mm; break-after: avoid; }
.toc { columns: 2; column-gap: 10mm; font-size: 9.6pt; background: var(--teal-soft); border-radius: 3mm;
       padding: 4mm 7mm; margin: 2mm 0 6mm; }
.toc ol { margin: 0; padding-right: 5mm; list-style: persian; }
.toc li { text-align: right; }

/* ---------- tables ---------- */
table { counter-increment: tab; border-collapse: separate; border-spacing: 0; width: 100%; margin: 3mm 0 2mm;
        font-size: 8.9pt; line-height: 1.55; break-inside: avoid; border: 1px solid var(--line); border-radius: 2.5mm;
        overflow: hidden; }
th { background: var(--teal); color: white; font-weight: 700; padding: 2mm 2.4mm; text-align: right; font-size: 8.6pt; }
td { padding: 1.6mm 2.4mm; text-align: right; vertical-align: top; border-top: 1px solid var(--line); }
tr:nth-child(even) td { background: #f8fafc; }
td[dir=ltr] { font-variant-numeric: tabular-nums; }
.tcap { font-size: 8.6pt; color: var(--muted); margin: 0 0 5mm; }
.tcap::before { content: "جدول " counter(tab, persian) " — "; color: var(--plum); font-weight: 700; }

/* ---------- figures ---------- */
.fig { counter-increment: fig; border: 1px solid var(--line); border-radius: 3mm; padding: 3mm 3mm 1.5mm;
       margin: 4mm 0 5mm; break-inside: avoid; background: white; }
.fig img { width: 100%; display: block; }
.fig.narrow img { width: 62%; margin: 0 auto; }
.fig p { margin: 0; }
.fig .cap { font-size: 8.7pt; color: var(--muted); margin-top: 1.5mm; line-height: 1.7; }
.fig .cap::before { content: "شکل " counter(fig, persian) " — "; color: var(--teal); font-weight: 700; }

/* ---------- callouts ---------- */
.find, .decide, .warn { border-radius: 2.5mm; padding: 2.5mm 4.5mm; margin: 3mm 0 4mm; break-inside: avoid; }
.find { background: var(--amber-soft); border-right: 4px solid var(--amber); }
.decide { background: var(--teal-soft); border-right: 4px solid var(--teal); }
.warn { background: #fdf2f8; border-right: 4px solid #be185d; }
.find > p:first-child::before { content: "یافته — "; font-weight: 700; color: var(--amber); font-family: "Noto Sans Arabic"; }
.decide > p:first-child::before { content: "تصمیم — "; font-weight: 700; color: var(--teal); font-family: "Noto Sans Arabic"; }
.warn > p:first-child::before { content: "هشدار نشت — "; font-weight: 700; color: #be185d; font-family: "Noto Sans Arabic"; }
.find p, .decide p, .warn p { margin: .6mm 0; }
.find ul, .decide ul, .warn ul { margin: 0; }

code { font-family: "JetBrains Mono", monospace; font-size: 8.3pt; background: #f1f5f9; padding: 0 1.2mm;
       border-radius: 1mm; direction: ltr; unicode-bidi: isolate; }
bdi { unicode-bidi: isolate; white-space: nowrap; }
.q { border: 1px solid var(--line); border-radius: 2.5mm; padding: 2mm 4mm; margin: 2mm 0; break-inside: avoid; }
.q.chosen { border: 2px solid var(--teal); background: var(--teal-soft); }
.refs { direction: ltr; text-align: left; font-size: 8.6pt; line-height: 1.6; }
.refs li { text-align: left; }
hr { border: none; border-top: 1px solid var(--line); margin: 6mm 0; }
"""

LATIN_ONLY = re.compile(r"^[^؀-ۿ]*$", re.S)


def postprocess(html: str) -> str:
    # Tables: cells without Persian letters (numbers, code, ranges) read left to right.
    html = re.sub(r"<td>((?:(?!</td>).)*)</td>",
                  lambda m: f"<td dir='ltr'>{m.group(1)}</td>" if LATIN_ONLY.match(m.group(1)) else m.group(0),
                  html, flags=re.S)
    # A table followed by a paragraph that starts with "Table:" gets a numbered caption.
    html = re.sub(r"<p>Table:\s*(.*?)</p>", r"<p class='tcap'>\1</p>", html, flags=re.S)
    # Keep hyphenated metric names and "x = number" expressions on one line, isolated as LTR.
    expr = re.compile(r"(?<![\w>])([A-Za-z][\w\-²]*(?: [A-Za-z][\w\-²]*)?\s?[=≈≥≤<>]\s?[−\-]?\$?\d[\d,]*(?:\.\d+)?%?)")
    parts = re.split(r"(<[^>]+>)", html)
    inside_code = False
    for i, part in enumerate(parts):
        if part.startswith("<"):
            inside_code = part.startswith("<code") or (inside_code and not part.startswith("</code"))
            continue
        if not inside_code:
            parts[i] = expr.sub(r"<bdi dir='ltr'>\1</bdi>", part)
    return "".join(parts)


def chrome() -> str:
    for c in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "google-chrome", "chromium"):
        if Path(c).exists() or shutil.which(c):
            return c
    raise SystemExit("Chrome/Chromium not found: open the HTML in writeup/_html and print it to PDF.")


def main(src: str, dst: str) -> None:
    md = Path(src).resolve()
    pdf = Path(dst).resolve()
    body = markdown.markdown(md.read_text(encoding="utf-8"), extensions=["tables", "md_in_html", "attr_list"])
    page = (f"<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'><title>{md.stem}</title>"
            f"<base href='{md.parent.as_uri()}/'><link rel='stylesheet' href='{FONTS}'><style>{STYLE}</style>"
            f"</head><body>{postprocess(body)}</body></html>")
    out = md.parent / "_html"
    out.mkdir(exist_ok=True)
    page_file = out / f"{md.stem}.html"
    page_file.write_text(page, encoding="utf-8")
    subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                    "--virtual-time-budget=20000", f"--print-to-pdf={pdf}", page_file.as_uri()],
                   check=True, capture_output=True)
    print(f"wrote {pdf}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
