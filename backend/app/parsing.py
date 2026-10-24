"""File parsing module for Local Echo Scan.

Supports PDF, DOCX, TXT, and common code files.
Extracts text and splits into meaningful paragraphs.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from pypdf import PdfReader
from docx import Document

from .models import Paragraph, StudentSubmission

logger = logging.getLogger(__name__)

# Supported file extensions
TEXT_EXTENSIONS = {".txt", ".md", ".csv"}
CODE_EXTENSIONS = {".py", ".java", ".c", ".cpp", ".h", ".hpp", ".js", ".ts", ".html", ".css", ".rb", ".go", ".rs"}
SUPPORTED_EXTENSIONS = {".pdf", ".docx"} | TEXT_EXTENSIONS | CODE_EXTENSIONS

# Minimum paragraph length (characters) to keep
MIN_PARAGRAPH_LENGTH = 40


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text content from a PDF file."""
    try:
        reader = PdfReader(file_path)
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
    except Exception as e:
        raise ValueError(f"Failed to read PDF '{file_path}': {e}") from e


def extract_text_from_docx(file_path: str) -> str:
    """Extract text content from a DOCX file."""
    try:
        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except Exception as e:
        raise ValueError(f"Failed to read DOCX '{file_path}': {e}") from e


def extract_text_from_text_file(file_path: str) -> str:
    """Extract text content from a plain text or code file."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        raise ValueError(f"Failed to read text file '{file_path}': {e}") from e


def extract_text(file_path: str) -> str:
    """Extract text from a file based on its extension.

    Args:
        file_path: Path to the file to parse.

    Returns:
        Extracted text content.

    Raises:
        ValueError: If the file type is unsupported or unreadable.
    """
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    elif ext in TEXT_EXTENSIONS | CODE_EXTENSIONS:
        return extract_text_from_text_file(file_path)
    else:
        raise ValueError(f"Unsupported file type: '{ext}'")


def split_into_paragraphs(text: str) -> list[Paragraph]:
    """Split text into paragraphs, filtering out very short ones.

    Splits on double newlines (or more). Each paragraph is stripped
    of excess whitespace. Paragraphs shorter than MIN_PARAGRAPH_LENGTH
    are discarded.

    Args:
        text: Raw text content.

    Returns:
        List of Paragraph objects with index positions.
    """
    # Split on one or more blank lines
    raw_paragraphs = text.split("\n\n")
    paragraphs: list[Paragraph] = []
    idx = 0

    for raw in raw_paragraphs:
        # Collapse internal whitespace but preserve structure
        cleaned = " ".join(raw.split())
        if len(cleaned) >= MIN_PARAGRAPH_LENGTH:
            paragraphs.append(Paragraph(text=cleaned, index=idx))
            idx += 1

    return paragraphs


def student_name_from_filename(filename: str) -> str:
    """Derive a student name from a filename.

    Strips the extension and replaces underscores/hyphens with spaces.

    Args:
        filename: Original filename.

    Returns:
        A human-readable student name.
    """
    stem = Path(filename).stem
    return stem.replace("_", " ").replace("-", " ").title()


def parse_file(file_path: str, filename: str | None = None) -> StudentSubmission:
    """Parse a single file into a StudentSubmission.

    Args:
        file_path: Path to the file on disk.
        filename: Original filename (used for student name).
                  Defaults to the basename of file_path.

    Returns:
        A StudentSubmission with extracted paragraphs, or an error
        if the file could not be read.
    """
    if filename is None:
        filename = os.path.basename(file_path)

    name = student_name_from_filename(filename)

    try:
        raw_text = extract_text(file_path)
        paragraphs = split_into_paragraphs(raw_text)

        logger.info(
            "Parsed '%s': %d paragraphs extracted",
            filename,
            len(paragraphs),
        )

        return StudentSubmission(
            name=name,
            filename=filename,
            paragraphs=paragraphs,
            raw_text=raw_text,
        )

    except ValueError as e:
        logger.warning("Error parsing '%s': %s", filename, e)
        return StudentSubmission(
            name=name,
            filename=filename,
            error=str(e),
        )


def parse_files(file_paths: list[tuple[str, str]]) -> list[StudentSubmission]:
    """Parse multiple files into StudentSubmissions.

    Args:
        file_paths: List of (file_path_on_disk, original_filename) tuples.

    Returns:
        List of StudentSubmission objects (some may have errors).
    """
    submissions: list[StudentSubmission] = []

    for path, filename in file_paths:
        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            logger.info("Skipping unsupported file: '%s'", filename)
            continue
        submission = parse_file(path, filename)
        submissions.append(submission)

    return submissions
