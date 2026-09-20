"""Read CV documents from disk. Plain text and .docx need no third-party packages."""

from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path

TEXT_SUFFIXES = {".txt", ".md", ".rst", ""}
SUPPORTED = TEXT_SUFFIXES | {".docx", ".pdf"}

_PARAGRAPH_END = re.compile(r"</w:p>", re.IGNORECASE)
_LINE_BREAK = re.compile(r"<w:(?:br|tab)\b[^>]*/?>", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")


class UnsupportedDocument(ValueError):
    """Raised when a file cannot be turned into text."""


def load_document(path: Path | str) -> str:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".docx":
        return _read_docx(path)
    if suffix == ".pdf":
        return _read_pdf(path)
    raise UnsupportedDocument(
        f"Cannot read '{suffix or path.name}'. Supported: {', '.join(sorted(s for s in SUPPORTED if s))}."
    )


def _read_docx(path: Path) -> str:
    """Pull the text out of the WordprocessingML body without external deps."""
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", errors="replace")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise UnsupportedDocument(f"{path.name} is not a readable .docx file") from exc

    xml = _LINE_BREAK.sub("\n", xml)
    xml = _PARAGRAPH_END.sub("\n", xml)
    text = html.unescape(_TAG.sub("", xml))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise UnsupportedDocument(
            "Reading PDF requires pypdf. Install it with 'pip install cv-analyzer[pdf]', "
            "or convert the file to text first."
        ) from exc

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
