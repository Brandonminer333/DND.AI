import os
from pathlib import Path
from typing import List, Tuple

from arangodb import *
from google import genai

# Environment variables
PROJECT_ROOT = Path("/Users/brandonminer/projects/dnd-ai") # TODO: Use .env to be cleaner
PROMPT_PATH = PROJECT_ROOT / "prompts/summarize.md"

MODEL_NAME = "gemini-2.5-flash"
GENAI_CLIENT = genai.Client(api_key=os.getenv("GEMINI_KEY"))


def load_session_transcript_docs(collection) -> List[dict]:
    """Return all session transcript documents from ArangoDB."""
    cursor = collection.all()
    return [doc for doc in cursor]

# Summary functions
def generate_fresh_summary(prompt: str, existing_summary: str, aggregated_transcript: str) -> str:
    """
    Generate a fresh summary from previous summary + new aggregated transcript.
    """
    prompt_content = (
        f"{prompt}\n\n"
        "You are updating a running session summary.\n"
        "If there is an existing summary, merge it with the new transcript details.\n"
        "Keep details useful for future retrieval by a GM assistant.\n\n"
        f"Existing summary:\n{existing_summary or '(none)'}\n\n"
        f"New transcript content:\n{aggregated_transcript}\n"
    )

    response = GENAI_CLIENT.models.generate_content(
        model=MODEL_NAME,
        contents=prompt_content,
    )
    return (response.text or "").strip()


def upsert_session_summary(collection, session_key: str, summary_text: str) -> None:
    """Persist a session summary as key-value pair in ArangoDB."""
    collection.insert(
        {"_key": session_key, "summary": summary_text},
        overwrite=True,
    )


def get_existing_session_summary(collection, session_key: str) -> str:
    """Return an existing summary for the session if present, otherwise empty."""
    doc = collection.get({"_key": session_key})
    if not doc:
        return ""
    return doc.get("summary", "")


def summarize_transcript() -> List[Tuple[str, str]]:
    """
    Process all transcript session documents in ArangoDB.
    For each session, build fresh summary and upsert into summary collection.
    Returns list of (session_key, summary_text).
    """
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"Summarization prompt file not found: {PROMPT_PATH}")

    transcript_collection = get_transcript_collection()
    summary_collection = get_summary_collection()
    transcript_docs = load_session_transcript_docs(transcript_collection)
    if not transcript_docs:
        print("No transcript documents found. Skipping summarization.")
        return []

    with open(PROMPT_PATH, "r", encoding="utf-8") as prompt_file:
        prompt = prompt_file.read()

    results: List[Tuple[str, str]] = []

    for transcript_doc in transcript_docs:
        try:
            session_key = transcript_doc.get("_key")
            if not session_key:
                print("Found transcript document without _key; skipping.")
                continue

            aggregated_transcript = (transcript_doc.get("transcript") or "").strip()
            if not aggregated_transcript.strip():
                print(f"Session {session_key} has empty transcript; skipping.")
                continue

            existing_summary = get_existing_session_summary(summary_collection, session_key)
            fresh_summary = generate_fresh_summary(
                prompt=prompt,
                existing_summary=existing_summary,
                aggregated_transcript=aggregated_transcript,
            )
            if not fresh_summary:
                raise ValueError(f"Generated summary for session {session_key} is empty.")

            upsert_session_summary(summary_collection, session_key, fresh_summary)
            results.append((session_key, fresh_summary))
            print(f"Updated summary for session: {session_key}")
        except Exception as exc:
            print(f"Failed to summarize session {session_key}: {exc}")

    return results


if __name__ == "__main__":
    summarize_transcript()  # Boilerplate just running a function is a good sign airflow will work correctly
