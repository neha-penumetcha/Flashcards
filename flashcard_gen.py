"""
flashcard_gen.py
Calls Groq's free-tier LLM (llama-3.3-70b-versatile) to turn one text chunk
into a list of flashcards, then dedupes overlapping/near-identical cards
across chunks (since overlap in chunker.py can cause repeats).

Get a free Groq API key at: https://console.groq.com/keys
"""

import requests
import json
import re
from difflib import SequenceMatcher

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"


def generate_flashcards_for_chunk(chunk: str, api_key: str, num_cards: int = 6, temperature: float = 0.4) -> list[dict]:
    """
    Sends one chunk of study material to Groq and asks for flashcards back
    as strict JSON. Returns a list of {"question": ..., "answer": ...}.

    temperature controls variety - use the default for a first pass, and a
    higher value (e.g. 0.8) when regenerating more questions from material
    that's already been covered, so the new batch reads differently rather
    than repeating the same phrasing.
    """
    prompt = f"""You are an exam-prep assistant. Read the study material below and create
{num_cards} high-quality flashcards for exam revision.

Rules:
- Questions should test understanding, not just word-matching (mix definition, "why", "how", and application questions)
- Answers should be concise (1-3 sentences), exam-ready
- Skip content that's just formatting/headers with no real information
- Respond with ONLY a JSON array, nothing else. No markdown fences, no preamble.

Format:
[{{"question": "...", "answer": "..."}}]

Study material:
\"\"\"{chunk}\"\"\"
"""

    try:
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": 2000,
            },
            timeout=60,
        )
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Couldn't reach Groq — check your internet connection.")
    except requests.exceptions.Timeout:
        raise RuntimeError("Groq took too long to respond (timed out after 60s). Try again.")

    if response.status_code == 401:
        raise RuntimeError("Invalid Groq API key — double check .streamlit/secrets.toml.")
    if response.status_code == 429:
        raise RuntimeError("Groq rate limit hit — wait a few seconds and try again.")
    response.raise_for_status()  # catches any other unexpected HTTP error

    raw_text = response.json()["choices"][0]["message"]["content"]
    return _parse_flashcard_json(raw_text)


def _parse_flashcard_json(raw_text: str) -> list[dict]:
    """
    LLMs sometimes wrap JSON in ```json fences despite instructions not to.
    Strip those, then parse. If parsing fails, return an empty list instead
    of crashing the whole app (one bad chunk shouldn't kill the run).
    """
    cleaned = re.sub(r"```json|```", "", raw_text).strip()
    try:
        cards = json.loads(cleaned)
        # Basic validation - only keep well-formed cards
        return [
            c for c in cards
            if isinstance(c, dict) and c.get("question") and c.get("answer")
        ]
    except json.JSONDecodeError:
        return []


def dedup_flashcards(cards: list[dict], similarity_threshold: float = 0.8) -> list[dict]:
    """
    Removes near-duplicate flashcards (common when chunk overlap causes the
    same concept to get a card twice). Uses simple string similarity -
    no extra ML dependency needed, keeps it free and fast.
    """
    unique_cards = []
    for card in cards:
        is_duplicate = False
        for existing in unique_cards:
            similarity = SequenceMatcher(
                None, card["question"].lower(), existing["question"].lower()
            ).ratio()
            if similarity > similarity_threshold:
                is_duplicate = True
                break
        if not is_duplicate:
            unique_cards.append(card)
    return unique_cards
