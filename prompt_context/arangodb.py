"""
ArangoDB helpers for DND.AI.

This module intentionally favors readability over cleverness:
- Small, explicit helper functions
- Clear naming around "legacy" vs "graph" collections
- Schema bootstrap function you can run at startup
"""

import os
from typing import Dict

from dotenv import load_dotenv
from arango import ArangoClient

load_dotenv()

# ---------------------------------------------------------------------------
# Connection config
# ---------------------------------------------------------------------------
ARANGO_URL = os.getenv("ARANGO_URL", "http://localhost:8529")
ARANGO_DB_NAME = os.getenv("ARANGO_DB_NAME", "dnd_ai")
ARANGO_USERNAME = os.getenv("ARANGO_USERNAME", "root")
ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "")

# ---------------------------------------------------------------------------
# Legacy collections (used by the existing `summarize.py` pipeline)
# ---------------------------------------------------------------------------
# These names come from the current codebase and are kept so the old pipeline
# still works while you migrate to the graph-first LightRAG model.
ARANGO_COLLECTION = os.getenv("ARANGO_COLLECTION", "session_summaries")
ARANGO_TRANSCRIPT_COLLECTION = os.getenv(
    "ARANGO_TRANSCRIPT_COLLECTION",
    "session_transcripts",
)

# ---------------------------------------------------------------------------
# New LightRAG-oriented collection names
# ---------------------------------------------------------------------------
ARANGO_TRANSCRIPT_CHUNKS_COLLECTION = os.getenv(
    "ARANGO_TRANSCRIPT_CHUNKS_COLLECTION",
    "TranscriptChunks",
)
ARANGO_ENTITIES_COLLECTION = os.getenv(
    "ARANGO_ENTITIES_COLLECTION",
    "Entities",
)
ARANGO_MENTIONS_COLLECTION = os.getenv(
    "ARANGO_MENTIONS_COLLECTION",
    "Mentions",
)
ARANGO_RULES_COLLECTION = os.getenv(
    "ARANGO_RULES_COLLECTION",
    "Rules",
)
ARANGO_GRAPH_NAME = os.getenv("ARANGO_GRAPH_NAME", "SessionGraph")


def get_arango_client() -> ArangoClient:
    """Create and return an ArangoDB client."""
    return ArangoClient(hosts=ARANGO_URL)


def get_database(db_name: str = ARANGO_DB_NAME):
    """
    Return an existing database handle.

    This does not create the database.
    """
    client = get_arango_client()
    return client.db(db_name, username=ARANGO_USERNAME, password=ARANGO_PASSWORD)


def get_or_create_database(db_name: str = ARANGO_DB_NAME):
    """
    Return a database handle, creating it first if needed.

    We create DBs through `_system`, which is ArangoDB's admin database.
    """
    client = get_arango_client()
    sys_db = client.db("_system", username=ARANGO_USERNAME, password=ARANGO_PASSWORD)
    if not sys_db.has_database(db_name):
        sys_db.create_database(db_name)
    return client.db(db_name, username=ARANGO_USERNAME, password=ARANGO_PASSWORD)


def get_or_create_collection(collection_name: str, db_name: str = ARANGO_DB_NAME):
    """
    Return/create a document collection by name.

    NOTE:
    - This helper creates document collections only.
    - For edge collections, use `get_or_create_edge_collection`.
    """
    db = get_or_create_database(db_name=db_name)
    if not db.has_collection(collection_name):
        db.create_collection(collection_name)
    return db.collection(collection_name)


def get_or_create_edge_collection(
    collection_name: str,
    db_name: str = ARANGO_DB_NAME,
):
    """Return/create an edge collection by name."""
    db = get_or_create_database(db_name=db_name)
    if not db.has_collection(collection_name):
        db.create_collection(collection_name, edge=True)
    return db.collection(collection_name)


