"""FastAPI boundary; compute work is never executed on the event-loop thread."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from time import perf_counter_ns
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import Field

from qmr.backends.base import BackendUnavailableError, LightingBackend
from qmr.backends.intel_gpu import IntelGpuBackend
from qmr.backends.registry import all_capabilities, create_backend
from qmr.benchmark import BenchmarkArtifacts, BenchmarkConfig, run_benchmark
from qmr.config import ServiceSettings, load_settings
from qmr.logging_config import configure_logging
from qmr.models import LightingRequest, LightingResult, StrictModel

BackendResolver = Callable[[LightingRequest], LightingBackend]
LOGGER = logging.getLogger("qmr.api")


class BenchmarkRunRequest(StrictModel):
    config: BenchmarkConfig


class BenchmarkRunResponse(StrictModel):
    jsonl: str
    csv: str
    plots: list[str] = Field(default_factory=list)
    skipped_plots: list[str] = Field(default_factory=list)
    successful_runs: int
    skipped_runs: int
    failed_runs: int


def _artifact_response(artifacts: BenchmarkArtifacts) -> BenchmarkRunResponse:
    return BenchmarkRunResponse(
        jsonl=str(artifacts.jsonl),
        csv=str(artifacts.csv),
        plots=[str(path) for path in artifacts.plots.generated] if artifacts.plots else [],
        skipped_plots=list(artifacts.plots.skipped) if artifacts.plots else [],
        successful_runs=artifacts.successful_runs,
        skipped_runs=artifacts.skipped_runs,
        failed_runs=artifacts.failed_runs,
    )


def _default_resolver(settings: ServiceSettings) -> BackendResolver:
    def resolve(request: LightingRequest) -> LightingBackend:
        selected = (
            request.algorithm if settings.backend.name == "request" else settings.backend.name
        )
        if str(selected) == "intel_gpu":
            return IntelGpuBackend(
                device_index=settings.backend.device_index,
                precision=settings.backend.precision,
                max_qubits=settings.backend.max_qubits,
            )
        return create_backend(selected)

    return resolve


def create_app(
    settings: ServiceSettings | None = None,
    backend_resolver: BackendResolver | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)
    resolve_backend = backend_resolver or _default_resolver(settings)
    semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
    app = FastAPI(
        title="Quantum Minecraft Rendering Service",
        version="0.1.0",
        description=(
            "Classical visibility-table research service. The quantum backend does not "
            "implement reversible ray marching."
        ),
    )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "schema_version": "1.0",
            "backend_policy": str(settings.backend.name),
        }

    @app.get("/capabilities")
    async def capabilities() -> dict[str, Any]:
        return {
            "backend_policy": str(settings.backend.name),
            "configured_device_index": settings.backend.device_index,
            "configured_precision": settings.backend.precision,
            "configured_max_qubits": settings.backend.max_qubits,
            "backends": all_capabilities(),
        }

    @app.post("/lighting/estimate", response_model=LightingResult)
    async def lighting_estimate(request: LightingRequest) -> LightingResult:
        started = perf_counter_ns()
        backend = resolve_backend(request)
        try:
            async with semaphore:
                result = await asyncio.wait_for(
                    asyncio.to_thread(backend.estimate, request),
                    timeout=settings.request_timeout_seconds,
                )
        except TimeoutError as exc:
            elapsed_ms = (perf_counter_ns() - started) / 1e6
            LOGGER.warning(
                "lighting_estimate_timeout",
                extra={
                    "request_id": str(request.request_id),
                    "backend": backend.name,
                    "elapsed_ms": elapsed_ms,
                    "status": 504,
                },
            )
            raise HTTPException(status_code=504, detail="lighting estimation timed out") from exc
        except BackendUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            LOGGER.exception(
                "lighting_estimate_failed",
                extra={
                    "request_id": str(request.request_id),
                    "backend": backend.name,
                    "status": 500,
                },
            )
            raise HTTPException(status_code=500, detail="lighting estimation failed") from exc

        handler_ms = (perf_counter_ns() - started) / 1e6
        metadata = {
            **result.metadata,
            "backend_end_to_end_ms": result.end_to_end_ms,
            "service_handler_ms": handler_ms,
        }
        warnings = list(result.warnings)
        selected = settings.backend.name
        if selected != "request" and str(selected) != str(request.algorithm):
            warnings.append(
                f"Configured backend {selected} overrode requested algorithm {request.algorithm}."
            )
        response = result.model_copy(
            update={
                "end_to_end_ms": max(result.end_to_end_ms, handler_ms),
                "metadata": metadata,
                "warnings": warnings,
            }
        )
        LOGGER.info(
            "lighting_estimate_completed",
            extra={
                "request_id": str(request.request_id),
                "backend": response.backend,
                "elapsed_ms": handler_ms,
                "status": 200,
            },
        )
        return response

    @app.post("/benchmark/run", response_model=BenchmarkRunResponse)
    async def benchmark_run(request: BenchmarkRunRequest) -> BenchmarkRunResponse:
        try:
            async with semaphore:
                artifacts = await asyncio.to_thread(
                    run_benchmark,
                    request.config,
                    settings.benchmark_output_dir,
                )
        except Exception as exc:
            LOGGER.exception("benchmark_run_failed", extra={"status": 500})
            raise HTTPException(status_code=500, detail="benchmark run failed") from exc
        return _artifact_response(artifacts)

    return app


app = create_app()
