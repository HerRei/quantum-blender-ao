"""Full enumeration baseline."""

from __future__ import annotations

from time import perf_counter_ns

from qmr.backends.base import BackendCapability, result_for
from qmr.models import LightingRequest, LightingResult
from qmr.raycast import visibility_table


class ExactBackend:
    name = "exact"

    def capability(self) -> BackendCapability:
        return BackendCapability(name=self.name, available=True, devices=("CPU",))

    def estimate(self, request: LightingRequest) -> LightingResult:
        started = perf_counter_ns()
        table = visibility_table(request)
        initialized = perf_counter_ns()
        estimate = sum(table) / len(table)
        completed = perf_counter_ns()
        return result_for(
            request,
            backend=self.name,
            estimate=estimate,
            truth=estimate,
            oracle_calls=len(table),
            initialization_ms=(initialized - started) / 1e6,
            simulation_ms=(completed - initialized) / 1e6,
            end_to_end_ms=(completed - started) / 1e6,
            metadata={
                "oracle_definition": "one lookup of a classically generated visibility-table bit",
                "visibility_table_entries": len(table),
            },
        )

