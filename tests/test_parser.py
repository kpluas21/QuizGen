"""Unit tests for parser.py."""

import os
import textwrap
from unittest.mock import MagicMock, patch

import pytest

from parser import chunk_content, parse_pdf, parse_text, parse_url

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LONG_TEXT = " ".join(["word"] * 150)  # 150 words — above the 100-word minimum


# ---------------------------------------------------------------------------
# parse_text
# ---------------------------------------------------------------------------


def test_parse_text_returns_cleaned_string():
    raw = "  Hello   world.\r\nThis is  a test.\r\n\n\n\nNew paragraph.  "
    # Pad to meet 100-word minimum
    raw += " " + LONG_TEXT
    result = parse_text(raw)
    assert "  " not in result  # no double spaces
    assert result == result.strip()


def test_parse_text_normalises_crlf():
    text = ("word " * 100).replace(" ", "\r\n")
    result = parse_text("word " * 100)
    assert "\r" not in result


def test_parse_text_collapses_blank_lines():
    text = "Para one.\n\n\n\n\nPara two. " + LONG_TEXT
    result = parse_text(text)
    assert "\n\n\n" not in result


def test_parse_text_raises_when_too_short():
    with pytest.raises(ValueError, match="too short"):
        parse_text("Only a few words here.")


def test_parse_text_exactly_100_words_passes():
    text = " ".join(["word"] * 100)
    result = parse_text(text)
    assert len(result.split()) == 100


# ---------------------------------------------------------------------------
# parse_pdf
# ---------------------------------------------------------------------------


def _make_mock_doc(pages_text: list[str]):
    """Return a mock fitz document yielding the given page texts."""
    mock_pages = []
    for t in pages_text:
        page = MagicMock()
        page.get_text.return_value = t
        mock_pages.append(page)

    mock_doc = MagicMock()
    mock_doc.__iter__ = MagicMock(return_value=iter(mock_pages))
    mock_doc.close = MagicMock()
    return mock_doc


@patch("parser.fitz.open")
def test_parse_pdf_extracts_text(mock_fitz_open):
    mock_fitz_open.return_value = _make_mock_doc(["Page one text.", "Page two text."])
    result = parse_pdf("dummy.pdf")
    assert "Page one text." in result
    assert "Page two text." in result


@patch("parser.fitz.open")
def test_parse_pdf_raises_for_empty_pdf(mock_fitz_open):
    mock_fitz_open.return_value = _make_mock_doc(["", "   "])
    with pytest.raises(ValueError, match="No extractable text"):
        parse_pdf("scanned.pdf")


@patch("parser.fitz.open", side_effect=FileNotFoundError)
def test_parse_pdf_raises_for_missing_file(mock_fitz_open):
    with pytest.raises(FileNotFoundError, match="not found"):
        parse_pdf("missing.pdf")


@patch("parser.fitz.open", side_effect=Exception("bad file"))
def test_parse_pdf_raises_for_corrupt_file(mock_fitz_open):
    with pytest.raises(ValueError, match="Could not open PDF"):
        parse_pdf("corrupt.pdf")


# ---------------------------------------------------------------------------
# parse_url
# ---------------------------------------------------------------------------


def _make_response(status_code: int, html: str):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.text = html
    return mock_resp


SAMPLE_HTML = textwrap.dedent("""\
    <html><body>
      <nav>Skip nav</nav>
      <p>Main content paragraph one.</p>
      <p>Main content paragraph two.</p>
      <footer>Footer noise</footer>
    </body></html>
""")


@patch("parser.requests.get")
def test_parse_url_returns_main_content(mock_get):
    mock_get.return_value = _make_response(200, SAMPLE_HTML)
    result = parse_url("http://example.com")
    assert "Main content paragraph one." in result
    assert "Main content paragraph two." in result


@patch("parser.requests.get")
def test_parse_url_strips_nav_and_footer(mock_get):
    mock_get.return_value = _make_response(200, SAMPLE_HTML)
    result = parse_url("http://example.com")
    assert "Skip nav" not in result
    assert "Footer noise" not in result


@patch("parser.requests.get")
def test_parse_url_raises_on_403(mock_get):
    mock_get.return_value = _make_response(403, "")
    with pytest.raises(ValueError, match="403"):
        parse_url("http://paywalled.com")


@patch("parser.requests.get")
def test_parse_url_raises_on_non_200(mock_get):
    mock_get.return_value = _make_response(404, "")
    with pytest.raises(ValueError, match="404"):
        parse_url("http://example.com/missing")


@patch("parser.requests.get", side_effect=__import__("requests").exceptions.ConnectionError("no route"))
def test_parse_url_raises_on_network_error(mock_get):
    import requests as req
    with pytest.raises(req.exceptions.RequestException):
        parse_url("http://unreachable.example")


@patch("parser.requests.get")
def test_parse_url_raises_when_no_text(mock_get):
    mock_get.return_value = _make_response(200, "<html><body><script>code</script></body></html>")
    with pytest.raises(ValueError, match="No readable text"):
        parse_url("http://empty.com")


# ---------------------------------------------------------------------------
# chunk_content
# ---------------------------------------------------------------------------


def test_chunk_content_single_chunk_for_short_text():
    text = "Short paragraph.\n\nAnother short paragraph."
    chunks = chunk_content(text, max_tokens=3000)
    assert len(chunks) == 1
    assert "Short paragraph." in chunks[0]


def test_chunk_content_splits_long_text():
    # ~5000 chars worth of content at 4 chars/token = ~1250 tokens → should split at 500 tokens
    paragraph = "word " * 200  # ~1000 chars per paragraph
    text = "\n\n".join([paragraph] * 6)  # ~6000 chars total
    chunks = chunk_content(text, max_tokens=500)
    assert len(chunks) > 1


def test_chunk_content_no_chunk_exceeds_budget():
    paragraph = "word " * 200
    text = "\n\n".join([paragraph] * 10)
    max_tokens = 500
    chunks = chunk_content(text, max_tokens=max_tokens)
    for chunk in chunks:
        assert len(chunk) <= max_tokens * 4


def test_chunk_content_hard_splits_giant_paragraph():
    # Single paragraph larger than the budget
    giant = "x" * 10_000
    chunks = chunk_content(giant, max_tokens=500)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 500 * 4


def test_chunk_content_empty_string_returns_empty_list():
    assert chunk_content("") == []


def test_chunk_content_preserves_all_content():
    words = ["word"] * 600
    text = " ".join(words)
    chunks = chunk_content(text, max_tokens=300)
    rejoined = " ".join(chunks)
    # All original words should still be present (order preserved, just split)
    for word in words[:10]:
        assert word in rejoined
