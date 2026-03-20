import wave
import time
import collections
from pathlib import Path

import webrtcvad
import numpy as np
import sounddevice as sd


def record():
    # --- Config ---
    SAMPLE_RATE = 16000          # webrtcvad requires 8k, 16k, or 32k
    FRAME_DURATION_MS = 30       # webrtcvad requires 10, 20, or 30ms
    FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS /
                     1000)  # samples per frame
    CHANNELS = 1
    VAD_SENSITIVITY = 2          # 0–3, higher = more aggressive silence detection
    # frames of silence before cutting a chunk (~900ms)
    SILENCE_THRESHOLD = 30
    MIN_CHUNK_FRAMES = 10        # ignore very short sounds (< 300ms)
    OUTPUT_DIR = Path("data/audio")

    # --- Setup ---
    OUTPUT_DIR.mkdir(exist_ok=True)
    vad = webrtcvad.Vad(VAD_SENSITIVITY)

    # --- State ---
    buffer = collections.deque()   # accumulates raw PCM bytes per frame
    voiced_frames = []             # frames confirmed as speech
    silence_count = 0
    is_speaking = False
    chunk_index = 0

    def save_chunk(frames: list[bytes], index: int) -> Path:
        """Save a list of PCM frames as a .wav file."""
        path = OUTPUT_DIR / f"chunk_{index:04d}.wav"
        with wave.open(str(path), 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b''.join(frames))
        print(f"  Saved: {path}")
        return path

    def callback(indata, frames, time_info, status):
        nonlocal silence_count, is_speaking, voiced_frames, chunk_index

        # Convert float32 → int16 PCM (webrtcvad requirement)
        pcm = (indata[:, 0] * 32767).astype(np.int16).tobytes()

        # webrtcvad needs exact frame sizes — split into FRAME_SIZE chunks
        for i in range(0, len(pcm), FRAME_SIZE * 2):  # *2 for 16-bit bytes
            frame = pcm[i:i + FRAME_SIZE * 2]
            if len(frame) < FRAME_SIZE * 2:
                break  # drop incomplete trailing frame

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
                    # keep trailing silence for natural cutoff
                    voiced_frames.append(frame)

                    if silence_count >= SILENCE_THRESHOLD:
                        # End of speech detected — save chunk
                        if len(voiced_frames) >= MIN_CHUNK_FRAMES:
                            save_chunk(voiced_frames, chunk_index)
                            chunk_index += 1

                        # Reset state
                        voiced_frames = []
                        silence_count = 0
                        is_speaking = False

    print(f"Listening... (chunks saved to '{OUTPUT_DIR}/')")
    print("Press Ctrl+C to stop.\n")

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='float32',
            blocksize=FRAME_SIZE,   # align sounddevice blocks to VAD frame size
            callback=callback
        ):
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        # Save any remaining speech on exit
        if voiced_frames and len(voiced_frames) >= MIN_CHUNK_FRAMES:
            print("\nSaving remaining audio...")
            save_chunk(voiced_frames, chunk_index)
        print("Stopped.")


if __name__ == "__main__":
    record()
