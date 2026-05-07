"""Core quiz generation logic using the Anthropic API."""

import json
import os
import warnings

import anthropic
from dotenv import load_dotenv

from parser import chunk_content

load_dotenv()

MODEL = "claude-sonnet-4-6"
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_QUESTION_TYPES = {"multiple_choice", "true_false", "short_answer"}
_REQUIRED_FIELDS = {"question", "type", "options", "correct_answer", "explanation", "difficulty", "topic"}

_QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "question":       {"type": "string"},
        "type":           {"type": "string", "enum": ["multiple_choice", "true_false", "short_answer"]},
        "options":        {"type": "array", "items": {"type": "string"}},
        "correct_answer": {"type": "string"},
        "explanation":    {"type": "string"},
        "difficulty":     {"type": "string", "enum": ["easy", "medium", "hard"]},
        "topic":          {"type": "string"},
    },
    "required": ["question", "type", "options", "correct_answer", "explanation", "difficulty", "topic"],
    "additionalProperties": False,
}

_TYPE_INSTRUCTIONS = {
    "multiple_choice": (
        'Generate a multiple-choice question with exactly 4 answer options '
        'labeled "A) ...", "B) ...", "C) ...", "D) ...". '
        'Set correct_answer to the single letter only, e.g. "B".'
    ),
    "true_false": (
        'Generate a True/False question. Set options to ["True", "False"] '
        'and correct_answer to "True" or "False".'
    ),
    "short_answer": (
        "Generate an open-ended short-answer question. Set options to an "
        "empty list [] and correct_answer to a concise model answer (1-2 sentences)."
    ),
}


def _get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set. Add it to a .env file or your environment."
        )
    return anthropic.Anthropic(api_key=api_key)


def validate_question(question: dict) -> bool:
    """Check that a question dict has the correct structure.

    Args:
        question: A question dict to validate.

    Returns:
        True if all required fields are present and correctly typed.
    """
    if not isinstance(question, dict):
        return False
    if not _REQUIRED_FIELDS.issubset(question.keys()):
        return False
    if question.get("type") not in VALID_QUESTION_TYPES:
        return False
    if question.get("difficulty") not in VALID_DIFFICULTIES:
        return False
    for field in ("question", "correct_answer", "explanation", "topic"):
        if not isinstance(question.get(field), str) or not question[field].strip():
            return False
    options = question.get("options")
    if not isinstance(options, list):
        return False
    if question["type"] == "multiple_choice" and len(options) != 4:
        return False
    if question["type"] == "true_false" and set(options) != {"True", "False"}:
        return False
    return True


def generate_question(chunk: str, question_type: str, difficulty: str = "medium") -> dict:
    """Generate a single quiz question from a text chunk using Claude.

    Args:
        chunk: The study material excerpt to base the question on.
        question_type: One of "multiple_choice", "true_false", "short_answer".
        difficulty: One of "easy", "medium", "hard".

    Returns:
        A validated question dict matching the quiz schema.

    Raises:
        ValueError: If question_type or difficulty is invalid, or if Claude
                    returns a malformed response after one retry.
        anthropic.APIError: On unrecoverable API errors.
    """
    if question_type not in VALID_QUESTION_TYPES:
        raise ValueError(f"question_type must be one of {VALID_QUESTION_TYPES}.")
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(f"difficulty must be one of {VALID_DIFFICULTIES}.")

    client = _get_client()

    system = (
        "You are an expert quiz writer. Generate educational quiz questions "
        "based on the provided study material. Questions must be factually "
        f"accurate, clear, and at {difficulty} difficulty."
    )

    user = (
        f"Generate one {difficulty} {question_type.replace('_', ' ')} question "
        f"from this study material:\n\n{chunk}\n\n"
        f"{_TYPE_INSTRUCTIONS[question_type]}\n\n"
        "Identify the specific topic or concept the question tests."
    )

    def _call() -> dict:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={
                "format": {"type": "json_schema", "schema": _QUESTION_SCHEMA}
            },
        )
        text = next(b.text for b in response.content if b.type == "text")
        return json.loads(text)

    question = _call()
    if validate_question(question):
        return question

    # Retry once before failing
    question = _call()
    if validate_question(question):
        return question

    raise ValueError(
        f"Claude returned an invalid question structure after one retry. "
        f"Got: {question}"
    )


def generate_quiz(
    content: str,
    num_questions: int = 10,
    difficulty: str = "medium",
    question_types: list[str] | None = None,
) -> list[dict]:
    """Generate a complete quiz from study material.

    Chunks the content so questions are drawn from different sections,
    giving broad coverage. Failed individual questions are skipped with a
    warning rather than aborting the whole quiz.

    Args:
        content: Cleaned study material (output of parse_text / parse_pdf / parse_url).
        num_questions: Number of questions to generate (default 10).
        difficulty: Difficulty for all questions ("easy", "medium", "hard").
        question_types: Ordered list of question types to cycle through.
                        Defaults to ["multiple_choice"].

    Returns:
        List of validated question dicts. May be shorter than num_questions
        if some API calls fail.

    Raises:
        ValueError: If difficulty is invalid or content yields no chunks.
        anthropic.APIError: On unrecoverable API errors.
    """
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(f"difficulty must be one of {VALID_DIFFICULTIES}.")
    if num_questions < 1:
        raise ValueError("num_questions must be at least 1.")

    if question_types is None:
        question_types = ["multiple_choice"]
    for qt in question_types:
        if qt not in VALID_QUESTION_TYPES:
            raise ValueError(f"Invalid question_type '{qt}'.")

    chunks = chunk_content(content, max_tokens=2000)
    if not chunks:
        raise ValueError("Content produced no usable chunks after splitting.")

    # Spread questions evenly across chunks for broad coverage
    chunk_seq = [chunks[i % len(chunks)] for i in range(num_questions)]
    type_seq = [question_types[i % len(question_types)] for i in range(num_questions)]

    quiz: list[dict] = []
    errors: list[str] = []

    for i, (chunk, qtype) in enumerate(zip(chunk_seq, type_seq)):
        try:
            quiz.append(generate_question(chunk, qtype, difficulty))
        except (ValueError, anthropic.APIError) as exc:
            errors.append(f"Q{i + 1}: {exc}")

    if errors:
        warnings.warn(
            f"Skipped {len(errors)} question(s) due to errors:\n" + "\n".join(errors),
            RuntimeWarning,
            stacklevel=2,
        )

    return quiz
