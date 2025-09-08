#!/usr/bin/env python3
"""
clipboard_monitor.py
Polls the system clipboard periodically and saves any image found into data/clipboard/.
Uses PIL.ImageGrab.grabclipboard() which works on Windows and macOS; Linux support is limited.
"""

import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from PIL import ImageGrab, UnidentifiedImageError
import argparse
import os
from dotenv import load_dotenv

load_dotenv()

LOG = logging.getLogger("envisage.clipboard")
LOG.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
LOG.addHandler(ch)

BASE = Path(__file__).resolve().parents[1]
CLIP_DIR = BASE / "data" / "clipboard"
ALLOWED_EXT = (".png", ".jpg", ".jpeg", ".bmp")

def utc_now_iso():
    # Windows-safe UTC timestamp, no colons or plus signs
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")


def ensure_dir():
    CLIP_DIR.mkdir(parents=True, exist_ok=True)

def save_clipboard_image(img, prefix="clipboard"):
    ts = utc_now_iso()
    filename = f"{ts}__{prefix}.png"
    out = CLIP_DIR / filename
    img.save(out)
    LOG.info(f"Saved clipboard image: {out}")
    return out

def grab_poll_loop(interval=1.0):
    ensure_dir()
    seen_hashes = set()
    try:
        while True:
            try:
                im = ImageGrab.grabclipboard()
            except Exception as e:
                LOG.debug(f"grabclipboard error: {e}")
                im = None

            if im is not None:
                try:
                    # if clipboard gave file list, PIL returns a list of filenames
                    if isinstance(im, list):
                        LOG.info("Clipboard contains file list; attempting to open first image file.")
                        candidate = Path(im[0])
                        if candidate.exists():
                            try:
                                from PIL import Image
                                img = Image.open(candidate)
                                saved = save_clipboard_image(img, prefix=candidate.stem)
                            except Exception as e:
                                LOG.exception("Failed to save clipboard file image")
                    else:
                        # im is a PIL Image instance
                        # quick duplicate prevention using bytes
                        try:
                            import io
                            b = io.BytesIO()
                            im.save(b, format="PNG")
                            digest = hash(b.getvalue())
                            if digest not in seen_hashes:
                                save_clipboard_image(im)
                                seen_hashes.add(digest)
                            else:
                                LOG.debug("Duplicate image in clipboard; skipping.")
                        except Exception:
                            save_clipboard_image(im)
                except UnidentifiedImageError:
                    LOG.debug("Clipboard content not an image")
            time.sleep(interval)
    except KeyboardInterrupt:
        LOG.info("Stopping clipboard monitor")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", "-i", type=float, default=1.0, help="poll interval seconds")
    args = parser.parse_args()
    grab_poll_loop(interval=args.interval)
