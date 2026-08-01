"""Exact, Monte Carlo, and finite-shot QAE estimators for binary visibility tables."""

from __future__ import annotations

import math
import random
import warnings
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any, cast

from qiskit import QuantumCircuit, transpile  # type: ignore[import-untyped]
from qiskit.circuit.library import grover_operator  # type: ignore[import-untyped]
from qiskit.primitives import StatevectorSampler  # type: ignore[import-untyped]
from qiskit_algorithms import (  # type: ignore[import-untyped]
    EstimationProblem,
    MaximumLikelihoodAmplitudeEstimation,
)


@dataclass(frozen=True, slots=True)
class Estimate:
    """One estimator output and the resources used to produce it."""

    value: float
    logical_queries: int
    seconds: float
    shots: int | None = None
    qubits: int | None = None
    max_circuit_depth: int | None = None
    max_circuit_gates: int | None = None
    schedule: tuple[int, ...] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.schedule is not None:
            data["schedule"] = list(self.schedule)
        return data


@dataclass(frozen=True, slots=True)
class QuantumBudget:
    """Finite-shot MLAE schedule bounded by logical lookup-oracle calls."""

    schedule: tuple[int, ...]
    shots_per_circuit: int

    @property
    def logical_queries(self) -> int:
        return self.shots_per_circuit * sum(2 * power + 1 for power in self.schedule)

    @property
    def total_shots(self) -> int:
        return self.shots_per_circuit * len(self.schedule)


def validate_table(table: tuple[int, ...] | list[int]) -> tuple[int, ...]:
    """Return a validated power-of-two binary table."""

    values = tuple(table)
    if not values or len(values) & (len(values) - 1):
        raise ValueError("visibility table length must be a non-zero power of two")
    if any(value not in {0, 1} for value in values):
        raise ValueError("visibility table values must be 0 or 1")
    return values


def plan_budget(max_logical_queries: int, desired_accuracy: float = 0.125) -> QuantumBudget:
    """Choose a power-of-two MLAE schedule that stays within a query cap."""

    if max_logical_queries < 1:
        raise ValueError("max_logical_queries must be at least 1")
    if not math.isfinite(desired_accuracy) or not 0 < desired_accuracy <= 1:
        raise ValueError("desired_accuracy must be finite and in (0, 1]")

    target_power = max(1, math.ceil(1 / (2 * min(desired_accuracy, 0.5))))
    schedule = [0]
    power = 1
    while power <= target_power:
        candidate = [*schedule, power]
        if sum(2 * item + 1 for item in candidate) > max_logical_queries:
            break
        schedule = candidate
        power *= 2

    calls_per_schedule = sum(2 * item + 1 for item in schedule)
    return QuantumBudget(tuple(schedule), max_logical_queries // calls_per_schedule)


def exact_visibility(table: tuple[int, ...] | list[int]) -> Estimate:
    """Evaluate every table entry."""

    values = validate_table(table)
    started = perf_counter()
    value = sum(values) / len(values)
    return Estimate(value=value, logical_queries=len(values), seconds=perf_counter() - started)


def monte_carlo_visibility(
    table: tuple[int, ...] | list[int], samples: int, seed: int
) -> Estimate:
    """Estimate visibility using iid table lookups with replacement."""

    values = validate_table(table)
    if samples < 1:
        raise ValueError("samples must be at least 1")
    started = perf_counter()
    rng = random.Random(seed)
    visible = sum(values[rng.randrange(len(values))] for _ in range(samples))
    return Estimate(
        value=visible / samples,
        logical_queries=samples,
        seconds=perf_counter() - started,
        shots=samples,
    )


def build_lookup_oracle(table: tuple[int, ...] | list[int]) -> QuantumCircuit:
    """Build U_f: |i,y> -> |i,y xor f(i)> from a classical visibility table."""

    values = validate_table(table)
    index_qubits = int(math.log2(len(values)))
    objective = index_qubits
    lookup = QuantumCircuit(index_qubits + 1, name="U_f_visibility")

    if all(values):
        lookup.x(objective)
        return lookup
    if not any(values):
        return lookup

    controls = list(range(index_qubits))
    for index, visible in enumerate(values):
        if not visible:
            continue
        zero_controls = [bit for bit in controls if not (index >> bit) & 1]
        if zero_controls:
            lookup.x(zero_controls)
        lookup.mcx(controls, objective)
        if zero_controls:
            lookup.x(zero_controls)
    return lookup


def build_estimation_problem(table: tuple[int, ...] | list[int]) -> EstimationProblem:
    """Encode uniform direction indices and their binary visibility in amplitudes."""

    lookup = build_lookup_oracle(table)
    index_qubits = lookup.num_qubits - 1
    objective = index_qubits

    preparation = QuantumCircuit(lookup.num_qubits, name="A_visibility")
    preparation.h(range(index_qubits))
    preparation.append(lookup.to_gate(), preparation.qubits)

    good_state = QuantumCircuit(lookup.num_qubits, name="S_good_visibility")
    good_state.z(objective)
    grover = grover_operator(good_state, state_preparation=preparation, name="Q_visibility")

    return EstimationProblem(
        state_preparation=preparation,
        objective_qubits=objective,
        grover_operator=grover,
    )


def _circuit_metrics(
    algorithm: MaximumLikelihoodAmplitudeEstimation,
    problem: EstimationProblem,
    seed: int,
) -> tuple[int, int]:
    circuits = algorithm.construct_circuits(problem, measurement=True)
    routed = cast(
        list[QuantumCircuit],
        transpile(
            circuits,
            basis_gates=["u", "cx"],
            optimization_level=1,
            seed_transpiler=seed,
        ),
    )
    excluded = {"barrier", "measure"}
    depths = [
        circuit.depth(filter_function=lambda item: item.operation.name not in excluded)
        for circuit in routed
    ]
    gates = [
        sum(count for name, count in circuit.count_ops().items() if name not in excluded)
        for circuit in routed
    ]
    return max(depths), max(gates)


def simulated_qae_visibility(
    table: tuple[int, ...] | list[int],
    max_logical_queries: int,
    seed: int,
    desired_accuracy: float = 0.125,
) -> Estimate:
    """Estimate visibility with finite-shot maximum-likelihood amplitude estimation."""

    values = validate_table(table)
    budget = plan_budget(max_logical_queries, desired_accuracy)
    started = perf_counter()
    problem = build_estimation_problem(values)
    sampler = StatevectorSampler(default_shots=budget.shots_per_circuit, seed=seed)
    algorithm = MaximumLikelihoodAmplitudeEstimation(
        evaluation_schedule=list(budget.schedule),
        sampler=sampler,
    )

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        result = algorithm.estimate(problem)

    value = min(1.0, max(0.0, float(result.estimation)))
    if value <= 1e-12:
        value = 0.0
    elif value >= 1.0 - 1e-12:
        value = 1.0
    depth, gates = _circuit_metrics(algorithm, problem, seed)
    return Estimate(
        value=value,
        logical_queries=budget.logical_queries,
        seconds=perf_counter() - started,
        shots=budget.total_shots,
        qubits=problem.state_preparation.num_qubits,
        max_circuit_depth=depth,
        max_circuit_gates=gates,
        schedule=budget.schedule,
    )
