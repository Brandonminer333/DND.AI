from google import genai
from dotenv import load_dotenv
from fastapi import FastAPI, Query, BackgroundTasks  # <-- Import BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from audio import record
from suggest import get_prompt, suggest

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()
client = genai.Client()

# --- NEW: Global state to control recording ---


class AppState:
    is_recording = False


@app.get("/")
def my_endpoint():
    return {"reply": "it worked!"}


@app.post("/suggest")
def suggest_endpoint(context: str = Query(...)):
    # ... your existing suggest code ...
    if context == "" or context is None:
        raise ValueError("Context parameter is required")
    prompt = get_prompt(context, summary=False)
    suggestions = suggest(client, prompt)
    return {"suggestion": suggestions}

# --- NEW: Background Task Function ---


def run_recording():
    try:
        # Pass the state class to your record function so it can check it
        record(AppState)
    except Exception as e:
        print(f"Recording failed: {e}")
    finally:
        # Ensure state resets if it crashes
        AppState.is_recording = False


@app.post("/record")
async def start_recording(background_tasks: BackgroundTasks):
    if AppState.is_recording:
        return {"state": "Already recording"}

    AppState.is_recording = True
    # Start the recording in the background so FastAPI doesn't freeze
    background_tasks.add_task(run_recording)

    return {"state": "Recording started successfully"}

# --- NEW: Stop Endpoint ---


@app.post("/stop-record")
async def stop_recording():
    if not AppState.is_recording:
        return {"state": "Not currently recording"}

    # Flip the flag! Your audio.py needs to check this flag.
    AppState.is_recording = False
    return {"state": "Recording stopped successfully"}
