"""
app.py - FlashGen
- Upload lives in the main area (not sidebar) - shown when the deck is empty.
- API key comes from .streamlit/secrets.toml, never typed into the UI.
- Quiz card itself has "Got it right" / "Skip" - that's where scoring happens.
- Review tab is a plain Q&A list with a live score pulled from those marks.

Run locally with:  streamlit run app.py
First time setup: copy .streamlit/secrets.toml.example to .streamlit/secrets.toml
and paste your free Groq key in (console.groq.com/keys).
"""

import streamlit as st
from streamlit_option_menu import option_menu
import random

from extractor import extract_text
from chunker import chunk_text
from flashcard_gen import generate_flashcards_for_chunk, dedup_flashcards
from styles import inject_css
from flip_card import render_flip_card

st.set_page_config(page_title="FlashGen", page_icon="📑", layout="centered")
inject_css()

# ---------- API KEY FROM SECRETS ----------
# Reads .streamlit/secrets.toml - never shown in the UI, never typed by hand.
api_key = st.secrets.get("GROQ_API_KEY") if hasattr(st, "secrets") else None
if not api_key or api_key.startswith("your-") or api_key.startswith("paste-"):
    api_key = None

# ---------- SESSION STATE ----------
if "flashcards" not in st.session_state:
    st.session_state.flashcards = []
if "quiz_index" not in st.session_state:
    st.session_state.quiz_index = 0
# review_marks: {card_index: "correct"} - only "Got it right" on the quiz card writes here
if "review_marks" not in st.session_state:
    st.session_state.review_marks = {}
if "reveal" not in st.session_state:
    st.session_state.reveal = set()  # which review cards have their answer shown

cards = st.session_state.flashcards

# ---------- TOP BAR: branding + clear-deck tucked in the corner ----------
top_left, top_right = st.columns([5, 1])
with top_left:
    st.markdown("<p class='brand-logo'>Flash<span>Gen</span></p>", unsafe_allow_html=True)
    st.caption("your study board")
with top_right:
    if cards:
        if st.button("🗑️", help="Clear deck"):
            st.session_state.flashcards = []
            st.session_state.quiz_index = 0
            st.session_state.review_marks = {}
            st.session_state.reveal = set()
            st.rerun()

if not api_key:
    st.warning("No Groq key found in secrets.toml — add one to generate cards.")

# ---------- MAIN NAV ----------
page = option_menu(
    menu_title=None,
    options=["Quiz", "Review"],
    icons=["collection-play", "card-checklist"],
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0", "background-color": "transparent", "margin-bottom": "10px"},
        "icon": {"color": "#F6F3E9", "font-size": "16px"},
        "nav-link": {
            "font-family": "Space Grotesk",
            "color": "#C9C4B4",
            "font-size": "15px",
            "border-radius": "8px",
            "text-align": "center",
        },
        "nav-link-selected": {"background-color": "#FF6B5B", "color": "#1E3A34", "font-weight": "700"},
    },
    key="main_nav",
)

