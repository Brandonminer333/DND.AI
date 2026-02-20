from whisper import load_model

model = load_model("base")  # or "small", "medium", etc.


def transcribe_audio(file_path: str) -> str:
    result = model.transcribe(file_path)
    return result["text"]
