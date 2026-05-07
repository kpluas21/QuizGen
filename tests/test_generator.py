"""Unit tests for generator.py."""

import json
import warnings
from unittest.mock import MagicMock, patch

import pytest

from generator import (
    VALID_DIFFICULTIES,
    VALID_QUESTION_TYPES,
    generate_question,
    generate_quiz,
    validate_question,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

GOOD_MC = {
    "question": "What is the powerhouse of the cell?",
    "type": "multiple_choice",
    "options": ["A) Nucleus", "B) Mitochondria", "C) Ribosome", "D) Golgi"],
    "correct_answer": "B",
    "explanation": "Mitochondria produce ATP via cellular respiration.",
    "difficulty": "easy",
    "topic": "Cell Biology",
}

GOOD_TF = {
    "question": "Mitochondria have their own DNA.",
    "type": "true_false",
    "options": ["True", "False"],
    "correct_answer": "True",
    "explanation": "Mitochondria carry circular DNA.",
    "difficulty": "medium",
    "topic": "Cell Biology",
}

GOOD_SA = {
    "question": "Describe the function of mitochondria.",
    "type": "short_answer",
    "options": [],
    "correct_answer": "They produce ATP through cellular respiration.",
    "explanation": "Mitochondria are the energy factories of the cell.",
    "difficulty": "hard",
    "topic": "Cell Biology",
}

LONG_TEXT = " ".join(["word"] * 600)  # well above 100-word minimum


def _make_api_response(question_dict: dict) -> MagicMock:
    """Construct a minimal mock Anthropic response object."""
    block = MagicMock()
    block.type = "text"
    block.text = json.dumps(question_dict)

    response = MagicMock()
    response.content = [block]
    return response


# ---------------------------------------------------------------------------
# validate_question
# ---------------------------------------------------------------------------


def test_validate_question_good_multiple_choice():
    assert validate_question(GOOD_MC) is True


def test_validate_question_good_true_false():
    assert validate_question(GOOD_TF) is True


def test_validate_question_good_short_answer():
    assert validate_question(GOOD_SA) is True


def test_validate_question_rejects_non_dict():
    assert validate_question("not a dict") is False
    assert validate_question(None) is False
    assert validate_question([]) is False


def test_validate_question_rejects_missing_field():
    bad = {**GOOD_MC}
    del bad["explanation"]
    assert validate_question(bad) is False


def test_validate_question_rejects_invalid_type():
    bad = {**GOOD_MC, "type": "fill_in_blank"}
    assert validate_question(bad) is False


def test_validate_question_rejects_invalid_difficulty():
    bad = {**GOOD_MC, "difficulty": "extreme"}
    assert validate_question(bad) is False


def test_validate_question_rejects_mc_with_wrong_option_count():
    bad = {**GOOD_MC, "options": ["A) Only one option"]}
    assert validate_question(bad) is False


def test_validate_question_rejects_tf_with_wrong_options():
    bad = {**GOOD_TF, "options": ["Yes", "No"]}
    assert validate_question(bad) is False


def test_validate_question_rejects_empty_question_string():
    bad = {**GOOD_MC, "question": "   "}
    assert validate_question(bad) is False


def test_validate_question_rejects_non_list_options():
    bad = {**GOOD_MC, "options": "A) option"}
    assert validate_question(bad) is False


# ---------------------------------------------------------------------------
# generate_question
# ---------------------------------------------------------------------------


@patch("generator._get_client")
def test_generate_question_returns_question(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.messages.create.return_value = _make_api_response(GOOD_MC)

    result = generate_question("Some study text about cells.", "multiple_choice", "easy")

    assert result == GOOD_MC
    mock_client.messages.create.assert_called_once()


@patch("generator._get_client")
def test_generate_question_passes_correct_model_and_schema(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.messages.create.return_value = _make_api_response(GOOD_TF)

    generate_question("Cell content.", "true_false", "medium")

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert "output_config" in call_kwargs
    assert call_kwargs["output_config"]["format"]["type"] == "json_schema"


@patch("generator._get_client")
def test_generate_question_retries_on_invalid_response(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    bad_q = {**GOOD_MC, "type": "invalid_type"}
    mock_client.messages.create.side_effect = [
        _make_api_response(bad_q),   # first call → invalid
        _make_api_response(GOOD_MC), # retry → valid
    ]

    result = generate_question("Cell content.", "multiple_choice")
    assert result == GOOD_MC
    assert mock_client.messages.create.call_count == 2


@patch("generator._get_client")
def test_generate_question_raises_after_two_bad_responses(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    bad_q = {**GOOD_MC, "difficulty": "impossible"}
    mock_client.messages.create.return_value = _make_api_response(bad_q)

    with pytest.raises(ValueError, match="invalid question structure"):
        generate_question("Cell content.", "multiple_choice")

    assert mock_client.messages.create.call_count == 2


def test_generate_question_raises_on_invalid_type():
    with pytest.raises(ValueError, match="question_type"):
        generate_question("text", "essay")


def test_generate_question_raises_on_invalid_difficulty():
    with pytest.raises(ValueError, match="difficulty"):
        generate_question("text", "multiple_choice", "extreme")


# ---------------------------------------------------------------------------
# generate_quiz
# ---------------------------------------------------------------------------


@patch("generator.generate_question")
def test_generate_quiz_returns_correct_count(mock_gq):
    mock_gq.return_value = GOOD_MC
    quiz = generate_quiz(LONG_TEXT, num_questions=5)
    assert len(quiz) == 5
    assert mock_gq.call_count == 5


@patch("generator.generate_question")
def test_generate_quiz_cycles_question_types(mock_gq):
    mock_gq.return_value = GOOD_MC
    generate_quiz(LONG_TEXT, num_questions=4, question_types=["multiple_choice", "true_false"])

    types_used = [call[0][1] for call in mock_gq.call_args_list]
    assert types_used == ["multiple_choice", "true_false", "multiple_choice", "true_false"]


@patch("generator.generate_question")
def test_generate_quiz_passes_difficulty(mock_gq):
    mock_gq.return_value = GOOD_SA
    generate_quiz(LONG_TEXT, num_questions=2, difficulty="hard")

    for call in mock_gq.call_args_list:
        assert call[0][2] == "hard"  # third positional arg is difficulty


@patch("generator.generate_question")
def test_generate_quiz_warns_and_skips_on_error(mock_gq):
    mock_gq.side_effect = [GOOD_MC, ValueError("API failed"), GOOD_MC]

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        quiz = generate_quiz(LONG_TEXT, num_questions=3)

    assert len(quiz) == 2
    assert len(w) == 1
    assert "Skipped" in str(w[0].message)


def test_generate_quiz_raises_on_invalid_difficulty():
    with pytest.raises(ValueError, match="difficulty"):
        generate_quiz(LONG_TEXT, difficulty="impossible")


def test_generate_quiz_raises_on_zero_questions():
    with pytest.raises(ValueError, match="num_questions"):
        generate_quiz(LONG_TEXT, num_questions=0)


def test_generate_quiz_raises_on_invalid_question_type():
    with pytest.raises(ValueError, match="question_type"):
        generate_quiz(LONG_TEXT, question_types=["essay"])


@patch("generator.generate_question")
def test_generate_quiz_empty_content_raises(mock_gq):
    # chunk_content on empty string returns [] → raises ValueError
    with pytest.raises(ValueError, match="no usable chunks"):
        generate_quiz("", num_questions=3)
