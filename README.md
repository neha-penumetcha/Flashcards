# Flashcards Generator

https://flashcards-gkc5hq4xkyalu3ejd3hzpj.streamlit.app/

Upload any amount of study material (PDFs, PPTs, Word docs, or even scanned/
handwritten notes as images) and get exam-ready flashcards with an in-app
flip-card quiz mode. Runs entirely on free tiers.

## How it works
1. **extractor.py** - pulls text out of whatever you upload. Scanned PDFs
   and images go through OCR (Tesseract) automatically.
2. **chunker.py** - splits huge documents into ~900-word chunks so the LLM
   never chokes on size, no matter how big the upload is.
3. **flashcard_gen.py** - sends each chunk to Groq's free llama-3.3-70b
   model, gets back structured flashcards, and removes near-duplicates.
4. **app.py** - the Streamlit UI: upload tab + quiz tab with flip cards,
   shuffle, and next/previous navigation.

## Run locally

```bash
# 1. Install Tesseract OCR (needed for scanned notes)
#    Windows: https://github.com/UB-Mannheim/tesseract/wiki
#    Mac: brew install tesseract poppler
#    Linux: sudo apt install tesseract-ocr poppler-utils

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

Get a **free** Groq API key at https://console.groq.com/keys (no credit
card needed) and paste it into the sidebar when the app opens.

## Deploy free on Streamlit Community Cloud
1. Push this folder to a GitHub repo (same flow as your ATS checker project)
2. Go to share.streamlit.io -> New app -> point it at `app.py`
3. Streamlit Cloud automatically installs `packages.txt` (Tesseract +
   Poppler) and `requirements.txt` for you - no extra config needed
4. Paste your Groq key into the sidebar once deployed (or store it in
   Streamlit's Secrets manager for convenience)

## Notes on "any size" handling
- Multiple files can be uploaded at once and get merged into one deck
- Large files are chunked automatically - a 300-page PDF just takes longer
  (progress bar shows chunk-by-chunk status), it won't fail
- Overlapping chunks + dedup logic prevent the same concept from producing
  5 nearly identical flashcards

## Possible extensions (good for your portfolio write-up)
- Export to Anki (.apkg) using the `genanki` library
- Spaced repetition scheduling (SM-2 algorithm) instead of simple next/prev
- Difficulty tagging (easy/medium/hard) via a second LLM pass
- Persist decks in SQLite so they survive across sessions/devices
