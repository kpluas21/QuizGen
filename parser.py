"""Input parsing utilities for the AI Quiz Generator."""

import re
import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup


def parse_text(text: str) -> str:
    """Clean and normalize raw text input.

    Args:
        text: Raw text pasted by the user.

    Returns:
        Cleaned text with normalized whitespace and removed noise.

    Raises:
        ValueError: If the cleaned text is fewer than 100 words.
    """
    # Normalize line endings and collapse whitespace
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.strip()

    word_count = len(text.split())
    if word_count < 100:
        raise ValueError(
            f"Input is too short ({word_count} words). Please provide at least 100 words of study material."
        )

    return text


def parse_pdf(filepath: str) -> str:
    """Extract and return all text from a PDF file.

    Args:
        filepath: Absolute or relative path to the PDF file.

    Returns:
        Extracted text content joined across all pages.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the PDF contains no extractable text (e.g. scanned image).
    """
    try:
        doc = fitz.open(filepath)
    except FileNotFoundError:
        raise FileNotFoundError(f"PDF file not found: {filepath}")
    except Exception as exc:
        raise ValueError(f"Could not open PDF '{filepath}': {exc}") from exc

    pages: list[str] = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()

    text = "\n\n".join(pages).strip()

    if not text:
        raise ValueError(
            "No extractable text found in this PDF. "
            "It may be a scanned image. Please provide a text-based PDF."
        )

    # Normalize whitespace the same way parse_text does
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def parse_url(url: str) -> str:
    """Scrape and return the main text content from a webpage.

    Args:
        url: The URL of the webpage to scrape.

    Returns:
        Cleaned text extracted from the page body.

    Raises:
        ValueError: If the page returns a non-200 status or yields no usable text.
        requests.exceptions.RequestException: On network-level failures.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; QuizGenBot/1.0)"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
    except requests.exceptions.RequestException as exc:
        raise requests.exceptions.RequestException(
            f"Failed to reach '{url}': {exc}"
        ) from exc

    if response.status_code == 403:
        raise ValueError(
            f"Access denied (403) for '{url}'. The page may be paywalled or bot-protected."
        )
    if response.status_code != 200:
        raise ValueError(
            f"Could not retrieve '{url}' (HTTP {response.status_code})."
        )

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    if not text:
        raise ValueError(f"No readable text content found at '{url}'.")

    return text


def chunk_content(text: str, max_tokens: int = 3000) -> list[str]:
    """Split text into chunks that fit within a token budget.

    Uses a conservative 4-characters-per-token estimate so chunks are
    safely under the limit without requiring a tokenizer dependency.

    Args:
        text: The full text to split.
        max_tokens: Maximum tokens allowed per chunk (default 3000).

    Returns:
        List of text chunks, each within the token budget.
    """
    max_chars = max_tokens * 4
    paragraphs = re.split(r"\n\n+", text)

    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If a single paragraph exceeds the budget, hard-split it
        if len(para) > max_chars:
            if current_parts:
                chunks.append("\n\n".join(current_parts))
                current_parts, current_len = [], 0
            for i in range(0, len(para), max_chars):
                chunks.append(para[i : i + max_chars])
            continue

        if current_len + len(para) > max_chars and current_parts:
            chunks.append("\n\n".join(current_parts))
            current_parts, current_len = [], 0

        current_parts.append(para)
        current_len += len(para)

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return chunks
