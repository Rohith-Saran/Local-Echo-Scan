"""Tests for Gemma explanation module (Ollama integration).

Covers:
- Valid raw JSON parsing
- Markdown-fenced JSON parsing (```json ... ``` and ``` ... ```)
- Invalid JSON handling with 1-retry fallback to ('unclassified', '')
- Ollama offline handling (ConnectError -> explanations_available=False, no crash)
- Per-pair timeout handling
- Top-N limit on explained pairs
"""

import os
import sys
from unittest.mock import MagicMock, patch

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.explain import (
    VALID_LABELS,
    build_prompt,
    explain_flagged_pairs,
    explain_single_pair,
    extract_json_response,
    is_ollama_online,
)
from backend.app.models import FlaggedPair, MatchedPair, Paragraph


def _create_sample_pair(
    name_a: str = "Alice",
    name_b: str = "Bob",
    score: float = 0.95,
) -> FlaggedPair:
    """Create a mock flagged pair with matched passages."""
    p_a = Paragraph(text="Current increased from 0.02A to 0.10A proportionally with voltage.", index=0)
    p_b = Paragraph(text="Current increased from 0.02A to 0.10A proportionally with voltage.", index=0)
    matched = MatchedPair(student_a_paragraph=p_a, student_b_paragraph=p_b, similarity=0.99)
    return FlaggedPair(student_a=name_a, student_b=name_b, score=score, matched_pairs=[matched])


# --- Test 1: JSON Parsing ---

def test_extract_json_valid_raw():
    """Valid raw JSON should be parsed correctly."""
    raw = '{"label": "likely copy", "reason": "Identical experimental values and text."}'
    result = extract_json_response(raw)
    assert result is not None
    assert result["label"] == "likely copy"
    assert result["reason"] == "Identical experimental values and text."
    print("✓ test_extract_json_valid_raw passed")


def test_extract_json_fenced_markdown():
    """JSON wrapped in ```json ... ``` or ``` ... ``` should be parsed safely."""
    fenced_1 = (
        "```json\n"
        '{"label": "paraphrase", "reason": "Identical readings with slightly modified phrasing."}\n'
        "```"
    )
    res_1 = extract_json_response(fenced_1)
    assert res_1 is not None
    assert res_1["label"] == "paraphrase"
    assert res_1["reason"] == "Identical readings with slightly modified phrasing."

    fenced_2 = (
        "```\n"
        '{"label": "shared source", "reason": "Both cite the apparatus from standard manual."}\n'
        "```"
    )
    res_2 = extract_json_response(fenced_2)
    assert res_2 is not None
    assert res_2["label"] == "shared source"

    fenced_coincidence = (
        "```json\n"
        '{"label": "coincidence", "reason": "Only generic introductory formulas overlap."}\n'
        "```"
    )
    res_3 = extract_json_response(fenced_coincidence)
    assert res_3 is not None
    assert res_3["label"] == "coincidence"
    print("✓ test_extract_json_fenced_markdown passed")


def test_extract_json_surrounded_by_text():
    """JSON embedded inside conversational text should be extracted."""
    text = (
        "Here is my analysis:\n"
        '{"label": "likely copy", "reason": "Verbatim sentences present."}\n'
        "I hope this helps!"
    )
    result = extract_json_response(text)
    assert result is not None
    assert result["label"] == "likely copy"
    print("✓ test_extract_json_surrounded_by_text passed")


def test_extract_json_invalid_labels():
    """Unrecognized label should return None."""
    raw = '{"label": "cheating", "reason": "They copied."}'
    result = extract_json_response(raw)
    assert result is None
    print("✓ test_extract_json_invalid_labels passed")


def test_extract_json_malformed():
    """Completely malformed text should return None."""
    assert extract_json_response("not json at all") is None
    assert extract_json_response("") is None
    assert extract_json_response(None) is None
    print("✓ test_extract_json_malformed passed")


# --- Test 2: Retry and Fallback ---

def test_explain_single_pair_retry_success():
    """If first attempt is invalid, it retries and succeeds if second attempt is valid."""
    pair = _create_sample_pair()

    mock_client = MagicMock(spec=httpx.Client)

    # Attempt 1: returns invalid non-JSON; Attempt 2: returns valid JSON
    resp_1 = MagicMock(status_code=200)
    resp_1.json.return_value = {"response": "Sorry, I forgot JSON format."}

    resp_2 = MagicMock(status_code=200)
    resp_2.json.return_value = {
        "response": '{"label": "paraphrase", "reason": "Reworded observations."}'
    }

    mock_client.post.side_effect = [resp_1, resp_2]

    label, reason = explain_single_pair(
        pair=pair,
        client=mock_client,
        host="http://localhost:11434",
        model="gemma3",
    )

    assert mock_client.post.call_count == 2
    assert label == "paraphrase"
    assert reason == "Reworded observations."
    print("✓ test_explain_single_pair_retry_success passed")


def test_explain_single_pair_retry_failure_fallback():
    """If both attempts return invalid output, fall back to 'unclassified' and empty reason."""
    pair = _create_sample_pair()

    mock_client = MagicMock(spec=httpx.Client)
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"response": "Still not JSON"}
    mock_client.post.return_value = resp

    label, reason = explain_single_pair(
        pair=pair,
        client=mock_client,
        host="http://localhost:11434",
        model="gemma3",
    )

    assert mock_client.post.call_count == 2
    assert label == "unclassified"
    assert reason == ""
    print("✓ test_explain_single_pair_retry_failure_fallback passed")


