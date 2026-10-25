"""Template removal module for Local Echo Scan.

Detects and removes boilerplate/template text from student submissions
so that only student-specific content (observations, calculations,
conclusions) is compared for similarity.

Two removal strategies:
1. Lab manual matching – paragraphs similar to a provided lab manual.
2. Auto-detect boilerplate – paragraphs that appear in many files.

Embeddings are cached so Step 3 (similarity) can reuse them.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
from sentence_transformers import SentenceTransformer

from .models import Paragraph, StudentSubmission

logger = logging.getLogger(__name__)

# Default thresholds
DEFAULT_BOILERPLATE_SIM_THRESHOLD = 0.9
DEFAULT_BOILERPLATE_FREQ_THRESHOLD = 0.6
DEFAULT_MANUAL_SIM_THRESHOLD = 0.85
MIN_FILES_FOR_AUTO_DETECT = 5


@dataclass
class RemovedParagraph:
    """A paragraph identified as template/boilerplate and removed."""

    text: str
    reason: str  # e.g. "lab manual match (similarity: 0.92)"
    source_student: str | None = None


@dataclass
class TemplateRemovalResult:
    """Result of template removal processing."""

    cleaned_submissions: list[StudentSubmission]
    removed_paragraphs: list[RemovedParagraph]
    removed_count: int
    boilerplate_texts: list[str]  # auto-detected boilerplate paragraph texts


class EmbeddingCache:
    """Manages sentence-transformer embeddings with caching.

    Loads the model once and caches embeddings keyed by paragraph text,
    so they can be reused across template removal and similarity steps.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        logger.info("Loading embedding model: %s", model_name)
        self._model = SentenceTransformer(model_name)
        self._cache: dict[str, np.ndarray] = {}
        logger.info("Embedding model loaded successfully")

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed a list of texts, using cache for previously seen texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            2D numpy array of shape (len(texts), embedding_dim).
        """
        uncached = [t for t in texts if t not in self._cache]

        if uncached:
            embeddings = self._model.encode(
                uncached,
                show_progress_bar=False,
                normalize_embeddings=True,  # pre-normalize for cosine sim
            )
            for text, emb in zip(uncached, embeddings):
                self._cache[text] = emb
            logger.debug(
                "Embedded %d new texts (%d from cache)",
                len(uncached),
                len(texts) - len(uncached),
            )

        return np.array([self._cache[t] for t in texts])

    def get_embedding(self, text: str) -> np.ndarray | None:
        """Get a cached embedding, or None if not cached."""
        return self._cache.get(text)

    @property
    def cache_size(self) -> int:
        """Number of cached embeddings."""
        return len(self._cache)


def cosine_similarity_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between all pairs of row vectors.

    Since embeddings are pre-normalized, this is just a dot product.

    Args:
        a: Matrix of shape (m, d).
        b: Matrix of shape (n, d).

    Returns:
        Similarity matrix of shape (m, n).
    """
    if a.size == 0 or b.size == 0:
        return np.zeros((a.shape[0], b.shape[0]), dtype=np.float32)
    a_mat = np.asarray(a, dtype=np.float32)
    b_mat = np.asarray(b, dtype=np.float32)
    sim = a_mat @ b_mat.T
    return np.clip(sim, -1.0, 1.0)


def detect_boilerplate(
    submissions: list[StudentSubmission],
    cache: EmbeddingCache,
    sim_threshold: float = DEFAULT_BOILERPLATE_SIM_THRESHOLD,
    freq_threshold: float = DEFAULT_BOILERPLATE_FREQ_THRESHOLD,
) -> list[str]:
    """Auto-detect boilerplate paragraphs that appear across many files.

    A paragraph is considered boilerplate if near-identical versions
    (cosine similarity > sim_threshold) appear in more than freq_threshold
    fraction of all files.

    Skips detection if fewer than MIN_FILES_FOR_AUTO_DETECT files.

    Args:
        submissions: List of parsed student submissions.
        cache: Embedding cache (will be populated as a side effect).
        sim_threshold: Minimum cosine similarity for "near-identical".
        freq_threshold: Minimum fraction of files containing the paragraph.

    Returns:
        List of boilerplate paragraph texts.
    """
    valid_subs = [s for s in submissions if not s.error and s.paragraphs]
    n_files = len(valid_subs)

    if n_files < MIN_FILES_FOR_AUTO_DETECT:
        logger.info(
            "Skipping boilerplate auto-detect: only %d files (need >= %d)",
            n_files,
            MIN_FILES_FOR_AUTO_DETECT,
        )
        return []

    # Collect all paragraphs with their file index
    all_texts: list[str] = []
    file_indices: list[int] = []

    for file_idx, sub in enumerate(valid_subs):
        for para in sub.paragraphs:
            all_texts.append(para.text)
            file_indices.append(file_idx)

    if not all_texts:
        return []

    # Embed all paragraphs (populates the cache)
    embeddings = cache.embed_texts(all_texts)

    # Compute pairwise similarity matrix
    sim_matrix = cosine_similarity_matrix(embeddings, embeddings)

    # For each paragraph, count distinct files with a near-identical match
    boilerplate_texts: list[str] = []
    seen: set[str] = set()

    for i in range(len(all_texts)):
        if all_texts[i] in seen:
            continue

        matching_files: set[int] = set()
        for j in range(len(all_texts)):
            if sim_matrix[i, j] >= sim_threshold:
                matching_files.add(file_indices[j])

        file_fraction = len(matching_files) / n_files

        if file_fraction > freq_threshold:
            boilerplate_texts.append(all_texts[i])
            # Mark all near-identical texts as seen to avoid duplicates
            for j in range(len(all_texts)):
                if sim_matrix[i, j] >= sim_threshold:
                    seen.add(all_texts[j])

    logger.info(
        "Detected %d boilerplate paragraphs (sim > %.2f in > %.0f%% of %d files)",
        len(boilerplate_texts),
        sim_threshold,
        freq_threshold * 100,
        n_files,
    )

    return boilerplate_texts


