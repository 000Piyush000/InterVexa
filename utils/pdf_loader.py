"""
Text extraction for PDF and TXT interview-experience documents.

Every function here is defensive: a corrupted or unreadable file raises a
clear, typed exception instead of crashing the Flask worker, so app.py can
catch it and show a friendly message in the UI.
"""

import os
import re

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class DocumentLoadError(Exception):
    """Raised when a source document cannot be read or contains no usable text."""


def load_pdf(file_path):
    """Extract raw text from every page of a PDF file.

    Raises:
        DocumentLoadError: if the file is missing, encrypted without a
            usable password, corrupted, or contains no extractable text.
    """
    if not os.path.isfile(file_path):
        raise DocumentLoadError(f"File not found: {file_path}")

    try:
        reader = PdfReader(file_path)
    except (PdfReadError, OSError, ValueError) as exc:
        raise DocumentLoadError(f"Could not open PDF '{os.path.basename(file_path)}': {exc}") from exc

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # noqa: BLE001 - pypdf raises various error types
            raise DocumentLoadError(
                f"PDF '{os.path.basename(file_path)}' is password protected and cannot be read."
            ) from exc

    pages_text = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001 - pypdf extraction can fail per-page
            raise DocumentLoadError(
                f"Failed extracting text from page {page_number} of "
                f"'{os.path.basename(file_path)}': {exc}"
            ) from exc
        if text.strip():
            pages_text.append(text)

    full_text = "\n".join(pages_text)
    if not full_text.strip():
        raise DocumentLoadError(
            f"No extractable text found in '{os.path.basename(file_path)}'. "
            "It may be a scanned/image-only PDF."
        )
    return full_text


def load_txt(file_path):
    """Read a plain-text interview experience file."""
    if not os.path.isfile(file_path):
        raise DocumentLoadError(f"File not found: {file_path}")

    encodings_to_try = ("utf-8", "utf-8-sig", "latin-1")
    last_error = None
    for encoding in encodings_to_try:
        try:
            with open(file_path, "r", encoding=encoding) as handle:
                text = handle.read()
            if text.strip():
                return text
            raise DocumentLoadError(f"'{os.path.basename(file_path)}' is empty.")
        except UnicodeDecodeError as exc:
            last_error = exc
            continue

    raise DocumentLoadError(
        f"Could not decode '{os.path.basename(file_path)}' with any supported encoding: {last_error}"
    )


def load_document(file_path):
    """Dispatch to the correct loader based on file extension."""
    extension = os.path.splitext(file_path)[1].lower().lstrip(".")
    if extension == "pdf":
        return load_pdf(file_path)
    if extension == "txt":
        return load_txt(file_path)
    raise DocumentLoadError(f"Unsupported file type '.{extension}'. Only PDF and TXT are allowed.")


def clean_text(raw_text):
    """Normalize whitespace and strip common PDF extraction artifacts."""
    if not raw_text:
        return ""

    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse hyphenated line-break splits, e.g. "algo-\nrithm" -> "algorithm"
    text = re.sub(r"-\n(?=[a-z])", "", text)
    # Collapse runs of blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse runs of horizontal whitespace
    text = re.sub(r"[ \t]{2,}", " ", text)
    # Remove stray page-number-only lines (e.g. "12" or "Page 3")
    text = re.sub(r"(?im)^\s*(page\s*)?\d{1,4}\s*$", "", text)
    # Strip leading/trailing whitespace on each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(line for line in lines if line != "" or True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_and_clean(file_path):
    """Convenience wrapper: load a document and return cleaned text."""
    raw_text = load_document(file_path)
    cleaned = clean_text(raw_text)
    if not cleaned:
        raise DocumentLoadError(f"'{os.path.basename(file_path)}' produced no usable text after cleaning.")
    return cleaned
