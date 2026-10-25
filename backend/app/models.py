"""Data models for Local Echo Scan."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Paragraph:
    """A single extracted paragraph from a student submission."""

    text: str
    index: int  # position within the document


@dataclass
class StudentSubmission:
    """Parsed student submission with extracted paragraphs."""

    name: str  # derived from filename
    filename: str
    paragraphs: list[Paragraph] = field(default_factory=list)
    raw_text: str = ""
    error: str | None = None


@dataclass
class MatchedPair:
    """A pair of paragraphs flagged as similar between two students."""

    student_a_paragraph: Paragraph
    student_b_paragraph: Paragraph
    similarity: float


@dataclass
class FlaggedPair:
    """A pair of students flagged for review."""

    student_a: str
    student_b: str
    score: float
    matched_pairs: list[MatchedPair] = field(default_factory=list)
    label: str | None = None  # Gemma label
    reason: str | None = None  # Gemma explanation

    @property
    def match_count(self) -> int:
        return len(self.matched_pairs)


@dataclass
class CopyRing:
    """A connected component of students sharing highly similar content."""

    members: list[str] = field(default_factory=list)
    size: int = 0
    pair_count: int = 0
    average_score: float = 0.0
    description: str = "Group of students with highly similar content"
