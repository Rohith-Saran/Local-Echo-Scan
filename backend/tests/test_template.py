"""Tests for template removal module.

Creates a fake dataset where:
- 6 students share the same aim, apparatus, and procedure (template text)
- Each student has unique observation and conclusion paragraphs
- Verifies that template text is auto-detected and removed
- Verifies that unique observations are kept
- Tests lab manual matching with configurable threshold
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.models import Paragraph, StudentSubmission
from backend.app.template import (
    EmbeddingCache,
    detect_boilerplate,
    remove_template,
    MIN_FILES_FOR_AUTO_DETECT,
)

# ---------- Shared template text (appears in all files) ----------

SHARED_AIM = (
    "Aim: To verify Ohm's Law by measuring the current through a "
    "conductor for different values of the applied voltage and to "
    "determine the resistance of the conductor."
)

SHARED_APPARATUS = (
    "Apparatus: A battery or DC power supply, an ammeter, a voltmeter, "
    "a rheostat, a resistance wire, connecting wires, and a one-way key."
)

SHARED_PROCEDURE = (
    "Procedure: Connect the circuit as shown in the circuit diagram. "
    "Close the key and adjust the rheostat to get the minimum reading "
    "on the ammeter. Note the ammeter and voltmeter readings. Repeat "
    "the experiment for five different values of current by adjusting "
    "the rheostat each time."
)

# ---------- Unique observations per student ----------

OBSERVATIONS = [
    (
        "Observation: When voltage was set to 2V the current was 0.020A, "
        "at 4V it was 0.041A, at 6V it was 0.059A, at 8V it was 0.082A, "
        "and at 10V it was 0.098A. The resistance computed was about 102 ohms."
    ),
    (
        "Observation: The measured values were V=1.5V I=0.015A, V=3V I=0.030A, "
        "V=4.5V I=0.044A, V=6V I=0.061A, V=7.5V I=0.074A. Average resistance "
        "was approximately 100.5 ohms across all five readings."
    ),
    (
        "Observation: Starting at 2V the ammeter showed 0.019A. Increasing to "
        "4V gave 0.040A. At 6V I got 0.062A, at 8V it was 0.079A and at 10V "
        "the reading was 0.101A. Calculated R around 99 ohms."
    ),
    (
        "Observation: I recorded the following data points during the experiment. "
        "For 1V the current was 10mA, for 2V it was 21mA, for 3V it was 29mA, "
        "for 4V it was 39mA, and for 5V it measured 50mA. The average resistance "
        "was determined to be about 100 ohms."
    ),
    (
        "Observation: My readings showed voltages of 2, 4, 6, 8, 10 volts with "
        "corresponding currents of 0.021, 0.039, 0.058, 0.080, 0.100 amperes. "
        "The V-I graph was linear and the slope gave R equals 100.3 ohms."
    ),
    (
        "Observation: The experiment yielded voltage readings of 3V, 6V, 9V, "
        "12V and 15V with current readings of 0.030A, 0.060A, 0.091A, 0.119A "
        "and 0.152A respectively. The calculated resistance was 99.1 ohms."
    ),
]

CONCLUSIONS = [
    "Conclusion: Ohm's Law was verified. The V-I characteristic is linear.",
    "Conclusion: The experiment confirms that current is proportional to voltage.",
    "Conclusion: Successfully verified Ohm's Law, resistance is constant.",
    "Conclusion: V is directly proportional to I as predicted by Ohm's Law.",
    "Conclusion: The law was verified and the conductor follows ohmic behavior.",
    "Conclusion: Experiment validates Ohm's Law for the given resistance wire.",
]


def _make_submission(
    name: str,
    observation: str,
    conclusion: str,
) -> StudentSubmission:
    """Create a fake student submission with shared template + unique content."""
    paragraphs = [
        Paragraph(text=SHARED_AIM, index=0),
        Paragraph(text=SHARED_APPARATUS, index=1),
        Paragraph(text=SHARED_PROCEDURE, index=2),
        Paragraph(text=observation, index=3),
        Paragraph(text=conclusion, index=4),
    ]
    return StudentSubmission(
        name=name,
        filename=f"{name.lower().replace(' ', '_')}.txt",
        paragraphs=paragraphs,
        raw_text="\n\n".join(p.text for p in paragraphs),
    )


def _build_fake_dataset() -> list[StudentSubmission]:
    """Build a fake dataset with 6 students."""
    names = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank"]
    return [
        _make_submission(names[i], OBSERVATIONS[i], CONCLUSIONS[i])
        for i in range(6)
    ]


def test_auto_detect_boilerplate():
    """Shared aim, apparatus, procedure should be detected as boilerplate."""
    submissions = _build_fake_dataset()
    cache = EmbeddingCache()

    boilerplate = detect_boilerplate(
        submissions, cache, sim_threshold=0.9, freq_threshold=0.6
    )

    # The 3 shared paragraphs should be detected
    assert len(boilerplate) >= 3, (
        f"Expected >= 3 boilerplate paragraphs, got {len(boilerplate)}"
    )

    # Each boilerplate text should be one of the shared texts
    shared_texts = {SHARED_AIM, SHARED_APPARATUS, SHARED_PROCEDURE}
    for bp_text in boilerplate:
        assert bp_text in shared_texts, (
            f"Unexpected boilerplate: {bp_text[:60]}..."
        )

    print(f"✓ auto-detect boilerplate: found {len(boilerplate)} shared paragraphs")


def test_skip_auto_detect_few_files():
    """Auto-detect should be skipped with fewer than MIN_FILES_FOR_AUTO_DETECT."""
    submissions = _build_fake_dataset()[:3]  # only 3 files
    cache = EmbeddingCache()

    boilerplate = detect_boilerplate(submissions, cache)
    assert len(boilerplate) == 0, "Should skip auto-detect with < 5 files"
    print("✓ skip auto-detect with few files")


def test_template_removal_keeps_observations():
    """After template removal, only unique observations should remain."""
    submissions = _build_fake_dataset()
    cache = EmbeddingCache()

    result = remove_template(
        submissions=submissions,
        cache=cache,
        boilerplate_sim_threshold=0.9,
        boilerplate_freq_threshold=0.6,
    )

    # Check that observations were kept for each student
    for cleaned in result.cleaned_submissions:
        para_texts = [p.text for p in cleaned.paragraphs]

        # Should NOT contain any shared template text
        for shared in [SHARED_AIM, SHARED_APPARATUS, SHARED_PROCEDURE]:
            assert shared not in para_texts, (
                f"'{cleaned.name}' still contains template: {shared[:40]}..."
            )

        # Should contain at least the observation paragraph
        has_observation = any("Observation:" in t for t in para_texts)
        assert has_observation, (
            f"'{cleaned.name}' lost its observation paragraph!"
        )

    # Check removal stats
    # 6 students × 3 shared paragraphs = 18 removals expected
    assert result.removed_count >= 18, (
        f"Expected >= 18 removals, got {result.removed_count}"
    )

    print(
        f"✓ template removal: {result.removed_count} paragraphs removed, "
        f"observations kept for all {len(result.cleaned_submissions)} students"
    )


def test_lab_manual_matching():
    """Paragraphs matching a lab manual should be removed at 0.85 threshold."""
    # Use only 3 files so auto-detect is skipped; test manual matching alone
    submissions = _build_fake_dataset()[:3]
    cache = EmbeddingCache()

    # Create a manual with the aim and procedure
    manual_paragraphs = [
        Paragraph(text=SHARED_AIM, index=0),
        Paragraph(text=SHARED_PROCEDURE, index=1),
    ]

    result = remove_template(
        submissions=submissions,
        cache=cache,
        manual_paragraphs=manual_paragraphs,
        manual_sim_threshold=0.85,
    )

    # Each of 3 students should have aim + procedure removed (2 each = 6)
    assert result.removed_count >= 6, (
        f"Expected >= 6 removals from manual, got {result.removed_count}"
    )

    # Observations should still be there
    for cleaned in result.cleaned_submissions:
        has_observation = any(
            "Observation:" in p.text for p in cleaned.paragraphs
        )
        assert has_observation, f"'{cleaned.name}' lost its observation!"

    # Check that removal reasons mention lab manual
    manual_removals = [
        rp for rp in result.removed_paragraphs
        if "lab manual" in rp.reason
    ]
    assert len(manual_removals) >= 6, (
        f"Expected >= 6 manual match removals, got {len(manual_removals)}"
    )

    print(
        f"✓ lab manual matching: {result.removed_count} removed, "
        f"{len(manual_removals)} by manual match"
    )


def test_embedding_cache_reuse():
    """Verify that embeddings are cached and reused across calls."""
    cache = EmbeddingCache()

    texts = ["This is a test paragraph for caching verification purposes."]
    cache.embed_texts(texts)
    size_after_first = cache.cache_size

    # Embed the same text again
    cache.embed_texts(texts)
    size_after_second = cache.cache_size

    assert size_after_first == size_after_second, "Cache should reuse embeddings"
    assert cache.get_embedding(texts[0]) is not None, "Should retrieve cached embedding"

    print(f"✓ embedding cache reuse: {cache.cache_size} cached entries")


if __name__ == "__main__":
    print("Running template removal tests...\n")
    print("Loading embedding model (first run may download it)...\n")

    test_embedding_cache_reuse()
    test_skip_auto_detect_few_files()
    test_auto_detect_boilerplate()
    test_template_removal_keeps_observations()
    test_lab_manual_matching()

    print("\nAll template removal tests passed! ✅")
