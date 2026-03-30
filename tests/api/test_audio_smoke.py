"""Smoke tests for `api/audio.py` (recording path is hardware-dependent)."""


def test_audio_module_imports():
    import audio  # noqa: F401
