# DND.AI

*Help new DMs focus on the story rather than running the game*

## How to run
1. Start Postgresql
2. Start Airflow Scheduler and Airflow dag-processor
3. Start Docker
4. Start ArangoDB 
5. start React UI (`npm dev run`)

# D&D Session Knowledge Graph & LightRAG Architecture

## Overview
This project implements a hybrid Retrieval-Augmented Generation (RAG) system to automatically record, transcribe, and summarize D&D sessions. It utilizes a LightRAG architecture powered by ArangoDB's multi-model capabilities, combining semantic vector search with graph traversal to retrieve highly contextual lore, character summaries, and session dialogue.

By separating real-time ingestion from batch-processed LLM summarizations, the architecture ensures low-latency performance during live gameplay while maintaining a deeply interconnected, cost-efficient knowledge graph.

---

## Core Technology Stack
* **Database:** ArangoDB (Multi-model: Document, Graph, and Vector Store)
* **Backend:** FastAPI (Real-time audio handling, querying)
* **Orchestration:** Apache Airflow (Batch processing, deferred summarizations)
* **Transcription & Generation:** OpenAI API (Whisper for VAD/transcription, GPT-4o/Claude for generation)
* **Local NLP Pipeline:**
    * **Embedding Model:** `sentence-transformers` (or lightweight API like `text-embedding-3-small`)
    * **NER Model:** GLiNER or custom `spaCy` pipeline (Zero-shot Named Entity Recognition)

---

## Pipeline Architecture

### 1. The Hot Path: Real-Time Ingestion (Low Latency, Low Cost)
This phase runs continuously during a live D&D session. It avoids expensive LLM calls to ensure zero bottlenecks.

1.  **Audio Capture & VAD:** The client app uses Voice Activity Detection (VAD) to slice audio at natural pauses (silence).
2.  **Transcription:** Audio chunks are transcribed via OpenAI Whisper.
3.  **Semantic Aggregation:** The FastAPI backend buffers transcriptions until a minimum semantic threshold is reached (e.g., 40 words) to ensure high-quality vector embeddings.
4.  **Local Processing:**
    * The aggregated text chunk is vectorized using the embedding model.
    * The raw text is passed through the local NER model to extract entities (Characters, Locations, Artifacts) without LLM intervention.
5.  **Graph Upsert (ArangoDB):**
    * The text is saved to the `TranscriptChunks` document collection (including its vector).
    * Extracted entities are upserted into the `Entities` collection (created if new, ignored if existing).
    * Edges are drawn in the `Mentions` edge collection linking the Chunk to the Entities. **Crucially, these edges are initialized with a property:** `{summarized: false}`.

### 2. The Cold Path: Deferred Summarization (Batch Processing)
To minimize API costs and optimize LLM usage, entity summaries are updated asynchronously.

1.  **Airflow Sweep:** An Airflow DAG runs on a schedule (e.g., every 30 minutes or post-session).
2.  **Targeting:** The script queries ArangoDB for all `Mentions` edges where `summarized == false`.
3.  **Grouping:** Retrieved chunks are grouped by their connected entities.
4.  **Bulk Update:** For each entity, a *single* LLM API call is made, providing the entity's current summary alongside all new chunks to generate an updated rolling summary.
5.  **State Update:** The new summary is saved to the Entity node, and the processed edges are updated to `{summarized: true}`.

### 3. The Query Path: Hybrid LightRAG Retrieval
When a user queries the chatbot, the system utilizes ArangoDB to perform vector search and graph traversal in a single database query.

1.  **Prompt Embedding:** The user's question is converted into a vector embedding.
2.  **Vector Search:** ArangoDB searches the `TranscriptChunks` collection for the top *K* most semantically similar pieces of dialogue.
3.  **Graph Traversal:** In the same AQL query, the database traverses the `Mentions` edges outward from the retrieved chunks to fetch the connected `Entities` and their pre-computed rolling summaries.
4.  **Generation:** The system prompt, user prompt, specific dialogue chunks, and broader entity summaries are compiled and sent to the LLM for the final, highly contextual response.

---

## ArangoDB Schema Design

* **Document Collections:**
    * `TranscriptChunks`: Stores the raw text, session ID, timestamp, and the vector embedding.
    * `Entities`: Stores the entity name, category (NPC, Location), and the rolling LLM-generated summary.
    * `Rules`: A separate document collection storing game mechanics and rulesets (with vector embeddings) for standard RAG retrieval, bypassing the campaign graph.
* **Edge Collections:**
    * `Mentions`: Connects `TranscriptChunks` `->` `Entities`. Tracks state with the `{summarized: boolean}` property.
