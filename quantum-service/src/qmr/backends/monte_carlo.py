"""Seeded classical Monte Carlo baseline with Wilson intervals."""

from __future__ import annotations

import math
import random
from statistics import NormalDist
from time import perf_counter_ns

from qmr.backends.base import BackendCapability, result_for
from qmr.models import ConfidenceInterval, LightingRequest, LightingResult
from qmr.raycast import visibility_table


def wilson_interval(successes: int, samples: int, level: float) -> tuple[float, float]:
    if samples <= 0:
        raise ValueError("samples must be positive")
    z = NormalDist().inv_cdf(0.5 + level / 2)
    proportion = successes / samples
    denominator = 1 + z * z / samples
    center = (proportion + z * z / (2 * samples)) / denominator
    spread = (
        z
        * math.sqrt(proportion * (1 - proportion) / samples + z * z / (4 * samples * samples))
        / denominator
    )
    return max(0.0, center - spread), min(1.0, center + spread)


class ClassicalMonteCarloBackend:
    name = "classical_monte_carlo"

    def capability(self) -> BackendCapability:
        return BackendCapability(name=self.name, available=True, devices=("CPU",))

    def estimate(self, request: LightingRequest) -> LightingResult:
        started = perf_counter_ns()
        table = visibility_table(request)
        table_completed = perf_counter_ns()
        truth = sum(table) / len(table)
        truth_completed = perf_counter_ns()

        samples = request.max_oracle_calls
        rng = random.Random(request.seed)
        successes = sum(table[rng.randrange(len(table))] for _ in range(samples))
        estimate = successes / samples
        low, high = wilson_interval(successes, samples, request.confidence_level)
        completed = perf_counter_ns()
        return result_for(
            request,
            backend=self.name,
            estimate=estimate,
            truth=truth,
            oracle_calls=samples,
            initialization_ms=(truth_completed - started) / 1e6,
            simulation_ms=(completed - truth_completed) / 1e6,
            end_to_end_ms=(completed - started) / 1e6,
            confidence_interval=ConfidenceInterval(
                low=low,
                high=high,
                level=request.confidence_level,
                method="wilson_score",
            ),
            metadata={
                "classical_samples": samples,
                "sampling": "with_replacement",
                "seed": request.seed,
                "visibility_table_entries": len(table),
                "classical_table_build_rays": len(table),
                "classical_ground_truth_table_reads": len(table),
                "oracle_accounting": "one logical visibility-table lookup per sampled index",
                "ground_truth_in_end_to_end_timing": True,
                "phase_timings_ms": {
                    "classical_visibility_table_dda": (table_completed - started) / 1e6,
                    "ground_truth_reduction": (truth_completed - table_completed) / 1e6,
                    "sampling_and_wilson_interval": (completed - truth_completed) / 1e6,
                },
            },
        )
