# AI Quiz Generator

A Python app that turns any study material — pasted text, a PDF, or a URL — into a polished quiz using the Anthropic Claude API. Includes a Streamlit web UI and a CLI.

---

## Features

- **Three input types:** paste raw text, upload a PDF, or scrape a web page
- **Three question types:** multiple choice, true/false, short answer
- **Configurable:** number of questions (1–20), difficulty (easy / medium / hard), mix of question types
- **Interactive quiz UI:** one question at a time, progress bar, instant scoring
- **Export:** download results as JSON or CSV (Google Forms-compatible)
- **CLI:** scriptable, pipeline-friendly, supports all the same options

---

## Sample Output

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

---

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/your-username/ai-quiz-generator.git
cd ai-quiz-generator
pip install -r requirements.txt
```

### 2. Add your Anthropic API key

```bash
cp .env.example .env
# Edit .env and replace the placeholder with your real key
```

Your `.env` file should look like:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Get a key at [console.anthropic.com](https://console.anthropic.com).

---

## Usage

### Web UI

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. Choose your input type, paste/upload your material, configure the quiz settings in the sidebar, and click **Generate Quiz**.

### CLI

```bash
# From a text string
python main.py --text "Mitochondria are membrane-bound organelles..." -n 5 -d easy

# From a PDF
python main.py --pdf lecture_notes.pdf -n 10 -d medium --export-json quiz.json

# From a URL, mixed question types, export to CSV
python main.py --url https://en.wikipedia.org/wiki/Photosynthesis \
  --types multiple_choice true_false \
  -n 8 -d hard \
  --export-csv quiz.csv
```

#### CLI options

| Flag | Description | Default |
|---|---|---|
| `--text TEXT` | Raw study material (quoted string) | — |
| `--pdf FILE` | Path to a PDF file | — |
| `--url URL` | Web page to scrape | — |
| `-n N` | Number of questions | 10 |
| `-d LEVEL` | Difficulty: `easy`, `medium`, `hard` | `medium` |
| `-t TYPE …` | Question type(s) to cycle through | `multiple_choice` |
| `--export-json FILE` | Save quiz as JSON | — |
| `--export-csv FILE` | Save quiz as CSV | — |

---

## Project Structure

```
ai-quiz-generator/
├── app.py               # Streamlit web UI
├── main.py              # CLI entry point
├── generator.py         # Claude API quiz generation
├── parser.py            # Text / PDF / URL input parsing
├── exporter.py          # JSON and CSV export
├── data/
│   └── sample_material.txt
├── tests/
│   ├── test_parser.py
│   ├── test_generator.py
│   └── test_exporter.py
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Running Tests

```bash
pytest tests/ -p no:playwright
```

62 tests covering all parser, generator, and exporter functions with mocked API calls — no real API key needed for the test suite.

---

## Tech Stack

| Layer | Library |
|---|---|
| AI | [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python) · `claude-sonnet-4-6` |
| Web UI | [Streamlit](https://streamlit.io) |
| PDF parsing | [PyMuPDF](https://pymupdf.readthedocs.io) |
| Web scraping | [requests](https://requests.readthedocs.io) + [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) |
| Testing | [pytest](https://pytest.org) |

---

## Deployment (Streamlit Cloud)

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo.
3. In **Advanced settings → Secrets**, add:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
4. Click **Deploy**.