def remove_template(
    submissions: list[StudentSubmission],
    cache: EmbeddingCache,
    manual_paragraphs: list[Paragraph] | None = None,
    manual_sim_threshold: float = DEFAULT_MANUAL_SIM_THRESHOLD,
    boilerplate_sim_threshold: float = DEFAULT_BOILERPLATE_SIM_THRESHOLD,
    boilerplate_freq_threshold: float = DEFAULT_BOILERPLATE_FREQ_THRESHOLD,
) -> TemplateRemovalResult:
    """Remove template/boilerplate text from student submissions.

    Two removal methods applied in order:
    1. Lab manual matching: remove paragraphs with cosine similarity
       > manual_sim_threshold to any lab manual paragraph.
    2. Auto-detect boilerplate: remove paragraphs that appear in
       > freq_threshold fraction of files (by sim > boilerplate_sim_threshold).

    Args:
        submissions: Parsed student submissions.
        cache: Embedding cache for reuse across pipeline steps.
        manual_paragraphs: Optional paragraphs from the lab manual.
        manual_sim_threshold: Similarity threshold for manual matching.
        boilerplate_sim_threshold: Similarity threshold for boilerplate.
        boilerplate_freq_threshold: Frequency threshold for boilerplate.

    Returns:
        TemplateRemovalResult with cleaned submissions and removal info.
    """
    removed_list: list[RemovedParagraph] = []

    # --- Embed lab manual paragraphs (if provided) ---
    manual_embeddings: np.ndarray | None = None
    if manual_paragraphs:
        manual_texts = [p.text for p in manual_paragraphs]
        manual_embeddings = cache.embed_texts(manual_texts)
        logger.info("Embedded %d lab manual paragraphs", len(manual_texts))

    # --- Auto-detect boilerplate ---
    boilerplate_texts = detect_boilerplate(
        submissions,
        cache,
        sim_threshold=boilerplate_sim_threshold,
        freq_threshold=boilerplate_freq_threshold,
    )

    boilerplate_embeddings: np.ndarray | None = None
    if boilerplate_texts:
        boilerplate_embeddings = cache.embed_texts(boilerplate_texts)

    # --- Filter paragraphs from each submission ---
    cleaned_submissions: list[StudentSubmission] = []
    total_removed = 0

    for sub in submissions:
        if sub.error or not sub.paragraphs:
            cleaned_submissions.append(sub)
            continue

        para_texts = [p.text for p in sub.paragraphs]
        para_embeddings = cache.embed_texts(para_texts)

        kept_paragraphs: list[Paragraph] = []

        for idx, para in enumerate(sub.paragraphs):
            emb = para_embeddings[idx].reshape(1, -1)
            removed = False
            removal_reason = ""

            # Check against lab manual first
            if manual_embeddings is not None:
                sims = cosine_similarity_matrix(emb, manual_embeddings)[0]
                max_sim = float(np.max(sims))
                if max_sim >= manual_sim_threshold:
                    removed = True
                    removal_reason = (
                        f"lab manual match (similarity: {max_sim:.2f})"
                    )

            # Check against auto-detected boilerplate
            if not removed and boilerplate_embeddings is not None:
                sims = cosine_similarity_matrix(emb, boilerplate_embeddings)[0]
                max_sim = float(np.max(sims))
                if max_sim >= boilerplate_sim_threshold:
                    removed = True
                    removal_reason = (
                        f"boilerplate detected (similarity: {max_sim:.2f})"
                    )

            if removed:
                removed_list.append(RemovedParagraph(
                    text=para.text,
                    reason=removal_reason,
                    source_student=sub.name,
                ))
                total_removed += 1
            else:
                kept_paragraphs.append(Paragraph(
                    text=para.text,
                    index=len(kept_paragraphs),
                ))

        cleaned_sub = StudentSubmission(
            name=sub.name,
            filename=sub.filename,
            paragraphs=kept_paragraphs,
            raw_text=sub.raw_text,
        )
        cleaned_submissions.append(cleaned_sub)

        logger.info(
            "'%s': kept %d / %d paragraphs",
            sub.name,
            len(kept_paragraphs),
            len(sub.paragraphs),
        )

    return TemplateRemovalResult(
        cleaned_submissions=cleaned_submissions,
        removed_paragraphs=removed_list,
        removed_count=total_removed,
        boilerplate_texts=boilerplate_texts,
    )
