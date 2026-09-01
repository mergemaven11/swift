"""PDF operations."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from .core import SwiftFilezError, atomic_write_text, safe_copy


def _reader(path: str | Path, password: str | None = None) -> PdfReader:
    pdf_path = Path(path)
    if not pdf_path.is_file():
        raise SwiftFilezError(f"PDF file not found: {pdf_path}")
    try:
        reader = PdfReader(str(pdf_path))
        if reader.is_encrypted and (not password or not reader.decrypt(password)):
            raise SwiftFilezError("PDF is encrypted; provide --password")
        return reader
    except SwiftFilezError:
        raise
    except Exception as exc:
        raise SwiftFilezError(f"Could not open PDF file: {pdf_path}") from exc


def inspect_pdf(path: str | Path, password: str | None = None) -> dict:
    reader = _reader(path, password)
    metadata = reader.metadata or {}
    return {
        "path": str(Path(path)),
        "pages": len(reader.pages),
        "encrypted": bool(getattr(reader, "is_encrypted", False)),
        "title": metadata.get("/Title"),
        "author": metadata.get("/Author"),
        "subject": metadata.get("/Subject"),
        "creator": metadata.get("/Creator"),
    }


def extract_text(path: str | Path, password: str | None = None) -> str:
    reader = _reader(path, password)
    return "\n\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()


def extract_pdf(path: str | Path, output: str | Path, password: str | None = None) -> Path:
    return atomic_write_text(output, extract_text(path, password) + "\n")


def copy_pdf(path: str | Path, output: str | Path) -> Path:
    return safe_copy(path, output)
