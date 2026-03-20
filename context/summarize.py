# context/summarize.py
import os
from pathlib import Path

from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
model_name = model_name = "gemini-2.5-flash"


def summarize_transcript(file_path: Path):
    with open("/Users/brandonminer/Projects/dnd-ai/prompts/summarize.md", 'r') as file:
        prompt = file.read()
    try:
        with open(file_path, 'r') as file:
            text = file.read()

        prompt_content = f"{prompt}\nThe transcript is below:\n\n{text}"

        summary = client.models.generate_content(
            model=model_name,
            contents=prompt_content
        )
        return summary.text
    except Exception as e:
        print(e)


if __name__ == "__main__":
    base_path = Path("/Users/brandonminer/Projects/dnd-ai/data/transcript")
    for file in os.listdir(base_path):
        summary = summarize_transcript(
            base_path / file
        )
        if summary is None:
            continue
            raise Exception
        with open("/Users/brandonminer/Projects/dnd-ai/data/summary/" + file, 'w') as f:
            f.write(summary)
        os.remove(base_path / file)
