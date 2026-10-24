"""Quick smoke test for the parsing module."""

import sys
import os
import tempfile

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.parsing import (
    extract_text_from_text_file,
    split_into_paragraphs,
    parse_file,
    student_name_from_filename,
)


def test_student_name():
    """Test student name extraction from filenames."""
    assert student_name_from_filename("john_doe.pdf") == "John Doe"
    assert student_name_from_filename("jane-smith.docx") == "Jane Smith"
    assert student_name_from_filename("alice.txt") == "Alice"
    print("✓ student_name_from_filename")


def test_paragraph_splitting():
    """Test paragraph splitting and filtering."""
    text = (
        "This is a short line.\n\n"
        "This is a longer paragraph that should definitely be kept because "
        "it has enough characters in it to pass the minimum threshold.\n\n"
        "Hi\n\n"
        "Another substantial paragraph with plenty of words and characters "
        "to make it past the forty-character minimum length filter."
    )
    paragraphs = split_into_paragraphs(text)
    assert len(paragraphs) == 2, f"Expected 2, got {len(paragraphs)}"
    assert paragraphs[0].index == 0
    assert paragraphs[1].index == 1
    print("✓ split_into_paragraphs")


def test_parse_text_file():
    """Test parsing a plain text file."""
    content = (
        "Lab Record: Experiment 1 - Ohm's Law\n\n"
        "Objective: To verify Ohm's Law by measuring the current through "
        "a conductor for different values of applied voltage.\n\n"
        "Observation: The current was found to be directly proportional to "
        "the voltage applied across the conductor, confirming Ohm's Law.\n\n"
        "Conclusion: The experiment successfully verified Ohm's Law. The "
        "graph of V vs I was a straight line passing through the origin."
    )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="student_alice_"
    ) as f:
        f.write(content)
        tmp_path = f.name

    try:
        submission = parse_file(tmp_path, "Alice_Johnson.txt")
        assert submission.name == "Alice Johnson"
        assert submission.error is None
        assert len(submission.paragraphs) >= 3
        print(f"✓ parse_file (text): {len(submission.paragraphs)} paragraphs")
    finally:
        os.unlink(tmp_path)


def test_parse_unsupported():
    """Test graceful handling of unsupported files."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xyz", delete=False
    ) as f:
        f.write("some data")
        tmp_path = f.name

    try:
        submission = parse_file(tmp_path, "bad_file.xyz")
        assert submission.error is not None
        print(f"✓ parse_file (unsupported): error = {submission.error}")
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    test_student_name()
    test_paragraph_splitting()
    test_parse_text_file()
    test_parse_unsupported()
    print("\nAll parsing tests passed! ✅")
