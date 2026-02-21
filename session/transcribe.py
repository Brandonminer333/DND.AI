import os
import warnings
import subprocess

from whisper import load_model


warnings.filterwarnings(
    "ignore", message="FP16 is not supported on CPU; using FP32 instead")
model = load_model("small")


def transcribe_audio(file_path: str) -> str:
    try:
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found at: {file_path}")

        result = model.transcribe(file_path)
        return result['text']
    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(e)


def save_transcript(text: str, output_path) -> None:

    try:
        # If the file exists, it truncates its contents.
        with open(output_path, 'w') as file:
            file.write(text)
        print(f"Successfully wrote to {output_path}")
        return len(text)
    except IOError as e:
        print(f"An I/O error occurred: {e}")
        return


# TODO remove temp
def test():
    try:
        txt = transcribe_audio(
            "/Users/brandonminer/Projects/DND.AI/data/audio/test.wav")
        hope = save_transcript(
            text=txt, output_path="/Users/brandonminer/Projects/DND.AI/data/transcripts/test.txt")
        if hope is None:
            raise
        return "success"
    except:
        return "fail"


if __name__ == "__main__":
    print(test())
