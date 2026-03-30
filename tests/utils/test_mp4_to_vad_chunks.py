"""Unit tests for `tests/utils/mp4_to_vad_chunks.py`."""

import sys
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

UTILS_DIR = Path(__file__).resolve().parent
if str(UTILS_DIR) not in sys.path:
    sys.path.insert(0, str(UTILS_DIR))

import mp4_to_vad_chunks as m  # noqa: E402


def test_save_wav_chunk_writes_valid_wav(tmp_path):
    frames = [b"\x00\x00" * m.FRAME_SIZE]
    out = m.save_wav_chunk(frames, 0, tmp_path)
    assert out.exists()
    with wave.open(str(out), "rb") as wf:
        assert wf.getnchannels() == m.CHANNELS
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == m.SAMPLE_RATE


def test_segment_pcm_by_vad_silence_writes_nothing(tmp_path):
    pcm = b"\x00\x00" * m.FRAME_SIZE * 200
    n = m.segment_pcm_by_vad(
        pcm,
        output_dir=tmp_path,
        vad_sensitivity=3,
        silence_threshold=5,
        min_chunk_frames=10,
    )
    assert n == 0
    assert not list(tmp_path.glob("chunk_*.wav"))


@patch("mp4_to_vad_chunks.subprocess.run")
def test_decode_mp4_to_pcm_s16le_mono_16k_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout=b"\x01\x00" * 100, stderr=b"")
    out = m.decode_mp4_to_pcm_s16le_mono_16k(Path("/fake/video.mp4"))
    assert len(out) == 200
    mock_run.assert_called_once()


@patch("mp4_to_vad_chunks.subprocess.run")
def test_decode_mp4_raises_on_ffmpeg_failure(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stdout=b"", stderr=b"no ffmpeg")
    with pytest.raises(RuntimeError, match="ffmpeg"):
        m.decode_mp4_to_pcm_s16le_mono_16k(Path("/fake/video.mp4"))