def _ensure_entity_indexes() -> None:
    """
    Ensure practical indexes for entity lookups.

    We use a unique index on (`name`, `category`) so the same entity-category pair
    cannot be inserted repeatedly.
    """
    entities = get_entities_collection()
    entities.add_persistent_index(fields=["name", "category"], unique=True)


def _ensure_mentions_indexes() -> None:
    """
    Ensure indexes for deferred summarization scans.

    `summarized` index makes `summarized == false` sweeps faster.
    """
    mentions = get_mentions_collection()
    mentions.add_persistent_index(fields=["summarized"], unique=False)


def _ensure_transcript_indexes() -> None:
    """
    Ensure useful indexes for transcript chunk filtering.

    `session_key` + `created_at` helps session timeline and grouping queries.
    """
    chunks = get_transcript_chunks_collection()
    chunks.add_persistent_index(fields=["session_key", "created_at"], unique=False)


def get_or_create_graph(graph_name: str = ARANGO_GRAPH_NAME):
    """
    Return/create the named graph and its edge definition.

    Graph shape:
    - Vertex collections: TranscriptChunks, Entities
    - Edge collection: Mentions
    """
    db = get_or_create_database()
    if db.has_graph(graph_name):
        return db.graph(graph_name)

    graph = db.create_graph(graph_name)
    graph.create_edge_definition(
        edge_collection=ARANGO_MENTIONS_COLLECTION,
        from_vertex_collections=[ARANGO_TRANSCRIPT_CHUNKS_COLLECTION],
        to_vertex_collections=[ARANGO_ENTITIES_COLLECTION],
    )
    return graph


def ensure_core_schema() -> Dict[str, str]:
    """
    Bootstrap all core collections/graph/indexes used by the new architecture.

    This function is safe to call repeatedly at startup.
    """
    get_or_create_database()

    # Document collections
    get_transcript_chunks_collection()
    get_entities_collection()
    get_rules_collection()

    # Edge collection + graph
    get_mentions_collection()
    get_or_create_graph()

    # Indexes
    _ensure_entity_indexes()
    _ensure_mentions_indexes()
    _ensure_transcript_indexes()

    return {
        "database": ARANGO_DB_NAME,
        "graph": ARANGO_GRAPH_NAME,
        "transcript_chunks": ARANGO_TRANSCRIPT_CHUNKS_COLLECTION,
        "entities": ARANGO_ENTITIES_COLLECTION,
        "mentions": ARANGO_MENTIONS_COLLECTION,
        "rules": ARANGO_RULES_COLLECTION,
        "legacy_transcripts": ARANGO_TRANSCRIPT_COLLECTION,
        "legacy_summaries": ARANGO_COLLECTION,
    }


# ---------------------------------------------------------------------------
# Legacy collection getters (existing scripts depend on these)
# ---------------------------------------------------------------------------
def get_summary_collection():
    """Return/create the legacy session summary collection."""
    return get_or_create_collection(ARANGO_COLLECTION)


def get_transcript_collection():
    """Return/create the legacy session transcript collection."""
    return get_or_create_collection(ARANGO_TRANSCRIPT_COLLECTION)


# ---------------------------------------------------------------------------
# New collection getters (graph architecture)
# ---------------------------------------------------------------------------
def get_transcript_chunks_collection():
    """Return/create `TranscriptChunks` collection (vertex)."""
    return get_or_create_collection(ARANGO_TRANSCRIPT_CHUNKS_COLLECTION)


def get_entities_collection():
    """Return/create `Entities` collection (vertex)."""
    return get_or_create_collection(ARANGO_ENTITIES_COLLECTION)


def get_mentions_collection():
    """Return/create `Mentions` edge collection."""
    return get_or_create_edge_collection(ARANGO_MENTIONS_COLLECTION)


def get_rules_collection():
    """Return/create `Rules` collection."""
    return get_or_create_collection(ARANGO_RULES_COLLECTION)
