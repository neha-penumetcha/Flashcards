"""
pdf_export.py
Builds a downloadable PDF of all Q&A flashcards, for offline studying or
printing. Uses fpdf2 - pure Python, no system-level binaries required, so
it works out of the box on Streamlit Cloud.

Layout:
  FlashGen                       <- brand heading
  Document: <deck name>          <- subtitle
  ------------------------------
  Q1. question
      A: answer
  ------------------------------
  Q2. ...
"""

from fpdf import FPDF

BOARD_COLOR = (30, 58, 52)     # dark teal, matches the app's chalkboard theme
GRAY = (90, 90, 90)
ANSWER_GRAY = (60, 60, 60)


def _safe(text: str) -> str:
    """
    fpdf2's built-in core fonts (Helvetica) only support latin-1.
    Smart quotes, em-dashes, or stray OCR/LLM symbols would otherwise
    crash PDF generation - replace anything unsupported with '?'.
    """
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _wrap_long_tokens(text: str, max_len: int = 20) -> str:
    """
    fpdf2 can't wrap a single unbroken "word" (long URL, filename, run-on
    term) and raises FPDFException instead of truncating it. Break
    anything longer than max_len characters into space-separated chunks
    so there's always somewhere to wrap.
    """
    words = text.split(" ")
    fixed = []
    for w in words:
        if len(w) > max_len:
            fixed.append(" ".join(w[i:i + max_len] for i in range(0, len(w), max_len)))
        else:
            fixed.append(w)
    return " ".join(fixed)


def _clean(text: str, max_len: int = 20) -> str:
    return _wrap_long_tokens(_safe(text), max_len)


def _safe_multicell(pdf: FPDF, text: str, line_height: float = 6.5):
    """
    Renders text in a multi_cell while explicitly resetting the x position
    and using the page's actual effective width (pdf.epw) instead of the
    shorthand w=0. This is what actually fixes "not enough horizontal
    space" - that error happens when leftover x-position from a previous
    element shrinks the usable width to near zero. If a single card is
    still somehow unrenderable, fall back to a short placeholder instead
    of crashing the whole PDF.
    """
    try:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, line_height, text)
    except Exception:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, line_height, "[This line couldn't be rendered]")


def build_qa_pdf(cards: list[dict], deck_name: str = "Study Deck") -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ---- Heading: FlashGen ----
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*BOARD_COLOR)
    pdf.set_x(pdf.l_margin)
    pdf.cell(pdf.epw, 12, "FlashGen", new_x="LMARGIN", new_y="NEXT")

    # ---- Subtitle: document/deck name ----
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*GRAY)
    pdf.set_x(pdf.l_margin)
    pdf.cell(pdf.epw, 8, f"Document: {_clean(deck_name, max_len=60)}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin)
    pdf.cell(pdf.epw, 6, f"{len(cards)} questions", new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)
    pdf.set_draw_color(*BOARD_COLOR)
    pdf.set_line_width(0.6)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)

    # ---- Q&A list ----
    for i, card in enumerate(cards, 1):
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(0, 0, 0)
        _safe_multicell(pdf, _clean(f"Q{i}. {card.get('question', '')}"), line_height=7)

        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*ANSWER_GRAY)
        _safe_multicell(pdf, _clean(f"A: {card.get('answer', '')}"), line_height=6)

        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        pdf.set_draw_color(200, 200, 200)
        pdf.set_line_width(0.2)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(5)

    return bytes(pdf.output())
