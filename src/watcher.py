#!/usr/bin/env python3
"""
watcher.py
Watches data/screenshots/ for new images, OCRs them with pytesseract,
and writes timestamped markdown notes into data/notes/.
"""

import os
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image, UnidentifiedImageError
import pytesseract
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from dotenv import load_dotenv

# Load .env (optional)
load_dotenv()

LOG = logging.getLogger("envisage.watcher")
LOG.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
LOG.addHandler(ch)

# default locations
BASE = Path(__file__).resolve().parents[1]  # project root
DATA_DIR = BASE / "data"
SCREEN_DIR = DATA_DIR / "screenshots"
NOTES_DIR = DATA_DIR / "notes"

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}


def ensure_dirs():
    SCREEN_DIR.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)


def configure_tesseract(cmd_from_env=None):
    # prefer explicit env var TESSERACT_CMD or .env, else leave default
    tcmd = cmd_from_env or os.getenv("TESSERACT_CMD")
    if tcmd:
        pytesseract.pytesseract.tesseract_cmd = tcmd
        LOG.info(f"Using Tesseract at: {pytesseract.pytesseract.tesseract_cmd}")
    else:
        LOG.info("Using Tesseract from PATH (if available).")


def utc_now_iso():
    # Windows-safe UTC timestamp, no colons or plus signs
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")



def wait_for_file_complete(path: Path, timeout=10.0, poll_interval=0.35):
    """
    Wait until the file stops changing size (i.e., is fully written).
    """
    start = time.time()
    last_size = -1
    while True:
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            size = -1
        if size == last_size and size > 0:
            return True
        if time.time() - start > timeout:
            LOG.warning(f"Timeout waiting for file to complete: {path}")
            return False
        last_size = size
        time.sleep(poll_interval)


def ocr_image_to_markdown(img_path: Path, source_tag="screenshot"):
    LOG.info(f"OCR start: {img_path}")
    if img_path.suffix.lower() not in ALLOWED_EXT:
        LOG.info(f"Skipping unsupported filetype: {img_path}")
        return None

    if not wait_for_file_complete(img_path):
        LOG.warning(f"File not stable: {img_path} -- continuing anyway.")

    try:
        img = Image.open(img_path)
    except UnidentifiedImageError:
        LOG.error(f"Cannot open image: {img_path}")
        return None

    try:
        text = pytesseract.image_to_string(img)
    except Exception as e:
        LOG.exception("Tesseract OCR failed")
        text = f"[OCR ERROR] {e}"

    ts = utc_now_iso()
    safe_name = img_path.stem.replace(" ", "_")
    out_filename = f"{ts}__{safe_name}.md"
    out_path = NOTES_DIR / out_filename

    # YAML frontmatter-like metadata
    meta = [
        "---",
        f"source: {source_tag}",
        f"orig_filename: {img_path.name}",
        f"timestamp_utc: {ts}",
        f"ocr_engine: tesseract",
        "---",
        "",
    ]
    content_lines = meta + (text.splitlines() if text else ["(no text)"])

    out_path.write_text("\n".join(content_lines), encoding="utf-8")
    LOG.info(f"OCR saved note: {out_path}")
    return out_path


class NewImageHandler(PatternMatchingEventHandler):
    def __init__(self, **kwargs):
        super().__init__(patterns=["*.png", "*.jpg", "*.jpeg", "*.bmp", "*.tif", "*.tiff", "*.webp"],
                         ignore_directories=True, case_sensitive=False)
        self._busy = set()

    def on_created(self, event):
        path = Path(event.src_path)
        LOG.info(f"New file event: {path}")
        # Avoid duplicates
        if path in self._busy:
            return
        self._busy.add(path)
        try:
            ocr_image_to_markdown(path, source_tag="screenshot")
        finally:
            # small delay to avoid race with multiple events
            time.sleep(0.2)
            self._busy.discard(path)


def main():
    parser = argparse.ArgumentParser(description="ENVISAGE Day1 screenshot watcher + OCR")
    parser.add_argument("--dir", "-d", type=str, default=str(SCREEN_DIR), help="directory to watch for screenshots")
    parser.add_argument("--tesseract-cmd", "-t", type=str, default=None, help="explicit path to tesseract executable")
    args = parser.parse_args()

    configure_tesseract(args.tesseract_cmd)
    ensure_dirs()

    event_handler = NewImageHandler()
    observer = Observer()
    observer.schedule(event_handler, path=args.dir, recursive=False)
    observer.start()
    LOG.info(f"Watching directory: {args.dir}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        LOG.info("Stopping watcher...")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
