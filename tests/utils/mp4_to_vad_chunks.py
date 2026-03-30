#!/usr/bin/env python3
"""
Decode an MP4 session recording to 16 kHz mono PCM, then split it into WAV chunks
using the same Voice Activity Detection + silence tail logic as `api/audio.py`.

Requirements:
  - `ffmpeg` on your PATH (used only to decode video → PCM).
  - Python deps already used by the project: `webrtcvad`, `numpy` (same as `api/audio.py`).

Default output: `tests/data/audio/chunk_XXXX.wav` (directory is created if missing).

Example:
  python tests/mp4_to_vad_chunks.py /path/to/session.mp4

Or set `SESSION_MP4` or `MP4_PATH`, or run with no args in a **terminal** to be prompted for the path.
(IDE “Run” often has no TTY; then pass the path as the first argument or use env vars.)

Optional overrides (same semantics as live `record()`):
  --silence-threshold   consecutive non-speech frames after speech starts before flush
  --min-chunk-frames    minimum voiced frames required to emit a chunk
  --vad-mode            webrtcvad aggressiveness 0–3 (see webrtcvad docs)
  --output-dir          where to write WAVs (default: tests/data/audio)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import warnings
import wave
from pathlib import Path

# webrtcvad may trigger setuptools' pkg_resources deprecation on import; hide that noise.
warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")

import webrtcvad

# --- Match `api/audio.py` live capture defaults ---
SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
CHANNELS = 1
DEFAULT_VAD_SENSITIVITY = 2
DEFAULT_SILENCE_THRESHOLD = 30
DEFAULT_MIN_CHUNK_FRAMES = 10

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "data" / "audio"


def decode_mp4_to_pcm_s16le_mono_16k(video_path: Path) -> bytes:
    """
    Use ffmpeg to produce raw s16le mono PCM at 16 kHz (same rate as `audio.py`).
    """
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, check=False)
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"ffmpeg failed (exit {proc.returncode}). Is ffmpeg installed and the path valid?\n{err}"
        )
    return proc.stdout


def save_wav_chunk(frames: list[bytes], index: int, output_dir: Path) -> Path:
    """Save PCM frames as 16-bit mono WAV (same as `api/audio.py`)."""
    path = output_dir / f"chunk_{index:04d}.wav"
    output_dir.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))
    return path


def segment_pcm_by_vad(
    pcm: bytes,
    *,
    output_dir: Path,
    vad_sensitivity: int,
    silence_threshold: int,
    min_chunk_frames: int,
) -> int:
    """
    Port of the `record()` callback loop in `api/audio.py`: walk frames with webrtcvad,
    buffer speech, and on sustained silence (`silence_count >= silence_threshold`) write a chunk.

    Returns the number of chunks written.
    """
    vad = webrtcvad.Vad(vad_sensitivity)
    voiced_frames: list[bytes] = []
    silence_count = 0
    is_speaking = False
    chunk_index = 0

    def save_chunk(frames: list[bytes]) -> None:
        nonlocal chunk_index
        path = save_wav_chunk(frames, chunk_index, output_dir)
        print(f"  Saved: {path}")
        chunk_index += 1

    for i in range(0, len(pcm), FRAME_SIZE * 2):
        frame = pcm[i : i + FRAME_SIZE * 2]
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

                if silence_count >= silence_threshold:
                    if len(voiced_frames) >= min_chunk_frames:
                        save_chunk(voiced_frames)

                    voiced_frames = []
                    silence_count = 0
                    is_speaking = False

    # End of stream: same as API path when recording stops (`audio.py` lines 104–107).
    if voiced_frames and len(voiced_frames) >= min_chunk_frames:
        print("\nSaving remaining audio at end of file...")
        save_chunk(voiced_frames)

    return chunk_index


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split an MP4 into VAD/silence-based WAV chunks (logic aligned with api/audio.py).",
        epilog=(
            "With no MP4 argument: you are prompted in a terminal, or set SESSION_MP4 / MP4_PATH.\n"
            "Example: python tests/mp4_to_vad_chunks.py ~/Videos/session.mp4"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "mp4_path",
        nargs="?",
        type=Path,
        default=None,
        help="Path to the session MP4 (optional if SESSION_MP4 or MP4_PATH is set)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for chunk_*.wav (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--vad-mode",
        type=int,
        default=DEFAULT_VAD_SENSITIVITY,
        choices=[0, 1, 2, 3],
        help="webrtcvad aggressiveness (default: 2, same as audio.py)",
    )
    parser.add_argument(
        "--silence-threshold",
        type=int,
        default=DEFAULT_SILENCE_THRESHOLD,
        help="Non-speech frames after speech before cutting a chunk (default: 30)",
    )
    parser.add_argument(
        "--min-chunk-frames",
        type=int,
        default=DEFAULT_MIN_CHUNK_FRAMES,
        help="Minimum frames in a chunk (default: 10)",
    )
    args = parser.parse_args()

    mp4_raw = args.mp4_path
    if mp4_raw is None:
        env_path = os.environ.get("SESSION_MP4") or os.environ.get("MP4_PATH")
        if env_path:
            mp4_raw = Path(env_path)
    if mp4_raw is None and sys.stdin.isatty():
        # No arg and no env: prompt when run interactively (e.g. IDE Run without args).
        try:
            line = input("Path to MP4 (drag file into terminal to paste path): ").strip()
        except EOFError:
            line = ""
        if line:
            # Strip common paste wrappers: quotes or backslash-escaped spaces
            line = line.strip().strip("'\"")
            mp4_raw = Path(line)
    if mp4_raw is None:
        parser.print_help(file=sys.stderr)
        print(
            "\nError: no MP4 path. Use one of:\n"
            "  • First argument: python tests/mp4_to_vad_chunks.py /path/to/session.mp4\n"
            "  • Environment: SESSION_MP4 or MP4_PATH\n"
            "  • Interactive: run again in a terminal (no args) to be prompted",
            file=sys.stderr,
        )
        return 2

    mp4 = mp4_raw.expanduser().resolve()
    if not mp4.is_file():
        print(f"Error: file not found: {mp4}", file=sys.stderr)
        return 1

    out_dir = args.output_dir.expanduser().resolve()
    print(f"Decoding: {mp4}")
    pcm = decode_mp4_to_pcm_s16le_mono_16k(mp4)
    if not pcm:
        print("Error: ffmpeg produced no audio data.", file=sys.stderr)
        return 1

    duration_s = len(pcm) / (SAMPLE_RATE * 2)
    print(f"PCM length: {len(pcm)} bytes (~{duration_s:.1f} s at {SAMPLE_RATE} Hz mono s16le)")
    print(f"Writing chunks under: {out_dir}/")
    print("(VAD + silence_count logic matches api/audio.py)\n")

    n = segment_pcm_by_vad(
        pcm,
        output_dir=out_dir,
        vad_sensitivity=args.vad_mode,
        silence_threshold=args.silence_threshold,
        min_chunk_frames=args.min_chunk_frames,
    )
    print(f"\nDone. Wrote {n} chunk file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
