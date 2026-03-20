import wave
import time
import collections
from pathlib import Path

import webrtcvad
import numpy as np
import sounddevice as sd

# We add `state=None` so it can accept AppState from FastAPI,
# but still works if you run this file directly.


def record(state=None):
    # --- Config ---
    SAMPLE_RATE = 16000
    FRAME_DURATION_MS = 30
    FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
    CHANNELS = 1
    VAD_SENSITIVITY = 2
    SILENCE_THRESHOLD = 30
    MIN_CHUNK_FRAMES = 10
    OUTPUT_DIR = Path("data/audio")

    # --- Setup ---
    OUTPUT_DIR.mkdir(exist_ok=True)
    vad = webrtcvad.Vad(VAD_SENSITIVITY)

    # --- State ---
    buffer = collections.deque()
    voiced_frames = []
    silence_count = 0
    is_speaking = False
    chunk_index = 0

    def save_chunk(frames: list[bytes], index: int) -> Path:
        """Save a list of PCM frames as a .wav file."""
        path = OUTPUT_DIR / f"chunk_{index:04d}.wav"
        with wave.open(str(path), 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b''.join(frames))
        print(f"  Saved: {path}")
        return path

    def callback(indata, frames, time_info, status):
        nonlocal silence_count, is_speaking, voiced_frames, chunk_index

        pcm = (indata[:, 0] * 32767).astype(np.int16).tobytes()

        for i in range(0, len(pcm), FRAME_SIZE * 2):
            frame = pcm[i:i + FRAME_SIZE * 2]
            if len(frame) < FRAME_SIZE * 2:
                break

            is_speech = vad.is_speech(frame, SAMPLE_RATE)

            if is_speech:
                voiced_frames.append(frame)
                silence_count = 0
                if not is_speaking:
                    print("  Speech detected...")
                    is_speaking = True
            else:
                if is_speaking:
                    silence_count += 1
                    voiced_frames.append(frame)

                    if silence_count >= SILENCE_THRESHOLD:
                        if len(voiced_frames) >= MIN_CHUNK_FRAMES:
                            save_chunk(voiced_frames, chunk_index)
                            chunk_index += 1

                        voiced_frames = []
                        silence_count = 0
                        is_speaking = False

    print(f"Listening... (chunks saved to '{OUTPUT_DIR}/')")

    if state is None:
        print("Press Ctrl+C to stop.\n")
    else:
        print("Waiting for stop signal from Website...\n")

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='float32',
            blocksize=FRAME_SIZE,
            callback=callback
        ):
            # --- THE KEY CHANGE IS HERE ---
            if state is None:
                # Standalone mode: loop forever until Ctrl+C
                while True:
                    time.sleep(0.1)
            else:
                # API mode: loop only while the FastAPI state is True
                while state.is_recording:
                    time.sleep(0.1)

        # If the API mode loop finishes naturally, save any leftover audio
        if voiced_frames and len(voiced_frames) >= MIN_CHUNK_FRAMES:
            print("\nSaving remaining audio...")
            save_chunk(voiced_frames, chunk_index)
        print("Stopped via API.")

    except KeyboardInterrupt:
        # Save any remaining speech on Ctrl+C exit
        if voiced_frames and len(voiced_frames) >= MIN_CHUNK_FRAMES:
            print("\nSaving remaining audio...")
            save_chunk(voiced_frames, chunk_index)
        print("Stopped via KeyboardInterrupt.")


if __name__ == "__main__":
    record()
