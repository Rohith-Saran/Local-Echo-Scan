"""Similarity scoring module for Local Echo Scan.

Compares all student pairs using cached paragraph embeddings.
For each pair, finds the best paragraph-to-paragraph matches and
computes a composite score to decide whether to flag the pair.
"""

from __future__ import annotations

import logging
from itertools import combinations

import numpy as np

from .models import FlaggedPair, MatchedPair, Paragraph, StudentSubmission
from .template import EmbeddingCache, cosine_similarity_matrix

logger = logging.getLogger(__name__)

# Default thresholds
DEFAULT_MATCH_THRESHOLD = 0.80
DEFAULT_FLAG_THRESHOLD = 0.85
DEFAULT_TOP_N = 3


def compute_pairwise_similarity(
    submissions: list[StudentSubmission],
    cache: EmbeddingCache,
    match_threshold: float = DEFAULT_MATCH_THRESHOLD,
    flag_threshold: float = DEFAULT_FLAG_THRESHOLD,
    top_n: int = DEFAULT_TOP_N,
) -> list[FlaggedPair]:
    """Compare all student pairs and flag those with similar content.

    For each pair of students, every paragraph of A is compared against
    every paragraph of B using cached embeddings. Matches above
    match_threshold are kept, and the pair score is the average of the
    top N matches. Pairs scoring above flag_threshold are flagged.

    Args:
        submissions: Cleaned student submissions (after template removal).
        cache: Embedding cache with pre-computed embeddings from Step 2.
        match_threshold: Minimum cosine similarity for a paragraph match.
        flag_threshold: Minimum pair score to flag for review.
        top_n: Number of top matches to average for the pair score.

    Returns:
        List of FlaggedPair objects, sorted by score (highest first).
    """
    valid = [s for s in submissions if not s.error and s.paragraphs]

    if len(valid) < 2:
        logger.info("Fewer than 2 valid submissions; nothing to compare.")
        return []

    # Pre-fetch all embeddings (reuses cache from template removal)
    sub_embeddings: dict[str, np.ndarray] = {}
    for sub in valid:
        texts = [p.text for p in sub.paragraphs]
        sub_embeddings[sub.name] = cache.embed_texts(texts)

    flagged_pairs: list[FlaggedPair] = []
    total_pairs = 0

    for sub_a, sub_b in combinations(valid, 2):
        total_pairs += 1

        emb_a = sub_embeddings[sub_a.name]
        emb_b = sub_embeddings[sub_b.name]

        # Similarity matrix: (|A paragraphs| × |B paragraphs|)
        sim_matrix = cosine_similarity_matrix(emb_a, emb_b)

        # Collect all matches above the match threshold
        matches: list[MatchedPair] = []
        for i in range(len(sub_a.paragraphs)):
            for j in range(len(sub_b.paragraphs)):
                sim = float(sim_matrix[i, j])
                if sim >= match_threshold:
                    matches.append(MatchedPair(
                        student_a_paragraph=sub_a.paragraphs[i],
                        student_b_paragraph=sub_b.paragraphs[j],
                        similarity=round(sim, 4),
                    ))

        if not matches:
            continue

        # Sort by similarity descending, keep top N
        matches.sort(key=lambda m: m.similarity, reverse=True)
        top_matches = matches[:top_n]

        # Pair score = average of top matches
        score = sum(m.similarity for m in top_matches) / len(top_matches)

        if score >= flag_threshold:
            flagged_pairs.append(FlaggedPair(
                student_a=sub_a.name,
                student_b=sub_b.name,
                score=round(score, 4),
                matched_pairs=top_matches,
            ))

    # Sort flagged pairs by score, highest first
    flagged_pairs.sort(key=lambda fp: fp.score, reverse=True)

    logger.info(
        "Compared %d student pairs, flagged %d (score >= %.2f)",
        total_pairs,
        len(flagged_pairs),
        flag_threshold,
    )

    return flagged_pairs
