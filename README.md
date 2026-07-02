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
