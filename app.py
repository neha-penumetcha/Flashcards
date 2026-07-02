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
from pdf_export import build_qa_pdf
from topic_map import generate_topic_map
from streamlit_agraph import agraph, Node, Edge, Config

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
if "stored_chunks" not in st.session_state:
    st.session_state.stored_chunks = []  # text chunks from every file uploaded so far
if "status_message" not in st.session_state:
    st.session_state.status_message = None  # (kind, text) - shown once, then cleared
if "source_files" not in st.session_state:
    st.session_state.source_files = []  # names of every file uploaded so far
if "topic_map" not in st.session_state:
    st.session_state.topic_map = None  # cached {"nodes": [...], "edges": [...]}

cards = st.session_state.flashcards


def _generate_and_append(chunks, cards_per_chunk, temperature=0.4):
    """
    Runs flashcard generation over the given chunks and appends only
    genuinely new (non-duplicate) cards to the existing deck - this is
    what makes "add more material" and "generate more questions" additive
    instead of overwriting what's already there. Returns (added_count, errors).
    """
    new_cards = []
    errors = []
    progress = st.progress(0.0, text="Generating...")
    for i, chunk in enumerate(chunks):
        progress.progress((i + 1) / len(chunks), text=f"Generating chunk {i + 1}/{len(chunks)}")
        try:
            new_cards.extend(
                generate_flashcards_for_chunk(chunk, api_key, cards_per_chunk, temperature=temperature)
            )
        except Exception as e:
            errors.append(str(e))
    progress.empty()
    combined = dedup_flashcards(st.session_state.flashcards + new_cards)
    added = len(combined) - len(st.session_state.flashcards)
    st.session_state.flashcards = combined
    return added, errors

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
            st.session_state.stored_chunks = []
            st.session_state.source_files = []
            st.session_state.topic_map = None
            st.rerun()

if not api_key:
    st.warning("No Groq key found in secrets.toml — add one to generate cards.")

