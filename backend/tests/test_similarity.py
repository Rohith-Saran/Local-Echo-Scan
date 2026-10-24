"""Tests for similarity scoring module.

Creates a small fake dataset with:
- A direct copy (identical observation text) → should be flagged, high score
- A reworded copy (paraphrased observation) → should be flagged, moderate score
- An unrelated pair (completely different content) → should NOT be flagged

Verifies that the similarity module correctly flags copies and
ignores unrelated work, reusing cached embeddings from template removal.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.models import Paragraph, StudentSubmission
from backend.app.template import EmbeddingCache, remove_template
from backend.app.similarity import compute_pairwise_similarity


# ---------- Test data ----------

# Student A: original observation
OBSERVATION_ORIGINAL = (
    "Observation: When the voltage was increased from 2V to 10V in steps of 2V, "
    "the current increased proportionally. At 2V the current was 0.020A, at 4V "
    "it was 0.041A, at 6V it was 0.059A, at 8V it was 0.082A, and at 10V it "
    "was 0.098A. The calculated resistance was approximately 102 ohms."
)

CONCLUSION_ORIGINAL = (
    "Conclusion: The experiment successfully verified Ohm's Law. The V-I "
    "characteristic was a straight line passing through the origin, confirming "
    "that the conductor follows ohmic behavior with constant resistance."
)

# Student B: DIRECT COPY of A (identical text)
OBSERVATION_COPY = OBSERVATION_ORIGINAL
CONCLUSION_COPY = CONCLUSION_ORIGINAL

# Student C: REWORDED COPY of A (paraphrased)
OBSERVATION_REWORDED = (
    "Observation: Increasing voltage from 2V to 10V in 2V intervals caused "
    "current to rise proportionally. Values recorded: 2V (0.020A), 4V (0.041A), "
    "6V (0.059A), 8V (0.082A), and 10V (0.098A). The resulting resistance "
    "was calculated to be roughly 102 ohms."
)

CONCLUSION_REWORDED = (
    "Conclusion: Ohm's Law was successfully verified in this experiment. "
    "The V-I characteristic curve was a straight line through the origin, "
    "confirming that the conductor follows ohmic behavior with constant resistance."
)

# Student D: COMPLETELY DIFFERENT experiment (unrelated)
OBSERVATION_UNRELATED = (
    "Observation: The pendulum was released from an angle of 10 degrees and "
    "its period was measured. After 20 oscillations, the average period was "
    "found to be 1.42 seconds. The length of the pendulum was 50 cm. Using "
    "T = 2*pi*sqrt(L/g), the value of g was calculated as 9.78 m/s^2."
)

CONCLUSION_UNRELATED = (
    "Conclusion: The acceleration due to gravity was determined to be 9.78 "
    "m/s^2, which is close to the accepted value of 9.81 m/s^2. The small "
    "error of 0.3% may be due to air resistance and measurement inaccuracy."
)


def _make_submission(name: str, obs: str, conc: str) -> StudentSubmission:
    """Create a submission with observation and conclusion paragraphs."""
    paragraphs = [
        Paragraph(text=obs, index=0),
        Paragraph(text=conc, index=1),
    ]
    return StudentSubmission(
        name=name,
        filename=f"{name.lower().replace(' ', '_')}.txt",
        paragraphs=paragraphs,
        raw_text=f"{obs}\n\n{conc}",
    )


def test_direct_copy_flagged():
    """A direct copy should be flagged with a very high score (>= 0.99)."""
    cache = EmbeddingCache()

    submissions = [
        _make_submission("Alice", OBSERVATION_ORIGINAL, CONCLUSION_ORIGINAL),
        _make_submission("Bob", OBSERVATION_COPY, CONCLUSION_COPY),
    ]

    flagged = compute_pairwise_similarity(
        submissions, cache,
        match_threshold=0.80,
        flag_threshold=0.85,
    )

    assert len(flagged) == 1, f"Expected 1 flagged pair, got {len(flagged)}"
    pair = flagged[0]

    assert pair.score >= 0.99, (
        f"Direct copy should score >= 0.99, got {pair.score}"
    )
    assert len(pair.matched_pairs) >= 2, (
        f"Should have >= 2 matched passages, got {len(pair.matched_pairs)}"
    )

    # Verify matched passages are returned
    for mp in pair.matched_pairs:
        assert mp.student_a_paragraph.text, "Missing text_a"
        assert mp.student_b_paragraph.text, "Missing text_b"
        assert mp.similarity >= 0.80, f"Match below threshold: {mp.similarity}"

    print(
        f"✓ direct copy flagged: score={pair.score}, "
        f"matches={pair.match_count}"
    )


def test_reworded_copy_flagged():
    """A paraphrased copy should be flagged with a moderate-to-high score."""
    cache = EmbeddingCache()

    submissions = [
        _make_submission("Alice", OBSERVATION_ORIGINAL, CONCLUSION_ORIGINAL),
        _make_submission("Carol", OBSERVATION_REWORDED, CONCLUSION_REWORDED),
    ]

    flagged = compute_pairwise_similarity(
        submissions, cache,
        match_threshold=0.80,
        flag_threshold=0.85,
    )

    assert len(flagged) == 1, f"Expected 1 flagged pair, got {len(flagged)}"
    pair = flagged[0]

    assert pair.score >= 0.85, (
        f"Reworded copy should score >= 0.85, got {pair.score}"
    )

    print(
        f"✓ reworded copy flagged: score={pair.score}, "
        f"matches={pair.match_count}"
    )


def test_unrelated_not_flagged():
    """Completely different submissions should NOT be flagged."""
    cache = EmbeddingCache()

    submissions = [
        _make_submission("Alice", OBSERVATION_ORIGINAL, CONCLUSION_ORIGINAL),
        _make_submission("Dave", OBSERVATION_UNRELATED, CONCLUSION_UNRELATED),
    ]

    flagged = compute_pairwise_similarity(
        submissions, cache,
        match_threshold=0.80,
        flag_threshold=0.85,
    )

    assert len(flagged) == 0, (
        f"Unrelated pair should NOT be flagged, but got {len(flagged)} pairs"
    )

    print("✓ unrelated pair NOT flagged")


def test_mixed_set_ranking():
    """In a mixed set, copies should be flagged and ranked above unrelated."""
    cache = EmbeddingCache()

    submissions = [
        _make_submission("Alice", OBSERVATION_ORIGINAL, CONCLUSION_ORIGINAL),
        _make_submission("Bob", OBSERVATION_COPY, CONCLUSION_COPY),
        _make_submission("Carol", OBSERVATION_REWORDED, CONCLUSION_REWORDED),
        _make_submission("Dave", OBSERVATION_UNRELATED, CONCLUSION_UNRELATED),
    ]

    flagged = compute_pairwise_similarity(
        submissions, cache,
        match_threshold=0.80,
        flag_threshold=0.85,
    )

    # Direct copy and reworded copy should be flagged
    flagged_names = {(fp.student_a, fp.student_b) for fp in flagged}

    # Alice-Bob (direct copy) must be flagged
    assert ("Alice", "Bob") in flagged_names, "Alice-Bob direct copy not flagged"

    # Alice-Carol (reworded) should be flagged
    assert ("Alice", "Carol") in flagged_names, (
        "Alice-Carol reworded copy not flagged"
    )

    # No pair involving Dave should be flagged (he did a different experiment)
    dave_pairs = [fp for fp in flagged if "Dave" in (fp.student_a, fp.student_b)]
    assert len(dave_pairs) == 0, (
        f"Dave should not be flagged, but {len(dave_pairs)} pairs found"
    )

    # Direct copy should rank higher than reworded
    if len(flagged) >= 2:
        assert flagged[0].score >= flagged[1].score, (
            "Flagged pairs should be sorted by score (highest first)"
        )

    print(
        f"✓ mixed set: {len(flagged)} pairs flagged, "
        f"sorted by score: {[fp.score for fp in flagged]}"
    )


def test_cache_reuse_across_steps():
    """Embeddings cached during template removal should be reused."""
    cache = EmbeddingCache()

    submissions = [
        _make_submission("Alice", OBSERVATION_ORIGINAL, CONCLUSION_ORIGINAL),
        _make_submission("Bob", OBSERVATION_COPY, CONCLUSION_COPY),
    ]

    # Run template removal first (populates cache)
    template_result = remove_template(submissions, cache)
    cache_size_after_template = cache.cache_size

    # Run similarity (should reuse cached embeddings)
    flagged = compute_pairwise_similarity(
        template_result.cleaned_submissions, cache,
        match_threshold=0.80,
        flag_threshold=0.85,
    )

    cache_size_after_similarity = cache.cache_size

    # Cache should not grow since all texts were already embedded
    assert cache_size_after_similarity == cache_size_after_template, (
        f"Cache grew from {cache_size_after_template} to "
        f"{cache_size_after_similarity}; embeddings were not reused"
    )

    assert len(flagged) == 1, "Direct copy should still be flagged"

    print(
        f"✓ cache reuse: {cache_size_after_template} entries, "
        f"no growth after similarity"
    )


if __name__ == "__main__":
    print("Running similarity tests...\n")

    test_direct_copy_flagged()
    test_reworded_copy_flagged()
    test_unrelated_not_flagged()
    test_mixed_set_ranking()
    test_cache_reuse_across_steps()

    print("\nAll similarity tests passed! ✅")
