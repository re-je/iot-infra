import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# Set env vars before importing main
os.environ["API_KEY"] = "test-key"
os.environ["PROJECT_ID"] = "test-project"
os.environ["TABLE"] = "test-table"

from fastapi.testclient import TestClient

# Mock google.auth.default before importing main to avoid credential errors
with patch("google.auth.default", return_value=(MagicMock(), "test-project")):
    from main import Event, app

client = TestClient(app)


@pytest.fixture
def mock_bq_client():
    with patch("main.bq_client") as mock:
        yield mock


def test_liveness():
    response = client.get("/liveness/")
    assert response.status_code == 200
    assert response.json() == {"message": "Liveness check succeeded."}


def test_create_item_unauthorized():
    response = client.post("/", json={}, headers={"x-api-key": "wrong-key"})
    assert response.status_code == 401


def test_create_item_success(mock_bq_client):
    mock_bq_client.insert_rows_json.return_value = []

    payload = {
        "instance": "inst1",
        "application": "app1",
        "device": "dev1",
        "sender": "sender1",
        "event_id": "evt1",
        "points": {"temp": {"present_value": 25.5}},
        "measured_at": "2023-10-27T10:00:00Z",
        "ingressed_at": "2023-10-27T10:00:01Z",
    }

    response = client.post("/", json=payload, headers={"x-api-key": "test-key"})
    assert response.status_code == 201
    assert response.json() == {"message": "New rows have been added."}

    mock_bq_client.insert_rows_json.assert_called_once()


def test_create_item_bq_error(mock_bq_client):
    mock_bq_client.insert_rows_json.return_value = [{"error": "some error"}]

    payload = {
        "instance": "inst1",
        "application": "app1",
        "device": "dev1",
        "sender": "sender1",
        "event_id": "evt1",
        "points": {"temp": {"present_value": 25.5}},
        "measured_at": "2023-10-27T10:00:00Z",
        "ingressed_at": "2023-10-27T10:00:01Z",
    }

    response = client.post("/", json=payload, headers={"x-api-key": "test-key"})
    assert response.status_code == 500
    assert "Encountered errors" in response.json()["error"]
