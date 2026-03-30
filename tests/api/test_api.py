"""Unit tests for `api/api.py` FastAPI app."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_app_state():
    import api as api_module

    api_module.AppState.is_recording = False
    yield
    api_module.AppState.is_recording = False


@pytest.fixture
def client():
    import api as api_module

    return TestClient(api_module.app)


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"reply": "it worked!"}


@patch("api.suggest")
@patch("api.get_prompt")
def test_suggest_endpoint(mock_get_prompt, mock_suggest, client):
    import api as api_module

    mock_get_prompt.return_value = "built prompt"
    mock_suggest.return_value = "one suggestion"

    r = client.post("/suggest?context=foo")

    assert r.status_code == 200
    assert r.json() == {"suggestion": "one suggestion"}
    mock_get_prompt.assert_called_once_with("foo", summary=False)
    mock_suggest.assert_called_once_with(api_module.client, "built prompt")


@patch("api.run_recording")
def test_record_start_stop(mock_run_recording, client):
    """Background task normally clears `AppState`; patch `run_recording` so state stays testable."""
    import api as api_module

    r = client.post("/record")
    assert r.status_code == 200
    assert "started" in r.json()["state"].lower()
    assert api_module.AppState.is_recording is True

    r2 = client.post("/record")
    assert "already" in r2.json()["state"].lower()

    r3 = client.post("/stop-record")
    assert r3.status_code == 200
    assert "stopped" in r3.json()["state"].lower()
    assert api_module.AppState.is_recording is False

    r4 = client.post("/stop-record")
    assert "not" in r4.json()["state"].lower()

    mock_run_recording.assert_called_once()
