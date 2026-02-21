# Rolling compression logic
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
model_name = model_name = "gemini-2.5-flash"


def summarize(file_path):
    with open("/Users/brandonminer/Projects/DND.AI/prompts/summarize.md", 'r') as file:
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


def test():
    summary = summarize(
        "/Users/brandonminer/Projects/DND.AI/data/transcripts/test.txt")
    if summary is None:
        raise Exception
    with open("/Users/brandonminer/Projects/DND.AI/data/summaries/test.mb", 'w') as file:
        file.write(summary)


if __name__ == "__main__":
    test()
