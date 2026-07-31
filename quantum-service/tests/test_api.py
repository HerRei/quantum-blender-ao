from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from qmr.api import create_app
from qmr.backends.mock import MockBackend
from qmr.config import BackendSettings, ServiceSettings
from qmr.models import Algorithm, LightingRequest, LightingResult
from qmr.scenes import open_sky


def _settings(tmp_path: Path, **updates: object) -> ServiceSettings:
    base: dict[str, object] = {
        "request_timeout_seconds": 2.0,
        "benchmark_output_dir": tmp_path / "results",
        "log_level": "ERROR",
        "backend": BackendSettings(name="request"),
    }
    base.update(updates)
    return ServiceSettings.model_validate(base)


def test_health_capabilities_and_exact_estimate(tmp_path: Path) -> None:
    with TestClient(create_app(_settings(tmp_path))) as client:
        assert client.get("/health").json()["status"] == "ok"
        capabilities = client.get("/capabilities").json()
        assert any(
            item["name"] == "intel_gpu" and not item["available"]
            for item in capabilities["backends"]
        )
        response = client.post(
            "/lighting/estimate",
            json=open_sky().request(direction_count=8).model_dump(mode="json"),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["backend"] == "exact"
    assert payload["estimate"] == 1.0
    assert payload["metadata"]["service_handler_ms"] >= 0


def test_configured_backend_overrides_request_with_warning(tmp_path: Path) -> None:
    settings = _settings(tmp_path, backend=BackendSettings(name=Algorithm.MOCK))
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/lighting/estimate",
            json=open_sky().request().model_dump(mode="json"),
        )

    assert response.status_code == 200
    assert response.json()["backend"] == "mock"
    assert any("overrode" in warning for warning in response.json()["warnings"])


def test_timeout_returns_504(tmp_path: Path) -> None:
    class SlowBackend(MockBackend):
        name = "slow_fixture"

        def estimate(self, request: LightingRequest) -> LightingResult:
            time.sleep(0.05)
            return super().estimate(request)

    settings = _settings(tmp_path, request_timeout_seconds=0.001)
    with TestClient(create_app(settings, lambda request: SlowBackend())) as client:
        response = client.post(
            "/lighting/estimate",
            json=open_sky().request().model_dump(mode="json"),
        )

    assert response.status_code == 504
    assert response.json()["detail"] == "lighting estimation timed out"


def test_benchmark_endpoint_writes_to_configured_directory(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    request = {
        "config": {
            "schema_version": "1.0",
            "name": "api-fixture",
            "scenes": ["open_sky"],
            "backends": ["exact"],
            "direction_counts": [8],
            "oracle_budgets": [8],
            "seeds": [1],
            "generate_plots": False,
        }
    }
    with TestClient(create_app(settings)) as client:
        response = client.post("/benchmark/run", json=request)

    assert response.status_code == 200
    assert response.json()["successful_runs"] == 1
    assert Path(response.json()["jsonl"]).is_file()

