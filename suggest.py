import os
# Suggestion generation


def suggest(context, summary=None):
    with open('prompts/suggest.md', 'r') as f:
        prompt = f.read()

    with open(f'data/summaries/{}')
    if summary is not None:
        prompt = prompt + "\n\n" + summary

    with open('data')
