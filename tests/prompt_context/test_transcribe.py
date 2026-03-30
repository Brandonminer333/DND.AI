"""Unit tests for `prompt_context/transcribe.py` helpers."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_get_session_key_from_path():
    import transcribe as t

    assert t.get_session_key_from_path(Path("session-1_2026-03-23.wav")) == "session-1"
    assert t.get_session_key_from_path(Path("session-1.wav")) == "session-1"


def test_count_words():
    import transcribe as t

    assert t.count_words("") == 0
    assert t.count_words("  a  b  c  ") == 3


def test_make_transcript_chunk_key_stable():
    import transcribe as t

    k1 = t.make_transcript_chunk_key("s1", "hello world", ["a.wav", "b.wav"])
    k2 = t.make_transcript_chunk_key("s1", "hello  world", ["a.wav", "b.wav"])
    assert k1 == k2
    assert len(k1) == 64


def test_make_transcript_chunk_key_differs_by_session():
    import transcribe as t

    k1 = t.make_transcript_chunk_key("s1", "text", [])
    k2 = t.make_transcript_chunk_key("s2", "text", [])
    assert k1 != k2


def test_upsert_aggregated_session_transcript_new():
    import transcribe as t

    coll = MagicMock()
    coll.get.return_value = None

    t.upsert_aggregated_session_transcript(
        coll, "sk", "f.wav", "first chunk"
    )

    coll.insert.assert_called_once()
    doc = coll.insert.call_args[0][0]
    assert doc["_key"] == "sk"
    assert "first chunk" in doc["transcript"]
    assert doc["chunk_count"] == 1
    assert doc["source_files"] == ["f.wav"]


def test_upsert_aggregated_session_transcript_append():
    import transcribe as t

    coll = MagicMock()
    coll.get.return_value = {
        "_key": "sk",
        "transcript": "old",
        "chunk_count": 1,
        "source_files": ["a.wav"],
        "created_at": "t0",
    }

    t.upsert_aggregated_session_transcript(coll, "sk", "b.wav", "new")

    doc = coll.insert.call_args[0][0]
    assert "old" in doc["transcript"] and "new" in doc["transcript"]
    assert doc["chunk_count"] == 2
    assert doc["source_files"] == ["a.wav", "b.wav"]
    assert doc["created_at"] == "t0"


def test_upsert_aggregated_session_transcript_rejects_empty_chunk():
    import transcribe as t

    coll = MagicMock()
    with pytest.raises(ValueError, match="empty"):
        t.upsert_aggregated_session_transcript(coll, "sk", "f.wav", "   ")


def test_flush_session_buffer_if_threshold_reached_noop_when_short():
    import transcribe as t

    buf = {"text": "a b", "source_files": ["x.wav"]}
    with patch.object(t, "process_transcript_chunk") as m_proc:
        assert (
            t.flush_session_buffer_if_threshold_reached(
                session_key="s",
                buffer=buf,
                threshold_words=100,
            )
            is False
        )
        m_proc.assert_not_called()


def test_flush_session_buffer_if_threshold_reached_flushes():
    import transcribe as t

    words = " ".join(f"w{i}" for i in range(50))
    buf = {"text": words, "source_files": ["a.wav"]}
    with patch.object(t, "process_transcript_chunk") as m_proc:
        assert (
            t.flush_session_buffer_if_threshold_reached(
                session_key="s",
                buffer=buf,
                threshold_words=40,
            )
            is True
        )
        m_proc.assert_called_once()
        assert buf["text"] == ""
        assert buf["source_files"] == []
