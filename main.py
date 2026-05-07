"""CLI entry point for the AI Quiz Generator."""

import argparse
import json
import sys

from exporter import to_csv, to_json
from generator import VALID_DIFFICULTIES, VALID_QUESTION_TYPES, generate_quiz
from parser import parse_pdf, parse_text, parse_url


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="quizgen",
        description="Generate a quiz from text, a PDF, or a URL using Claude AI.",
    )

    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--text",  metavar="TEXT", help="Raw study text (quote it).")
    src.add_argument("--pdf",   metavar="FILE", help="Path to a PDF file.")
    src.add_argument("--url",   metavar="URL",  help="Web page URL to scrape.")

    p.add_argument(
        "-n", "--num-questions",
        type=int, default=10, metavar="N",
        help="Number of questions to generate (default: 10).",
    )
    p.add_argument(
        "-d", "--difficulty",
        choices=sorted(VALID_DIFFICULTIES), default="medium",
        help="Question difficulty (default: medium).",
    )
    p.add_argument(
        "-t", "--types",
        nargs="+",
        choices=sorted(VALID_QUESTION_TYPES),
        default=["multiple_choice"],
        metavar="TYPE",
        help=(
            "Question type(s) to cycle through. "
            f"Choices: {sorted(VALID_QUESTION_TYPES)}. Default: multiple_choice."
        ),
    )
    p.add_argument("--export-json", metavar="FILE", help="Save quiz to a JSON file.")
    p.add_argument("--export-csv",  metavar="FILE", help="Save quiz to a CSV file.")

    return p


def _fetch_content(args: argparse.Namespace) -> str:
    if args.text:
        return parse_text(args.text)
    if args.pdf:
        return parse_pdf(args.pdf)
    return parse_url(args.url)


def _print_quiz(quiz: list[dict]) -> None:
    for i, q in enumerate(quiz, 1):
        print(f"\n{'─' * 60}")
        print(f"Q{i}. [{q['type']}] [{q['difficulty']}] Topic: {q['topic']}")
        print(f"\n{q['question']}")
        for opt in q.get("options", []):
            print(f"   {opt}")
        print(f"\n✓ Answer: {q['correct_answer']}")
        print(f"  {q['explanation']}")
    print(f"\n{'─' * 60}")
    print(f"Total: {len(quiz)} question(s) generated.")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # --- Fetch and clean content ---
    try:
        print("Fetching content…", file=sys.stderr)
        content = _fetch_content(args)
    except (ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error while fetching content: {exc}", file=sys.stderr)
        return 1

    # --- Generate quiz ---
    try:
        print(
            f"Generating {args.num_questions} {args.difficulty} question(s) "
            f"(types: {', '.join(args.types)})…",
            file=sys.stderr,
        )
        quiz = generate_quiz(
            content,
            num_questions=args.num_questions,
            difficulty=args.difficulty,
            question_types=args.types,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error during generation: {exc}", file=sys.stderr)
        return 1

    if not quiz:
        print("Error: No questions were generated.", file=sys.stderr)
        return 1

    # --- Display ---
    _print_quiz(quiz)

    # --- Export ---
    if args.export_json:
        try:
            to_json(quiz, args.export_json)
            print(f"\nSaved JSON → {args.export_json}", file=sys.stderr)
        except OSError as exc:
            print(f"Warning: Could not write JSON: {exc}", file=sys.stderr)

    if args.export_csv:
        try:
            to_csv(quiz, args.export_csv)
            print(f"Saved CSV  → {args.export_csv}", file=sys.stderr)
        except OSError as exc:
            print(f"Warning: Could not write CSV: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
