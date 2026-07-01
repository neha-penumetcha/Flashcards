"""
app.py - FlashGen: Bulk Material -> Flashcards -> In-App Quiz
Run locally with:  streamlit run app.py
Deploy free on Streamlit Community Cloud (same as your ATS checker).
"""

import streamlit as st
import random
from extractor import extract_text
from chunker import chunk_text
from flashcard_gen import generate_flashcards_for_chunk, dedup_flashcards

st.set_page_config(page_title="FlashGen - AI Flashcard Generator", page_icon="🤓", layout="centered")

# ---------- SESSION STATE SETUP ----------
# session_state persists data across reruns (Streamlit reruns the whole
# script on every interaction, so anything we want to "remember" - like
# generated flashcards or quiz progress - must live here).
if "flashcards" not in st.session_state:
    st.session_state.flashcards = []
if "quiz_index" not in st.session_state:
    st.session_state.quiz_index = 0
if "show_answer" not in st.session_state:
    st.session_state.show_answer = False
if "known_count" not in st.session_state:
    st.session_state.known_count = 0

st.title("🤓 FlashGen")
st.caption("Upload any study material (PDFs, PPTs, Word docs, even scanned notes) and get exam-ready flashcards.")

# ---------- SIDEBAR: API KEY ----------
# Check st.secrets FIRST (works both locally via .streamlit/secrets.toml
# and on Streamlit Cloud via the dashboard's Secrets manager).
# Only fall back to an on-screen input if no secret is configured -
# this way your key never has to be typed/pasted in front of anyone
# viewing your screen, and never lives in the code itself.
secret_key = st.secrets.get("GROQ_API_KEY", None)

with st.sidebar:
    st.header("Setup")
    if secret_key:
        api_key = secret_key
        st.success("Groq API key loaded from secrets ✅")
    else:
        api_key = st.text_input(
            "Groq API Key",
            type="password",
            help="Free key from console.groq.com/keys - takes 30 seconds to get",
        )
    cards_per_chunk = st.slider("Flashcards per chunk", 3, 10, 6)
    st.markdown("---")
    st.markdown(f"**Cards generated so far:** {len(st.session_state.flashcards)}")
    if st.session_state.flashcards:
        if st.button("🗑️ Clear all flashcards"):
            st.session_state.flashcards = []
            st.session_state.quiz_index = 0
            st.rerun()

# ---------- UPLOAD + GENERATE ----------
tab1, tab2 = st.tabs(["📤 Upload & Generate", "🎴 Quiz Mode"])

with tab1:
    uploaded_files = st.file_uploader(
        "Upload material (multiple files allowed - any size)",
        type=["pdf", "docx", "pptx", "txt", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
    )

    if st.button("Generate Flashcards", type="primary", disabled=not (uploaded_files and api_key)):
        if not api_key:
            st.error("Add your free Groq API key in the sidebar first.")
        else:
            all_new_cards = []
            progress = st.progress(0.0, text="Starting...")

            # Step 1: extract text from every uploaded file
            all_chunks = []
            for f in uploaded_files:
                progress.progress(0.05, text=f"Reading {f.name}...")
                text = extract_text(f.name, f.read())
                chunks = chunk_text(text)
                all_chunks.extend(chunks)

            if not all_chunks:
                st.warning("Couldn't extract any text from these files. Are they empty or corrupted?")
            else:
                # Step 2: generate flashcards chunk by chunk, updating progress
                # as we go so large uploads don't feel frozen
                for i, chunk in enumerate(all_chunks):
                    progress.progress(
                        (i + 1) / len(all_chunks),
                        text=f"Generating flashcards... chunk {i + 1}/{len(all_chunks)}",
                    )
                    try:
                        cards = generate_flashcards_for_chunk(chunk, api_key, cards_per_chunk)
                        all_new_cards.extend(cards)
                    except Exception as e:
                        st.warning(f"Skipped one chunk due to an error: {e}")

                # Step 3: dedup against everything (new + previously generated)
                combined = st.session_state.flashcards + all_new_cards
                st.session_state.flashcards = dedup_flashcards(combined)
                progress.empty()
                st.success(f"Done! {len(all_new_cards)} new flashcards generated "
                           f"({len(st.session_state.flashcards)} total after removing duplicates).")

    # Preview generated cards
    if st.session_state.flashcards:
        with st.expander(f"Preview all {len(st.session_state.flashcards)} flashcards"):
            for i, card in enumerate(st.session_state.flashcards, 1):
                st.markdown(f"**Q{i}: {card['question']}**")
                st.markdown(f"_{card['answer']}_")
                st.divider()

with tab2:
    cards = st.session_state.flashcards

    if not cards:
        st.info("Generate some flashcards first in the Upload tab.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔀 Shuffle deck"):
                random.shuffle(st.session_state.flashcards)
                st.session_state.quiz_index = 0
                st.session_state.show_answer = False
                st.rerun()
        with col2:
            st.markdown(f"**Progress:** {st.session_state.quiz_index + 1} / {len(cards)}")

        current = cards[st.session_state.quiz_index]

        # ---- The flip card itself ----
        st.markdown("### ")
        card_box = st.container(border=True)
        with card_box:
            if not st.session_state.show_answer:
                st.markdown(f"#### ❓ {current['question']}")
                st.button("Flip to see answer", on_click=lambda: st.session_state.update(show_answer=True))
            else:
                st.markdown(f"#### ✅ {current['answer']}")
                st.button("Flip back to question", on_click=lambda: st.session_state.update(show_answer=False))

        st.markdown("")

        # ---- Navigation ----
        nav1, nav2, nav3 = st.columns(3)
        with nav1:
            if st.button("⬅️ Previous", disabled=st.session_state.quiz_index == 0):
                st.session_state.quiz_index -= 1
                st.session_state.show_answer = False
                st.rerun()
        with nav2:
            if st.button("I knew this ✅"):
                st.session_state.known_count += 1
                if st.session_state.quiz_index < len(cards) - 1:
                    st.session_state.quiz_index += 1
                    st.session_state.show_answer = False
                    st.rerun()
        with nav3:
            if st.button("Next ➡️", disabled=st.session_state.quiz_index >= len(cards) - 1):
                st.session_state.quiz_index += 1
                st.session_state.show_answer = False
                st.rerun()
