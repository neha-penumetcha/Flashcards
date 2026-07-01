"""
flip_card.py
Renders one flashcard as a real 3D-flipping index card using CSS
`perspective` + `rotateY` + `backface-visibility`. The flip itself is
handled entirely client-side (JS toggles a class on click) - no round
trip to Streamlit/Python needed, which is what makes the animation feel
instant instead of laggy.

Each card gets a unique `key` baked into its CSS class names so multiple
renders on the same page don't clash.
"""

import streamlit.components.v1 as components
import html as html_lib


def render_flip_card(question: str, answer: str, key: str, height: int = 320):
    # Escape user/LLM-generated text so it can't break the HTML structure
    q = html_lib.escape(question)
    a = html_lib.escape(answer)

    card_html = f"""
    <style>
        .scene-{key} {{
            perspective: 1200px;
            width: 100%;
            height: {height - 20}px;
            font-family: 'Space Grotesk', sans-serif;
        }}
        .card-{key} {{
            position: relative;
            width: 100%;
            height: 100%;
            cursor: pointer;
            transform-style: preserve-3d;
            transition: transform 0.55s cubic-bezier(0.4, 0.2, 0.2, 1);
        }}
        .card-{key}.flipped {{
            transform: rotateY(180deg);
        }}
        .face-{key} {{
            position: absolute;
            inset: 0;
            backface-visibility: hidden;
            border-radius: 16px;
            border: 2px dashed rgba(246,243,233,0.35);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 28px;
            box-sizing: border-box;
        }}
        .front-{key} {{
            background: #234840;
            color: #F6F3E9;
        }}
        .back-{key} {{
            background: #FF6B5B;
            color: #1E3A34;
            transform: rotateY(180deg);
        }}
        .eyebrow-{key} {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            letter-spacing: 2px;
            text-transform: uppercase;
            opacity: 0.7;
            margin-bottom: 14px;
        }}
        .text-{key} {{
            font-size: 1.35rem;
            font-weight: 600;
            line-height: 1.5;
        }}
        .hint-{key} {{
            position: absolute;
            bottom: 14px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.7rem;
            opacity: 0.6;
        }}
    </style>

    <div class="scene-{key}">
        <div class="card-{key}" id="cardEl-{key}" onclick="this.classList.toggle('flipped')">
            <div class="face-{key} front-{key}">
                <div class="eyebrow-{key}">Question</div>
                <div class="text-{key}">{q}</div>
                <div class="hint-{key}">tap to flip</div>
            </div>
            <div class="face-{key} back-{key}">
                <div class="eyebrow-{key}">Answer</div>
                <div class="text-{key}">{a}</div>
                <div class="hint-{key}">tap to flip back</div>
            </div>
        </div>
    </div>
    """
    components.html(card_html, height=height)
