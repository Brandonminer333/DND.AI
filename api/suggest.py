import os

from google import genai
# Suggestion generation


def get_prompt(context, summary=True):
    with open('../prompts/suggest.md', 'r') as f:
        prompt = f.read()

    if summary:
        with open(f'../data/summaries/{context}.md', 'r') as f:
            summary = f.read()
        prompt = prompt + "\n\n" + summary

    with open(f'../data/transcripts/{context}.md', 'r') as f:
        prompt = prompt + "\n\n" + f.read()

    return prompt


def suggest(client, prompt, model_name="gemini-2.5-flash"):
    with open('../prompts/suggest.md', 'r') as f:
        suggest_prompt = f.read()

    prompt = suggest_prompt + "\n\n" + prompt
    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )

    return response.text


def example():
    from google import genai
    from dotenv import load_dotenv

    load_dotenv()

    client = genai.Client()
    context = 'example'

    prompt = get_prompt(context, summary=False)

    suggestions = suggest(client, prompt)
    print(suggestions)


if __name__ == "__main__":
    example()
