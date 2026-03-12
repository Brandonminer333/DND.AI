from google import genai
from fastapi import FastAPI, Query
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from suggest import get_prompt, suggest


app = FastAPI()

# Add this block ↓
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()
client = genai.Client()


@app.get("/")
def my_endpoint():
    return {"reply": "it worked!"}


@app.post("/suggest")
def suggest_endpoint(context: str = Query(...)):
    if context == "" or context is None:
        raise ValueError("Context parameter is required")

    prompt = get_prompt(context, summary=False)

    suggestions = suggest(client, prompt)
    print(suggestions)

    return {"suggestion": suggestions}
