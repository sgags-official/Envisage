#!/usr/bin/env python3
"""
generate_index.py
Scans data/notes/*.md and generates a small static site under site/,
creating index.html and per-note HTML files.
"""

import re
from pathlib import Path
from datetime import datetime
import argparse
import html
import markdown as md

BASE = Path(__file__).resolve().parents[1]
NOTES_DIR = BASE / "data" / "notes"
SITE_DIR = BASE / "site"
SITE_NOTES = SITE_DIR / "notes"
VER = "ENVISAGE Day1 site generator v0.1"

FRONT_RE = re.compile(r"^---\s*(.*?)\s*---\s*", re.S)

def parse_frontmatter(text):
    m = FRONT_RE.match(text)
    meta = {}
    rest = text
    if m:
        fm = m.group(1)
        rest = text[m.end():]
        for line in fm.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    return meta, rest

def title_from_md(mdtext):
    for line in mdtext.splitlines():
        l = line.strip()
        if l.startswith("# "):
            return l[2:].strip()
    # fallback to first non-empty line
    for line in mdtext.splitlines():
        if line.strip():
            return line.strip()[:60]
    return "Untitled"

def ensure_dirs():
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    SITE_NOTES.mkdir(parents=True, exist_ok=True)

def build_note_html(md_path: Path):
    raw = md_path.read_text(encoding="utf-8")
    meta, body_md = parse_frontmatter(raw)
    title = meta.get("title") or title_from_md(body_md) or md_path.stem
    html_body = md.markdown(body_md)
    note_html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;max-width:900px;margin:2rem auto;padding:1rem}}
header{{border-bottom:1px solid #eee;margin-bottom:1rem;padding-bottom:0.5rem}}
pre,code{{background:#f5f5f5;padding:0.2rem 0.4rem;border-radius:4px}}
</style>
</head>
<body>
<header>
<h1>{html.escape(title)}</h1>
<p><small>source: {html.escape(meta.get('source','-'))} • original file: {html.escape(meta.get('orig_filename','-'))} • timestamp_utc: {html.escape(meta.get('timestamp_utc','-'))}</small></p>
</header>
<main>
{html_body}
</main>
<footer style="margin-top:2rem"><small>{VER} — generated {datetime.utcnow().isoformat()}Z</small></footer>
</body>
</html>
"""
    out_name = md_path.stem + ".html"
    out_path = SITE_NOTES / out_name
    out_path.write_text(note_html, encoding="utf-8")
    return {"title": title, "meta": meta, "path": f"notes/{out_name}", "src": md_path.name}

def build_index(note_entries):
    rows = []
    for e in sorted(note_entries, key=lambda x: x["meta"].get("timestamp_utc", ""), reverse=True):
        ts = e["meta"].get("timestamp_utc", "")
        rows.append(f'<li><a href="{e["path"]}">{html.escape(e["title"])}</a> — <small>{html.escape(ts)} — {html.escape(e["src"])}</small></li>')
    idx_html = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ENVISAGE Notes</title>
<style>body{{font-family:system-ui;max-width:900px;margin:2rem auto}}li{{margin:0.6rem 0}}</style>
</head>
<body>
<h1>ENVISAGE — Notes</h1>
<p>Auto-generated index of OCR notes.</p>
<ul>
{chr(10).join(rows)}
</ul>
<footer><small>{VER} — {datetime.utcnow().isoformat()}Z</small></footer>
</body></html>
"""
    (SITE_DIR / "index.html").write_text(idx_html, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--notes-dir", default=str(NOTES_DIR))
    parser.add_argument("--site-dir", default=str(SITE_DIR))
    args = parser.parse_args()
    ensure_dirs()
    entries = []
    notes = sorted(Path(args.notes_dir).glob("*.md"))
    for n in notes:
        try:
            info = build_note_html(n)
            entries.append(info)
        except Exception as e:
            print("Failed to build:", n, e)
    build_index(entries)
    print("Site generated at:", SITE_DIR.resolve())


if __name__ == "__main__":
    main()
