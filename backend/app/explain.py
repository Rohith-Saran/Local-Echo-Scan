"""Gemma explanation module for Local Echo Scan.

Uses Ollama (default model 'gemma3') to classify flagged student pairs
into neutral categories: 'likely copy', 'paraphrase', 'shared source',
or 'coincidence', with a one-sentence neutral explanation.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx

from .models import FlaggedPair

logger = logging.getLogger(__name__)

# Allowed labels
VALID_LABELS = {"likely copy", "paraphrase", "shared source", "coincidence"}

# Configuration defaults
DEFAULT_OLLAMA_HOST = os.getenv("OLLAMA_HOST", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3")
DEFAULT_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "20.0"))
DEFAULT_TOP_N_EXPLAIN = 10


def extract_json_response(raw_text: str) -> dict[str, str] | None:
    """Safely extract and validate JSON response from Gemma.

    Strips markdown code fences (```json ... ```) and verifies the schema:
    {"label": "...", "reason": "..."} where label is in VALID_LABELS.
    """
    if not raw_text or not isinstance(raw_text, str):
        return None

    cleaned = raw_text.strip()

    # Strip code fences like ```json ... ``` or ``` ... ```
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    # Try direct parse
    data = None
    try:
        data = json.loads(cleaned)
    except Exception:
        # Fallback: search for first JSON object {...}
        match = re.search(r"(\{[\s\S]*\})", cleaned)
        if match:
            try:
                data = json.loads(match.group(1))
            except Exception:
                pass

    if not isinstance(data, dict):
        return None

    label = data.get("label")
    reason = data.get("reason")

    if not isinstance(label, str):
        return None

    norm_label = label.strip().lower()
    if norm_label not in VALID_LABELS:
        return None

    norm_reason = str(reason).strip() if reason is not None else ""
    return {
        "label": norm_label,
        "reason": norm_reason,
    }


def build_prompt(pair: FlaggedPair) -> str:
    """Build a neutral, objective prompt for Gemma."""
    # Build text of matching passages (up to top 3)
    passages_text = []
    for idx, match in enumerate(pair.matched_pairs[:3], 1):
        passages_text.append(
            f"--- Match {idx} (similarity: {match.similarity:.2f}) ---\n"
            f"Passage A: {match.student_a_paragraph.text}\n"
            f"Passage B: {match.student_b_paragraph.text}"
        )

    passages_block = "\n\n".join(passages_text)

    prompt = (
        "You are an academic analysis assistant. Compare the following matching passages "
        "extracted from two student submissions and categorize their relationship.\n\n"
        f"{passages_block}\n\n"
        "Categorize the similarity with exactly one of these labels:\n"
        "- \"likely copy\": passages share verbatim or nearly verbatim content and data\n"
        "- \"paraphrase\": passages convey identical observations or conclusions using reworded sentences\n"
        "- \"shared source\": passages appear to come from standard lab instructions, templates, or textbook definitions\n"
        "- \"coincidence\": similarity appears incidental or routine\n\n"
        "Provide a single, objective one-sentence explanation in neutral wording. Never accuse anyone.\n"
        "Reply with ONLY valid JSON with no markdown formatting or commentary in this exact format:\n"
        "{\"label\": \"likely copy\" | \"paraphrase\" | \"shared source\" | \"coincidence\", \"reason\": \"<one sentence>\"}"
    )
    return prompt


def is_ollama_online(host: str = DEFAULT_OLLAMA_HOST, timeout: float = 3.0) -> bool:
    """Quick check if Ollama server is responding."""
    try:
        with httpx.Client(timeout=timeout) as client:
            res = client.get(f"{host}/api/tags")
            return res.status_code == 200
    except Exception:
        return False


def explain_single_pair(
    pair: FlaggedPair,
    client: httpx.Client,
    host: str,
    model: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[str, str]:
    """Request explanation for a single pair from Ollama with 1 retry on invalid output."""
    url = f"{host}/api/generate"
    prompt = build_prompt(pair)

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }

    # Attempt 1
    try:
        res = client.post(url, json=payload, timeout=timeout)
        if res.status_code == 200:
            raw_response = res.json().get("response", "")
            parsed = extract_json_response(raw_response)
            if parsed:
                return parsed["label"], parsed["reason"]
            logger.warning("Invalid JSON from Gemma on attempt 1: %r", raw_response)
        else:
            logger.warning("Ollama returned status %d on attempt 1", res.status_code)
    except (httpx.TimeoutException, httpx.RequestError) as e:
        logger.warning("Error communicating with Ollama on attempt 1: %s", e)
        # If connection refused / host offline, re-raise to abort batch quickly
        if isinstance(e, httpx.ConnectError):
            raise

    # Attempt 2 (Retry with strict instruction)
    retry_prompt = (
        f"{prompt}\n\nIMPORTANT: Your previous output was invalid. Return ONLY raw JSON: "
        '{"label": "<label>", "reason": "<one sentence>"}'
    )
    payload["prompt"] = retry_prompt

    try:
        res = client.post(url, json=payload, timeout=timeout)
        if res.status_code == 200:
            raw_response = res.json().get("response", "")
            parsed = extract_json_response(raw_response)
            if parsed:
                return parsed["label"], parsed["reason"]
            logger.warning("Invalid JSON from Gemma on retry: %r", raw_response)
    except (httpx.TimeoutException, httpx.RequestError) as e:
        logger.warning("Error communicating with Ollama on retry: %s", e)
        if isinstance(e, httpx.ConnectError):
            raise

    # Fallback if both attempts failed
    return "unclassified", ""


def explain_flagged_pairs(
    flagged_pairs: list[FlaggedPair],
    top_n: int = DEFAULT_TOP_N_EXPLAIN,
    host: str = DEFAULT_OLLAMA_HOST,
    model: str = DEFAULT_OLLAMA_MODEL,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[list[FlaggedPair], bool]:
    """Generate explanations for the top N flagged pairs.

    Args:
        flagged_pairs: List of FlaggedPair objects, sorted highest score first.
        top_n: Max number of pairs to explain.
        host: Ollama host URL.
        model: Ollama model name.
        timeout: Timeout per pair in seconds.

    Returns:
        tuple (flagged_pairs, explanations_available)
        Where explanations_available is True if Ollama was accessible,
        False if Ollama was offline or unavailable.
    """
    if not flagged_pairs:
        return flagged_pairs, True

    # Check if Ollama is online before starting
    if not is_ollama_online(host=host, timeout=3.0):
        logger.warning("Ollama is offline or unreachable at %s", host)
        return flagged_pairs, False

    pairs_to_process = flagged_pairs[:top_n]
    explanations_available = True

    try:
        with httpx.Client(timeout=timeout) as client:
            for pair in pairs_to_process:
                try:
                    label, reason = explain_single_pair(
                        pair=pair,
                        client=client,
                        host=host,
                        model=model,
                        timeout=timeout,
                    )
                    pair.label = label
                    pair.reason = reason
                except httpx.ConnectError:
                    logger.warning("Lost connection to Ollama; marking offline.")
                    explanations_available = False
                    break
                except Exception as e:
                    logger.warning("Unexpected error explaining pair %s - %s: %s", pair.student_a, pair.student_b, e)
                    pair.label = "unclassified"
                    pair.reason = ""
    except Exception as e:
        logger.warning("Failed to initialize HTTP client for Ollama: %s", e)
        explanations_available = False

    return flagged_pairs, explanations_available