# ---------- MAIN NAV ----------
page = option_menu(
    menu_title=None,
    options=["Quiz", "Review", "Topics"],
    icons=["collection-play", "card-checklist", "diagram-3"],
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
    # ---- Add material / generate more - always available, not just when empty ----
    with st.expander("➕ Add material or generate more questions", expanded=not cards):
        # Show the result of the last generate attempt (success, or what went wrong) -
        # stored in session_state so it survives the rerun instead of flashing and vanishing.
        if st.session_state.status_message:
            kind, text = st.session_state.status_message
            getattr(st, kind)(text)
            st.session_state.status_message = None

        uploaded_files = st.file_uploader(
            "Upload PDFs, PPTs, Word docs, or scanned/handwritten images — any size, any mix",
            type=["pdf", "docx", "pptx", "txt", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
        )
        cards_per_chunk = st.slider("Flashcards per chunk", 3, 10, 6)

        # "Generate more" only makes sense once there's material to draw on -
        # keep it hidden entirely (not just disabled) until after the first generation.
        if st.session_state.stored_chunks:
            col_a, col_b = st.columns(2)
        else:
            col_a = st.container()
            col_b = None

        with col_a:
            add_clicked = st.button(
                "Generate from these files", type="primary", disabled=not (uploaded_files and api_key)
            )
        more_clicked = False
        if col_b is not None:
            with col_b:
                more_clicked = st.button(
                    "🔁 Generate more (different)",
                    disabled=not api_key,
                    help="Reuses everything already uploaded to make a fresh, differently-worded batch.",
                )

        if add_clicked:
            all_chunks = []
            failed_files = []
            for f in uploaded_files:
                try:
                    text = extract_text(f.name, f.read())
                    all_chunks.extend(chunk_text(text))
                except Exception as e:
                    failed_files.append(f"{f.name} ({e})")

            if not all_chunks:
                reason = f" Failed: {'; '.join(failed_files)}" if failed_files else ""
                st.session_state.status_message = (
                    "warning",
                    "Couldn't extract any text from these files. Are they empty, corrupted, or password-protected?" + reason,
                )
            else:
                st.session_state.stored_chunks.extend(all_chunks)
                for f in uploaded_files:
                    if f.name not in st.session_state.source_files:
                        st.session_state.source_files.append(f.name)
                added, errors = _generate_and_append(all_chunks, cards_per_chunk)
                if errors:
                    st.session_state.status_message = (
                        "error", f"{added} cards added, but some chunks failed: {errors[0]}"
                    )
                else:
                    st.session_state.status_message = (
                        "success", f"{added} new cards added — {len(st.session_state.flashcards)} total in your deck."
                    )
            st.rerun()

        if more_clicked:
            # Higher temperature = more varied phrasing/coverage than the first pass;
            # dedup_flashcards inside _generate_and_append filters out anything too similar.
            added, errors = _generate_and_append(st.session_state.stored_chunks, cards_per_chunk, temperature=0.8)
            if errors:
                st.session_state.status_message = ("error", f"{added} cards added, but some chunks failed: {errors[0]}")
            elif added == 0:
                st.session_state.status_message = (
                    "info", "Didn't find any genuinely new questions this round — try again, or add more material."
                )
            else:
                st.session_state.status_message = (
                    "success", f"{added} new cards added — {len(st.session_state.flashcards)} total in your deck."
                )
            st.rerun()

    if not cards:
        st.info("Upload material above to get started — your quiz will start right here.")

    elif st.session_state.quiz_index >= len(cards):
        # ---- Quiz complete: show score summary instead of a card ----
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
        st.caption("Head to the Review tab for the full question-by-question breakdown, "
                    "or add more material above to keep going.")

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

        # ---- Download the whole deck as a PDF ----
        st.markdown("---")
        default_name = ", ".join(st.session_state.source_files) if st.session_state.source_files else "Study Deck"
        deck_name = st.text_input("Document name (shown on the PDF)", value=default_name)
        try:
            pdf_bytes = build_qa_pdf(cards, deck_name=deck_name)
            st.download_button(
                "📄 Download as PDF",
                data=pdf_bytes,
                file_name="flashgen_deck.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.error(f"Couldn't build the PDF: {e}")

# ---------- TOPICS PAGE: auto-generated concept map ----------
elif page == "Topics":
    st.markdown("# Topic map")
    st.caption("How the concepts in your deck connect to each other.")

    if not cards:
        st.info("Generate a deck first on the Quiz tab, then come back here.")
    else:
        col_gen, col_regen = st.columns([1, 1])
        with col_gen:
            gen_clicked = st.button(
                "📑 Generate topic map" if not st.session_state.topic_map else "Regenerate topic map",
                type="primary",
                disabled=not api_key,
            )

        if gen_clicked:
            with st.spinner("Mapping out how these concepts connect..."):
                st.session_state.topic_map = generate_topic_map(cards, api_key)
            st.rerun()

        data = st.session_state.topic_map
        if data is None:
            st.info("Click **Generate topic map** to visualize how your flashcards connect.")
        elif not data["nodes"]:
            st.warning("Couldn't build a topic map from this deck — try regenerating, or check your API key.")
        else:
            nodes = [
                Node(id=n["id"], label=n["label"], size=22, color="#FF6B5B", font={"color": "#F6F3E9"})
                for n in data["nodes"]
            ]
            edges = [
                Edge(source=e["source"], target=e["target"], label=e.get("label", ""), color="#8FD9C4")
                for e in data["edges"]
            ]
            config = Config(
                width="100%",
                height=520,
                directed=True,
                physics=True,
                hierarchical=False,
                nodeHighlightBehavior=True,
                highlightColor="#FFD166",
                collapsible=False,
                node={"labelProperty": "label"},
            )
            agraph(nodes=nodes, edges=edges, config=config)
            st.caption("Drag nodes to rearrange • scroll to zoom • click a node to highlight its connections")
