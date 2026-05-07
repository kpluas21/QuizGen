# AI Quiz Generator — Project Context

## Project Goal
Build a Python-based AI quiz generator that accepts study material (text, PDF, or URL)
and uses the Anthropic API to automatically generate quiz questions with multiple choice
answers, correct answer labels, and difficulty ratings.
This is a portfolio project demonstrating practical AI, NLP, and document processing skills.

## Tech Stack
- **Language:** Python 3.10+
- **AI:** Anthropic SDK (claude-sonnet-4-6)
- **Web UI:** Streamlit
- **PDF Parsing:** PyMuPDF (fitz)
- **Web Scraping:** requests + BeautifulSoup4
- **Testing:** pytest
- **Storage:** JSON (local file, no database needed)

## Project Structure
```
ai-quiz-generator/
├── CLAUDE.md
├── main.py                  # CLI entry point
├── generator.py             # Core quiz generation logic (Anthropic API)
├── parser.py                # Input parsing (text / PDF / URL)
├── app.py                   # Streamlit web UI
├── exporter.py              # Export to JSON / CSV / PDF
├── data/
│   └── sample_material.txt  # Sample study material for testing
├── tests/
│   ├── test_generator.py
│   └── test_parser.py
├── requirements.txt
└── README.md
```

## Core Features

### Input Sources
- Raw text pasted directly into the UI or CLI
- PDF file upload
- URL (scrape the page content automatically)

### Quiz Generation
- Generate N questions (user configurable, default 10)
- Question types:
  - Multiple choice (4 options, 1 correct)
  - True / False
  - Short answer (open ended)
- Difficulty levels: Easy / Medium / Hard
- Each question tagged with the topic/concept it tests

### Output Formats
- Interactive Streamlit quiz (user answers, then sees score)
- Exportable JSON (for integration with other tools)
- Exportable CSV (for sharing or importing into Google Forms)

## Core Functions to Build

### parser.py
- `parse_text(text: str) -> str` — cleans and chunks raw text
- `parse_pdf(filepath: str) -> str` — extracts text from PDF
- `parse_url(url: str) -> str` — scrapes and cleans webpage content
- `chunk_content(text: str, max_tokens: int) -> list[str]` — splits long content for API

### generator.py
- `generate_quiz(content: str, num_questions: int, difficulty: str) -> list[dict]`
- `generate_question(chunk: str, question_type: str) -> dict`
- `validate_question(question: dict) -> bool` — checks output structure is correct

### exporter.py
- `to_json(quiz: list[dict], filepath: str)`
- `to_csv(quiz: list[dict], filepath: str)`

## What Good Output Looks Like
```json
{
  "question": "What is the primary function of mitochondria in a cell?",
  "type": "multiple_choice",
  "options": [
    "A) Protein synthesis",
    "B) Energy production (ATP)",
    "C) DNA replication",
    "D) Waste removal"
  ],
  "correct_answer": "B",
  "explanation": "Mitochondria are known as the powerhouse of the cell because they produce ATP through cellular respiration.",
  "difficulty": "medium",
  "topic": "Cell Biology"
}
```

## Streamlit UI Flow
1. User selects input type (text / PDF / URL)
2. User provides the material
3. User configures: number of questions, difficulty, question types
4. Click "Generate Quiz" → spinner while API runs
5. Questions appear one at a time — user selects answers
6. Submit → score screen with correct answers and explanations
7. Option to export or regenerate

## Coding Standards
- Type hints on all functions
- Docstrings on every public function
- All API errors caught and shown as friendly UI messages (not raw tracebacks)
- API key loaded via environment variable (ANTHROPIC_API_KEY) using python-dotenv
- Never hardcode the API key or commit .env to Git

## Edge Cases to Handle
- Input material that is too short (< 100 words) → warn user
- Input material that is too long → chunk it, generate questions per chunk
- PDF with no extractable text (scanned image) → show clear error message
- URL that is paywalled or returns 403 → show clear error message
- API response that doesn't match expected JSON structure → retry once, then fail gracefully

## Testing
- Unit tests for all parser functions (mock file/URL reads)
- Unit tests for generator (mock Anthropic API responses)
- Test edge cases: empty input, very short input, malformed API response

## Resume / Portfolio Notes
Prioritize making this impressive to non-technical reviewers too:
- Clean, friendly Streamlit UI (not just a raw terminal tool)
- A working live demo (deploy on Streamlit Cloud — it's free)
- README with a short demo GIF, sample input, and sample quiz output
- Add a "topics covered" summary at the end of each quiz (shows AI summarization chops)
