"""Export quiz data to JSON and CSV formats."""

import csv
import json
import os


def to_json(quiz: list[dict], filepath: str) -> None:
    """Write a quiz to a JSON file.

    Args:
        quiz: List of question dicts produced by generate_quiz.
        filepath: Destination file path. Parent directories must exist.

    Raises:
        ValueError: If quiz is empty.
        OSError: On file-write failures.
    """
    if not quiz:
        raise ValueError("Cannot export an empty quiz.")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(quiz, f, indent=2, ensure_ascii=False)


def to_csv(quiz: list[dict], filepath: str) -> None:
    """Write a quiz to a CSV file, one row per question.

    Columns: question, type, option_a, option_b, option_c, option_d,
             correct_answer, explanation, difficulty, topic.

    Multiple-choice options are spread across option_a–option_d.
    True/False questions use option_a and option_b; option_c and option_d
    are left blank. Short-answer questions leave all option columns blank.

    Args:
        quiz: List of question dicts produced by generate_quiz.
        filepath: Destination file path. Parent directories must exist.

    Raises:
        ValueError: If quiz is empty.
        OSError: On file-write failures.
    """
    if not quiz:
        raise ValueError("Cannot export an empty quiz.")

    fieldnames = [
        "question", "type",
        "option_a", "option_b", "option_c", "option_d",
        "correct_answer", "explanation", "difficulty", "topic",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for q in quiz:
            options = q.get("options", [])
            writer.writerow({
                "question":       q.get("question", ""),
                "type":           q.get("type", ""),
                "option_a":       options[0] if len(options) > 0 else "",
                "option_b":       options[1] if len(options) > 1 else "",
                "option_c":       options[2] if len(options) > 2 else "",
                "option_d":       options[3] if len(options) > 3 else "",
                "correct_answer": q.get("correct_answer", ""),
                "explanation":    q.get("explanation", ""),
                "difficulty":     q.get("difficulty", ""),
                "topic":          q.get("topic", ""),
            })
