"""Reproducible scientific-audit experiments for MC versus simulated MLAE.

This module is deliberately independent from :mod:`qmr.benchmark` and
:mod:`qmr.plots`.  Its large statistical study samples the analytically known
finite-shot measurement distribution.  Separate, explicitly labelled runtime
runs execute synthesized 64-entry lookup circuits with Qiskit's
``StatevectorSampler``.  Neither path is represented as physical-QPU evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import random
import shutil
import statistics
import subprocess
import sys
import tomllib
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from statistics import NormalDist
from time import perf_counter_ns
from typing import Any, Literal, cast

import matplotlib
import numpy as np
import psutil
from numpy.typing import NDArray
from pydantic import Field, model_validator
from qiskit import QuantumCircuit, transpile  # type: ignore[import-untyped]
from qiskit.primitives import StatevectorSampler  # type: ignore[import-untyped]
from qiskit_algorithms import (  # type: ignore[import-untyped]
    MaximumLikelihoodAmplitudeEstimation,
)

from qmr.backends.cpu_quantum import build_estimation_problem, plan_budget
from qmr.models import StrictModel

# isort: off
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
# isort: on


BASELINE_COMMIT = "a4170570e76db3a9229def731a260112d68d304e"
REQUIRED_AMPLITUDE_NUMERATORS = (0, 1, 8, 32, 56, 63, 64)
REQUIRED_AMPLITUDE_DENOMINATOR = 64
REQUIRED_REQUESTED_BUDGETS = (32, 64, 128, 256, 512, 1024)
REQUIRED_MINIMUM_REPLICATES = 256
EXACT_ENUMERATION_CALLS = 64
REQUIRED_MLE_GRID_POINTS = 8193
REQUIRED_BASE_SEED = 20260731
REQUIRED_BOOTSTRAP_REPLICATES = 2000
REQUIRED_BOOTSTRAP_CONFIDENCE_LEVEL = 0.95
REQUIRED_BOOTSTRAP_SEED = 20260801
REQUIRED_RUNTIME_ORDER_SEED = 20260802
REQUIRED_RUNTIME_WARMUP_REPEATS = 1
REQUIRED_RUNTIME_MEASURED_REPEATS = 5
TABLE_LAYOUT: Literal["contiguous_prefix_visible_then_blocked"] = (
    "contiguous_prefix_visible_then_blocked"
)
AUDIT_SOURCE_PATHS = (
    "quantum-service/src/qmr/audit_experiment.py",
    "quantum-service/src/qmr/backends/cpu_quantum.py",
)
ANALYTICAL_MODEL = (
    "analytical measurement model: finite-shot binomial circuit outcomes; "
    "no QPU execution and no statevector simulation runtime"
)
QISKIT_RUNTIME_MODEL = (
    "Qiskit StatevectorSampler finite-shot CPU simulation of synthesized circuits; not a QPU"
)
PLOT_NAMES = (
    "rmse-vs-logical-oracle-calls",
    "bias-vs-logical-oracle-calls",
    "std-vs-logical-oracle-calls",
    "runtime-vs-logical-oracle-calls",
    "circuit-depth-vs-logical-oracle-calls",
    "gate-count-vs-logical-oracle-calls",
)


class AuditExperimentConfig(StrictModel):
    """Versioned configuration for the dedicated scientific-audit protocol."""

    schema_version: Literal["1.0"] = "1.0"
    name: str = Field(default="scientific-audit", min_length=1)
    baseline_commit: str = BASELINE_COMMIT
    amplitude_denominator: int = Field(default=64, ge=1)
    amplitude_numerators: list[int] = Field(default_factory=list, min_length=1)
    requested_oracle_budgets: list[int] = Field(default_factory=list, min_length=1)
    desired_accuracy: float = Field(default=0.05, gt=0, le=1)
    confidence_level: float = Field(default=0.95, gt=0, lt=1)
    analytical_replicates: int = Field(default=256, ge=1)
    mle_grid_points: int = Field(default=8193, ge=257)
    base_seed: int = Field(default=20260731, ge=0, le=2**32 - 1)
    bootstrap_replicates: int = Field(default=2000, ge=100)
    bootstrap_confidence_level: float = Field(default=0.95, gt=0, lt=1)
    bootstrap_seed: int = Field(default=20260801, ge=0, le=2**32 - 1)
    runtime_order_seed: int = Field(default=20260802, ge=0, le=2**32 - 1)
    runtime_warmup_repeats: int = Field(default=1, ge=0, le=10)
    runtime_measured_repeats: int = Field(default=5, ge=1, le=100)
    runtime_fail_fast: bool = False
    table_layout: Literal["contiguous_prefix_visible_then_blocked"] = TABLE_LAYOUT
    require_clean_worktree: bool = True

    @model_validator(mode="after")
    def validate_structure(self) -> AuditExperimentConfig:
        if self.mle_grid_points % 2 == 0:
            raise ValueError("mle_grid_points must be odd so that a=1/2 lies on the grid")
        if len(self.amplitude_numerators) != len(set(self.amplitude_numerators)):
            raise ValueError("amplitude_numerators must be unique")
        if any(
            numerator < 0 or numerator > self.amplitude_denominator
            for numerator in self.amplitude_numerators
        ):
            raise ValueError("amplitude numerator lies outside [0, denominator]")
        if len(self.requested_oracle_budgets) != len(set(self.requested_oracle_budgets)):
            raise ValueError("requested_oracle_budgets must be unique")
        if any(budget < 1 for budget in self.requested_oracle_budgets):
            raise ValueError("requested_oracle_budgets must be positive")
        return self

    @classmethod
    def load(cls, path: Path) -> AuditExperimentConfig:
        with path.open("rb") as stream:
            return cls.model_validate(tomllib.load(stream))

    def validate_scientific_protocol(self) -> None:
        """Reject a long-run configuration that deviates from the audit preregistration."""

        if self.baseline_commit != BASELINE_COMMIT:
            raise ValueError(f"baseline_commit must be {BASELINE_COMMIT}")
        if self.amplitude_denominator != REQUIRED_AMPLITUDE_DENOMINATOR:
            raise ValueError("scientific audit requires amplitude_denominator=64")
        if tuple(self.amplitude_numerators) != REQUIRED_AMPLITUDE_NUMERATORS:
            raise ValueError(
                f"scientific audit requires amplitude numerators {REQUIRED_AMPLITUDE_NUMERATORS}"
            )
        if tuple(self.requested_oracle_budgets) != REQUIRED_REQUESTED_BUDGETS:
            raise ValueError(
                f"scientific audit requires requested budgets {REQUIRED_REQUESTED_BUDGETS}"
            )
        if self.desired_accuracy != 0.05:
            raise ValueError("scientific audit requires desired_accuracy=0.05")
        expected_values: tuple[tuple[str, Any, Any], ...] = (
            ("schema_version", self.schema_version, "1.0"),
            ("name", self.name, "scientific-audit"),
            ("confidence_level", self.confidence_level, 0.95),
            ("analytical_replicates", self.analytical_replicates, REQUIRED_MINIMUM_REPLICATES),
            ("mle_grid_points", self.mle_grid_points, REQUIRED_MLE_GRID_POINTS),
            ("base_seed", self.base_seed, REQUIRED_BASE_SEED),
            (
                "bootstrap_replicates",
                self.bootstrap_replicates,
                REQUIRED_BOOTSTRAP_REPLICATES,
            ),
            (
                "bootstrap_confidence_level",
                self.bootstrap_confidence_level,
                REQUIRED_BOOTSTRAP_CONFIDENCE_LEVEL,
            ),
            ("bootstrap_seed", self.bootstrap_seed, REQUIRED_BOOTSTRAP_SEED),
            ("runtime_order_seed", self.runtime_order_seed, REQUIRED_RUNTIME_ORDER_SEED),
            (
                "runtime_warmup_repeats",
                self.runtime_warmup_repeats,
                REQUIRED_RUNTIME_WARMUP_REPEATS,
            ),
            (
                "runtime_measured_repeats",
                self.runtime_measured_repeats,
                REQUIRED_RUNTIME_MEASURED_REPEATS,
            ),
            ("runtime_fail_fast", self.runtime_fail_fast, False),
            ("table_layout", self.table_layout, TABLE_LAYOUT),
            ("require_clean_worktree", self.require_clean_worktree, True),
        )
        for field_name, actual, expected in expected_values:
            if actual != expected:
                raise ValueError(
                    f"scientific audit requires {field_name}={expected!r}; got {actual!r}"
                )


@dataclass(frozen=True, slots=True)
class AuditDesign:
    requested_budget: int
    schedule: tuple[int, ...]
    shots_per_circuit: int
    logical_lookup_oracle_calls: int
    state_preparation_applications: int
    inverse_state_preparation_applications: int
    grover_iterations: int
    good_state_markings: int
    total_shots: int
    distinct_circuits: int
    sampler_jobs: int


@dataclass(frozen=True, slots=True)
class GridMlaeResult:
    estimate: float
    confidence_low: float
    confidence_high: float
    maximum_log_likelihood: float
    maximizing_grid_index: int
    maximizing_grid_ties: int


@dataclass(frozen=True, slots=True)
class AuditArtifacts:
    output_dir: Path
    analytical_jsonl: Path
    analytical_csv: Path
    analytical_summary_csv: Path
    exact_jsonl: Path
    exact_csv: Path
    exact_summary_csv: Path
    runtime_jsonl: Path
    runtime_csv: Path
    runtime_summary_csv: Path
    plots: tuple[Path, ...]
    manifest: Path


def audit_designs(config: AuditExperimentConfig) -> tuple[AuditDesign, ...]:
    """Resolve every requested cap through the production ``plan_budget`` function."""

    designs: list[AuditDesign] = []
    for requested in config.requested_oracle_budgets:
        budget = plan_budget(requested, config.desired_accuracy)
        designs.append(
            AuditDesign(
                requested_budget=requested,
                schedule=budget.schedule,
                shots_per_circuit=budget.shots_per_circuit,
                logical_lookup_oracle_calls=budget.logical_lookup_oracle_calls,
                state_preparation_applications=budget.state_preparation_applications,
                inverse_state_preparation_applications=(
                    budget.inverse_state_preparation_applications
                ),
                grover_iterations=budget.grover_iterations,
                good_state_markings=budget.good_state_markings,
                total_shots=budget.total_shots,
                distinct_circuits=budget.distinct_circuits,
                sampler_jobs=budget.sampler_jobs,
            )
        )
    return tuple(designs)


class FixedGridMlae:
    """Global finite-shot MLAE likelihood maximization on one fixed amplitude grid."""

    def __init__(self, grid_points: int) -> None:
        if grid_points < 3:
            raise ValueError("grid_points must be at least 3")
        self.amplitude_grid: NDArray[np.float64] = np.linspace(0.0, 1.0, grid_points)
        self._log_probability_cache: dict[
            tuple[int, ...], tuple[NDArray[np.float64], NDArray[np.float64]]
        ] = {}

    def _log_probabilities(
        self, schedule: tuple[int, ...]
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        cached = self._log_probability_cache.get(schedule)
        if cached is not None:
            return cached
        theta = np.arcsin(np.sqrt(self.amplitude_grid))
        powers = np.asarray([2 * power + 1 for power in schedule], dtype=np.float64)
        probabilities = np.sin(powers[:, np.newaxis] * theta[np.newaxis, :]) ** 2
        tiny = np.finfo(np.float64).tiny
        clipped = np.clip(probabilities, tiny, 1.0 - np.finfo(np.float64).eps)
        logs = (np.log(clipped), np.log1p(-clipped))
        self._log_probability_cache[schedule] = logs
        return logs

    def estimate(
        self,
        *,
        schedule: tuple[int, ...],
        shots_per_circuit: int,
        good_counts: Sequence[int],
        confidence_level: float,
    ) -> GridMlaeResult:
        if shots_per_circuit < 1:
            raise ValueError("shots_per_circuit must be positive")
        if len(good_counts) != len(schedule):
            raise ValueError("one good-state count is required per schedule circuit")
        if any(count < 0 or count > shots_per_circuit for count in good_counts):
            raise ValueError("good-state count lies outside [0, shots_per_circuit]")
        if not 0 < confidence_level < 1:
            raise ValueError("confidence_level must lie in (0, 1)")

        log_p, log_one_minus_p = self._log_probabilities(schedule)
        successes = np.asarray(good_counts, dtype=np.float64)
        failures = shots_per_circuit - successes
        log_likelihood = successes @ log_p + failures @ log_one_minus_p
        best_index = int(np.argmax(log_likelihood))
        maximum = float(log_likelihood[best_index])
        ties = int(np.count_nonzero(np.isclose(log_likelihood, maximum, rtol=0.0, atol=1e-12)))

        z_value = NormalDist().inv_cdf(0.5 + confidence_level / 2)
        likelihood_ratio_cutoff = maximum - 0.5 * z_value * z_value
        included = np.flatnonzero(log_likelihood >= likelihood_ratio_cutoff)
        return GridMlaeResult(
            estimate=float(self.amplitude_grid[best_index]),
            confidence_low=float(self.amplitude_grid[int(included[0])]),
            confidence_high=float(self.amplitude_grid[int(included[-1])]),
            maximum_log_likelihood=maximum,
            maximizing_grid_index=best_index,
            maximizing_grid_ties=ties,
        )


def qae_good_probabilities(amplitude: float, schedule: Sequence[int]) -> tuple[float, ...]:
    """Return ``sin^2((2k+1) theta)`` for ``theta=asin(sqrt(a))``."""

    if not 0 <= amplitude <= 1:
        raise ValueError("amplitude must lie in [0, 1]")
    theta = math.asin(math.sqrt(amplitude))
    return tuple(math.sin((2 * power + 1) * theta) ** 2 for power in schedule)


def contiguous_prefix_visibility_table(numerator: int, denominator: int = 64) -> list[int]:
    """Return the preregistered table: visible prefix, then blocked suffix."""

    if denominator < 1 or numerator < 0 or numerator > denominator:
        raise ValueError("table numerator must lie in [0, denominator]")
    return [1] * numerator + [0] * (denominator - numerator)


def visibility_table_sha256(table: Sequence[int]) -> str:
    if not table or any(value not in {0, 1} for value in table):
        raise ValueError("visibility table must be non-empty and binary")
    return hashlib.sha256(bytes(table)).hexdigest()


def _derived_seed(base_seed: int, *parts: object) -> int:
    payload = "|".join([str(base_seed), *(str(part) for part in parts)]).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % (2**32)


def _bernoulli_count(probability: float, samples: int, seed: int) -> int:
    rng = random.Random(seed)
    return sum(rng.random() < probability for _ in range(samples))


def _wilson_interval(successes: int, samples: int, level: float) -> tuple[float, float]:
    if samples < 1:
        raise ValueError("samples must be positive")
    z_value = NormalDist().inv_cdf(0.5 + level / 2)
    proportion = successes / samples
    denominator = 1 + z_value * z_value / samples
    center = (proportion + z_value * z_value / (2 * samples)) / denominator
    spread = (
        z_value
        * math.sqrt(
            proportion * (1 - proportion) / samples + z_value * z_value / (4 * samples * samples)
        )
        / denominator
    )
    return max(0.0, center - spread), min(1.0, center + spread)


def _base_analytical_record(
    *,
    config: AuditExperimentConfig,
    design: AuditDesign,
    numerator: int,
    replicate: int,
    method: str,
) -> dict[str, Any]:
    amplitude = numerator / config.amplitude_denominator
    table = contiguous_prefix_visibility_table(numerator, config.amplitude_denominator)
    case_seed = _derived_seed(
        config.base_seed,
        numerator,
        config.amplitude_denominator,
        design.requested_budget,
        replicate,
    )
    return {
        "schema_version": "1.0",
        "record_kind": "analytical_statistics",
        "analysis_model": ANALYTICAL_MODEL,
        "method": method,
        "amplitude_numerator": numerator,
        "amplitude_denominator": config.amplitude_denominator,
        "amplitude": amplitude,
        "table_layout": config.table_layout,
        "visibility_table_sha256": visibility_table_sha256(table),
        "requested_oracle_budget": design.requested_budget,
        "logical_lookup_oracle_calls": design.logical_lookup_oracle_calls,
        "oracle_domain_size": config.amplitude_denominator,
        "requested_budget_ge_domain_size": (
            design.requested_budget >= config.amplitude_denominator
        ),
        "realized_calls_ge_domain_size": (
            design.logical_lookup_oracle_calls >= config.amplitude_denominator
        ),
        "replicate": replicate,
        "case_seed": case_seed,
        "sampling_seed": _derived_seed(case_seed, method),
        "desired_accuracy": config.desired_accuracy,
        "requested_confidence_level": config.confidence_level,
        "status": "ok",
        "error": None,
    }


def simulate_analytical_records(
    config: AuditExperimentConfig,
    designs: Sequence[AuditDesign] | None = None,
) -> list[dict[str, Any]]:
    """Generate paired QAE/MC records without executing a statevector simulator."""

    selected_designs = tuple(designs) if designs is not None else audit_designs(config)
    estimator = FixedGridMlae(config.mle_grid_points)
    records: list[dict[str, Any]] = []
    for numerator in config.amplitude_numerators:
        amplitude = numerator / config.amplitude_denominator
        for design in selected_designs:
            probabilities = qae_good_probabilities(amplitude, design.schedule)
            for replicate in range(config.analytical_replicates):
                qae_record = _base_analytical_record(
                    config=config,
                    design=design,
                    numerator=numerator,
                    replicate=replicate,
                    method="analytical_mlae",
                )
                qae_seed = int(qae_record["sampling_seed"])
                try:
                    good_counts = [
                        _bernoulli_count(
                            probability,
                            design.shots_per_circuit,
                            _derived_seed(qae_seed, circuit_index),
                        )
                        for circuit_index, probability in enumerate(probabilities)
                    ]
                    result = estimator.estimate(
                        schedule=design.schedule,
                        shots_per_circuit=design.shots_per_circuit,
                        good_counts=good_counts,
                        confidence_level=config.confidence_level,
                    )
                    signed_error = result.estimate - amplitude
                    qae_record.update(
                        {
                            "evaluation_schedule": list(design.schedule),
                            "shots_per_circuit": design.shots_per_circuit,
                            "total_shots": design.total_shots,
                            "distinct_circuits": design.distinct_circuits,
                            "sampler_jobs": design.sampler_jobs,
                            "state_preparation_applications": (
                                design.state_preparation_applications
                            ),
                            "inverse_state_preparation_applications": (
                                design.inverse_state_preparation_applications
                            ),
                            "grover_iterations": design.grover_iterations,
                            "good_state_markings": design.good_state_markings,
                            "per_circuit_good_probabilities": list(probabilities),
                            "per_circuit_good_counts": good_counts,
                            "estimate": result.estimate,
                            "signed_error": signed_error,
                            "absolute_error": abs(signed_error),
                            "squared_error": signed_error * signed_error,
                            "confidence_interval_low": result.confidence_low,
                            "confidence_interval_high": result.confidence_high,
                            "confidence_interval_level": config.confidence_level,
                            "confidence_interval_method": (
                                "audit_fixed_grid_likelihood_ratio_envelope_not_qiskit_ci"
                            ),
                            "confidence_interval_covers_truth": (
                                result.confidence_low <= amplitude <= result.confidence_high
                            ),
                            "maximum_log_likelihood": result.maximum_log_likelihood,
                            "maximizing_grid_index": result.maximizing_grid_index,
                            "maximizing_grid_ties": result.maximizing_grid_ties,
                            "mle_grid_points": config.mle_grid_points,
                        }
                    )
                except Exception as exc:
                    qae_record.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
                records.append(qae_record)

                mc_record = _base_analytical_record(
                    config=config,
                    design=design,
                    numerator=numerator,
                    replicate=replicate,
                    method="classical_monte_carlo",
                )
                try:
                    mc_samples = design.logical_lookup_oracle_calls
                    successes = _bernoulli_count(
                        amplitude, mc_samples, int(mc_record["sampling_seed"])
                    )
                    estimate = successes / mc_samples
                    low, high = _wilson_interval(successes, mc_samples, config.confidence_level)
                    signed_error = estimate - amplitude
                    mc_record.update(
                        {
                            "evaluation_schedule": None,
                            "shots_per_circuit": None,
                            "total_shots": None,
                            "distinct_circuits": None,
                            "sampler_jobs": None,
                            "state_preparation_applications": None,
                            "inverse_state_preparation_applications": None,
                            "grover_iterations": None,
                            "good_state_markings": None,
                            "classical_samples": mc_samples,
                            "classical_successes": successes,
                            "sampling": "with_replacement",
                            "estimate": estimate,
                            "signed_error": signed_error,
                            "absolute_error": abs(signed_error),
                            "squared_error": signed_error * signed_error,
                            "confidence_interval_low": low,
                            "confidence_interval_high": high,
                            "confidence_interval_level": config.confidence_level,
                            "confidence_interval_method": "wilson_score",
                            "confidence_interval_covers_truth": low <= amplitude <= high,
                        }
                    )
                except Exception as exc:
                    mc_record.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
                records.append(mc_record)
    return records


def _validate_bootstrap_options(replicates: int, confidence_level: float) -> None:
    if replicates < 1:
        raise ValueError("bootstrap_replicates must be positive")
    if not 0 < confidence_level < 1:
        raise ValueError("bootstrap_confidence_level must lie in (0, 1)")


def _percentile_interval(
    values: NDArray[np.float64], confidence_level: float
) -> tuple[float | None, float | None]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return None, None
    tail = (1.0 - confidence_level) / 2.0
    quantiles = np.quantile(finite, [tail, 1.0 - tail])
    return float(quantiles[0]), float(quantiles[1])


def aggregate_analytical_records(
    records: Sequence[dict[str, Any]],
    *,
    bootstrap_replicates: int = REQUIRED_BOOTSTRAP_REPLICATES,
    bootstrap_confidence_level: float = REQUIRED_BOOTSTRAP_CONFIDENCE_LEVEL,
    bootstrap_seed: int = REQUIRED_BOOTSTRAP_SEED,
) -> list[dict[str, Any]]:
    """Compute statistics and paired full-range slope percentile intervals."""

    _validate_bootstrap_options(bootstrap_replicates, bootstrap_confidence_level)

    groups: dict[tuple[str, int, int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        key = (
            str(record["method"]),
            int(record["amplitude_numerator"]),
            int(record["amplitude_denominator"]),
            int(record["requested_oracle_budget"]),
            int(record["logical_lookup_oracle_calls"]),
        )
        groups[key].append(record)

    summary: list[dict[str, Any]] = []
    for key, candidates in sorted(groups.items()):
        method, numerator, denominator, requested, calls = key
        successful = [record for record in candidates if record.get("status") == "ok"]
        errors = [float(record["signed_error"]) for record in successful]
        estimates = [float(record["estimate"]) for record in successful]
        squared_errors = [float(record["squared_error"]) for record in successful]
        coverages = [bool(record["confidence_interval_covers_truth"]) for record in successful]
        widths = [
            float(record["confidence_interval_high"]) - float(record["confidence_interval_low"])
            for record in successful
        ]
        first = candidates[0]
        group_seed = _derived_seed(
            bootstrap_seed,
            "analytical-point",
            method,
            numerator,
            denominator,
            requested,
            calls,
        )
        if errors:
            error_values = np.asarray(errors, dtype=np.float64)
            bootstrap_rng = np.random.default_rng(group_seed)
            sampled_indices = bootstrap_rng.integers(
                0, len(errors), size=(bootstrap_replicates, len(errors))
            )
            sampled_errors = error_values[sampled_indices]
            bootstrap_bias = np.mean(sampled_errors, axis=1)
            bootstrap_rmse = np.sqrt(np.mean(np.square(sampled_errors), axis=1))
            if len(errors) >= 2:
                bootstrap_std = np.std(sampled_errors, axis=1, ddof=1)
            else:
                bootstrap_std = np.full(bootstrap_replicates, np.nan, dtype=np.float64)
            bias_low, bias_high = _percentile_interval(bootstrap_bias, bootstrap_confidence_level)
            rmse_low, rmse_high = _percentile_interval(bootstrap_rmse, bootstrap_confidence_level)
            std_low, std_high = _percentile_interval(bootstrap_std, bootstrap_confidence_level)
        else:
            bias_low = bias_high = None
            rmse_low = rmse_high = None
            std_low = std_high = None
        summary.append(
            {
                "schema_version": "1.0",
                "summary_kind": "analytical_statistics",
                "analysis_model": ANALYTICAL_MODEL,
                "method": method,
                "amplitude_numerator": numerator,
                "amplitude_denominator": denominator,
                "amplitude": numerator / denominator,
                "requested_oracle_budget": requested,
                "logical_lookup_oracle_calls": calls,
                "oracle_domain_size": first.get("oracle_domain_size"),
                "requested_budget_ge_domain_size": first.get("requested_budget_ge_domain_size"),
                "realized_calls_ge_domain_size": first.get("realized_calls_ge_domain_size"),
                "evaluation_schedule": first.get("evaluation_schedule"),
                "shots_per_circuit": first.get("shots_per_circuit"),
                "n": len(successful),
                "n_requested": len(candidates),
                "n_failed": len(candidates) - len(successful),
                "mean_estimate": statistics.fmean(estimates) if estimates else None,
                "bias": statistics.fmean(errors) if errors else None,
                "rmse": math.sqrt(statistics.fmean(squared_errors)) if squared_errors else None,
                "sample_std": statistics.stdev(estimates) if len(estimates) >= 2 else None,
                "mean_absolute_error": statistics.fmean(abs(error) for error in errors)
                if errors
                else None,
                "empirical_ci_coverage": statistics.fmean(coverages) if coverages else None,
                "mean_ci_width": statistics.fmean(widths) if widths else None,
                "confidence_level": first.get("requested_confidence_level"),
                "bootstrap_replicates": bootstrap_replicates,
                "bootstrap_confidence_level": bootstrap_confidence_level,
                "bootstrap_base_seed": bootstrap_seed,
                "bootstrap_group_seed": group_seed,
                "bias_bootstrap_ci_low": bias_low,
                "bias_bootstrap_ci_high": bias_high,
                "rmse_bootstrap_ci_low": rmse_low,
                "rmse_bootstrap_ci_high": rmse_high,
                "sample_std_bootstrap_ci_low": std_low,
                "sample_std_bootstrap_ci_high": std_high,
            }
        )

    slope_groups: dict[tuple[str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in summary:
        slope_groups[
            (
                str(row["method"]),
                int(row["amplitude_numerator"]),
                int(row["amplitude_denominator"]),
            )
        ].append(row)
    for slope_key, rows in slope_groups.items():
        method, numerator, denominator = slope_key
        ordered = sorted(rows, key=lambda item: int(item["logical_lookup_oracle_calls"]))
        full_range_is_usable = len(ordered) >= 2 and all(
            row["rmse"] is not None and float(row["rmse"]) > 0 for row in ordered
        )
        slope_bootstrap_seed = _derived_seed(
            bootstrap_seed, "analytical-full-range-slope", method, numerator, denominator
        )
        slope_bootstrap_low: float | None = None
        slope_bootstrap_high: float | None = None
        slope_bootstrap_valid = 0
        joint_replicates: list[int] = []
        if full_range_is_usable:
            x_values = np.log(
                np.asarray([row["logical_lookup_oracle_calls"] for row in ordered], dtype=float)
            )
            y_values = np.log(np.asarray([row["rmse"] for row in ordered], dtype=float))
            slope = float(np.polyfit(x_values, y_values, 1)[0])
            slope_status = "all_preregistered_budget_points_positive_rmse"
            slope_min = int(ordered[0]["logical_lookup_oracle_calls"])
            slope_max = int(ordered[-1]["logical_lookup_oracle_calls"])

            successful_by_budget: list[dict[int, dict[str, Any]]] = []
            for row in ordered:
                raw_key = (
                    method,
                    numerator,
                    denominator,
                    int(row["requested_oracle_budget"]),
                    int(row["logical_lookup_oracle_calls"]),
                )
                successful_by_budget.append(
                    {
                        int(record["replicate"]): record
                        for record in groups[raw_key]
                        if record.get("status") == "ok"
                    }
                )
            if successful_by_budget:
                joint_ids = set(successful_by_budget[0])
                for by_replicate in successful_by_budget[1:]:
                    joint_ids.intersection_update(by_replicate)
                joint_replicates = sorted(joint_ids)
            if joint_replicates:
                squared_error_matrix = np.asarray(
                    [
                        [
                            float(by_replicate[replicate]["squared_error"])
                            for replicate in joint_replicates
                        ]
                        for by_replicate in successful_by_budget
                    ],
                    dtype=np.float64,
                )
                slope_rng = np.random.default_rng(slope_bootstrap_seed)
                sampled_indices = slope_rng.integers(
                    0,
                    len(joint_replicates),
                    size=(bootstrap_replicates, len(joint_replicates)),
                )
                bootstrap_rmse = np.sqrt(
                    np.mean(squared_error_matrix[:, sampled_indices], axis=2)
                ).T
                valid_mask = np.all(bootstrap_rmse > 0, axis=1)
                if np.any(valid_mask):
                    centered_x = x_values - np.mean(x_values)
                    bootstrap_slopes = (np.log(bootstrap_rmse[valid_mask]) @ centered_x) / float(
                        centered_x @ centered_x
                    )
                    slope_bootstrap_low, slope_bootstrap_high = _percentile_interval(
                        bootstrap_slopes, bootstrap_confidence_level
                    )
                    slope_bootstrap_valid = int(bootstrap_slopes.size)
        else:
            slope = None
            slope_status = "undefined_full_range_contains_nonpositive_or_missing_rmse"
            slope_min = None
            slope_max = None
        for row in rows:
            row.update(
                {
                    "full_range_loglog_rmse_slope": slope,
                    "slope_status": slope_status,
                    "slope_point_count": len(ordered) if full_range_is_usable else 0,
                    "slope_min_logical_lookup_oracle_calls": slope_min,
                    "slope_max_logical_lookup_oracle_calls": slope_max,
                    "full_range_loglog_rmse_slope_bootstrap_ci_low": slope_bootstrap_low,
                    "full_range_loglog_rmse_slope_bootstrap_ci_high": slope_bootstrap_high,
                    "slope_bootstrap_valid_resamples": slope_bootstrap_valid,
                    "slope_bootstrap_joint_replicates": len(joint_replicates),
                    "slope_bootstrap_seed": slope_bootstrap_seed,
                }
            )
    return summary


def exact_statistical_control(config: AuditExperimentConfig) -> list[dict[str, Any]]:
    """Return the deterministic finite-domain control at exactly 64 table reads."""

    return [
        {
            "schema_version": "1.0",
            "summary_kind": "exact_finite_domain_control",
            "analysis_model": "deterministic exact enumeration of the supplied 64-entry table",
            "method": "exact_enumeration",
            "amplitude_numerator": numerator,
            "amplitude_denominator": config.amplitude_denominator,
            "amplitude": numerator / config.amplitude_denominator,
            "table_layout": config.table_layout,
            "visibility_table_sha256": visibility_table_sha256(
                contiguous_prefix_visibility_table(numerator, config.amplitude_denominator)
            ),
            "requested_oracle_budget": None,
            "logical_lookup_oracle_calls": EXACT_ENUMERATION_CALLS,
            "oracle_domain_size": config.amplitude_denominator,
            "requested_budget_ge_domain_size": None,
            "realized_calls_ge_domain_size": True,
            "evaluation_schedule": None,
            "shots_per_circuit": None,
            "n": 1,
            "n_requested": 1,
            "n_failed": 0,
            "mean_estimate": numerator / config.amplitude_denominator,
            "bias": 0.0,
            "rmse": 0.0,
            "sample_std": 0.0,
            "mean_absolute_error": 0.0,
            "empirical_ci_coverage": 1.0,
            "mean_ci_width": 0.0,
            "confidence_level": None,
            "bootstrap_replicates": config.bootstrap_replicates,
            "bootstrap_confidence_level": config.bootstrap_confidence_level,
            "bootstrap_base_seed": config.bootstrap_seed,
            "bootstrap_group_seed": None,
            "bias_bootstrap_ci_low": 0.0,
            "bias_bootstrap_ci_high": 0.0,
            "rmse_bootstrap_ci_low": 0.0,
            "rmse_bootstrap_ci_high": 0.0,
            "sample_std_bootstrap_ci_low": 0.0,
            "sample_std_bootstrap_ci_high": 0.0,
            "full_range_loglog_rmse_slope": None,
            "full_range_loglog_rmse_slope_bootstrap_ci_low": None,
            "full_range_loglog_rmse_slope_bootstrap_ci_high": None,
            "slope_status": "not_applicable_deterministic_exact_control",
            "slope_point_count": 0,
            "slope_min_logical_lookup_oracle_calls": None,
            "slope_max_logical_lookup_oracle_calls": None,
            "slope_bootstrap_valid_resamples": 0,
            "slope_bootstrap_joint_replicates": 0,
            "slope_bootstrap_seed": None,
        }
        for numerator in config.amplitude_numerators
    ]


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return value


def write_jsonl_csv(records: Sequence[dict[str, Any]], jsonl_path: Path, csv_path: Path) -> None:
    """Write the same raw records losslessly as JSONL and flatten containers for CSV."""

    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    write_csv(records, csv_path)


def write_csv(records: Sequence[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for record in records:
        fieldnames.extend(key for key in record if key not in fieldnames)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(
            {key: _csv_value(value) for key, value in record.items()} for record in records
        )


def _transpiled_resource_metrics(
    algorithm: MaximumLikelihoodAmplitudeEstimation,
    problem: Any,
    design: AuditDesign,
    seed: int,
) -> dict[str, Any]:
    """Transpile analysis copies and report explicitly defined quantum-gate metrics."""

    circuits = algorithm.construct_circuits(problem, measurement=True)
    transpiled = cast(
        list[QuantumCircuit],
        transpile(
            circuits,
            basis_gates=["u", "cx"],
            optimization_level=0,
            seed_transpiler=seed,
        ),
    )
    excluded = {"barrier", "measure"}
    details: list[dict[str, Any]] = []
    for power, circuit in zip(design.schedule, transpiled, strict=True):
        operation_counts = {str(name): int(count) for name, count in circuit.count_ops().items()}
        gate_count = sum(count for name, count in operation_counts.items() if name not in excluded)
        depth = circuit.depth(
            filter_function=lambda instruction: instruction.operation.name not in excluded
        )
        details.append(
            {
                "grover_power": power,
                "qubits": circuit.num_qubits,
                "max_transpiled_quantum_depth": int(depth),
                "transpiled_quantum_gate_count": gate_count,
                "operation_counts_including_non_gates": operation_counts,
            }
        )
    schedule_gate_count = sum(int(detail["transpiled_quantum_gate_count"]) for detail in details)
    return {
        "max_transpiled_quantum_depth": max(
            int(detail["max_transpiled_quantum_depth"]) for detail in details
        ),
        "max_transpiled_quantum_gate_count": max(
            int(detail["transpiled_quantum_gate_count"]) for detail in details
        ),
        "schedule_transpiled_quantum_gate_count": schedule_gate_count,
        "shot_weighted_transpiled_quantum_gate_count": (
            design.shots_per_circuit * schedule_gate_count
        ),
        "per_circuit_transpiled_metrics": details,
        "transpilation_basis_gates": ["u", "cx"],
        "transpilation_optimization_level": 0,
    }


def _runtime_record_base(
    *,
    config: AuditExperimentConfig,
    design: AuditDesign,
    numerator: int,
    repeat: int,
    warmup: bool,
    method: str,
) -> dict[str, Any]:
    table = contiguous_prefix_visibility_table(numerator, config.amplitude_denominator)
    return {
        "schema_version": "1.0",
        "record_kind": "actual_runtime_and_circuit_metrics",
        "method": method,
        "execution_model": (
            QISKIT_RUNTIME_MODEL if method == "qiskit_statevector_mlae" else "Python table MC"
        ),
        "amplitude_numerator": numerator,
        "amplitude_denominator": config.amplitude_denominator,
        "amplitude": numerator / config.amplitude_denominator,
        "table_layout": config.table_layout,
        "visibility_table_sha256": visibility_table_sha256(table),
        "requested_oracle_budget": design.requested_budget,
        "logical_lookup_oracle_calls": design.logical_lookup_oracle_calls,
        "oracle_domain_size": config.amplitude_denominator,
        "requested_budget_ge_domain_size": (
            design.requested_budget >= config.amplitude_denominator
        ),
        "realized_calls_ge_domain_size": (
            design.logical_lookup_oracle_calls >= config.amplitude_denominator
        ),
        "evaluation_schedule": list(design.schedule)
        if method == "qiskit_statevector_mlae"
        else None,
        "shots_per_circuit": design.shots_per_circuit
        if method == "qiskit_statevector_mlae"
        else None,
        "total_shots": design.total_shots if method == "qiskit_statevector_mlae" else None,
        "repeat": repeat,
        "warmup": warmup,
        "sampling_seed": _derived_seed(
            config.base_seed,
            "runtime",
            method,
            numerator,
            design.requested_budget,
            repeat,
            warmup,
        ),
        "status": "ok",
        "error": None,
    }


def _run_qiskit_runtime_record(
    *,
    config: AuditExperimentConfig,
    design: AuditDesign,
    numerator: int,
    repeat: int,
    warmup: bool,
) -> dict[str, Any]:
    record = _runtime_record_base(
        config=config,
        design=design,
        numerator=numerator,
        repeat=repeat,
        warmup=warmup,
        method="qiskit_statevector_mlae",
    )
    amplitude = numerator / config.amplitude_denominator
    table = contiguous_prefix_visibility_table(numerator, config.amplitude_denominator)
    started = perf_counter_ns()
    try:
        synthesis_started = perf_counter_ns()
        problem = build_estimation_problem(table)
        synthesis_completed = perf_counter_ns()

        setup_started = perf_counter_ns()
        sampler = StatevectorSampler(
            default_shots=design.shots_per_circuit,
            seed=int(record["sampling_seed"]),
        )
        algorithm = MaximumLikelihoodAmplitudeEstimation(
            evaluation_schedule=list(design.schedule), sampler=sampler
        )
        setup_completed = perf_counter_ns()

        transpilation_started = perf_counter_ns()
        metrics = _transpiled_resource_metrics(
            algorithm, problem, design, int(record["sampling_seed"])
        )
        transpilation_completed = perf_counter_ns()

        estimator_started = perf_counter_ns()
        algorithm_result = algorithm.estimate(problem)
        estimator_completed = perf_counter_ns()

        interval_started = perf_counter_ns()
        confidence = algorithm.compute_confidence_interval(
            algorithm_result,
            alpha=1 - config.confidence_level,
            kind="likelihood_ratio",
        )
        interval_completed = perf_counter_ns()
        estimate = float(algorithm_result.estimation)
        signed_error = estimate - amplitude
        record.update(
            {
                "estimate": estimate,
                "signed_error": signed_error,
                "absolute_error": abs(signed_error),
                "confidence_interval_low": max(0.0, float(confidence[0])),
                "confidence_interval_high": min(1.0, float(confidence[1])),
                "confidence_interval_level": config.confidence_level,
                "confidence_interval_method": "qiskit_mlae_likelihood_ratio",
                "state_preparation_applications": design.state_preparation_applications,
                "inverse_state_preparation_applications": (
                    design.inverse_state_preparation_applications
                ),
                "grover_iterations": design.grover_iterations,
                "good_state_markings": design.good_state_markings,
                "distinct_circuits": design.distinct_circuits,
                "sampler_jobs": design.sampler_jobs,
                "oracle_synthesis_ms": (synthesis_completed - synthesis_started) / 1e6,
                "sampler_algorithm_setup_ms": (setup_completed - setup_started) / 1e6,
                "analysis_copy_transpilation_ms": (transpilation_completed - transpilation_started)
                / 1e6,
                "estimator_runtime_ms": (estimator_completed - estimator_started) / 1e6,
                "confidence_interval_postprocessing_ms": (interval_completed - interval_started)
                / 1e6,
                "audit_end_to_end_ms": (interval_completed - started) / 1e6,
                **metrics,
            }
        )
    except Exception as exc:
        record.update(
            {
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
                "audit_end_to_end_ms": (perf_counter_ns() - started) / 1e6,
            }
        )
        if config.runtime_fail_fast:
            raise
    return record


def _run_classical_runtime_record(
    *,
    config: AuditExperimentConfig,
    design: AuditDesign,
    numerator: int,
    repeat: int,
    warmup: bool,
) -> dict[str, Any]:
    record = _runtime_record_base(
        config=config,
        design=design,
        numerator=numerator,
        repeat=repeat,
        warmup=warmup,
        method="classical_monte_carlo",
    )
    table = contiguous_prefix_visibility_table(numerator, config.amplitude_denominator)
    amplitude = numerator / config.amplitude_denominator
    started = perf_counter_ns()
    try:
        rng = random.Random(int(record["sampling_seed"]))
        successes = sum(
            table[rng.randrange(len(table))] for _ in range(design.logical_lookup_oracle_calls)
        )
        estimate = successes / design.logical_lookup_oracle_calls
        sampling_completed = perf_counter_ns()
        interval_started = perf_counter_ns()
        low, high = _wilson_interval(
            successes, design.logical_lookup_oracle_calls, config.confidence_level
        )
        completed = perf_counter_ns()
        signed_error = estimate - amplitude
        record.update(
            {
                "classical_samples": design.logical_lookup_oracle_calls,
                "classical_successes": successes,
                "sampling": "with_replacement",
                "estimate": estimate,
                "signed_error": signed_error,
                "absolute_error": abs(signed_error),
                "confidence_interval_low": low,
                "confidence_interval_high": high,
                "confidence_interval_level": config.confidence_level,
                "confidence_interval_method": "wilson_score",
                "estimator_runtime_ms": (sampling_completed - started) / 1e6,
                "confidence_interval_postprocessing_ms": (completed - interval_started) / 1e6,
                "audit_end_to_end_ms": (completed - started) / 1e6,
            }
        )
    except Exception as exc:
        record.update(
            {
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
                "audit_end_to_end_ms": (perf_counter_ns() - started) / 1e6,
            }
        )
        if config.runtime_fail_fast:
            raise
    return record


def _run_exact_runtime_record(
    *,
    config: AuditExperimentConfig,
    numerator: int,
    repeat: int,
    warmup: bool,
) -> dict[str, Any]:
    amplitude = numerator / config.amplitude_denominator
    table = contiguous_prefix_visibility_table(numerator, config.amplitude_denominator)
    record: dict[str, Any] = {
        "schema_version": "1.0",
        "record_kind": "exact_finite_domain_control",
        "method": "exact_enumeration",
        "execution_model": "Python sum over the supplied 64-entry deterministic table",
        "amplitude_numerator": numerator,
        "amplitude_denominator": config.amplitude_denominator,
        "amplitude": amplitude,
        "table_layout": config.table_layout,
        "visibility_table_sha256": visibility_table_sha256(table),
        "requested_oracle_budget": None,
        "logical_lookup_oracle_calls": EXACT_ENUMERATION_CALLS,
        "oracle_domain_size": config.amplitude_denominator,
        "requested_budget_ge_domain_size": None,
        "realized_calls_ge_domain_size": True,
        "repeat": repeat,
        "warmup": warmup,
        "status": "ok",
        "error": None,
    }
    started = perf_counter_ns()
    try:
        estimate = sum(table) / len(table)
        completed = perf_counter_ns()
        signed_error = estimate - amplitude
        record.update(
            {
                "estimate": estimate,
                "signed_error": signed_error,
                "absolute_error": abs(signed_error),
                "confidence_interval_low": estimate,
                "confidence_interval_high": estimate,
                "confidence_interval_level": None,
                "confidence_interval_method": "degenerate_exact_enumeration",
                "confidence_interval_covers_truth": estimate == amplitude,
                "estimator_runtime_ms": (completed - started) / 1e6,
                "audit_end_to_end_ms": (completed - started) / 1e6,
            }
        )
    except Exception as exc:
        record.update(
            {
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
                "audit_end_to_end_ms": (perf_counter_ns() - started) / 1e6,
            }
        )
        if config.runtime_fail_fast:
            raise
    return record


def run_exact_control_records(config: AuditExperimentConfig) -> list[dict[str, Any]]:
    """Measure marked warmup and exact-enumeration repetitions once per amplitude."""

    records: list[dict[str, Any]] = []
    tasks: list[tuple[bool, int, int]] = []
    for warmup, count in (
        (True, config.runtime_warmup_repeats),
        (False, config.runtime_measured_repeats),
    ):
        phase_tasks = [
            (warmup, numerator, ordinal - count if warmup else ordinal)
            for numerator in config.amplitude_numerators
            for ordinal in range(count)
        ]
        random.Random(
            _derived_seed(config.runtime_order_seed, "exact-runtime-order", warmup)
        ).shuffle(phase_tasks)
        tasks.extend(phase_tasks)
    for execution_sequence, (warmup, numerator, repeat) in enumerate(tasks):
        record = _run_exact_runtime_record(
            config=config,
            numerator=numerator,
            repeat=repeat,
            warmup=warmup,
        )
        record.update(
            {
                "runtime_execution_sequence": execution_sequence,
                "runtime_order_seed": config.runtime_order_seed,
                "runtime_order_phase": "warmup" if warmup else "measured",
                "runtime_order_scope": "exact_control_deterministic_phase_shuffle",
            }
        )
        records.append(record)
    return records


def combine_exact_control_summary(
    statistical_rows: Sequence[dict[str, Any]],
    runtime_rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Combine deterministic zero-error fields with measured enumeration timing."""

    runtime_by_amplitude = {
        (int(row["amplitude_numerator"]), int(row["amplitude_denominator"])): row
        for row in runtime_rows
    }
    combined: list[dict[str, Any]] = []
    for statistical in statistical_rows:
        key = (
            int(statistical["amplitude_numerator"]),
            int(statistical["amplitude_denominator"]),
        )
        runtime = runtime_by_amplitude[key]
        row = dict(statistical)
        row.update(
            {
                "runtime_n": runtime["n"],
                "runtime_n_requested": runtime["n_requested"],
                "runtime_n_failed": runtime["n_failed"],
                "runtime_failure_messages": runtime["failure_messages"],
                "runtime_warmup_records_excluded": runtime["warmup_records_excluded"],
                "mean_estimator_runtime_ms": runtime["mean_estimator_runtime_ms"],
                "median_estimator_runtime_ms": runtime["median_estimator_runtime_ms"],
                "median_estimator_runtime_ms_bootstrap_ci_low": runtime[
                    "median_estimator_runtime_ms_bootstrap_ci_low"
                ],
                "median_estimator_runtime_ms_bootstrap_ci_high": runtime[
                    "median_estimator_runtime_ms_bootstrap_ci_high"
                ],
                "sample_std_estimator_runtime_ms": runtime["sample_std_estimator_runtime_ms"],
                "min_estimator_runtime_ms": runtime["min_estimator_runtime_ms"],
                "max_estimator_runtime_ms": runtime["max_estimator_runtime_ms"],
                "mean_audit_end_to_end_ms": runtime["mean_audit_end_to_end_ms"],
                "median_audit_end_to_end_ms": runtime["median_audit_end_to_end_ms"],
                "median_audit_end_to_end_ms_bootstrap_ci_low": runtime[
                    "median_audit_end_to_end_ms_bootstrap_ci_low"
                ],
                "median_audit_end_to_end_ms_bootstrap_ci_high": runtime[
                    "median_audit_end_to_end_ms_bootstrap_ci_high"
                ],
                "sample_std_audit_end_to_end_ms": runtime["sample_std_audit_end_to_end_ms"],
                "min_audit_end_to_end_ms": runtime["min_audit_end_to_end_ms"],
                "max_audit_end_to_end_ms": runtime["max_audit_end_to_end_ms"],
                "median_oracle_synthesis_ms": runtime["median_oracle_synthesis_ms"],
                "median_sampler_algorithm_setup_ms": runtime["median_sampler_algorithm_setup_ms"],
                "median_analysis_copy_transpilation_ms": runtime[
                    "median_analysis_copy_transpilation_ms"
                ],
                "median_confidence_interval_postprocessing_ms": runtime[
                    "median_confidence_interval_postprocessing_ms"
                ],
            }
        )
        combined.append(row)
    return combined


