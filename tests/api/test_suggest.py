"""Unit tests for `api/suggest.py`."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _layout_api_relative_prompts(tmp_path: Path) -> Path:
    """Mirror layout expected when cwd is `.../api` (paths use `../`)."""
    base = tmp_path / "proj"
    (base / "prompts").mkdir(parents=True)
    (base / "data" / "transcripts").mkdir(parents=True)
    (base / "data" / "summaries").mkdir(parents=True)
    (base / "api").mkdir()
    (base / "prompts" / "suggest.md").write_text("BASE_PROMPT\n", encoding="utf-8")
    return base


def test_get_prompt_without_summary(tmp_path, monkeypatch):
    base = _layout_api_relative_prompts(tmp_path)
    (base / "data" / "transcripts" / "sess1.md").write_text(
        "TRANSCRIPT_BODY", encoding="utf-8"
    )
    monkeypatch.chdir(base / "api")

    import suggest

    out = suggest.get_prompt("sess1", summary=False)
    assert "BASE_PROMPT" in out
    assert "TRANSCRIPT_BODY" in out


def test_get_prompt_with_summary(tmp_path, monkeypatch):
    base = _layout_api_relative_prompts(tmp_path)
    (base / "data" / "transcripts" / "sess1.md").write_text(
        "TRANSCRIPT_BODY", encoding="utf-8"
    )
    (base / "data" / "summaries" / "sess1.md").write_text(
        "SUMMARY_BODY", encoding="utf-8"
    )
    monkeypatch.chdir(base / "api")

    import suggest

    out = suggest.get_prompt("sess1", summary=True)
    assert "BASE_PROMPT" in out
    assert "SUMMARY_BODY" in out
    assert "TRANSCRIPT_BODY" in out


def test_suggest_calls_genai(monkeypatch, tmp_path):
    base = _layout_api_relative_prompts(tmp_path)
    monkeypatch.chdir(base / "api")

    import suggest

    mock_resp = MagicMock()
    mock_resp.text = "AI_REPLY"
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    result = suggest.suggest(mock_client, "user content here")
    assert result == "AI_REPLY"
    mock_client.models.generate_content.assert_called_once()
    call_kw = mock_client.models.generate_content.call_args.kwargs
    assert "user content here" in call_kw["contents"]
