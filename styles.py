"""
styles.py
Injects the "chalkboard study board" theme across the whole app.
Streamlit doesn't give us full CSS control by default, so we target
its stable data-testid attributes to restyle sidebar, buttons, headers,
progress bars, etc.

Design tokens (keep these consistent if you extend the UI further):
  --board        #1E3A34  deep chalkboard green (background)
  --board-light  #234840  slightly lighter panel green (cards/containers)
  --chalk        #F6F3E9  chalk white (primary text)
  --chalk-dim    #C9C4B4  muted chalk (secondary text)
  --coral        #FF6B5B  coral chalk (primary accent / CTAs / questions)
  --mint         #8FD9C4  mint chalk (success / "knew this" / answers)
  --yellow       #FFD166  yellow chalk (highlights / progress)
  --rule         rgba(246,243,233,0.14)  faint chalk rule lines

Fonts:
  Display (handwritten headers): 'Caveat'
  Body (readable UI text):       'Space Grotesk'
  Mono (stats/counters):         'JetBrains Mono'
"""

import streamlit as st

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Caveat:wght@600;700&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&family=Fredoka:wght@600;700&display=swap');

    :root {
        --board: #1E3A34;
        --board-light: #234840;
        --board-lighter: #2A5148;
        --chalk: #F6F3E9;
        --chalk-dim: #C9C4B4;
        --coral: #FF6B5B;
        --mint: #8FD9C4;
        --yellow: #FFD166;
        --rule: rgba(246,243,233,0.14);
    }

    /* ---- Global background + body text ---- */
    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: var(--board);
    }
    [data-testid="stAppViewContainer"] {
        background-image:
            radial-gradient(circle at 15% 20%, rgba(246,243,233,0.03) 0%, transparent 40%),
            radial-gradient(circle at 85% 75%, rgba(246,243,233,0.03) 0%, transparent 40%);
    }
    html, body, [class*="css"], p, span, label, div {
        font-family: 'Space Grotesk', sans-serif;
        color: var(--chalk);
    }

    /* ---- Handwritten headers ---- */
    h1, h2, h3 {
        font-family: 'Caveat', cursive !important;
        color: var(--chalk) !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px;
    }
    h1 { font-size: 3rem !important; border-bottom: 2px dashed var(--rule); padding-bottom: 0.3rem; }
    h4 { font-family: 'Space Grotesk', sans-serif !important; color: var(--chalk) !important; }

    /* ---- Brand logo (top bar, distinct from handwritten page headers) ---- */
    .brand-logo {
        font-family: 'Fredoka', sans-serif !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
        color: var(--chalk) !important;
        letter-spacing: 0.5px;
        margin-bottom: 0;
    }
    .brand-logo span { color: var(--coral) !important; }

    /* ---- Buttons: chalk-drawn look ---- */
    .stButton > button {
        background-color: transparent;
        color: var(--chalk) !important;
        border: 2px dashed var(--chalk-dim);
        border-radius: 10px;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        padding: 0.5rem 1.2rem;
        transition: all 0.15s ease;
    }
    .stButton > button:hover {
        border-color: var(--coral);
        color: var(--coral) !important;
        transform: translateY(-1px);
    }
    .stButton > button[kind="primary"] {
        background-color: var(--coral);
        border: none;
        color: var(--board) !important;
        font-weight: 700;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: var(--yellow);
        color: var(--board) !important;
    }

    /* ---- Progress bar ---- */
    [data-testid="stProgress"] > div > div {
        background-color: var(--yellow) !important;
    }

    /* ---- File uploader ---- */
    [data-testid="stFileUploader"] {
        border: 2px dashed var(--rule);
        border-radius: 12px;
        padding: 0.5rem;
        background-color: var(--board-light);
    }

    /* ---- Text input / slider labels ---- */
    [data-testid="stTextInput"] input {
        background-color: var(--board-lighter);
        color: var(--chalk);
        border: 1px dashed var(--rule);
    }

    /* ---- Dividers ---- */
    hr { border-top: 2px dashed var(--rule); }

    /* ---- Expander ---- */
    [data-testid="stExpander"] {
        border: 1px dashed var(--rule);
        border-radius: 10px;
        background-color: var(--board-light);
    }

    /* ---- Metric-style stat blocks (used on Dashboard) ---- */
    .stat-block {
        background-color: var(--board-light);
        border: 2px dashed var(--rule);
        border-radius: 14px;
        padding: 1.2rem 1.5rem;
        text-align: center;
    }
    .stat-number {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2.4rem;
        font-weight: 600;
        color: var(--yellow);
        display: block;
    }
    .stat-label {
        font-family: 'Space Grotesk', sans-serif;
        color: var(--chalk-dim);
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    </style>
    """, unsafe_allow_html=True)
