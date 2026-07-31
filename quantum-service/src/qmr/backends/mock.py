"""Deterministic no-compute backend for client and timeout tests."""

from __future__ import annotations

from time import perf_counter_ns

from qmr.backends.base import BackendCapability, result_for
from qmr.models import LightingRequest, LightingResult


class MockBackend:
    name = "mock"

    def __init__(self, value: float = 0.5) -> None:
        if not 0 <= value <= 1:
            raise ValueError("mock value must lie in [0, 1]")
        self.value = value

    def capability(self) -> BackendCapability:
        return BackendCapability(name=self.name, available=True, devices=("none",))

    def estimate(self, request: LightingRequest) -> LightingResult:
        started = perf_counter_ns()
        completed = perf_counter_ns()
        return result_for(
            request,
            backend=self.name,
            estimate=self.value,
            truth=None,
            oracle_calls=0,
            initialization_ms=0.0,
            simulation_ms=0.0,
            end_to_end_ms=(completed - started) / 1e6,
            warnings=["Mock backend value is deterministic fixture data, not a measurement."],
            device_name="none",
        )

