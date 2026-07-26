from __future__ import annotations

from conftest import FakeBackend
from fastapi.testclient import TestClient

from vaahan.app import create_app
from vaahan.config import Settings


def test_health_version_and_analysis(settings, manifest, valid_output: str) -> None:
    backend = FakeBackend(valid_output)
    with TestClient(create_app(settings, backend, manifest)) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").json() == {"ready": True}
        version = client.get("/v1/version")
        assert version.status_code == 200
        assert version.json()["release"] == "setu-2b-v1.0.0"

        response = client.post("/v1/analyze", json={"message": "UPI se payment fail hai"})
        assert response.status_code == 200
        assert response.json()["result"]["payment_method"] == "upi"
        assert response.headers["X-Request-ID"]


def test_authentication(settings, manifest, valid_output: str) -> None:
    protected = Settings(**{**settings.__dict__, "api_key": "secret"})
    with TestClient(create_app(protected, FakeBackend(valid_output), manifest)) as client:
        assert client.get("/v1/version").status_code == 401
        assert client.get("/v1/version", headers={"X-API-Key": "secret"}).status_code == 200


def test_invalid_model_output_is_502(settings, manifest) -> None:
    with TestClient(create_app(settings, FakeBackend("{}"), manifest)) as client:
        response = client.post("/v1/analyze", json={"message": "refund ka status?"})
        assert response.status_code == 502
        assert response.json()["code"] == "invalid_model_output"
