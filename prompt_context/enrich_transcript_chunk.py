"""
prompt_context/enrich_transcript_chunk.py

This script is the "graph enrichment" step of your pipeline:

1. Store an incoming transcript chunk as a `TranscriptChunks` vertex,
   including its embedding vector.
2. Extract entities using local NLP (GLiNER by default).
3. Store extracted entities in `Entities`.
4. Create `Mentions` edges from the chunk -> each entity with:
   `{"summarized": false}`

It is designed to be idempotent:
- Transcript chunk `_key` is deterministic (provided by `transcribe.py`).
- Entity and edge `_key`s are deterministic (computed here).
"""

import os
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

from arangodb import (
    ensure_core_schema,
    get_entities_collection,
    get_mentions_collection,
    get_transcript_chunks_collection,
)

load_dotenv()

NER_BACKEND = os.getenv("NER_BACKEND", "gliner")
NER_MODEL_NAME = os.getenv("NER_MODEL_NAME", "urchade/gliner_multi-v2.1")
NER_LABELS = [label.strip() for label in os.getenv("NER_LABELS", "NPC,Location,Faction,Artifact").split(",") if label.strip()]

EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "sentence_transformers")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")

_SCHEMA_BOOTSTRAPPED = False

_EMBED_MODEL = None
_NER_MODEL = None


def _normalize_entity_name(name: str) -> str:
    # Keep it simple and consistent for idempotent entity keys.
    normalized = (name or "").strip()
    normalized = " ".join(normalized.split())
    # Title-case is a good readability default (and stable for keys).
    return normalized.title()


def _compute_entity_key(category: str, normalized_name: str) -> str:
    raw = f"{category.lower()}|{normalized_name.lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _compute_edge_key(chunk_key: str, entity_key: str) -> str:
    raw = f"{chunk_key}|{entity_key}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _get_embedding_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is not None:
        return _EMBED_MODEL

    if EMBEDDING_BACKEND != "sentence_transformers":
        raise ValueError(
            f"Unsupported EMBEDDING_BACKEND='{EMBEDDING_BACKEND}'. "
            "Currently only 'sentence_transformers' is implemented."
        )

    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        raise ImportError(
            "Missing dependency for embeddings. Install `sentence-transformers`."
        ) from e

    _EMBED_MODEL = SentenceTransformer(EMBEDDING_MODEL_NAME, device=EMBEDDING_DEVICE)
    return _EMBED_MODEL


def embed_text(text: str) -> List[float]:
    """Return embedding vector for `text` as a Python list of floats."""
    model = _get_embedding_model()
    # encode() returns a numpy array; ArangoDB expects a serializable list.
    vector = model.encode(text, normalize_embeddings=False)
    return vector.tolist() if hasattr(vector, "tolist") else list(vector)


def _get_ner_model():
    global _NER_MODEL
    if _NER_MODEL is not None:
        return _NER_MODEL

    if NER_BACKEND != "gliner":
        raise ValueError(
            f"Unsupported NER_BACKEND='{NER_BACKEND}'. Currently only 'gliner' is implemented."
        )

    try:
        from gliner import GLiNER
    except Exception as e:
        raise ImportError("Missing dependency for NER. Install `gliner`.") from e

    _NER_MODEL = GLiNER.from_pretrained(NER_MODEL_NAME)
    return _NER_MODEL


def extract_entities(text: str) -> List[Dict[str, object]]:
    """
    Extract entities from `text`.

    Returns: [{"name": str, "category": str, "score": float}, ...]
    """
    if not (text or "").strip():
        return []

    model = _get_ner_model()

    try:
        predictions = model.predict_entities(
            text=text,
            labels=NER_LABELS,
            threshold=0.4,
        )
    except TypeError:
        # GLiNER API can vary slightly across versions; keep error actionable.
        raise RuntimeError(
            "GLiNER predict_entities signature mismatch. "
            "If you upgraded GLiNER, update the call in extract_entities()."
        )

    entities: List[Dict[str, object]] = []
    for pred in predictions or []:
        # Documented output keys: "text", "label", "score"
        raw_name = pred.get("text") or ""
        category = (pred.get("label") or "").strip()
        score = float(pred.get("score") or 0.0)

        if not raw_name or not category:
            continue

        entities.append(
            {
                "name": _normalize_entity_name(raw_name),
                "category": category,
                "score": score,
            }
        )

    # Deduplicate by (category, normalized_name), keeping best score.
    best_by_key: Dict[Tuple[str, str], Dict[str, object]] = {}
    for ent in entities:
        key = (ent["category"], ent["name"])
        if key not in best_by_key or float(ent["score"]) > float(best_by_key[key]["score"]):
            best_by_key[key] = ent

    return list(best_by_key.values())


