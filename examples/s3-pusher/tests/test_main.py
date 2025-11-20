import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# Set env vars before importing main
os.environ["API_KEY"] = "test-key"
os.environ["PROJECT_ID"] = "test-project"
os.environ["BUCKET"] = "test-bucket"

import sys

from fastapi.testclient import TestClient

# Mock google.auth.default before importing main to avoid credential errors
with patch(
    "google.auth.default",
    return_value=(MagicMock(universe_domain="googleapis.com"), "test-project"),
):
    from main import app

client = TestClient(app)


@pytest.fixture
def mock_storage_client():
    with patch("main.storage_client") as mock:
        yield mock


@pytest.fixture
def mock_bucket():
    with patch("main.bucket") as mock:
        yield mock


def test_liveness():
    response = client.get("/liveness/")
    assert response.status_code == 200
    assert response.json() == {"message": "Liveness check succeeded."}


def test_create_item_unauthorized():
    response = client.post("/", json={}, headers={"x-api-key": "wrong-key"})
    assert response.status_code == 401


def test_create_item_success(mock_bucket):
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob

    payload = {
        "id": "evt1",
        "subject": "test/subject",
        "timestamp": "2023-10-27T10:00:00Z",
        "data": "some data",
        "application": "app1",
        "device": "dev1",
        "partitionkey": "pk1",
    }

    response = client.post("/", json=payload, headers={"x-api-key": "test-key"})
    assert response.status_code == 201
    assert response.json() == {"message": "Item created"}

    mock_bucket.blob.assert_called_once()
    mock_blob.upload_from_string.assert_called_once()


def test_create_item_invalid_payload():
    payload = {
        "id": "evt1",
        # missing fields
    }

    response = client.post("/", json=payload, headers={"x-api-key": "test-key"})
    assert response.status_code == 422
