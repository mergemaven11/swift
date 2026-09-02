"""Inspect, extract, and safely copy PDF artifacts."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from .core import SwiftFilezError, atomic_write_text, safe_copy


def _reader(path: str | Path, password: str | None = None) -> PdfReader:
    """Open a PDF and decrypt it when credentials are supplied.

    Args:
        path: PDF file to open.
        password: Optional password for an encrypted PDF.

    Returns:
        Ready-to-read ``PdfReader`` instance.

    Raises:
        SwiftFilezError: If the file is missing, cannot be parsed, or requires
            a password that was not supplied or accepted.
    """
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
    """Return page, encryption, and document-metadata details for a PDF.

    Args:
        path: PDF file to inspect.
        password: Optional password for an encrypted PDF.

    Returns:
        Mapping containing path, page count, encryption state, and common PDF
        metadata fields.

    Raises:
        SwiftFilezError: If the PDF cannot be opened or decrypted.
    """
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
    """Extract readable text from every page of a PDF.

    Args:
        path: PDF file to extract.
        password: Optional password for an encrypted PDF.

    Returns:
        Page text joined with blank lines and trimmed at the boundaries.

    Raises:
        SwiftFilezError: If the PDF cannot be opened or decrypted.
    """
    reader = _reader(path, password)
    return "\n\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()


def extract_pdf(path: str | Path, output: str | Path, password: str | None = None) -> Path:
    """Extract PDF text and atomically write it to a text file.

    Args:
        path: Source PDF file.
        output: Destination text file.
        password: Optional password for an encrypted PDF.

    Returns:
        Path to the written output file.

    Raises:
        SwiftFilezError: If the PDF cannot be opened or decrypted.
    """
    return atomic_write_text(output, extract_text(path, password) + "\n")


def copy_pdf(path: str | Path, output: str | Path) -> Path:
    """Safely copy a PDF without modifying its contents.

    Args:
        path: Source PDF file.
        output: Destination path.

    Returns:
        Path to the copied file.
    """
    return safe_copy(path, output)
