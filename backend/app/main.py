"""Local Echo Scan – FastAPI backend.

A local-only tool that helps professors find suspiciously similar
student submissions. All processing runs on the professor's laptop.
No data is sent to any online service.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path

from typing import Optional, List, Dict, Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .parsing import parse_file, parse_files, split_into_paragraphs, SUPPORTED_EXTENSIONS
from .template import EmbeddingCache, remove_template
from .similarity import compute_pairwise_similarity
from .explain import explain_flagged_pairs
from .rings import find_copy_rings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# Lazy-loaded embedding cache (model loaded on first use)
_embedding_cache: EmbeddingCache | None = None


def get_embedding_cache() -> EmbeddingCache:
    """Get or create the global embedding cache singleton."""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache

app = FastAPI(
    title="Local Echo Scan",
    description="Local-only similarity detection for student submissions.",
    version="0.1.0",
)

# Allow the React dev server to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _save_uploads(
    files: list[UploadFile],
    dest_dir: str,
) -> list[tuple[str, str]]:
    """Save uploaded files to a temporary directory.

    Returns a list of (saved_path, original_filename) tuples.
    """
    saved: list[tuple[str, str]] = []
    for upload in files:
        if not upload.filename:
            continue
        ext = Path(upload.filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            logger.info("Skipping unsupported upload: '%s'", upload.filename)
            continue
        dest_path = os.path.join(dest_dir, upload.filename)
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(upload.file, f)
        saved.append((dest_path, upload.filename))
    return saved


@app.post("/parse")
async def parse_submissions(
    files: list[UploadFile] = File(..., description="Student submission files"),
) -> JSONResponse:
    """Parse uploaded student submissions and return extracted paragraphs.

    This is the Step 1 endpoint: upload files, extract text, split into
    paragraphs, and return structured results.
    """
    if not files:
        return JSONResponse(
            status_code=400,
            content={"error": "No files provided."},
        )

    # Save uploads to a temp directory for processing
    tmp_dir = tempfile.mkdtemp(prefix="les_")
    try:
        saved_files = _save_uploads(files, tmp_dir)

        if not saved_files:
            return JSONResponse(
                status_code=400,
                content={"error": "No supported files found."},
            )

        submissions = parse_files(saved_files)

        # Build response
        results = []
        for sub in submissions:
            results.append({
                "name": sub.name,
                "filename": sub.filename,
                "paragraph_count": len(sub.paragraphs),
                "paragraphs": [
                    {"text": p.text, "index": p.index}
                    for p in sub.paragraphs
                ],
                "error": sub.error,
            })

        total_paragraphs = sum(len(s.paragraphs) for s in submissions)
        errors = [s.filename for s in submissions if s.error]

        logger.info(
            "Parsed %d files → %d paragraphs (%d errors)",
            len(submissions),
            total_paragraphs,
            len(errors),
        )

        return JSONResponse(content={
            "submissions": results,
            "summary": {
                "total_files": len(submissions),
                "total_paragraphs": total_paragraphs,
                "files_with_errors": errors,
            },
        })

    finally:
        # Clean up temp files
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/parse-with-template")
async def parse_and_clean(
    files: List[UploadFile] = File(..., description="Student submission files"),
    manual: Optional[UploadFile] = File(None, description="Optional lab manual"),
    manual_sim_threshold: float = Form(0.85),
    boilerplate_sim_threshold: float = Form(0.9),
    boilerplate_freq_threshold: float = Form(0.6),
) -> JSONResponse:
    """Parse submissions and remove template/boilerplate text.

    Accepts student files plus an optional lab manual. Returns cleaned
    paragraphs per student along with what was removed and why.
    """
    if not files:
        return JSONResponse(
            status_code=400,
            content={"error": "No files provided."},
        )

    tmp_dir = tempfile.mkdtemp(prefix="les_")
    try:
        saved_files = _save_uploads(files, tmp_dir)
        if not saved_files:
            return JSONResponse(
                status_code=400,
                content={"error": "No supported files found."},
            )

        submissions = parse_files(saved_files)

        # Parse lab manual if provided
        manual_paragraphs = None
        if manual and manual.filename:
            manual_path = os.path.join(tmp_dir, f"_manual_{manual.filename}")
            with open(manual_path, "wb") as f:
                shutil.copyfileobj(manual.file, f)
            manual_sub = parse_file(manual_path, manual.filename)
            if not manual_sub.error:
                manual_paragraphs = manual_sub.paragraphs
                logger.info(
                    "Lab manual: %d paragraphs", len(manual_paragraphs)
                )

        # Run template removal
        cache = get_embedding_cache()
        result = remove_template(
            submissions=submissions,
            cache=cache,
            manual_paragraphs=manual_paragraphs,
            manual_sim_threshold=manual_sim_threshold,
            boilerplate_sim_threshold=boilerplate_sim_threshold,
            boilerplate_freq_threshold=boilerplate_freq_threshold,
        )

        # Build response
        cleaned_results = []
        for sub in result.cleaned_submissions:
            cleaned_results.append({
                "name": sub.name,
                "filename": sub.filename,
                "paragraph_count": len(sub.paragraphs),
                "paragraphs": [
                    {"text": p.text, "index": p.index}
                    for p in sub.paragraphs
                ],
                "error": sub.error,
            })

        removed_info = [
            {
                "text": rp.text[:120] + ("…" if len(rp.text) > 120 else ""),
                "reason": rp.reason,
                "student": rp.source_student,
            }
            for rp in result.removed_paragraphs
        ]

        total_cleaned = sum(
            len(s.paragraphs) for s in result.cleaned_submissions
        )

        return JSONResponse(content={
            "submissions": cleaned_results,
            "template_removal": {
                "removed_count": result.removed_count,
                "boilerplate_detected": len(result.boilerplate_texts),
                "removed_paragraphs": removed_info,
            },
            "summary": {
                "total_files": len(submissions),
                "total_paragraphs_after_cleaning": total_cleaned,
                "files_with_errors": [
                    s.filename for s in submissions if s.error
                ],
            },
        })

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/analyze")
async def analyze(
    files: List[UploadFile] = File(..., description="Student submission files"),
    manual: Optional[UploadFile] = File(None, description="Optional lab manual"),
    threshold: float = Form(0.85, description="Flag threshold for pair score"),
    match_threshold: float = Form(0.80, description="Min similarity for a paragraph match"),
    manual_sim_threshold: float = Form(0.85),
    boilerplate_sim_threshold: float = Form(0.9),
    boilerplate_freq_threshold: float = Form(0.6),
    explain: bool = Form(False, description="Run Gemma explanations for flagged pairs"),
    explain_top_n: int = Form(10, description="Max flagged pairs to explain"),
    min_ring_size: int = Form(3, description="Minimum students to form a copy ring"),
) -> JSONResponse:
    """Full analysis pipeline: parse → template removal → similarity → explanations → rings.

    Accepts student files and an optional lab manual, runs all processing
    steps, and returns flagged pairs with scores, matching passages,
    template removal info, optional Gemma explanations, and detected copy rings.
    """
    if not files:
        return JSONResponse(
            status_code=400,
            content={"error": "No files provided."},
        )

    tmp_dir = tempfile.mkdtemp(prefix="les_")
    try:
        # --- Step 1: Parse ---
        saved_files = _save_uploads(files, tmp_dir)
        if not saved_files:
            return JSONResponse(
                status_code=400,
                content={"error": "No supported files found."},
            )

        submissions = parse_files(saved_files)

        # Parse lab manual if provided
        manual_paragraphs = None
        if manual and manual.filename:
            manual_path = os.path.join(tmp_dir, f"_manual_{manual.filename}")
            with open(manual_path, "wb") as f:
                shutil.copyfileobj(manual.file, f)
            manual_sub = parse_file(manual_path, manual.filename)
            if not manual_sub.error:
                manual_paragraphs = manual_sub.paragraphs
                logger.info(
                    "Lab manual: %d paragraphs", len(manual_paragraphs)
                )

        # --- Step 2: Template removal ---
        cache = get_embedding_cache()
        template_result = remove_template(
            submissions=submissions,
            cache=cache,
            manual_paragraphs=manual_paragraphs,
            manual_sim_threshold=manual_sim_threshold,
            boilerplate_sim_threshold=boilerplate_sim_threshold,
            boilerplate_freq_threshold=boilerplate_freq_threshold,
        )

        # --- Step 3: Similarity scoring ---
        flagged_pairs = compute_pairwise_similarity(
            submissions=template_result.cleaned_submissions,
            cache=cache,
            match_threshold=match_threshold,
            flag_threshold=threshold,
        )

        # --- Step 4: Gemma explanations ---
        explanations_available = False
        if explain and flagged_pairs:
            flagged_pairs, explanations_available = explain_flagged_pairs(
                flagged_pairs=flagged_pairs,
                top_n=explain_top_n,
            )

        # --- Step 5: Copy rings ---
        copy_rings = find_copy_rings(
            flagged_pairs=flagged_pairs,
            min_ring_size=min_ring_size,
            explanations_available=explanations_available,
        )

        # --- Build response ---
        flagged_response = []
        for fp in flagged_pairs:
            flagged_response.append({
                "student_a": fp.student_a,
                "student_b": fp.student_b,
                "score": fp.score,
                "match_count": len(fp.matched_pairs),
                "label": fp.label,
                "reason": fp.reason,
                "matched_passages": [
                    {
                        "text_a": mp.student_a_paragraph.text,
                        "text_b": mp.student_b_paragraph.text,
                        "similarity": mp.similarity,
                    }
                    for mp in fp.matched_pairs
                ],
            })

        copy_rings_response = [
            {
                "members": cr.members,
                "size": cr.size,
                "pair_count": cr.pair_count,
                "average_score": cr.average_score,
                "description": cr.description,
            }
            for cr in copy_rings
        ]

        # Submission summaries
        submission_summaries = []
        for sub in template_result.cleaned_submissions:
            submission_summaries.append({
                "name": sub.name,
                "filename": sub.filename,
                "paragraph_count": len(sub.paragraphs),
                "paragraphs": [
                    {"text": p.text, "index": p.index}
                    for p in sub.paragraphs
                ],
                "error": sub.error,
            })

        removed_info = [
            {
                "text": rp.text[:120] + ("\u2026" if len(rp.text) > 120 else ""),
                "reason": rp.reason,
                "student": rp.source_student,
            }
            for rp in template_result.removed_paragraphs
        ]

        total_cleaned = sum(
            len(s.paragraphs)
            for s in template_result.cleaned_submissions
        )

        return JSONResponse(content={
            "flagged_pairs": flagged_response,
            "copy_rings": copy_rings_response,
            "submissions": submission_summaries,
            "explanations_available": explanations_available,
            "template_removal": {
                "removed_count": template_result.removed_count,
                "boilerplate_detected": len(
                    template_result.boilerplate_texts
                ),
                "removed_paragraphs": removed_info,
            },
            "summary": {
                "total_files": len(submissions),
                "total_paragraphs_after_cleaning": total_cleaned,
                "flagged_pair_count": len(flagged_pairs),
                "copy_ring_count": len(copy_rings),
                "explanations_available": explanations_available,
                "files_with_errors": [
                    s.filename for s in submissions if s.error
                ],
            },
        })

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "Local Echo Scan"}
