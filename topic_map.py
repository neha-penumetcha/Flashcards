"""
topic_map.py
Turns a flashcard deck into a topic/concept map: asks Groq to identify the
main topics covered and how they relate to each other, then that structure
gets rendered as a draggable, physics-based graph in the Topics tab.

Built from the flashcard QUESTIONS only (not full answers) - keeps the
prompt compact regardless of how large the original uploaded material was,
since by this point the deck has already condensed everything down to its
key concepts.
"""

import requests
import json
import re

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"


def generate_topic_map(cards: list[dict], api_key: str) -> dict:
    """
    Returns {"nodes": [{"id": ..., "label": ...}], "edges": [{"source": ..., "target": ..., "label": ...}]}
    Falls back to an empty structure if the LLM response can't be parsed -
    the UI shows a friendly message rather than crashing.
    """
    questions = [c["question"] for c in cards]
    # Cap how many questions we send - keeps the prompt fast even on huge decks,
    # and a topic map with 200 nodes wouldn't be readable anyway.
    questions = questions[:80]
    joined = "\n".join(f"- {q}" for q in questions)

    prompt = f"""You are analyzing a set of exam-prep flashcard questions to build a topic map.

Flashcard questions:
{joined}

Identify the 6-16 main topics/concepts these questions cover, and how those
topics relate to each other (e.g. "is a type of", "depends on", "contrasts with",
"part of", "leads to"). Keep topic names short (2-5 words).

Respond with ONLY JSON in this exact format, nothing else, no markdown fences:
{{"nodes": [{{"id": "n1", "label": "Topic Name"}}],
  "edges": [{{"source": "n1", "target": "n2", "label": "relation"}}]}}
"""

    try:
        response = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 1500,
            },
            timeout=60,
        )
        response.raise_for_status()
        raw_text = response.json()["choices"][0]["message"]["content"]
    except Exception:
        return {"nodes": [], "edges": []}

    cleaned = re.sub(r"```json|```", "", raw_text).strip()
    try:
        data = json.loads(cleaned)
        nodes = [n for n in data.get("nodes", []) if n.get("id") and n.get("label")]
        node_ids = {n["id"] for n in nodes}
        # Only keep edges whose endpoints actually exist as nodes - avoids
        # the graph library erroring on a dangling reference from a
        # slightly malformed LLM response.
        edges = [
            e for e in data.get("edges", [])
            if e.get("source") in node_ids and e.get("target") in node_ids
        ]
        return {"nodes": nodes, "edges": edges}
    except json.JSONDecodeError:
        return {"nodes": [], "edges": []}
