"""Unit tests for exporter.py."""

import csv
import json
import os

import pytest

from exporter import to_csv, to_json

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MC = {
    "question": "What is the powerhouse of the cell?",
    "type": "multiple_choice",
    "options": ["A) Nucleus", "B) Mitochondria", "C) Ribosome", "D) Golgi"],
    "correct_answer": "B",
    "explanation": "Mitochondria produce ATP.",
    "difficulty": "easy",
    "topic": "Cell Biology",
}

TF = {
    "question": "Mitochondria have their own DNA.",
    "type": "true_false",
    "options": ["True", "False"],
    "correct_answer": "True",
    "explanation": "They carry circular DNA.",
    "difficulty": "medium",
    "topic": "Genetics",
}

SA = {
    "question": "Describe the function of mitochondria.",
    "type": "short_answer",
    "options": [],
    "correct_answer": "They produce ATP.",
    "explanation": "Mitochondria are the cell's energy factories.",
    "difficulty": "hard",
    "topic": "Cell Biology",
}

QUIZ = [MC, TF, SA]


# ---------------------------------------------------------------------------
# to_json
# ---------------------------------------------------------------------------


def test_to_json_creates_file(tmp_path):
    out = tmp_path / "quiz.json"
    to_json(QUIZ, str(out))
    assert out.exists()


def test_to_json_round_trips_data(tmp_path):
    out = tmp_path / "quiz.json"
    to_json(QUIZ, str(out))
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded == QUIZ


def test_to_json_pretty_printed(tmp_path):
    out = tmp_path / "quiz.json"
    to_json(QUIZ, str(out))
    raw = out.read_text(encoding="utf-8")
    assert "\n" in raw  # indented output has newlines


def test_to_json_preserves_unicode(tmp_path):
    q = {**MC, "question": "¿Cuál es la función de las mitocondrias?"}
    out = tmp_path / "quiz.json"
    to_json([q], str(out))
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded[0]["question"] == q["question"]


def test_to_json_raises_on_empty_quiz(tmp_path):
    with pytest.raises(ValueError, match="empty"):
        to_json([], str(tmp_path / "out.json"))


def test_to_json_overwrites_existing_file(tmp_path):
    out = tmp_path / "quiz.json"
    out.write_text("old content")
    to_json([MC], str(out))
    loaded = json.loads(out.read_text())
    assert loaded == [MC]


# ---------------------------------------------------------------------------
# to_csv
# ---------------------------------------------------------------------------


def _read_csv(path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_to_csv_creates_file(tmp_path):
    out = tmp_path / "quiz.csv"
    to_csv(QUIZ, str(out))
    assert out.exists()


def test_to_csv_header_columns(tmp_path):
    out = tmp_path / "quiz.csv"
    to_csv(QUIZ, str(out))
    rows = _read_csv(out)
    expected_cols = {
        "question", "type", "option_a", "option_b",
        "option_c", "option_d", "correct_answer",
        "explanation", "difficulty", "topic",
    }
    assert set(rows[0].keys()) == expected_cols


def test_to_csv_row_count(tmp_path):
    out = tmp_path / "quiz.csv"
    to_csv(QUIZ, str(out))
    rows = _read_csv(out)
    assert len(rows) == 3


def test_to_csv_multiple_choice_options(tmp_path):
    out = tmp_path / "quiz.csv"
    to_csv([MC], str(out))
    row = _read_csv(out)[0]
    assert row["option_a"] == "A) Nucleus"
    assert row["option_b"] == "B) Mitochondria"
    assert row["option_c"] == "C) Ribosome"
    assert row["option_d"] == "D) Golgi"
    assert row["correct_answer"] == "B"


def test_to_csv_true_false_options(tmp_path):
    out = tmp_path / "quiz.csv"
    to_csv([TF], str(out))
    row = _read_csv(out)[0]
    assert row["option_a"] == "True"
    assert row["option_b"] == "False"
    assert row["option_c"] == ""
    assert row["option_d"] == ""


def test_to_csv_short_answer_options_blank(tmp_path):
    out = tmp_path / "quiz.csv"
    to_csv([SA], str(out))
    row = _read_csv(out)[0]
    assert row["option_a"] == ""
    assert row["option_b"] == ""
    assert row["option_c"] == ""
    assert row["option_d"] == ""


def test_to_csv_all_fields_present(tmp_path):
    out = tmp_path / "quiz.csv"
    to_csv([MC], str(out))
    row = _read_csv(out)[0]
    assert row["question"] == MC["question"]
    assert row["type"] == "multiple_choice"
    assert row["difficulty"] == "easy"
    assert row["topic"] == "Cell Biology"
    assert row["explanation"] == MC["explanation"]


def test_to_csv_raises_on_empty_quiz(tmp_path):
    with pytest.raises(ValueError, match="empty"):
        to_csv([], str(tmp_path / "out.csv"))


def test_to_csv_overwrites_existing_file(tmp_path):
    out = tmp_path / "quiz.csv"
    out.write_text("stale,data\n1,2")
    to_csv([MC], str(out))
    rows = _read_csv(out)
    assert len(rows) == 1
    assert rows[0]["type"] == "multiple_choice"


def test_to_csv_mixed_types_in_single_file(tmp_path):
    out = tmp_path / "quiz.csv"
    to_csv(QUIZ, str(out))
    rows = _read_csv(out)
    types = [r["type"] for r in rows]
    assert types == ["multiple_choice", "true_false", "short_answer"]