def balanced_runtime_execution_plan(
    config: AuditExperimentConfig,
    designs: Sequence[AuditDesign] | None = None,
) -> list[dict[str, Any]]:
    """Return a deterministic paired plan balanced within warmup/measured phases."""

    selected_designs = tuple(designs) if designs is not None else audit_designs(config)
    plan: list[dict[str, Any]] = []
    execution_sequence = 0
    for phase, warmup, repeat_count in (
        ("warmup", True, config.runtime_warmup_repeats),
        ("measured", False, config.runtime_measured_repeats),
    ):
        pair_units = [
            (numerator, design_index, repeat - repeat_count if warmup else repeat)
            for numerator in config.amplitude_numerators
            for design_index in range(len(selected_designs))
            for repeat in range(repeat_count)
        ]
        phase_seed = _derived_seed(config.runtime_order_seed, "paired-runtime-order", phase)
        random.Random(phase_seed).shuffle(pair_units)
        starting_method_offset = _derived_seed(phase_seed, "starting-method") % 2
        for phase_pair_sequence, (numerator, design_index, repeat) in enumerate(pair_units):
            classical_first = (phase_pair_sequence + starting_method_offset) % 2 == 0
            methods = (
                ("classical_monte_carlo", "qiskit_statevector_mlae")
                if classical_first
                else ("qiskit_statevector_mlae", "classical_monte_carlo")
            )
            pair_order = "mc_then_qiskit" if classical_first else "qiskit_then_mc"
            pair_id = f"{phase}-{phase_pair_sequence:04d}"
            for within_pair_position, method in enumerate(methods):
                plan.append(
                    {
                        "runtime_execution_sequence": execution_sequence,
                        "runtime_phase_pair_sequence": phase_pair_sequence,
                        "runtime_pair_id": pair_id,
                        "runtime_within_pair_position": within_pair_position,
                        "runtime_paired_method_order": pair_order,
                        "runtime_order_seed": config.runtime_order_seed,
                        "runtime_order_phase_seed": phase_seed,
                        "runtime_order_phase": phase,
                        "method": method,
                        "amplitude_numerator": numerator,
                        "design_index": design_index,
                        "repeat": repeat,
                        "warmup": warmup,
                    }
                )
                execution_sequence += 1
    return plan


