"""Unit tests for `prompt_context/summarize.py` helpers."""

from unittest.mock import MagicMock, patch

import pytest


def test_load_session_transcript_docs():
    import summarize as s

    coll = MagicMock()
    coll.all.return_value = iter([{"_key": "a"}, {"_key": "b"}])
    docs = s.load_session_transcript_docs(coll)
    assert len(docs) == 2


def test_get_existing_session_summary():
    import summarize as s

    coll = MagicMock()
    coll.get.return_value = {"_key": "k", "summary": "hello"}
    assert s.get_existing_session_summary(coll, "k") == "hello"

    coll.get.return_value = None
    assert s.get_existing_session_summary(coll, "k") == ""


def test_upsert_session_summary():
    import summarize as s

    coll = MagicMock()
    s.upsert_session_summary(coll, "sk", "text")
    coll.insert.assert_called_once_with(
        {"_key": "sk", "summary": "text"},
        overwrite=True,
    )


@patch("summarize.GENAI_CLIENT")
def test_generate_fresh_summary(mock_client):
    import summarize as s

    mock_client.models.generate_content.return_value = MagicMock(text="  new summary  ")
    out = s.generate_fresh_summary(
        prompt="P",
        existing_summary="old",
        aggregated_transcript="trans",
    )
    assert out == "new summary"
    mock_client.models.generate_content.assert_called_once()


def test_summarize_transcript_skips_when_no_prompt_file(tmp_path, monkeypatch):
    import summarize as s

    monkeypatch.setattr(s, "PROMPT_PATH", tmp_path / "missing.md")

    with pytest.raises(FileNotFoundError):
        s.summarize_transcript()


@patch("summarize.get_transcript_collection")
@patch("summarize.get_summary_collection")
def test_summarize_transcript_empty_docs(mock_sum_coll, mock_tr_coll, tmp_path, monkeypatch):
    import summarize as s

    prompt_file = tmp_path / "summarize.md"
    prompt_file.write_text("prompt", encoding="utf-8")
    monkeypatch.setattr(s, "PROMPT_PATH", prompt_file)

    mock_tr_coll.return_value.all.return_value = iter([])

    assert s.summarize_transcript() == []
    mock_tr_coll.assert_called_once()
    mock_sum_coll.assert_called_once()
