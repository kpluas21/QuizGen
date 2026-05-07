"""Streamlit web UI for the AI Quiz Generator."""

import io
import tempfile
import os

import streamlit as st

from exporter import to_csv, to_json
from generator import generate_quiz
from parser import parse_pdf, parse_text, parse_url

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Quiz Generator",
    page_icon="🧠",
    layout="centered",
)

# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def _reset():
    st.session_state.quiz = []
    st.session_state.answers = {}
    st.session_state.submitted = False
    st.session_state.current_q = 0


if "quiz" not in st.session_state:
    _reset()


# ---------------------------------------------------------------------------
# Sidebar — configuration
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Quiz Settings")

    num_questions = st.slider("Number of questions", 1, 20, 10)

    difficulty = st.selectbox(
        "Difficulty",
        ["easy", "medium", "hard"],
        index=1,
    )

    question_types = st.multiselect(
        "Question types",
        ["multiple_choice", "true_false", "short_answer"],
        default=["multiple_choice"],
    )
    if not question_types:
        question_types = ["multiple_choice"]

    st.markdown("---")
    st.caption("Powered by Claude · Anthropic")


# ---------------------------------------------------------------------------
# Screen 1 — Input
# ---------------------------------------------------------------------------

def _show_input_screen():
    st.title("🧠 AI Quiz Generator")
    st.write("Paste study material, upload a PDF, or point to a URL — Claude handles the rest.")

    input_type = st.radio(
        "Input type",
        ["Text", "PDF", "URL"],
        horizontal=True,
    )

    content = None
    error = None

    if input_type == "Text":
        raw = st.text_area(
            "Paste your study material here",
            height=250,
            placeholder="Minimum 100 words…",
        )
        if raw:
            try:
                content = parse_text(raw)
            except ValueError as exc:
                error = str(exc)

    elif input_type == "PDF":
        uploaded = st.file_uploader("Upload a PDF", type=["pdf"])
        if uploaded:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded.read())
                tmp_path = tmp.name
            try:
                content = parse_pdf(tmp_path)
            except (ValueError, FileNotFoundError) as exc:
                error = str(exc)
            finally:
                os.unlink(tmp_path)

    else:  # URL
        url = st.text_input("Enter a URL", placeholder="https://…")
        if url:
            try:
                content = parse_url(url)
            except (ValueError, Exception) as exc:
                error = str(exc)

    if error:
        st.error(error)

    ready = content is not None and not error
    if st.button("✨ Generate Quiz", disabled=not ready, type="primary"):
        with st.spinner(f"Generating {num_questions} questions…"):
            try:
                quiz = generate_quiz(
                    content,
                    num_questions=num_questions,
                    difficulty=difficulty,
                    question_types=question_types,
                )
                if not quiz:
                    st.error("No questions were generated. Try providing more study material.")
                    return
                st.session_state.quiz = quiz
                st.session_state.answers = {}
                st.session_state.submitted = False
                st.session_state.current_q = 0
                st.rerun()
            except Exception as exc:
                st.error(f"Generation failed: {exc}")


# ---------------------------------------------------------------------------
# Screen 2 — Quiz
# ---------------------------------------------------------------------------

def _show_quiz_screen():
    quiz = st.session_state.quiz
    total = len(quiz)

    st.title("📝 Quiz Time")
    progress = st.session_state.current_q / total
    st.progress(progress, text=f"Question {st.session_state.current_q + 1} of {total}")

    q_idx = st.session_state.current_q
    q = quiz[q_idx]

    st.markdown(f"### Q{q_idx + 1}. {q['question']}")
    st.caption(f"Topic: {q['topic']} · {q['difficulty'].capitalize()}")

    key = f"answer_{q_idx}"

    if q["type"] == "multiple_choice":
        choice = st.radio(
            "Select your answer:",
            q["options"],
            key=key,
            index=None,
        )
        answered = choice is not None

    elif q["type"] == "true_false":
        choice = st.radio(
            "Select your answer:",
            ["True", "False"],
            key=key,
            index=None,
        )
        answered = choice is not None

    else:  # short_answer
        choice = st.text_input("Your answer:", key=key)
        answered = bool(choice and choice.strip())

    if answered:
        st.session_state.answers[q_idx] = choice

    col_prev, col_next = st.columns([1, 1])

    with col_prev:
        if q_idx > 0:
            if st.button("← Previous"):
                st.session_state.current_q -= 1
                st.rerun()

    with col_next:
        if q_idx < total - 1:
            if st.button("Next →", disabled=not answered):
                st.session_state.current_q += 1
                st.rerun()
        else:
            all_answered = len(st.session_state.answers) == total
            if st.button("Submit Quiz ✅", disabled=not all_answered, type="primary"):
                st.session_state.submitted = True
                st.rerun()

    st.markdown("---")
    if st.button("🔄 Start Over"):
        _reset()
        st.rerun()


