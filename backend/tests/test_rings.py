"""Tests for copy rings module (NetworkX connected components).

Covers:
- A cluster/ring of 3-4 students sharing similar work is detected as one ring
- Two separate copy pairs (e.g. A-B and C-D) do NOT form a ring (size < min_ring_size)
- Unrelated students are not included in rings
- Exclude pairs labeled 'coincidence' when explanations are active
- Configurable min_ring_size
- Integration test with FastAPI /analyze endpoint
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.models import FlaggedPair, MatchedPair, Paragraph
from backend.app.rings import find_copy_rings


def _make_flagged_pair(
    student_a: str,
    student_b: str,
    score: float = 0.92,
    label: str | None = None,
    reason: str | None = None,
) -> FlaggedPair:
    p_a = Paragraph(text="Sample paragraph for student A", index=0)
    p_b = Paragraph(text="Sample paragraph for student B", index=0)
    matched = [MatchedPair(student_a_paragraph=p_a, student_b_paragraph=p_b, similarity=score)]
    return FlaggedPair(
        student_a=student_a,
        student_b=student_b,
        score=score,
        matched_pairs=matched,
        label=label,
        reason=reason,
    )


def test_ring_of_3_students():
    """A, B, C connected in a chain or triangle should form 1 ring of size 3."""
    pairs = [
        _make_flagged_pair("Alice", "Bob", score=0.95),
        _make_flagged_pair("Bob", "Charlie", score=0.91),
    ]

    rings = find_copy_rings(pairs, min_ring_size=3)
    assert len(rings) == 1, f"Expected 1 ring, got {len(rings)}"
    ring = rings[0]

    assert ring.members == ["Alice", "Bob", "Charlie"]
    assert ring.size == 3
    assert ring.pair_count == 2
    assert ring.average_score == round((0.95 + 0.91) / 2, 4)
    assert "highly similar content" in ring.description
    print("✓ test_ring_of_3_students passed")


def test_ring_of_4_students():
    """4 students sharing work in a cluster should form a single ring of size 4."""
    pairs = [
        _make_flagged_pair("Alice", "Bob", score=0.96),
        _make_flagged_pair("Bob", "Carol", score=0.92),
        _make_flagged_pair("Carol", "Dave", score=0.88),
        _make_flagged_pair("Alice", "Dave", score=0.90),
    ]

    rings = find_copy_rings(pairs, min_ring_size=3)
    assert len(rings) == 1
    ring = rings[0]
    assert ring.members == ["Alice", "Bob", "Carol", "Dave"]
    assert ring.size == 4
    assert ring.pair_count == 4
    expected_avg = round((0.96 + 0.92 + 0.88 + 0.90) / 4, 4)
    assert ring.average_score == expected_avg
    print("✓ test_ring_of_4_students passed")


def test_two_separate_pairs_do_not_form_ring():
    """Two disjoint pairs of 2 students (A-B and C-D) do NOT form any ring (min_size=3)."""
    pairs = [
        _make_flagged_pair("Alice", "Bob", score=0.95),
        _make_flagged_pair("Charlie", "Dave", score=0.92),
    ]

    rings = find_copy_rings(pairs, min_ring_size=3)
    assert len(rings) == 0, f"Expected 0 rings for disjoint pairs, got {len(rings)}"
    print("✓ test_two_separate_pairs_do_not_form_ring passed")


def test_unrelated_students_excluded():
    """Unrelated students not in any flagged pair are never in the ring."""
    # Alice, Bob, Charlie are connected; Dave, Eve are not connected to them
    pairs = [
        _make_flagged_pair("Alice", "Bob", score=0.90),
        _make_flagged_pair("Bob", "Charlie", score=0.92),
    ]

    rings = find_copy_rings(pairs, min_ring_size=3)
    assert len(rings) == 1
    assert "Dave" not in rings[0].members
    assert "Eve" not in rings[0].members
    assert rings[0].members == ["Alice", "Bob", "Charlie"]
    print("✓ test_unrelated_students_excluded passed")


def test_coincidence_pair_excluded_when_explanations_available():
    """When explanations are active, pairs marked 'coincidence' are excluded from the graph."""
    # Alice-Bob (likely copy), Bob-Charlie (coincidence)
    # Without Bob-Charlie, size is only 2, so no ring should form with min_size=3
    pairs = [
        _make_flagged_pair("Alice", "Bob", score=0.95, label="likely copy"),
        _make_flagged_pair("Bob", "Charlie", score=0.86, label="coincidence"),
    ]

    # With explanations_available=True, Bob-Charlie should be ignored
    rings = find_copy_rings(pairs, min_ring_size=3, explanations_available=True)
    assert len(rings) == 0, "Coincidence edge should be excluded, leaving no ring >= 3"

    # With explanations_available=False, the coincidence label is not used to filter
    rings_unfiltered = find_copy_rings(pairs, min_ring_size=3, explanations_available=False)
    assert len(rings_unfiltered) == 1, "Should include edge when explanations_available=False"
    print("✓ test_coincidence_pair_excluded_when_explanations_available passed")


def test_configurable_min_ring_size():
    """Setting min_ring_size=4 requires at least 4 students to form a ring."""
    pairs = [
        _make_flagged_pair("Alice", "Bob", score=0.90),
        _make_flagged_pair("Bob", "Charlie", score=0.92),
    ]

    # Size is 3; min_ring_size=4 -> 0 rings
    rings_4 = find_copy_rings(pairs, min_ring_size=4)
    assert len(rings_4) == 0

    # min_ring_size=2 -> 1 ring of size 3
    rings_2 = find_copy_rings(pairs, min_ring_size=2)
    assert len(rings_2) == 1
    print("✓ test_configurable_min_ring_size passed")


def test_analyze_endpoint_returns_copy_rings():
    """Verify /analyze returns copy_rings and summary count in the API response."""
    from fastapi.testclient import TestClient
    from backend.app.main import app

    client = TestClient(app)

    # 3 identical files -> Alice, Bob, Charlie
    content = (
        "Observation: When voltage was increased from 2V to 10V in steps of 2V, "
        "the current increased proportionally. At 2V the current was 0.020A, at 4V "
        "it was 0.041A, at 6V it was 0.059A, at 8V it was 0.082A, and at 10V it "
        "was 0.098A. The calculated resistance was approximately 102 ohms.\n\n"
        "Conclusion: The experiment successfully verified Ohm's Law with constant resistance."
    )

    files = [
        ("files", ("alice.txt", content.encode("utf-8"), "text/plain")),
        ("files", ("bob.txt", content.encode("utf-8"), "text/plain")),
        ("files", ("charlie.txt", content.encode("utf-8"), "text/plain")),
    ]

    response = client.post(
        "/analyze",
        files=files,
        data={"threshold": "0.85", "min_ring_size": "3"},
    )

    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()

    assert "copy_rings" in data
    assert "copy_ring_count" in data["summary"]
    assert len(data["copy_rings"]) == 1
    ring = data["copy_rings"][0]
    assert ring["size"] == 3
    assert set(ring["members"]) == {"Alice", "Bob", "Charlie"}
    assert ring["pair_count"] == 3  # All pairs flagged
    assert ring["average_score"] >= 0.95
    assert data["summary"]["copy_ring_count"] == 1
    print("✓ test_analyze_endpoint_returns_copy_rings passed")


if __name__ == "__main__":
    print("Running copy ring tests...\n")
    test_ring_of_3_students()
    test_ring_of_4_students()
    test_two_separate_pairs_do_not_form_ring()
    test_unrelated_students_excluded()
    test_coincidence_pair_excluded_when_explanations_available()
    test_configurable_min_ring_size()
    test_analyze_endpoint_returns_copy_rings()
    print("\nAll copy ring tests passed! ✅")
