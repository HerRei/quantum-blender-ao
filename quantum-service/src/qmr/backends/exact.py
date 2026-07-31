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
        table_completed = perf_counter_ns()
        estimate = sum(table) / len(table)
        completed = perf_counter_ns()
        return result_for(
            request,
            backend=self.name,
            estimate=estimate,
            truth=estimate,
            oracle_calls=len(table),
            initialization_ms=(table_completed - started) / 1e6,
            simulation_ms=(completed - table_completed) / 1e6,
            end_to_end_ms=(completed - started) / 1e6,
            metadata={
                "oracle_definition": "one lookup of a classically generated visibility-table bit",
                "visibility_table_entries": len(table),
                "classical_table_build_rays": len(table),
                "ground_truth_table_reads": len(table),
                "ground_truth_in_end_to_end_timing": True,
                "phase_timings_ms": {
                    "classical_visibility_table_dda": (table_completed - started) / 1e6,
                    "exact_table_reduction": (completed - table_completed) / 1e6,
                },
            },
        )
