"""
chunker.py
Why this exists: an LLM call can't safely take a 300-page textbook in one
shot (too many tokens, quality drops, and Groq's free tier has per-request
limits). So we split any amount of text into overlapping word-based chunks,
and flashcards get generated chunk-by-chunk.

This is the piece that makes "bulk material, any size" actually work.
"""

def chunk_text(text: str, chunk_size: int = 900, overlap: int = 100) -> list[str]:
    """
    Splits text into chunks of ~chunk_size words, with a bit of overlap
    so we don't lose context at chunk boundaries (e.g. a concept explained
    right at the cut-off point).

    chunk_size=900 words is roughly ~1200 tokens - safe and fast for Groq,
    while still giving the model enough context per chunk to write good
    questions (too small = shallow/trivial flashcards).
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap  # step back a bit for overlap

    return chunks