# ---------------------------------------------------------------------------
# Screen 3 — Results
# ---------------------------------------------------------------------------

def _show_results_screen():
    quiz = st.session_state.quiz
    answers = st.session_state.answers
    total = len(quiz)

    # Score (skip short_answer in auto-scoring)
    gradable = [i for i, q in enumerate(quiz) if q["type"] != "short_answer"]
    correct = sum(
        1 for i in gradable
        if _normalise(answers.get(i, "")) == _normalise(quiz[i]["correct_answer"])
    )
    scored = len(gradable)

    st.title("🏆 Results")
    if scored:
        pct = int(correct / scored * 100)
        st.metric("Score", f"{correct} / {scored}", f"{pct}%")
        if pct == 100:
            st.success("Perfect score! 🎉")
        elif pct >= 70:
            st.info("Great work! Keep it up.")
        else:
            st.warning("Keep studying — you'll get there!")
    else:
        st.info("Short-answer quiz — review your answers below.")

    st.markdown("---")

    # Per-question review
    for i, q in enumerate(quiz):
        user_ans = answers.get(i, "—")
        correct_ans = q["correct_answer"]

        if q["type"] == "short_answer":
            icon = "📝"
        elif _normalise(user_ans) == _normalise(correct_ans):
            icon = "✅"
        else:
            icon = "❌"

        with st.expander(f"{icon} Q{i + 1}: {q['question'][:80]}…"):
            if q["options"]:
                for opt in q["options"]:
                    st.write(f"  {opt}")
            st.markdown(f"**Your answer:** {user_ans}")
            st.markdown(f"**Correct answer:** {correct_ans}")
            st.info(q["explanation"])

    # Export
    st.markdown("---")
    st.subheader("Export")
    col_json, col_csv = st.columns(2)

    with col_json:
        buf = io.StringIO()
        import json as _json
        buf.write(_json.dumps(quiz, indent=2, ensure_ascii=False))
        st.download_button(
            "⬇ Download JSON",
            data=buf.getvalue(),
            file_name="quiz.json",
            mime="application/json",
        )

    with col_csv:
        import csv as _csv
        csv_buf = io.StringIO()
        fieldnames = [
            "question", "type", "option_a", "option_b", "option_c", "option_d",
            "correct_answer", "explanation", "difficulty", "topic",
        ]
        writer = _csv.DictWriter(csv_buf, fieldnames=fieldnames)
        writer.writeheader()
        for q in quiz:
            opts = q.get("options", [])
            writer.writerow({
                "question":       q.get("question", ""),
                "type":           q.get("type", ""),
                "option_a":       opts[0] if len(opts) > 0 else "",
                "option_b":       opts[1] if len(opts) > 1 else "",
                "option_c":       opts[2] if len(opts) > 2 else "",
                "option_d":       opts[3] if len(opts) > 3 else "",
                "correct_answer": q.get("correct_answer", ""),
                "explanation":    q.get("explanation", ""),
                "difficulty":     q.get("difficulty", ""),
                "topic":          q.get("topic", ""),
            })
        st.download_button(
            "⬇ Download CSV",
            data=csv_buf.getvalue(),
            file_name="quiz.csv",
            mime="text/csv",
        )

    st.markdown("---")
    if st.button("🔄 Generate Another Quiz", type="primary"):
        _reset()
        st.rerun()


def _normalise(s: str) -> str:
    """Strip and lowercase for lenient answer comparison."""
    return s.strip().lower() if s else ""


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

if st.session_state.submitted:
    _show_results_screen()
elif st.session_state.quiz:
    _show_quiz_screen()
else:
    _show_input_screen()
