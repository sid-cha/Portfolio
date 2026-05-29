"""
Document Parser
Supports: PDF (PyMuPDF), plain text, HTML, Confluence/Slack (JSON export)
"""

import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)


def parse_document(file_path: str, source_type: str = None) -> Tuple[str, str]:
    """
    Parse a document and return (text_content, detected_source_type).
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if source_type == "pdf" or ext == ".pdf":
        return _parse_pdf(file_path), "pdf"
    elif source_type == "confluence" or ext == ".json":
        return _parse_confluence_json(file_path), "confluence"
    elif ext in (".txt", ".md"):
        return _parse_text(file_path), "text"
    elif ext in (".html", ".htm"):
        return _parse_html(file_path), "html"
    else:
        return _parse_text(file_path), "text"


def _parse_pdf(file_path: str) -> str:
    import fitz  # PyMuPDF
    doc = fitz.open(file_path)
    pages = []
    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        if text.strip():
            pages.append(f"[Page {page_num + 1}]\n{text}")
    full_text = "\n\n".join(pages)
    logger.info(f"Parsed PDF: {file_path} ({len(doc)} pages)")
    doc.close()
    return full_text


def _parse_text(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _parse_html(file_path: str) -> str:
    from bs4 import BeautifulSoup
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    return soup.get_text(separator="\n")


def _parse_confluence_json(file_path: str) -> str:
    import json
    with open(file_path, "r") as f:
        data = json.load(f)
    # Handle Confluence space export format
    if isinstance(data, list):
        return "\n\n".join(
            f"# {item.get('title', '')}\n{item.get('body', '')}"
            for item in data
        )
    return str(data)
