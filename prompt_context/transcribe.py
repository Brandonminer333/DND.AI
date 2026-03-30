# context/transcribe.py
import os
import hashlib
import warnings
from pathlib import Path
from typing import Dict, List
from datetime import datetime, timezone


from dotenv import load_dotenv
from whisper import load_model

from arangodb import (
    get_transcript_collection,
)
from enrich_transcript_chunk import process_transcript_chunk

warnings.filterwarnings(
    "ignore", message="FP16 is not supported on CPU; using FP32 instead")

model = None


load_dotenv()
TRANSCRIPT_CHUNK_THRESHOLD_WORDS = int(
    os.getenv("TRANSCRIPT_CHUNK_THRESHOLD_WORDS", "40")
)


def get_model(size="small"):
    global model
    if model is None:
        model = load_model(size)
    return model


def get_session_key_from_path(audio_path: Path) -> str:
    """
    Extract session key from audio filename.
    Example:
      - 'session-1_2026-03-23-12-00-00.wav' -> 'session-1'
      - 'session-1.wav' -> 'session-1'
    """
    return audio_path.stem.split("_")[0]


def upsert_aggregated_session_transcript(
    collection,
    session_key: str,
    source_filename: str,
    transcript_chunk: str,
    ) -> None:
    """Append a transcript chunk to the aggregated session document."""
    now_iso = datetime.now(timezone.utc).isoformat()
    existing_doc = collection.get({"_key": session_key}) or {}
    existing_text = (existing_doc.get("transcript") or "").strip()
    clean_chunk = (transcript_chunk or "").strip()

    if not clean_chunk:
        raise ValueError(f"Transcript chunk for session {session_key} is empty.")

    if existing_text:
        aggregated = f"{existing_text}\n\n{clean_chunk}"
        chunk_count = int(existing_doc.get("chunk_count", 0)) + 1
    else:
        aggregated = clean_chunk
        chunk_count = 1

    source_files = existing_doc.get("source_files", [])
    source_files.append(source_filename)

    collection.insert(
        {
            "_key": session_key,
            "session_key": session_key,
            "transcript": aggregated,
            "chunk_count": chunk_count,
            "source_files": source_files,
            "updated_at": now_iso,
            "created_at": existing_doc.get("created_at", now_iso),
        },
        overwrite=True,
    )


def count_words(text: str) -> int:
    """Simple word counter for threshold aggregation."""
    return len((text or "").strip().split())


def make_transcript_chunk_key(
    session_key: str,
    chunk_text: str,
    source_files: List[str],
    ) -> str:
    """
    Deterministic key for a transcript chunk.

    We include:
    - session_key
    - chunk_text (whitespace-normalized)
    - first/last source filenames (helps distinguish similar text across files)
    """
    normalized_text = " ".join((chunk_text or "").split())
    first_file = (source_files[0] if source_files else "")
    last_file = (source_files[-1] if source_files else "")
    raw = f"{session_key}|{first_file}|{last_file}|{normalized_text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def flush_session_buffer_if_threshold_reached(
    *,
    session_key: str,
    buffer: Dict[str, List[str] | str],
    threshold_words: int,
    ) -> bool:
    """
    Flush the buffer into the graph ingestion pipeline if it reached the threshold.

    Returns True if a flush happened successfully.
    """
    chunk_text = (buffer.get("text") or "").strip()
    source_files = buffer.get("source_files") or []
    if not chunk_text:
        return False

    if count_words(chunk_text) < threshold_words:
        return False

    now_iso = datetime.now(timezone.utc).isoformat()
    chunk_key = make_transcript_chunk_key(
        session_key=session_key,
        chunk_text=chunk_text,
        source_files=source_files,  # includes all files contributing to this flush
    )

    # Enrich/transcript chunk processing is designed to be idempotent using keys.
    process_transcript_chunk(
        session_key=session_key,
        chunk_key=chunk_key,
        chunk_text=chunk_text,
        source_files=source_files,
        created_at_iso=now_iso,
    )

    # Only clear if we know ingestion succeeded.
    buffer["text"] = ""
    buffer["source_files"] = []
    return True


def transcribe_audio():
    """
    Finds all .wav files in the audio dir, transcribes each,
    appends transcript chunks into session transcript documents,
    then deletes source audio.
    """

    model = get_model()
    legacy_collection = get_transcript_collection()

    AUDIO_GLOB = "/Users/brandonminer/projects/dnd-ai/data/audio/*.wav"
    AUDIO_DIR = "/Users/brandonminer/projects/dnd-ai/data/audio"

    audio_files = sorted([
        os.path.join(AUDIO_DIR, name)
        for name in os.listdir(AUDIO_DIR)
        if name.endswith('.wav')
    ])

    if not audio_files:
        raise FileNotFoundError(f"No audio files found matching: {AUDIO_GLOB}")

    # Buffer per session so we can aggregate multiple short transcript results
    # into one higher-quality embedding/NER chunk.
    session_buffers: Dict[str, Dict[str, List[str] | str]] = {}

    for file_path in audio_files:
        try:
            result = model.transcribe(file_path)
            source_path = Path(file_path)
            session_key = get_session_key_from_path(source_path)

            # --------------------------
            # 1) Legacy session transcript aggregation (backward compatibility)
            # --------------------------
            upsert_aggregated_session_transcript(
                collection=legacy_collection,
                session_key=session_key,
                source_filename=source_path.name,
                transcript_chunk=result['text'],
            )

            print(f"Updated aggregated transcript for session: {session_key}")

            # --------------------------
            # 2) Threshold buffer for graph ingestion
            # --------------------------
            if session_key not in session_buffers:
                session_buffers[session_key] = {"text": "", "source_files": []}

            session_buffers[session_key]["text"] = (
                session_buffers[session_key].get("text", "") + "\n\n" + (result["text"] or "").strip()
            )
            session_buffers[session_key]["source_files"].append(source_path.name)

            flushed = flush_session_buffer_if_threshold_reached(
                session_key=session_key,
                buffer=session_buffers[session_key],
                threshold_words=TRANSCRIPT_CHUNK_THRESHOLD_WORDS,
            )
            if flushed:
                print(
                    f"Flushed transcript buffer to graph for session: {session_key}"
                )

            # Delete audio after successful transcription
            os.remove(file_path)
            print(f"Deleted audio file: {file_path}")
        except Exception as e:
            print(f"Failed to transcribe {file_path}: {e}")

    # Optional final flush so leftover buffered text still gets embedded/NER'd.
    # This is important if the session ends before the threshold is reached.
    for session_key, buffer in session_buffers.items():
        try:
            # If text exists but threshold wasn't reached, we still ingest it.
            if (buffer.get("text") or "").strip():
                now_iso = datetime.now(timezone.utc).isoformat()
                chunk_text = (buffer.get("text") or "").strip()
                source_files = buffer.get("source_files") or []
                chunk_key = make_transcript_chunk_key(
                    session_key=session_key,
                    chunk_text=chunk_text,
                    source_files=source_files,
                )
                process_transcript_chunk(
                    session_key=session_key,
                    chunk_key=chunk_key,
                    chunk_text=chunk_text,
                    source_files=source_files,
                    created_at_iso=now_iso,
                )
                buffer["text"] = ""
                buffer["source_files"] = []
                print(f"Final flush to graph for session: {session_key}")
        except Exception as e:
            print(f"Failed final flush for session {session_key}: {e}")


if __name__ == "__main__":
    # files = os.listdir("data/audio")
    # for file in files:
    transcribe_audio()
