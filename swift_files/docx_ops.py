"""DOCX operations."""
from __future__ import annotations

from pathlib import Path
from docx import Document
from .core import SwiftFilezError, atomic_write_text, safe_copy


def _document(path: str | Path) -> Document:
    docx_path = Path(path)
    if not docx_path.is_file():
        raise SwiftFilezError(f"DOCX file not found: {docx_path}")
    try:
        return Document(str(docx_path))
    except Exception as exc:
        raise SwiftFilezError(f"Could not open DOCX file: {docx_path}") from exc


def extract_text(path: str | Path) -> str:
    document = _document(path)
    blocks = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
    for table in document.tables:
        for row in table.rows:
            blocks.append("\t".join(cell.text for cell in row.cells))
    return "\n".join(blocks)


def inspect_docx(path: str | Path) -> dict:
    document = _document(path)
    text = extract_text(path)
    return {"path": str(Path(path)), "paragraphs": len(document.paragraphs), "tables": len(document.tables), "words": len(text.split()), "characters": len(text), "title": document.core_properties.title or None, "author": document.core_properties.author or None}


def extract_docx(path: str | Path, output: str | Path) -> Path:
    return atomic_write_text(output, extract_text(path) + "\n")


def copy_docx(path: str | Path, output: str | Path) -> Path:
    return safe_copy(path, output)