# --- Test 3: Ollama Offline Handling ---

def test_explain_flagged_pairs_ollama_offline_initial():
    """If Ollama is completely offline initially, return results without explanations."""
    pair = _create_sample_pair()
    pairs = [pair]

    with patch("backend.app.explain.is_ollama_online", return_value=False):
        res_pairs, available = explain_flagged_pairs(
            pairs,
            top_n=10,
            host="http://localhost:11434",
        )

        assert available is False
        assert res_pairs[0].label is None
        assert res_pairs[0].reason is None
    print("✓ test_explain_flagged_pairs_ollama_offline_initial passed")


def test_explain_flagged_pairs_ollama_connection_error_during_call():
    """If Ollama drops mid-batch, gracefully terminate and set explanations_available=False."""
    pairs = [_create_sample_pair("A", "B"), _create_sample_pair("C", "D")]

    with patch("backend.app.explain.is_ollama_online", return_value=True):
        with patch("backend.app.explain.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            # Simulate ConnectError on request
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")

            res_pairs, available = explain_flagged_pairs(
                pairs,
                top_n=10,
                host="http://localhost:11434",
            )

            assert available is False
            # Never crash!
            assert len(res_pairs) == 2
    print("✓ test_explain_flagged_pairs_ollama_connection_error_during_call passed")


# --- Test 4: Timeout Handling ---

def test_explain_single_pair_timeout_handled():
    """A timeout should fall back to 'unclassified' without crashing."""
    pair = _create_sample_pair()
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.side_effect = httpx.TimeoutException("Read timed out")

    label, reason = explain_single_pair(
        pair=pair,
        client=mock_client,
        host="http://localhost:11434",
        model="gemma3",
    )

    assert label == "unclassified"
    assert reason == ""
    print("✓ test_explain_single_pair_timeout_handled passed")


# --- Test 5: Top-N Limiting ---

def test_explain_top_n_limiting():
    """Only the top N flagged pairs should receive explanations."""
    pairs = [
        _create_sample_pair(f"A{i}", f"B{i}", score=1.0 - (i * 0.05))
        for i in range(5)
    ]

    with patch("backend.app.explain.is_ollama_online", return_value=True):
        with patch("backend.app.explain.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            resp = MagicMock(status_code=200)
            resp.json.return_value = {
                "response": '{"label": "likely copy", "reason": "Matching experimental results."}'
            }
            mock_client.post.return_value = resp

            res_pairs, available = explain_flagged_pairs(
                pairs,
                top_n=2,  # Only top 2
                host="http://localhost:11434",
            )

            assert available is True
            # First 2 should have explanations
            assert res_pairs[0].label == "likely copy"
            assert res_pairs[1].label == "likely copy"
            # Remaining pairs should not have explanations
            assert res_pairs[2].label is None
            assert res_pairs[3].label is None
            assert res_pairs[4].label is None
            assert mock_client.post.call_count == 2
            assert mock_client.post.call_count == 2
    print("✓ test_explain_top_n_limiting passed")


# --- Test 6: API Endpoint /analyze with explain=true ---

def test_analyze_endpoint_with_explain():
    """Verify /analyze endpoint returns explanations and explanations_available flag."""
    from fastapi.testclient import TestClient
    from backend.app.main import app

    client = TestClient(app)

    file_a_content = (
        "When voltage was increased from 2V to 10V in steps of 2V, "
        "the current increased proportionally. At 2V the current was 0.020A, at 4V "
        "it was 0.041A, at 6V it was 0.059A, at 8V it was 0.082A, and at 10V it "
        "was 0.098A. The calculated resistance was approximately 102 ohms.\n\n"
        "The experiment successfully verified Ohm's Law with constant resistance."
    )
    file_b_content = file_a_content  # Direct copy

    files = [
        ("files", ("alice.txt", file_a_content.encode("utf-8"), "text/plain")),
        ("files", ("bob.txt", file_b_content.encode("utf-8"), "text/plain")),
    ]

    with patch("backend.app.explain.is_ollama_online", return_value=True):
        with patch("backend.app.explain.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            resp = MagicMock(status_code=200)
            resp.json.return_value = {
                "response": '{"label": "likely copy", "reason": "Both students report identical observation readings."}'
            }
            mock_client.post.return_value = resp

            response = client.post(
                "/analyze",
                files=files,
                data={"explain": "true", "threshold": "0.85"},
            )

            assert response.status_code == 200, f"Error: {response.text}"
            data = response.json()

            assert data["explanations_available"] is True
            assert len(data["flagged_pairs"]) >= 1
            pair = data["flagged_pairs"][0]
            assert pair["label"] == "likely copy"
            assert pair["reason"] == "Both students report identical observation readings."
            assert "matched_passages" in pair

    print("✓ test_analyze_endpoint_with_explain passed")


if __name__ == "__main__":
    print("Running Gemma explanation tests...\n")
    test_extract_json_valid_raw()
    test_extract_json_fenced_markdown()
    test_extract_json_surrounded_by_text()
    test_extract_json_invalid_labels()
    test_extract_json_malformed()
    test_explain_single_pair_retry_success()
    test_explain_single_pair_retry_failure_fallback()
    test_explain_flagged_pairs_ollama_offline_initial()
    test_explain_flagged_pairs_ollama_connection_error_during_call()
    test_explain_single_pair_timeout_handled()
    test_explain_top_n_limiting()
    test_analyze_endpoint_with_explain()
    print("\nAll explanation tests passed! ✅")
