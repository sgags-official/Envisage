#!/usr/bin/env python3
"""
generate_index.py
- parse notes metadata (frontmatter)
- convert markdown to HTML per-note
- build site/index.html with table of notes sorted by created_utc (newest first)
- exposes generate_site(notes_dir=..., site_dir=...)
"""

from pathlib import Path
import re
import html
from datetime import datetime
import markdown as md
import argparse
import logging

LOG = logging.getLogger("envisage.generate")
LOG.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
LOG.addHandler(ch)

BASE = Path(__file__).resolve().parents[1]
NOTES_DIR = BASE / "data" / "notes"
SITE_DIR = BASE / "site"
SITE_NOTES_DIR = SITE_DIR / "notes"

FRONT_RE = re.compile(r"^---\s*(.*?)\s*---\s*", re.S)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (meta_dict, rest_text)."""
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


def title_from_md(mdtext: str) -> str:
    for line in mdtext.splitlines():
        l = line.strip()
        if l.startswith("# "):
            return l[2:].strip()
    # fallback first non-empty
    for line in mdtext.splitlines():
        if line.strip():
            return line.strip()[:80]
    return "Untitled"


def ensure_dirs():
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    SITE_NOTES_DIR.mkdir(parents=True, exist_ok=True)


def _parse_iso(dt_str: str):
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except Exception:
            return None


def build_note_html(md_path: Path) -> dict:
    raw = md_path.read_text(encoding="utf-8")
    meta, body_md = parse_frontmatter(raw)
    title = meta.get("title") or title_from_md(body_md) or md_path.stem
    html_body = md.markdown(body_md)
    created = meta.get("created_utc", "")
    created_dt = _parse_iso(created) if created else None
    out_name = md_path.stem + ".html"
    out_path = SITE_NOTES_DIR / out_name
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
.meta{{color:#444;font-size:0.9rem}}
</style>
</head>
<body>
<header>
<h1>{html.escape(title)}</h1>
<p class="meta">source: {html.escape(meta.get('source','-'))} • original: {html.escape(meta.get('orig_filename','-'))} • topics: {html.escape(meta.get('topics','-'))} • version: {html.escape(meta.get('version','-'))} • created_utc: {html.escape(created)}</p>
</header>
<main>{html_body}</main>
<footer style="margin-top:2rem"><small>ENVISAGE notes — generated {datetime.utcnow().isoformat()}Z</small></footer>
</body></html>
"""
    out_path.write_text(note_html, encoding="utf-8")
    return {
        "title": title,
        "created_utc": created,
        "created_dt": created_dt,
        "source": meta.get("source", ""),
        "topics": meta.get("topics", ""),
        "version": meta.get("version", ""),
        "path": f"notes/{out_name}",
        "md_name": md_path.name
    }


def build_index(entries: list[dict]):
    # Sort by created_dt (newest first). If no dt, put at the end.
    entries_sorted = sorted(entries, key=lambda e: e["created_dt"] or datetime.min, reverse=True)

    rows = []
    for e in entries_sorted:
        created = e["created_utc"] or ""
        rows.append(
            f"<tr>"
            f"<td><a href=\"{e['path']}\">{html.escape(e['title'])}</a></td>"
            f"<td>{html.escape(created)}</td>"
            f"<td>{html.escape(e['source'])}</td>"
            f"<td>{html.escape(e['topics'])}</td>"
            f"<td>{html.escape(e['version'])}</td>"
            f"<td>{html.escape(e['md_name'])}</td>"
            f"</tr>"
        )

    idx_html = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ENVISAGE Notes</title>
<style>
body{{font-family:system-ui;max-width:1100px;margin:2rem auto;padding:1rem}}
table{{width:100%;border-collapse:collapse}}
th,td{{text-align:left;padding:0.6rem;border-bottom:1px solid #eee}}
th{{background:#fafafa}}
</style>
</head>
<body>
<h1>ENVISAGE — Notes</h1>
<p>Auto-generated index of OCR notes (sorted by newest first).</p>
<table>
<thead><tr><th>Title</th><th>Created (UTC)</th><th>Source</th><th>Topics</th><th>Ver</th><th>File</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
<footer><small>ENVISAGE — index generated {datetime.utcnow().isoformat()}Z</small></footer>
</body></html>
"""
    (SITE_DIR / "index.html").write_text(idx_html, encoding="utf-8")


def generate_site(notes_dir: str | None = None, site_dir: str | None = None):
    notes_dir = Path(notes_dir) if notes_dir else NOTES_DIR
    site_dir = Path(site_dir) if site_dir else SITE_DIR
    SITE_DIR = site_dir
    SITE_NOTES_DIR = SITE_DIR / "notes"
    NOTES_DIR = notes_dir
    ensure_dirs()

    entries = []
    for md in sorted(NOTES_DIR.glob("*.md")):
        try:
            info = build_note_html(md)
            entries.append(info)
        except Exception as e:
            LOG.exception("Failed to build note %s: %s", md, e)
    build_index(entries)
    LOG.info("Site generated at: %s", SITE_DIR.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--notes-dir")
    parser.add_argument("--site-dir")
    args = parser.parse_args()
    generate_site(notes_dir=args.notes_dir, site_dir=args.site_dir)