def upsert_transcript_chunk(
    *,
    session_key: str,
    chunk_key: str,
    chunk_text: str,
    source_files: List[str],
    created_at_iso: str,
    embedding: List[float],
    ) -> None:
    chunks = get_transcript_chunks_collection()

    doc = {
        "_key": chunk_key,
        "session_key": session_key,
        "chunk_key": chunk_key,
        "text": chunk_text,
        "source_files": source_files,
        "created_at": created_at_iso,
        "updated_at": created_at_iso,
        "embedding": embedding,
    }
    chunks.insert(doc, overwrite=True)


def upsert_entity(
    *,
    category: str,
    name: str,
    created_at_iso: str,
    ) -> str:
    entities = get_entities_collection()
    category = (category or "").strip()

    entity_key = _compute_entity_key(category=category, normalized_name=name)
    existing = entities.get({"_key": entity_key}) or {}
    existing_summary = existing.get("summary", "") or ""

    doc = {
        "_key": entity_key,
        "name": name,
        "category": category,
        # Keep rolling summary if the entity already exists.
        "summary": existing_summary,
        "created_at": existing.get("created_at", created_at_iso),
        "updated_at": created_at_iso,
    }
    entities.insert(doc, overwrite=True)
    return entity_key


def upsert_mention_edge(
    *,
    chunk_vertex_id: str,
    entity_vertex_id: str,
    chunk_key: str,
    entity_key: str,
    created_at_iso: str,
    ) -> None:
    mentions = get_mentions_collection()
    edge_key = _compute_edge_key(chunk_key=chunk_key, entity_key=entity_key)

    existing = mentions.get({"_key": edge_key}) or {}
    existing_summarized = bool(existing.get("summarized", False))

    doc = {
        "_key": edge_key,
        "_from": chunk_vertex_id,
        "_to": entity_vertex_id,
        "summarized": existing_summarized,
        "created_at": created_at_iso,
        "updated_at": created_at_iso,
    }
    mentions.insert(doc, overwrite=True)


def process_transcript_chunk(
    *,
    session_key: str,
    chunk_key: str,
    chunk_text: str,
    source_files: List[str],
    created_at_iso: Optional[str] = None,
    ) -> None:
    """
    Main entry point used by `transcribe.py`.

    It will:
    - embed + upsert transcript chunk
    - extract + upsert entities
    - create mentions edges with summarized=false (unless already summarized)
    """
    global _SCHEMA_BOOTSTRAPPED
    if not _SCHEMA_BOOTSTRAPPED:
        ensure_core_schema()
        _SCHEMA_BOOTSTRAPPED = True

    if not created_at_iso:
        created_at_iso = datetime.now(timezone.utc).isoformat()

    cleaned_chunk_text = (chunk_text or "").strip()
    if not cleaned_chunk_text:
        # Nothing to ingest.
        return

    embedding = embed_text(cleaned_chunk_text)

    # 1) Transcript chunk vertex
    upsert_transcript_chunk(
        session_key=session_key,
        chunk_key=chunk_key,
        chunk_text=cleaned_chunk_text,
        source_files=source_files,
        created_at_iso=created_at_iso,
        embedding=embedding,
    )

    chunks = get_transcript_chunks_collection()
    entities = get_entities_collection()

    chunk_vertex_id = f"{chunks.name}/{chunk_key}"

    # 2) Entities + 3) Mentions edges
    extracted = extract_entities(cleaned_chunk_text)
    for ent in extracted:
        category = str(ent.get("category") or "").strip()
        name = str(ent.get("name") or "").strip()
        if not category or not name:
            continue

        entity_key = upsert_entity(
            category=category,
            name=name,
            created_at_iso=created_at_iso,
        )
        entity_vertex_id = f"{entities.name}/{entity_key}"

        upsert_mention_edge(
            chunk_vertex_id=chunk_vertex_id,
            entity_vertex_id=entity_vertex_id,
            chunk_key=chunk_key,
            entity_key=entity_key,
            created_at_iso=created_at_iso,
        )

