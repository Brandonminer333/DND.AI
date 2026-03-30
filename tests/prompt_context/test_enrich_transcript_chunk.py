"""Unit tests for pure helpers in `prompt_context/enrich_transcript_chunk.py`."""

import hashlib

import enrich_transcript_chunk as etc


def test_normalize_entity_name():
    assert etc._normalize_entity_name("  foo   bar  ") == "Foo Bar"


def test_compute_entity_key_deterministic():
    k = etc._compute_entity_key("NPC", "Alice")
    raw = "npc|alice"
    assert k == hashlib.sha256(raw.encode("utf-8")).hexdigest()


def test_compute_edge_key_deterministic():
    k = etc._compute_edge_key("chunk123", "ent456")
    raw = "chunk123|ent456"
    assert k == hashlib.sha256(raw.encode("utf-8")).hexdigest()
