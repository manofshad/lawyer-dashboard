from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.extractions import get_restaurant_extractor
from app.settings import get_settings


class _StubExtractor:
    def __init__(self, restaurant_name: str | None = "Don Angie") -> None:
        self.restaurant_name = restaurant_name

    def extract_restaurant_name(self, record):
        return type("Result", (), {"restaurant_name": self.restaurant_name})


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides = {}
    get_settings.cache_clear()
    yield
    app.dependency_overrides = {}
    get_settings.cache_clear()


def test_restaurant_extractions_endpoint_returns_paginated_items(monkeypatch) -> None:
    monkeypatch.setenv("BACKEND_SAMPLE_TIKTOK_JSON_PATH", "../Pasted code.json")
    monkeypatch.setenv("BACKEND_OPENAI_API_KEY", "test-key")
    app.dependency_overrides[get_restaurant_extractor] = lambda: _StubExtractor()
    client = TestClient(app)

    response = client.post("/api/extractions/restaurants", json={"limit": 2, "offset": 1})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 2
    assert payload["items"][0]["restaurant_name"] == "Don Angie"


def test_restaurant_extractions_endpoint_returns_500_for_bad_sample_path(
    monkeypatch,
) -> None:
    monkeypatch.setenv("BACKEND_SAMPLE_TIKTOK_JSON_PATH", "missing.json")
    monkeypatch.setenv("BACKEND_OPENAI_API_KEY", "test-key")
    app.dependency_overrides[get_restaurant_extractor] = lambda: _StubExtractor()
    client = TestClient(app)

    response = client.post("/api/extractions/restaurants", json={})

    assert response.status_code == 500
    assert "not found" in response.json()["detail"].lower()


def test_restaurant_extractions_endpoint_returns_500_when_api_key_missing(
    monkeypatch,
) -> None:
    monkeypatch.setenv("BACKEND_SAMPLE_TIKTOK_JSON_PATH", "../Pasted code.json")
    monkeypatch.delenv("BACKEND_OPENAI_API_KEY", raising=False)
    client = TestClient(app)

    response = client.post("/api/extractions/restaurants", json={})

    assert response.status_code == 500
    assert "api key" in response.json()["detail"].lower()


def test_restaurant_extractions_endpoint_returns_502_on_extractor_failure(
    monkeypatch,
) -> None:
    from fastapi import HTTPException

    class _FailingExtractor:
        def extract_restaurant_name(self, record):
            raise HTTPException(status_code=502, detail="OpenAI extraction request failed.")

    monkeypatch.setenv("BACKEND_SAMPLE_TIKTOK_JSON_PATH", "../Pasted code.json")
    monkeypatch.setenv("BACKEND_OPENAI_API_KEY", "test-key")
    app.dependency_overrides[get_restaurant_extractor] = lambda: _FailingExtractor()
    client = TestClient(app)

    response = client.post("/api/extractions/restaurants", json={"limit": 1})

    assert response.status_code == 502
    assert response.json()["detail"] == "OpenAI extraction request failed."
