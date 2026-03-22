# context/transcribe.py
import os
import warnings
from pathlib import Path

from whisper import load_model

warnings.filterwarnings(
    "ignore", message="FP16 is not supported on CPU; using FP32 instead")

model = None


def get_model(size="small"):
    global model
    if model is None:
        model = load_model(size)
    return model


def transcribe_audio():
    """
    Finds all .wav files in the audio dir, transcribes each,
    saves transcripts, deletes source audio, and pushes transcript
    paths to XCom for the next task.
    """

    model = get_model()

    AUDIO_GLOB = "/Users/brandonminer/projects/dnd-ai/data/audio/*.wav"
    TRANSCRIPT_DIR = Path(
        "/Users/brandonminer/projects/dnd-ai/data/transcript")

    audio_files = [
        "/Users/brandonminer/projects/dnd-ai/data/audio/" + name for name in os.listdir(
            "/Users/brandonminer/projects/dnd-ai/data/audio") if not ".DS_Store"]

    if not audio_files:
        raise FileNotFoundError(f"No audio files found matching: {AUDIO_GLOB}")

    transcript_paths = []
    for file_path in audio_files:
        try:
            result = model.transcribe(file_path)
            transcript_path = save_transcript(
                text=result['text'],
                source_path=Path(file_path),
                output_dir=TRANSCRIPT_DIR,
            )
            transcript_paths.append(str(transcript_path))

            # Delete audio after successful transcription
            os.remove(file_path)
            print(f"Deleted audio file: {file_path}")

        except Exception as e:
            print(f"Failed to transcribe {file_path}: {e}")


def save_transcript(text: str, source_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    # Reuse the audio filename, just swap the extension
    output_path = output_dir / source_path.with_suffix(".txt").name
    with open(output_path, 'w') as f:
        f.write(text)
    print(f"Saved transcript: {output_path}")
    return output_path


if __name__ == "__main__":
    # files = os.listdir("data/audio")
    # for file in files:
    transcribe_audio()
