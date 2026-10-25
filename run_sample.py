#!/usr/bin/env python3
"""Runner script for Local Echo Scan sample dataset.

Sends all 15 student files and lab manual from sample_data/output/
to POST /analyze (with explain=true) and prints a formatted report
of flagged pairs and copy rings.

Can target a running server at http://localhost:8000 or run directly
using FastAPI TestClient if the server is not currently running.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import httpx

API_URL = os.getenv("LES_API_URL", "http://localhost:8000/analyze")
OUTPUT_DIR = Path(__file__).resolve().parent / "sample_data" / "output"


def main():
    if not OUTPUT_DIR.exists():
        print("Sample data directory not found. Running generate.py...")
        from sample_data.generate import generate_sample_dataset
        generate_sample_dataset(OUTPUT_DIR)

    manual_file = OUTPUT_DIR / "lab_manual.txt"
    student_files = sorted([
        f for f in OUTPUT_DIR.iterdir()
        if f.is_file() and f.name != "lab_manual.txt" and not f.name.startswith(".")
    ])

    print(f"Found {len(student_files)} student submissions and lab manual:")
    print(f"Manual: {manual_file.name}")
    for sf in student_files:
        print(f"  - {sf.name}")
    print("\nSending files to /analyze (explain=true)...")

    # Prepare multipart files
    files = []
    file_handles = []
    try:
        for sf in student_files:
            fh = open(sf, "rb")
            file_handles.append(fh)
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if sf.suffix == ".docx" else "text/plain"
            files.append(("files", (sf.name, fh, content_type)))

        manual_fh = None
        if manual_file.exists():
            manual_fh = open(manual_file, "rb")
            file_handles.append(manual_fh)
            files.append(("manual", (manual_file.name, manual_fh, "text/plain")))

        data = {
            "threshold": "0.85",
            "match_threshold": "0.80",
            "explain": "true",
            "min_ring_size": "3",
        }

        # First try live server
        response_data = None
        try:
            with httpx.Client(timeout=120.0) as client:
                res = client.post(API_URL, files=files, data=data)
                if res.status_code == 200:
                    response_data = res.json()
        except Exception:
            # Fallback to direct FastAPI app invocation if live server is not up
            print(f"(Server at {API_URL} not reachable; running via direct FastAPI app runner)")
            # Rewind file handles
            for fh in file_handles:
                fh.seek(0)

            from fastapi.testclient import TestClient
            from backend.app.main import app
            client = TestClient(app)
            res = client.post("/analyze", files=files, data=data)
            if res.status_code == 200:
                response_data = res.json()
            else:
                print(f"Analysis failed: {res.status_code} {res.text}")
                return

    finally:
        for fh in file_handles:
            try:
                fh.close()
            except Exception:
                pass

    if not response_data:
        print("No response received.")
        return

    # Print Report
    print("\n" + "=" * 65)
    print("           LOCAL ECHO SCAN - ANALYSIS REPORT")
    print("=" * 65)

    summary = response_data.get("summary", {})
    tpl = response_data.get("template_removal", {})

    print(f"\nFiles processed:               {summary.get('total_files')}")
    print(f"Paragraphs after template removal: {summary.get('total_paragraphs_after_cleaning')}")
    print(f"Template paragraphs removed:   {tpl.get('removed_count')}")
    print(f"Explanations available:        {response_data.get('explanations_available')}")
    print(f"Flagged pairs detected:        {summary.get('flagged_pair_count')}")
    print(f"Copy rings detected:           {summary.get('copy_ring_count')}")

    print("\n" + "-" * 65)
    print("FLAGGED PAIRS (Ranked by Similarity Score)")
    print("-" * 65)

    flagged_pairs = response_data.get("flagged_pairs", [])
    if not flagged_pairs:
        print("No pairs flagged above threshold.")
    else:
        for i, pair in enumerate(flagged_pairs, 1):
            label = pair.get("label") or "unclassified"
            score = pair.get("score", 0.0)
            a = pair.get("student_a")
            b = pair.get("student_b")
            reason = pair.get("reason") or "No explanation generated."
            match_count = pair.get("match_count", 0)

            print(f"\n[{i}] {a}  <--->  {b}")
            print(f"    Similarity Score: {score:.4f}  ({match_count} matching passages)")
            print(f"    Gemma Label:      [{label.upper()}]")
            print(f"    Gemma Note:       {reason}")

    print("\n" + "-" * 65)
    print("COPY RINGS (Clusters >= 3 Students)")
    print("-" * 65)

    copy_rings = response_data.get("copy_rings", [])
    if not copy_rings:
        print("No copy rings detected.")
    else:
        for i, ring in enumerate(copy_rings, 1):
            members = ", ".join(ring.get("members", []))
            size = ring.get("size")
            pairs = ring.get("pair_count")
            avg_score = ring.get("average_score")
            desc = ring.get("description")

            print(f"\n[Ring {i}] ({size} students, {pairs} internal pairs, avg score: {avg_score:.4f})")
            print(f"    Description: {desc}")
            print(f"    Members:     {members}")

    print("\n" + "=" * 65 + "\n")


if __name__ == "__main__":
    main()
