#!/usr/bin/env python3
"""
ocr_utils.py
- configure_tesseract()
- extract_text(image_path) -> text
- create_note_from_image(image_path, source='screenshot', topics=None, version='1.0') -> Path(note_md)
Writes a Markdown file with YAML-like frontmatter metadata into data/notes/.
"""

from pathlib import Path
from datetime import datetime, timezone
from PIL import Image, UnidentifiedImageError, Image
import pytesseract
import logging
import os
from dotenv import load_dotenv

load_dotenv()

LOG = logging.getLogger("envisage.ocr")
LOG.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
LOG.addHandler(ch)

# Project base and dirs
BASE = Path(__file__).resolve().parents[1]
DATA_DIR = BASE / "data"
NOTES_DIR = DATA_DIR / "notes"
NOTES_DIR.mkdir(parents=True, exist_ok=True)


def configure_tesseract(cmd_from_env: str | None = None):
    """Set pytesseract path if provided via env or arg."""
    tcmd = cmd_from_env or os.getenv("TESSERACT_CMD")
    if tcmd:
        pytesseract.pytesseract.tesseract_cmd = tcmd
        LOG.info(f"Using Tesseract at: {pytesseract.pytesseract.tesseract_cmd}")
    else:
        LOG.info("Using tesseract from PATH (if available).")


def _utc_now_iso():
    """ISO timestamp for metadata (timezone-aware)."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _safe_ts_for_filename():
    """Windows-safe timestamp string for filenames: YYYYMMDDTHHMMSS_mmmmmmZ"""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")


def extract_text(image_path: Path, tesseract_config: str = "") -> str:
    """Extract text from image using pytesseract. Returns string."""
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"{image_path} not found")

    try:
        img = Image.open(image_path)
    except UnidentifiedImageError as e:
        LOG.error(f"Cannot open image {image_path}: {e}")
        raise

    try:
        text = pytesseract.image_to_string(img, config=tesseract_config or "")
    except Exception as e:
        LOG.exception("Tesseract OCR failed")
        text = f"[OCR ERROR] {e}"
    return text


def create_note_from_image(image_path: Path, source: str = "screenshot",
                           topics: str | None = None, version: str = "1.0",
                           tesseract_config: str = "") -> Path:
    """
    Run OCR on a given image and create a markdown note with metadata.
    Returns Path to created markdown file.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(image_path)

    # ensure directories
    NOTES_DIR.mkdir(parents=True, exist_ok=True)

    # Run OCR
    LOG.info(f"OCR extracting from: {image_path}")
    text = extract_text(image_path, tesseract_config=tesseract_config)

    # Create metadata
    created_utc = _utc_now_iso()
    safe_ts = _safe_ts_for_filename()
    safe_name = image_path.stem.replace(" ", "_")
    out_filename = f"{safe_ts}__{safe_name}.md"
    out_path = NOTES_DIR / out_filename

    topics_field = (topics or "general").strip()
    meta_lines = [
        "---",
        f"created_utc: {created_utc}",
        f"source: {source}",
        f"orig_filename: {image_path.name}",
        f"topics: {topics_field}",
        f"version: {version}",
        f"ocr_engine: tesseract",
        "---",
        ""
    ]

    body_lines = text.splitlines() if text else ["(no text)"]
    out_path.write_text("\n".join(meta_lines + body_lines), encoding="utf-8")
    LOG.info(f"Note written: {out_path}")
    return out_path
