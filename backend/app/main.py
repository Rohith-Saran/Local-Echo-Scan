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

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .parsing import parse_files, SUPPORTED_EXTENSIONS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Local Echo Scan",
    description="Local-only similarity detection for student submissions.",
    version="0.1.0",
)

# Allow the React dev server to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "Local Echo Scan"}
