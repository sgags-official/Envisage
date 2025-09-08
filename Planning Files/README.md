Save as README.md in repo root:

# ENVISAGE — Day 1: Initial setup + basic OCR watcher

This repo contains the Day-1 scaffold for ENVISAGE: a small local system which watches screenshots and clipboard images, extracts text via Tesseract OCR, stores notes, and can generate a tiny static site for browsing notes.

## Quick start

1. Create & activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1


2. Install Python deps:


    pip install -r requirements.txt


3. Install Tesseract OCR on your OS:

Windows: install the Tesseract Windows installer or choco install -y tesseract

macOS: brew install tesseract

Ubuntu: sudo apt update && sudo apt install -y tesseract-ocr

4. Verify:
    
    
    tesseract --version


5. Prepare directories:

    
    mkdir -p data/screenshots data/clipboard data/notes site/notes src


6. Copy .env.template → .env and edit if tesseract is not on PATH:

    
    cp .env.template .env
    # edit .env to set TESSERACT_CMD if needed