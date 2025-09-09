#!/usr/bin/env python3
"""
watcher.py (Day 2)
- watches screenshots directory for new images
- delegates OCR and note creation to ocr_utils.create_note_from_image()
- updates site via generate_index.generate_site()
- commits & pushes changes via git_ops.git_add_commit_push()
"""

import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from dotenv import load_dotenv

load_dotenv()

LOG = logging.getLogger("envisage.watcher")
LOG.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
LOG.addHandler(ch)

from ocr_utils import configure_tesseract, create_note_from_image
import git_ops
import generate_index

BASE = Path(__file__).resolve().parents[1]
DATA_DIR = BASE / "data"
SCREEN_DIR = DATA_DIR / "screenshots"


def wait_for_file_complete(path: Path, timeout=10.0, poll_interval=0.35):
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


class NewImageHandler(PatternMatchingEventHandler):
    def __init__(self, **kwargs):
        super().__init__(patterns=["*.png", "*.jpg", "*.jpeg", "*.bmp", "*.tif", "*.tiff", "*.webp"],
                         ignore_directories=True, case_sensitive=False)
        self._busy = set()

    def on_created(self, event):
        path = Path(event.src_path)
        LOG.info(f"New file event: {path}")
        if path in self._busy:
            return
        self._busy.add(path)
        try:
            if not wait_for_file_complete(path):
                LOG.warning("File didn't stabilize, proceeding anyway.")
            # Run OCR & create note
            note_path = create_note_from_image(path, source="screenshot", topics="general", version="1.0")
            LOG.info(f"OCR created note: {note_path}")
            # Regenerate site index
            generate_index.generate_site()
            LOG.info("Site regenerated.")
            # Commit & push
            res = git_ops.git_add_commit_push(repo_dir=str(BASE), message=f"Add note: {note_path.name}", all_files=True)
            LOG.info("GitOps result: %s", res)
        except Exception as e:
            LOG.exception("Error processing new screenshot: %s", e)
        finally:
            # small delay then clear busy
            time.sleep(0.25)
            self._busy.discard(path)


def main(watch_dir: str | None = None, tesseract_cmd: str | None = None):
    configure_tesseract(tesseract_cmd)
    SCREEN_DIR.mkdir(parents=True, exist_ok=True)
    handler = NewImageHandler()
    observer = Observer()
    observer.schedule(handler, path=watch_dir or str(SCREEN_DIR), recursive=False)
    observer.start()
    LOG.info("Watching directory: %s", watch_dir or SCREEN_DIR)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        LOG.info("Stopping watcher...")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
