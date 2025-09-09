from pathlib import Path
import os
from datetime import datetime
import markdown as md
import html
from datetime import timezone

# Global paths
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
NOTES_DIR = DATA_DIR / "notes"
SITE_DIR = BASE_DIR / "site"
SITE_NOTES_DIR = SITE_DIR / "notes"

SITE_DIR.mkdir(parents=True, exist_ok=True)
SITE_NOTES_DIR.mkdir(parents=True, exist_ok=True)


def parse_metadata(note_path):
    """Parse frontmatter metadata from a note file."""
    metadata = {}
    with open(note_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("---") or not line:
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                metadata[k.strip()] = v.strip()
            else:
                break
    metadata["filename"] = note_path.name
    return metadata



def build_note_html(md_path: Path):
    """Create HTML version of a single note."""
    raw = md_path.read_text(encoding="utf-8")
    meta, body = {}, raw
    lines = raw.splitlines()
    if lines and lines[0].strip() == "---":
        end_idx = None
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                end_idx = i
                break
        if end_idx:
            fm_lines = lines[1:end_idx]
            body = "\n".join(lines[end_idx+1:])
            for line in fm_lines:
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
    title = meta.get("title") or md_path.stem
    html_body = md.markdown(body)
    created = meta.get("created_utc", "")
    created_dt = None
    created_dt = None
    try:
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)
    except:
        created_dt = datetime.utcnow().replace(tzinfo=timezone.utc)

    # Write HTML version
    out_path = SITE_NOTES_DIR / f"{md_path.stem}.html"
    html_content = f"""<!doctype html>
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
<p class="meta">source: {html.escape(meta.get('source','-'))} • original: {html.escape(meta.get('orig_filename','-'))} • topics: {html.escape(meta.get('topic','-'))} • version: {html.escape(meta.get('version','-'))} • created_utc: {html.escape(created)}</p>
</header>
<main>{html_body}</main>
<footer style="margin-top:2rem"><small>ENVISAGE notes — generated {datetime.utcnow().isoformat()}Z</small></footer>
</body></html>
"""
    out_path.write_text(html_content, encoding="utf-8")

    meta["created_dt"] = created_dt
    meta["html_path"] = f"notes/{out_path.name}"
    return meta


def generate_site():
    """Generate full site: HTML notes + index.html grouped by topic & date."""
    SITE_NOTES_DIR.mkdir(parents=True, exist_ok=True)

    # Convert all notes to HTML and gather metadata
    entries = []
    for note_file in NOTES_DIR.glob("*.md"):
        try:
            meta = build_note_html(note_file)
            entries.append(meta)
        except Exception as e:
            print(f"Failed to process {note_file}: {e}")

    # Group by topic
    grouped = {}
    for e in entries:
        topic = e.get("topic", "general")
        grouped.setdefault(topic, []).append(e)

    for topic_notes in grouped.values():
        topic_notes.sort(
            key=lambda x: x.get("created_dt") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True
        )
    # Sort each topic by created_dt descending
    for topic_notes in grouped.values():
        topic_notes.sort(key=lambda x: x.get("created_dt") or datetime.min, reverse=True)

    # Build index.html
    html_lines = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'><title>ENVISAGE Notes</title>",
        "<style>body{font-family:sans-serif;} table{border-collapse: collapse;width:100%;} td, th{border:1px solid #ccc;padding:6px;} h2{margin-top:1.5em;} th{background:#f5f5f5}</style>",
        "</head><body>",
        "<h1>ENVISAGE Notes</h1>"
    ]

    for topic, topic_notes in grouped.items():
        html_lines.append(f"<h2>{topic}</h2>")
        html_lines.append("<table><tr><th>Date UTC</th><th>Note</th><th>Version</th><th>Source</th></tr>")
        for note in topic_notes:
            date = note.get("created_utc", "")
            filename = note.get("html_path")
            version = note.get("version", "1.0")
            source = note.get("source", "screenshot")
            html_lines.append(f"<tr><td>{date}</td><td><a href='{filename}'>{filename}</a></td><td>{version}</td><td>{source}</td></tr>")
        html_lines.append("</table>")

    html_lines.append("</body></html>")

    index_path = SITE_DIR / "index.html"
    index_path.write_text("\n".join(html_lines), encoding="utf-8")
    print(f"Site index updated: {index_path}")


if __name__ == "__main__":
    generate_site()
