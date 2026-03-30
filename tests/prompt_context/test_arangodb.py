"""Unit tests for `prompt_context/arangodb.py` connection helpers."""

from unittest.mock import MagicMock, patch


def test_get_arango_client_returns_client():
    import arangodb as db

    with patch.object(db, "ArangoClient", return_value=MagicMock(name="client")) as m:
        c = db.get_arango_client()
        m.assert_called_once_with(hosts=db.ARANGO_URL)
        assert c is m.return_value


def test_get_database_uses_config():
    import arangodb as db

    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_client.db.return_value = mock_db

    with patch.object(db, "get_arango_client", return_value=mock_client):
        out = db.get_database("mydb")

    mock_client.db.assert_called_once_with(
        "mydb",
        username=db.ARANGO_USERNAME,
        password=db.ARANGO_PASSWORD,
    )
    assert out is mock_db


def test_get_or_create_collection_creates_when_missing():
    import arangodb as db

    mock_db = MagicMock()
    mock_db.has_collection.return_value = False
    mock_col = MagicMock()
    mock_db.create_collection.return_value = None
    mock_db.collection.return_value = mock_col

    with patch.object(db, "get_or_create_database", return_value=mock_db):
        col = db.get_or_create_collection("Things", db_name="dnd")

    mock_db.create_collection.assert_called_once_with("Things")
    mock_db.collection.assert_called_once_with("Things")
    assert col is mock_col