def run_actual_runtime_records(
    config: AuditExperimentConfig,
    designs: Sequence[AuditDesign] | None = None,
) -> list[dict[str, Any]]:
    """Execute the deterministic balanced runtime plan and archive its order."""

    selected_designs = tuple(designs) if designs is not None else audit_designs(config)
    records: list[dict[str, Any]] = []
    for task in balanced_runtime_execution_plan(config, selected_designs):
        method = str(task["method"])
        runner = (
            _run_classical_runtime_record
            if method == "classical_monte_carlo"
            else _run_qiskit_runtime_record
        )
        record = runner(
            config=config,
            design=selected_designs[int(task["design_index"])],
            numerator=int(task["amplitude_numerator"]),
            repeat=int(task["repeat"]),
            warmup=bool(task["warmup"]),
        )
        record.update(
            {
                key: value
                for key, value in task.items()
                if key not in {"method", "amplitude_numerator", "design_index", "repeat", "warmup"}
            }
        )
        records.append(record)
    return records


def aggregate_runtime_records(
    records: Sequence[dict[str, Any]],
    *,
    bootstrap_replicates: int = REQUIRED_BOOTSTRAP_REPLICATES,
    bootstrap_confidence_level: float = REQUIRED_BOOTSTRAP_CONFIDENCE_LEVEL,
    bootstrap_seed: int = REQUIRED_BOOTSTRAP_SEED,
) -> list[dict[str, Any]]:
    """Summarize successful measured runs and retain explicit failure counts."""

    _validate_bootstrap_options(bootstrap_replicates, bootstrap_confidence_level)
    groups: dict[tuple[str, int, int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        requested_value = record.get("requested_oracle_budget")
        key = (
            str(record["method"]),
            int(record["amplitude_numerator"]),
            int(record["amplitude_denominator"]),
            -1 if requested_value is None else int(requested_value),
            int(record["logical_lookup_oracle_calls"]),
        )
        groups[key].append(record)

    summary: list[dict[str, Any]] = []
    for key, candidates in sorted(groups.items()):
        method, numerator, denominator, requested, calls = key
        measured = [
            record
            for record in candidates
            if not bool(record.get("warmup")) and record.get("status") == "ok"
        ]
        failed_measured = [
            record
            for record in candidates
            if not bool(record.get("warmup")) and record.get("status") != "ok"
        ]
        runtimes = [float(record["estimator_runtime_ms"]) for record in measured]
        end_to_end = [float(record["audit_end_to_end_ms"]) for record in measured]
        first = measured[0] if measured else candidates[0]
        group_seed = _derived_seed(
            bootstrap_seed,
            "runtime-medians",
            method,
            numerator,
            denominator,
            requested,
            calls,
        )
        if measured:
            sampled_indices = np.random.default_rng(group_seed).integers(
                0, len(measured), size=(bootstrap_replicates, len(measured))
            )
            bootstrap_estimator_medians = np.median(
                np.asarray(runtimes, dtype=np.float64)[sampled_indices], axis=1
            )
            bootstrap_end_to_end_medians = np.median(
                np.asarray(end_to_end, dtype=np.float64)[sampled_indices], axis=1
            )
            estimator_low, estimator_high = _percentile_interval(
                bootstrap_estimator_medians, bootstrap_confidence_level
            )
            end_to_end_low, end_to_end_high = _percentile_interval(
                bootstrap_end_to_end_medians, bootstrap_confidence_level
            )
        else:
            estimator_low = estimator_high = None
            end_to_end_low = end_to_end_high = None
        measured_requested = sum(not bool(record.get("warmup")) for record in candidates)
        phase_medians = {
            f"median_{phase_key}": (
                statistics.median(
                    float(record[phase_key])
                    for record in measured
                    if record.get(phase_key) is not None
                )
                if any(record.get(phase_key) is not None for record in measured)
                else None
            )
            for phase_key in (
                "oracle_synthesis_ms",
                "sampler_algorithm_setup_ms",
                "analysis_copy_transpilation_ms",
                "confidence_interval_postprocessing_ms",
            )
        }
        summary.append(
            {
                "schema_version": "1.0",
                "summary_kind": "actual_runtime_and_circuit_metrics",
                "method": method,
                "execution_model": first["execution_model"],
                "amplitude_numerator": numerator,
                "amplitude_denominator": denominator,
                "amplitude": numerator / denominator,
                "requested_oracle_budget": None if requested == -1 else requested,
                "logical_lookup_oracle_calls": calls,
                "oracle_domain_size": first.get("oracle_domain_size"),
                "requested_budget_ge_domain_size": first.get("requested_budget_ge_domain_size"),
                "realized_calls_ge_domain_size": first.get("realized_calls_ge_domain_size"),
                "n": len(measured),
                "n_requested": measured_requested,
                "n_failed": len(failed_measured),
                "failure_messages": sorted(
                    {str(record.get("error")) for record in failed_measured if record.get("error")}
                ),
                "warmup_records_excluded": sum(bool(record.get("warmup")) for record in candidates),
                "mean_estimator_runtime_ms": statistics.fmean(runtimes) if runtimes else None,
                "median_estimator_runtime_ms": statistics.median(runtimes) if runtimes else None,
                "median_estimator_runtime_ms_bootstrap_ci_low": estimator_low,
                "median_estimator_runtime_ms_bootstrap_ci_high": estimator_high,
                "sample_std_estimator_runtime_ms": statistics.stdev(runtimes)
                if len(runtimes) >= 2
                else None,
                "min_estimator_runtime_ms": min(runtimes) if runtimes else None,
                "max_estimator_runtime_ms": max(runtimes) if runtimes else None,
                "mean_audit_end_to_end_ms": statistics.fmean(end_to_end) if end_to_end else None,
                "median_audit_end_to_end_ms": statistics.median(end_to_end) if end_to_end else None,
                "median_audit_end_to_end_ms_bootstrap_ci_low": end_to_end_low,
                "median_audit_end_to_end_ms_bootstrap_ci_high": end_to_end_high,
                "sample_std_audit_end_to_end_ms": statistics.stdev(end_to_end)
                if len(end_to_end) >= 2
                else None,
                "min_audit_end_to_end_ms": min(end_to_end) if end_to_end else None,
                "max_audit_end_to_end_ms": max(end_to_end) if end_to_end else None,
                **phase_medians,
                "bootstrap_replicates": bootstrap_replicates,
                "bootstrap_confidence_level": bootstrap_confidence_level,
                "bootstrap_base_seed": bootstrap_seed,
                "bootstrap_group_seed": group_seed,
                "max_transpiled_quantum_depth": first.get("max_transpiled_quantum_depth"),
                "max_transpiled_quantum_gate_count": first.get("max_transpiled_quantum_gate_count"),
                "schedule_transpiled_quantum_gate_count": first.get(
                    "schedule_transpiled_quantum_gate_count"
                ),
                "shot_weighted_transpiled_quantum_gate_count": first.get(
                    "shot_weighted_transpiled_quantum_gate_count"
                ),
            }
        )
    return summary


def _amplitude_label(numerator: int, denominator: int) -> str:
    divisor = math.gcd(numerator, denominator)
    if numerator == 0:
        return "a=0"
    if numerator == denominator:
        return "a=1"
    return f"a={numerator // divisor}/{denominator // divisor}"


def _save_figure(fig: Any, output_dir: Path, name: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    png = output_dir / f"{name}.png"
    pdf = output_dir / f"{name}.pdf"
    fig.tight_layout()
    fig.savefig(png, dpi=180)
    fig.savefig(pdf)
    plt.close(fig)
    return png, pdf


def _amplitude_colors(rows: Sequence[dict[str, Any]]) -> dict[tuple[int, int], Any]:
    amplitudes = sorted(
        {(int(row["amplitude_numerator"]), int(row["amplitude_denominator"])) for row in rows},
        key=lambda item: item[0] / item[1],
    )
    colormap = plt.get_cmap("viridis")
    denominator = max(1, len(amplitudes) - 1)
    return {amplitude: colormap(index / denominator) for index, amplitude in enumerate(amplitudes)}


def _two_method_plot(
    rows: Sequence[dict[str, Any]],
    *,
    methods: Sequence[tuple[str, str]],
    y_key: str,
    ylabel: str,
    y_scale: Literal["log", "symlog", "linear"],
) -> Any:
    fig, axes_value = plt.subplots(
        1, len(methods), figsize=(5.1 * len(methods), 4.8), squeeze=False
    )
    axes = axes_value[0]
    colors = _amplitude_colors(rows)
    interval_keys = {
        "bias": ("bias_bootstrap_ci_low", "bias_bootstrap_ci_high"),
        "rmse": ("rmse_bootstrap_ci_low", "rmse_bootstrap_ci_high"),
        "sample_std": (
            "sample_std_bootstrap_ci_low",
            "sample_std_bootstrap_ci_high",
        ),
        "median_audit_end_to_end_ms": (
            "median_audit_end_to_end_ms_bootstrap_ci_low",
            "median_audit_end_to_end_ms_bootstrap_ci_high",
        ),
    }
    for axis, (method, title) in zip(axes, methods, strict=True):
        selected = [row for row in rows if row.get("method") == method]
        for amplitude, color in colors.items():
            numerator, denominator = amplitude
            amplitude_rows = sorted(
                (
                    row
                    for row in selected
                    if int(row["amplitude_numerator"]) == numerator
                    and int(row["amplitude_denominator"]) == denominator
                    and row.get(y_key) is not None
                ),
                key=lambda row: int(row["logical_lookup_oracle_calls"]),
            )
            points = [
                (int(row["logical_lookup_oracle_calls"]), float(row[y_key]))
                for row in amplitude_rows
            ]
            if points:
                x_values = [point[0] for point in points]
                axis.plot(
                    x_values,
                    [point[1] for point in points],
                    marker="o",
                    color=color,
                    label=_amplitude_label(numerator, denominator),
                )
                interval = interval_keys.get(y_key)
                if interval is not None and all(
                    row.get(interval[0]) is not None and row.get(interval[1]) is not None
                    for row in amplitude_rows
                ):
                    axis.fill_between(
                        x_values,
                        [float(row[interval[0]]) for row in amplitude_rows],
                        [float(row[interval[1]]) for row in amplitude_rows],
                        color=color,
                        alpha=0.16,
                        linewidth=0,
                    )
        axis.set_title(title)
        axis.set_xscale("log", base=2)
        if y_scale == "symlog":
            axis.set_yscale("symlog", linthresh=1e-5)
        elif y_scale == "log":
            axis.set_yscale("log")
        axis.set_xlabel("Executed logical $U_f/U_f^{-1}$ calls")
        axis.set_ylabel(ylabel)
        axis.grid(alpha=0.25, which="both")
        axis.legend(fontsize="small", ncol=2)
        failed = sum(int(row.get("n_failed", 0)) for row in selected)
        requested = sum(
            int(row.get("n_requested", int(row.get("n", 0)) + int(row.get("n_failed", 0))))
            for row in selected
        )
        axis.text(
            0.02,
            0.98,
            f"failed measured runs: {failed}/{requested}",
            transform=axis.transAxes,
            ha="left",
            va="top",
            fontsize="x-small",
        )
        if method == "exact_enumeration" and y_key in {"rmse", "bias", "sample_std"}:
            axis.scatter(
                [EXACT_ENUMERATION_CALLS],
                [0.0],
                marker="*",
                s=180,
                color="black",
                zorder=10,
            )
            axis.annotate(
                "all amplitudes: exact error = 0 at M=N=64",
                (EXACT_ENUMERATION_CALLS, 0.0),
                xytext=(5, 12),
                textcoords="offset points",
                fontsize="small",
            )
    return fig


def _single_qiskit_resource_plot(rows: Sequence[dict[str, Any]], *, y_key: str, ylabel: str) -> Any:
    fig, axis = plt.subplots(figsize=(7.4, 4.8))
    selected = [row for row in rows if row.get("method") == "qiskit_statevector_mlae"]
    colors = _amplitude_colors(selected)
    for (numerator, denominator), color in colors.items():
        points = sorted(
            (
                int(row["logical_lookup_oracle_calls"]),
                float(row[y_key]),
            )
            for row in selected
            if int(row["amplitude_numerator"]) == numerator
            and int(row["amplitude_denominator"]) == denominator
            and row.get(y_key) is not None
        )
        if points:
            axis.plot(
                [point[0] for point in points],
                [point[1] for point in points],
                marker="o",
                color=color,
                label=_amplitude_label(numerator, denominator),
            )
    axis.set_xscale("log", base=2)
    axis.set_yscale("log")
    axis.set_xlabel("Executed logical $U_f/U_f^{-1}$ calls")
    axis.set_ylabel(ylabel)
    axis.grid(alpha=0.25, which="both")
    axis.legend(fontsize="small", ncol=2)
    failed = sum(int(row.get("n_failed", 0)) for row in selected)
    requested = sum(
        int(row.get("n_requested", int(row.get("n", 0)) + int(row.get("n_failed", 0))))
        for row in selected
    )
    axis.text(
        0.02,
        0.98,
        f"failed measured runs: {failed}/{requested}",
        transform=axis.transAxes,
        ha="left",
        va="top",
        fontsize="x-small",
    )
    return fig


def generate_audit_plots(
    analytical_summary: Sequence[dict[str, Any]],
    runtime_summary: Sequence[dict[str, Any]],
    output_dir: Path,
) -> tuple[Path, ...]:
    """Generate exactly the six preregistered audit figures in PNG and PDF."""

    generated: list[Path] = []
    analytical_methods = (
        ("exact_enumeration", "Exact finite-table control"),
        ("classical_monte_carlo", "Classical Monte Carlo"),
        ("analytical_mlae", "Analytical finite-shot MLAE"),
    )
    runtime_methods = (
        ("exact_enumeration", "Exact enumeration"),
        ("classical_monte_carlo", "Classical Monte Carlo"),
        ("qiskit_statevector_mlae", "Qiskit StatevectorSampler MLAE"),
    )

    generated.extend(
        _save_figure(
            _two_method_plot(
                analytical_summary,
                methods=analytical_methods,
                y_key="rmse",
                ylabel="RMSE",
                y_scale="symlog",
            ),
            output_dir,
            PLOT_NAMES[0],
        )
    )
    generated.extend(
        _save_figure(
            _two_method_plot(
                analytical_summary,
                methods=analytical_methods,
                y_key="bias",
                ylabel="Bias",
                y_scale="symlog",
            ),
            output_dir,
            PLOT_NAMES[1],
        )
    )
    generated.extend(
        _save_figure(
            _two_method_plot(
                analytical_summary,
                methods=analytical_methods,
                y_key="sample_std",
                ylabel="Sample standard deviation",
                y_scale="symlog",
            ),
            output_dir,
            PLOT_NAMES[2],
        )
    )
    generated.extend(
        _save_figure(
            _two_method_plot(
                runtime_summary,
                methods=runtime_methods,
                y_key="median_audit_end_to_end_ms",
                ylabel="Measured audit end-to-end runtime (ms), median",
                y_scale="log",
            ),
            output_dir,
            PLOT_NAMES[3],
        )
    )
    generated.extend(
        _save_figure(
            _single_qiskit_resource_plot(
                runtime_summary,
                y_key="max_transpiled_quantum_depth",
                ylabel="Maximum transpiled quantum depth",
            ),
            output_dir,
            PLOT_NAMES[4],
        )
    )

    gate_fig, gate_axes = plt.subplots(1, 2, figsize=(12, 4.8))
    gate_rows = [row for row in runtime_summary if row.get("method") == "qiskit_statevector_mlae"]
    colors = _amplitude_colors(gate_rows)
    for axis, key, title in (
        (
            gate_axes[0],
            "max_transpiled_quantum_gate_count",
            "Maximum gates in one circuit",
        ),
        (
            gate_axes[1],
            "shot_weighted_transpiled_quantum_gate_count",
            "Shot-weighted schedule gates",
        ),
    ):
        for (numerator, denominator), color in colors.items():
            points = sorted(
                (
                    int(row["logical_lookup_oracle_calls"]),
                    float(row[key]),
                )
                for row in gate_rows
                if int(row["amplitude_numerator"]) == numerator
                and int(row["amplitude_denominator"]) == denominator
                and row.get(key) is not None
            )
            if points:
                axis.plot(
                    [point[0] for point in points],
                    [point[1] for point in points],
                    marker="o",
                    color=color,
                    label=_amplitude_label(numerator, denominator),
                )
        axis.set_title(title)
        axis.set_xscale("log", base=2)
        axis.set_yscale("log")
        axis.set_xlabel("Executed logical $U_f/U_f^{-1}$ calls")
        axis.set_ylabel("Transpiled quantum gates")
        axis.grid(alpha=0.25, which="both")
        axis.legend(fontsize="small", ncol=2)
        failed = sum(int(row.get("n_failed", 0)) for row in gate_rows)
        requested = sum(
            int(row.get("n_requested", int(row.get("n", 0)) + int(row.get("n_failed", 0))))
            for row in gate_rows
        )
        axis.text(
            0.02,
            0.98,
            f"failed measured runs: {failed}/{requested}",
            transform=axis.transAxes,
            ha="left",
            va="top",
            fontsize="x-small",
        )
    generated.extend(_save_figure(gate_fig, output_dir, PLOT_NAMES[5]))

    expected = {f"{name}.{suffix}" for name in PLOT_NAMES for suffix in ("png", "pdf")}
    actual = {path.name for path in generated}
    if actual != expected:
        raise AssertionError(f"audit plot set differs from preregistration: {sorted(actual)}")
    return tuple(generated)


def _read_jsonl_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected one JSON object per line")
            records.append(value)
    return records


def regenerate_audit_plots(bundle_dir: Path, output_dir: Path) -> tuple[Path, ...]:
    """Regenerate all six figures solely from an archived config and raw JSONL files."""

    config = AuditExperimentConfig.load(bundle_dir / "scientific-audit.toml")
    config.validate_scientific_protocol()
    analytical_records = _read_jsonl_records(bundle_dir / "analytical-raw.jsonl")
    exact_records = _read_jsonl_records(bundle_dir / "exact-control-raw.jsonl")
    runtime_records = _read_jsonl_records(bundle_dir / "runtime-raw.jsonl")
    analytical_summary = aggregate_analytical_records(
        analytical_records,
        bootstrap_replicates=config.bootstrap_replicates,
        bootstrap_confidence_level=config.bootstrap_confidence_level,
        bootstrap_seed=config.bootstrap_seed,
    )
    exact_runtime_summary = aggregate_runtime_records(
        exact_records,
        bootstrap_replicates=config.bootstrap_replicates,
        bootstrap_confidence_level=config.bootstrap_confidence_level,
        bootstrap_seed=config.bootstrap_seed,
    )
    runtime_summary = aggregate_runtime_records(
        runtime_records,
        bootstrap_replicates=config.bootstrap_replicates,
        bootstrap_confidence_level=config.bootstrap_confidence_level,
        bootstrap_seed=config.bootstrap_seed,
    )
    return generate_audit_plots(
        [*exact_statistical_control(config), *analytical_summary],
        [*exact_runtime_summary, *runtime_summary],
        output_dir,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_output(repository_root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def assert_clean_worktree(repository_root: Path) -> None:
    """Refuse a scientific long run unless tracked and untracked state is clean."""

    dirty_lines = [
        line
        for line in _git_output(
            repository_root, "status", "--porcelain", "--untracked-files=all"
        ).splitlines()
        if line
    ]
    if dirty_lines:
        preview = "\n".join(dirty_lines[:20])
        suffix = "\n..." if len(dirty_lines) > 20 else ""
        raise RuntimeError(
            "scientific audit requires a clean Git worktree before any output is written:\n"
            f"{preview}{suffix}"
        )


def _installed_version(distribution: str) -> str | None:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return None


def build_bundle_manifest(
    *,
    config: AuditExperimentConfig,
    repository_root: Path,
    output_dir: Path,
    config_copy: Path,
    artifact_paths: Sequence[Path],
    analytical_records: Sequence[dict[str, Any]],
    exact_records: Sequence[dict[str, Any]],
    runtime_records: Sequence[dict[str, Any]],
    designs: Sequence[AuditDesign],
    worktree_clean_at_start: bool | None = None,
) -> dict[str, Any]:
    """Build provenance and definitions after every measured file has been written."""

    head = _git_output(repository_root, "rev-parse", "HEAD")
    git_tree = _git_output(repository_root, "rev-parse", "HEAD^{tree}")
    dirty_lines = [
        line
        for line in _git_output(
            repository_root, "status", "--porcelain", "--untracked-files=all"
        ).splitlines()
        if line
    ]
    hashes = {
        str(path.relative_to(output_dir)): sha256_file(path)
        for path in [config_copy, *artifact_paths]
    }
    source_hashes = {
        relative_path: sha256_file(repository_root / relative_path)
        for relative_path in AUDIT_SOURCE_PATHS
    }
    source_blob_ids = {
        relative_path: _git_output(
            repository_root, "hash-object", str(repository_root / relative_path)
        )
        for relative_path in AUDIT_SOURCE_PATHS
    }
    source_bundle_payload = "".join(
        f"{relative_path}\0{source_hashes[relative_path]}\n"
        for relative_path in sorted(source_hashes)
    ).encode()
    truth_tables = [
        {
            "amplitude_numerator": numerator,
            "amplitude_denominator": config.amplitude_denominator,
            "marked_count": numerator,
            "table_layout": config.table_layout,
            "visibility_table_sha256": visibility_table_sha256(
                contiguous_prefix_visibility_table(numerator, config.amplitude_denominator)
            ),
        }
        for numerator in config.amplitude_numerators
    ]
    return {
        "schema_version": "1.0",
        "bundle_kind": "scientific_audit_experiment",
        "created_utc": datetime.now(UTC).isoformat(),
        "baseline_commit": config.baseline_commit,
        "current_head": head,
        "current_head_tree": git_tree,
        "current_head_dirty": bool(dirty_lines),
        "dirty_status_entries": dirty_lines,
        "worktree_clean_required": config.require_clean_worktree,
        "worktree_clean_at_start": worktree_clean_at_start,
        "config": config.model_dump(mode="json"),
        "config_sha256": sha256_file(config_copy),
        "artifact_sha256": hashes,
        "source_sha256": source_hashes,
        "source_git_blob_ids": source_blob_ids,
        "source_bundle_sha256": hashlib.sha256(source_bundle_payload).hexdigest(),
        "truth_table_hash_encoding": (
            "SHA-256(bytes(table)); exactly one byte 0x00 or 0x01 per table index, in "
            "ascending index order"
        ),
        "truth_tables": truth_tables,
        "environment": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor() or "unknown",
            "logical_cpu_count": os.cpu_count(),
            "total_system_memory_bytes": psutil.virtual_memory().total,
            "python": sys.version,
            "packages": {
                name: _installed_version(name)
                for name in (
                    "quantum-minecraft-rendering",
                    "qiskit",
                    "qiskit-algorithms",
                    "numpy",
                    "matplotlib",
                    "psutil",
                )
            },
        },
        "analytical_execution_model": ANALYTICAL_MODEL,
        "runtime_execution_model": QISKIT_RUNTIME_MODEL,
        "exact_enumeration_calls": EXACT_ENUMERATION_CALLS,
        "finite_domain_fairness": {
            "oracle_domain_size": config.amplitude_denominator,
            "interpretation": (
                "Exact enumeration has zero error after N=64 logical table reads. "
                "Every QAE/MC cell records requested_budget_ge_domain_size and "
                "realized_calls_ge_domain_size; M>=N cells cannot establish an advantage "
                "over the exact finite-domain classical control."
            ),
        },
        "confidence_interval_methods": {
            "analytical_mlae": (
                "audit_fixed_grid_likelihood_ratio_envelope_not_qiskit_ci; envelope of all "
                "fixed amplitude-grid points passing the one-parameter LR cutoff"
            ),
            "classical_monte_carlo": "Wilson score interval",
            "exact_enumeration": "degenerate exact interval [a, a]",
        },
        "bootstrap_protocol": {
            "method": "deterministic nonparametric percentile bootstrap",
            "replicates": config.bootstrap_replicates,
            "confidence_level": config.bootstrap_confidence_level,
            "base_seed": config.bootstrap_seed,
            "point_metrics": ["bias", "rmse", "sample_std", "runtime_median"],
            "slope_resampling": (
                "joint replicate identifiers are resampled once and reused across every "
                "preregistered budget; a slope resample is invalid if any RMSE is zero"
            ),
        },
        "cost_model": {
            "exact_enumeration_calls": (
                "64 deterministic reads, one for every entry in the finite oracle domain"
            ),
            "logical_lookup_oracle_calls": (
                "shots_per_circuit * sum(2*k + 1); counts executed logical U_f and "
                "U_f^-1 applications, including the leading state preparation"
            ),
            "classical_monte_carlo_calls": (
                "one deterministic 64-entry table lookup per sample; exactly matched to "
                "realized logical_lookup_oracle_calls for MLAE"
            ),
            "shots": "measurement repetitions; never used as an alias for oracle calls",
            "grover_iterations": "shots_per_circuit * sum(k)",
            "gate_count": (
                "u/cx basis quantum gates only; barrier and measurement excluded; max, "
                "schedule sum, and shot-weighted schedule sum reported separately"
            ),
            "circuit_depth": (
                "maximum quantum-operation depth among separately transpiled schedule circuits"
            ),
        },
        "timer_definitions": {
            "clock": "time.perf_counter_ns monotonic wall clock",
            "import_costs": (
                "Python, Qiskit, and Matplotlib imports complete before every per-record timer "
                "and are excluded from audit_end_to_end_ms"
            ),
            "oracle_synthesis_ms": "build_estimation_problem(table)",
            "analysis_copy_transpilation_ms": (
                "construct and optimization_level=0 transpile resource-analysis circuit copies"
            ),
            "estimator_runtime_ms_qiskit": (
                "MaximumLikelihoodAmplitudeEstimation.estimate; includes primitive circuit "
                "handling, StatevectorSampler sampling, and MLE postprocessing"
            ),
            "estimator_runtime_ms_mc": "seeded table sampling and sample mean",
            "estimator_runtime_ms_exact": "Python sum over all 64 supplied table entries",
            "confidence_interval_postprocessing_ms": (
                "method-specific confidence-interval call after the estimator timer; Qiskit "
                "likelihood-ratio for MLAE and Wilson score for MC"
            ),
            "audit_end_to_end_ms": (
                "sum of the explicitly executed audit phases for one runtime record; excludes "
                "raw-file serialization and manifest collection"
            ),
            "warmup_policy": (
                "warmup records are retained with warmup=true and excluded from runtime summary; "
                "they exercise lazy runtime initialization after imports and do not measure imports"
            ),
            "runtime_plot_metric": (
                "median audit_end_to_end_ms with deterministic percentile-bootstrap interval; "
                "median estimator_runtime_ms remains available as a separately labelled core time"
            ),
        },
        "runtime_order_protocol": {
            "seed": config.runtime_order_seed,
            "method": (
                "warmup and measured pair units are separately deterministically shuffled; "
                "adjacent MC/Qiskit order alternates, giving exact phase balance when the "
                "number of pair units is even"
            ),
            "raw_record_fields": [
                "runtime_execution_sequence",
                "runtime_phase_pair_sequence",
                "runtime_pair_id",
                "runtime_within_pair_position",
                "runtime_paired_method_order",
                "runtime_order_phase_seed",
            ],
        },
        "outlier_policy": {
            "removal_or_winsorization": "none",
            "raw_archive": "every successful, failed, and warmup record is retained",
            "summary_exclusions": (
                "only records explicitly marked warmup are excluded by design; failed records "
                "without a valid metric are separately counted and never silently imputed"
            ),
            "reported_runtime_statistics": ["median", "mean", "min", "max", "sample_std"],
        },
        "budget_designs": [
            {
                "requested_oracle_budget": design.requested_budget,
                "evaluation_schedule": list(design.schedule),
                "shots_per_circuit": design.shots_per_circuit,
                "logical_lookup_oracle_calls": design.logical_lookup_oracle_calls,
                "oracle_domain_size": config.amplitude_denominator,
                "requested_budget_ge_domain_size": (
                    design.requested_budget >= config.amplitude_denominator
                ),
                "realized_calls_ge_domain_size": (
                    design.logical_lookup_oracle_calls >= config.amplitude_denominator
                ),
                "state_preparation_applications": design.state_preparation_applications,
                "inverse_state_preparation_applications": (
                    design.inverse_state_preparation_applications
                ),
                "grover_iterations": design.grover_iterations,
                "total_shots": design.total_shots,
                "distinct_circuits": design.distinct_circuits,
                "sampler_jobs": design.sampler_jobs,
            }
            for design in designs
        ],
        "record_counts": {
            "analytical_total": len(analytical_records),
            "analytical_failed": sum(record.get("status") != "ok" for record in analytical_records),
            "exact_total_including_warmup": len(exact_records),
            "exact_failed": sum(record.get("status") != "ok" for record in exact_records),
            "exact_warmup": sum(bool(record.get("warmup")) for record in exact_records),
            "runtime_total_including_warmup": len(runtime_records),
            "runtime_failed": sum(record.get("status") != "ok" for record in runtime_records),
            "runtime_warmup": sum(bool(record.get("warmup")) for record in runtime_records),
        },
        "plot_protocol": {
            "figure_count": len(PLOT_NAMES),
            "names": list(PLOT_NAMES),
            "regeneration_function": "qmr.audit_experiment.regenerate_audit_plots",
            "regeneration_inputs": [
                "scientific-audit.toml",
                "analytical-raw.jsonl",
                "exact-control-raw.jsonl",
                "runtime-raw.jsonl",
            ],
            "selective_curve_fits": False,
            "slope_definition": (
                "ordinary least squares of log(RMSE) on log(realized calls) over every "
                "preregistered budget for one method/amplitude; undefined if any full-range "
                "point is missing or nonpositive"
            ),
            "uncertainty": (
                "deterministic 95% percentile-bootstrap bands for bias, RMSE, sample standard "
                "deviation, and runtime median"
            ),
            "failure_counts_visible": True,
        },
        "non_claims": [
            "Analytical measurement-model runtime is not QPU or simulator runtime.",
            "StatevectorSampler runtime is classical CPU simulation, not physical-QPU runtime.",
            "The lookup truth table is classically specified; this is not reversible ray marching.",
            "No practical quantum speed-up or hardware result is inferred from this bundle.",
        ],
    }


def run_scientific_audit(
    config_path: Path,
    output_dir: Path,
    repository_root: Path,
) -> AuditArtifacts:
    """Execute the full preregistered long run and write a self-describing bundle."""

    config = AuditExperimentConfig.load(config_path)
    config.validate_scientific_protocol()
    if config.require_clean_worktree:
        assert_clean_worktree(repository_root)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"audit output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = output_dir / "plots"
    config_copy = output_dir / "scientific-audit.toml"
    shutil.copy2(config_path, config_copy)

    designs = audit_designs(config)
    analytical_records = simulate_analytical_records(config, designs)
    analytical_summary = aggregate_analytical_records(
        analytical_records,
        bootstrap_replicates=config.bootstrap_replicates,
        bootstrap_confidence_level=config.bootstrap_confidence_level,
        bootstrap_seed=config.bootstrap_seed,
    )
    exact_statistics = exact_statistical_control(config)
    analytical_jsonl = output_dir / "analytical-raw.jsonl"
    analytical_csv = output_dir / "analytical-raw.csv"
    analytical_summary_csv = output_dir / "analytical-summary.csv"
    write_jsonl_csv(analytical_records, analytical_jsonl, analytical_csv)
    write_csv(analytical_summary, analytical_summary_csv)

    exact_records = run_exact_control_records(config)
    exact_runtime_summary = aggregate_runtime_records(
        exact_records,
        bootstrap_replicates=config.bootstrap_replicates,
        bootstrap_confidence_level=config.bootstrap_confidence_level,
        bootstrap_seed=config.bootstrap_seed,
    )
    exact_summary = combine_exact_control_summary(exact_statistics, exact_runtime_summary)
    exact_jsonl = output_dir / "exact-control-raw.jsonl"
    exact_csv = output_dir / "exact-control-raw.csv"
    exact_summary_csv = output_dir / "exact-control-summary.csv"
    write_jsonl_csv(exact_records, exact_jsonl, exact_csv)
    write_csv(exact_summary, exact_summary_csv)

    runtime_records = run_actual_runtime_records(config, designs)
    runtime_summary = aggregate_runtime_records(
        runtime_records,
        bootstrap_replicates=config.bootstrap_replicates,
        bootstrap_confidence_level=config.bootstrap_confidence_level,
        bootstrap_seed=config.bootstrap_seed,
    )
    runtime_jsonl = output_dir / "runtime-raw.jsonl"
    runtime_csv = output_dir / "runtime-raw.csv"
    runtime_summary_csv = output_dir / "runtime-summary.csv"
    write_jsonl_csv(runtime_records, runtime_jsonl, runtime_csv)
    write_csv(runtime_summary, runtime_summary_csv)

    plots = generate_audit_plots(
        [*exact_statistics, *analytical_summary],
        [*exact_runtime_summary, *runtime_summary],
        plots_dir,
    )
    artifact_paths = (
        analytical_jsonl,
        analytical_csv,
        analytical_summary_csv,
        exact_jsonl,
        exact_csv,
        exact_summary_csv,
        runtime_jsonl,
        runtime_csv,
        runtime_summary_csv,
        *plots,
    )
    manifest_payload = build_bundle_manifest(
        config=config,
        repository_root=repository_root,
        output_dir=output_dir,
        config_copy=config_copy,
        artifact_paths=artifact_paths,
        analytical_records=analytical_records,
        exact_records=exact_records,
        runtime_records=runtime_records,
        designs=designs,
        worktree_clean_at_start=True,
    )
    manifest = output_dir / "manifest.json"
    manifest.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n")
    return AuditArtifacts(
        output_dir=output_dir,
        analytical_jsonl=analytical_jsonl,
        analytical_csv=analytical_csv,
        analytical_summary_csv=analytical_summary_csv,
        exact_jsonl=exact_jsonl,
        exact_csv=exact_csv,
        exact_summary_csv=exact_summary_csv,
        runtime_jsonl=runtime_jsonl,
        runtime_csv=runtime_csv,
        runtime_summary_csv=runtime_summary_csv,
        plots=plots,
        manifest=manifest,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m qmr.audit_experiment",
        description="Run the dedicated, preregistered scientific-audit bundle",
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    artifacts = run_scientific_audit(
        args.config.resolve(), args.output_dir.resolve(), args.repository_root.resolve()
    )
    print(
        json.dumps(
            {
                "output_dir": str(artifacts.output_dir),
                "manifest": str(artifacts.manifest),
                "analytical_raw": str(artifacts.analytical_jsonl),
                "exact_control_raw": str(artifacts.exact_jsonl),
                "runtime_raw": str(artifacts.runtime_jsonl),
                "plots": [str(path) for path in artifacts.plots],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