# ---------- QUIZ PAGE ----------
if page == "Quiz":
    if not cards:
        # ---- Upload lives HERE, in the main area, only shown when deck is empty ----
        st.markdown("# Upload your material")
        st.caption("PDFs, PPTs, Word docs, or scanned/handwritten images — any size, any mix.")

        uploaded_files = st.file_uploader(
            "Drop files here",
            type=["pdf", "docx", "pptx", "txt", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
        cards_per_chunk = st.slider("Flashcards per chunk", 3, 10, 6)

        if st.button("Generate flashcards", type="primary", disabled=not (uploaded_files and api_key)):
            all_new_cards = []
            progress = st.progress(0.0, text="Reading files...")

            all_chunks = []
            for f in uploaded_files:
                text = extract_text(f.name, f.read())
                all_chunks.extend(chunk_text(text))

            if not all_chunks:
                st.warning("Couldn't extract any text from these files. Are they empty or corrupted?")
            else:
                for i, chunk in enumerate(all_chunks):
                    progress.progress((i + 1) / len(all_chunks), text=f"Generating chunk {i + 1}/{len(all_chunks)}")
                    try:
                        all_new_cards.extend(generate_flashcards_for_chunk(chunk, api_key, cards_per_chunk))
                    except Exception as e:
                        st.warning(f"Skipped one chunk: {e}")

                st.session_state.flashcards = dedup_flashcards(all_new_cards)
                st.session_state.quiz_index = 0
                progress.empty()
                st.rerun()  # deck is no longer empty -> next run shows the quiz card

    else:
        # ---- Quiz complete: show score summary instead of a card ----
        if st.session_state.quiz_index >= len(cards):
            marks = st.session_state.review_marks
            attempted = len(marks)
            correct = sum(1 for v in marks.values() if v == "correct")
            pct = round((correct / attempted) * 100) if attempted else 0

            st.markdown("# Done! 🎉")
            st.markdown(
                f"<div class='stat-block'><span class='stat-number'>{pct}%</span>"
                f"<span class='stat-label'>{correct} correct out of {attempted} attempted "
                f"({len(cards)} cards total)</span></div>",
                unsafe_allow_html=True,
            )
            st.markdown("")
            st.caption("Head to the Review tab for the full question-by-question breakdown.")

            if st.button("🔁 Retake quiz"):
                st.session_state.quiz_index = 0
                st.rerun()

        else:
            # ---- Flip card + scoring lives HERE ----
            current = cards[st.session_state.quiz_index]

            top1, top2 = st.columns([3, 1])
            with top1:
                st.caption(f"Card {st.session_state.quiz_index + 1} of {len(cards)}")
                st.progress((st.session_state.quiz_index + 1) / len(cards))
            with top2:
                if st.button("🔀 Shuffle"):
                    random.shuffle(st.session_state.flashcards)
                    st.session_state.quiz_index = 0
                    st.rerun()

            render_flip_card(current["question"], current["answer"], key=f"card{st.session_state.quiz_index}")

            def _advance():
                st.session_state.quiz_index += 1  # can now reach len(cards) -> triggers summary screen

            nav1, nav2, nav3, nav4 = st.columns(4)
            with nav1:
                if st.button("⬅️ Previous", disabled=st.session_state.quiz_index == 0):
                    st.session_state.quiz_index -= 1
                    st.rerun()
            with nav2:
                # Marks this card correct AND moves to the next one - this is where scoring happens
                if st.button("Got it right ✅"):
                    st.session_state.review_marks[st.session_state.quiz_index] = "correct"
                    _advance()
                    st.rerun()
            with nav3:
                # Marks this card wrong AND moves to the next one
                if st.button("Got it wrong ❌"):
                    st.session_state.review_marks[st.session_state.quiz_index] = "incorrect"
                    _advance()
                    st.rerun()
            with nav4:
                # Moves on without marking it - stays "unattempted" in the Review score
                if st.button("Skip ⏭️"):
                    _advance()
                    st.rerun()

# ---------- REVIEW PAGE: plain Q&A list + live score ----------
elif page == "Review":
    if not cards:
        st.markdown("# Review")
        st.info("Nothing to review yet — generate a deck first on the Quiz tab.")
    else:
        marks = st.session_state.review_marks
        attempted = len(marks)
        correct = sum(1 for v in marks.values() if v == "correct")

        s1, s2, s3 = st.columns(3)
        for col, number, label in [
            (s1, len(cards), "Total cards"),
            (s2, attempted, "Attempted"),
            (s3, f"{correct}/{attempted}" if attempted else "—", "Score"),
        ]:
            with col:
                st.markdown(
                    f"<div class='stat-block'><span class='stat-number'>{number}</span>"
                    f"<span class='stat-label'>{label}</span></div>",
                    unsafe_allow_html=True,
                )

        st.markdown("")

        for i, card in enumerate(cards):
            with st.container(border=True):
                st.markdown(f"**Q{i + 1}. {card['question']}**")

                if i in st.session_state.reveal:
                    st.markdown(f"✅ **Answer:** {card['answer']}")
                else:
                    if st.button("Show answer", key=f"reveal_{i}"):
                        st.session_state.reveal.add(i)
                        st.rerun()

                if marks.get(i) == "correct":
                    st.caption("✅ You got this right in the quiz")
