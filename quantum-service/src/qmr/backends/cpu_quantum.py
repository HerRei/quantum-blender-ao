"""Shot-based, qubit-sparse Qiskit amplitude estimation on a CPU simulator."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from time import perf_counter_ns
from typing import Any, cast

from qiskit import QuantumCircuit, transpile  # type: ignore[import-untyped]
from qiskit.circuit.library import grover_operator  # type: ignore[import-untyped]
from qiskit.primitives import StatevectorSampler  # type: ignore[import-untyped]
from qiskit_algorithms import (  # type: ignore[import-untyped]
    EstimationProblem,
    MaximumLikelihoodAmplitudeEstimation,
)

from qmr.backends.base import BackendCapability, result_for
from qmr.models import ConfidenceInterval, LightingRequest, LightingResult
from qmr.raycast import visibility_table


@dataclass(frozen=True, slots=True)
class QuantumBudget:
    schedule: tuple[int, ...]
    shots_per_circuit: int
    table_oracle_calls: int


def plan_budget(max_oracle_calls: int, desired_accuracy: float) -> QuantumBudget:
    """Plan a power-of-two MLAE schedule that never exceeds the table-query budget."""

    target_power = max(1, math.ceil(1 / (2 * min(desired_accuracy, 0.5))))
    schedule = [0]
    power = 1
    while power <= target_power:
        candidate = [*schedule, power]
        if sum(2 * item + 1 for item in candidate) > max_oracle_calls:
            break
        schedule = candidate
        power *= 2
    per_shot_calls = sum(2 * item + 1 for item in schedule)
    shots = max(1, max_oracle_calls // per_shot_calls)
    return QuantumBudget(tuple(schedule), shots, shots * per_shot_calls)


def build_estimation_problem(table: list[int]) -> EstimationProblem:
    """Encode f(i) in an index register and one objective qubit."""

    if not table or len(table) & (len(table) - 1):
        raise ValueError("visibility table length must be a non-zero power of two")
    if any(value not in {0, 1} for value in table):
        raise ValueError("visibility table must be binary")

    index_qubits = int(math.log2(len(table)))
    objective = index_qubits
    preparation = QuantumCircuit(index_qubits + 1, name="A_visibility")
    preparation.h(range(index_qubits))
    if all(table):
        preparation.x(objective)
    elif any(table):
        controls = list(range(index_qubits))
        for index, visible in enumerate(table):
            if not visible:
                continue
            zero_controls = [bit for bit in controls if not (index >> bit) & 1]
            if zero_controls:
                preparation.x(zero_controls)
            preparation.mcx(controls, objective)
            if zero_controls:
                preparation.x(zero_controls)
    phase_oracle = QuantumCircuit(index_qubits + 1, name="S_visibility")
    phase_oracle.z(objective)
    grover = grover_operator(phase_oracle, state_preparation=preparation)
    return EstimationProblem(
        state_preparation=preparation,
        objective_qubits=objective,
        grover_operator=grover,
    )


def _circuit_metrics(
    algorithm: MaximumLikelihoodAmplitudeEstimation,
    problem: EstimationProblem,
    seed: int,
) -> tuple[int, int, list[dict[str, int]]]:
    circuits = algorithm.construct_circuits(problem, measurement=True)
    transpiled = cast(
        list[QuantumCircuit],
        transpile(circuits, basis_gates=["u", "cx"], optimization_level=0, seed_transpiler=seed),
    )
    details: list[dict[str, int]] = []
    for circuit in transpiled:
        details.append(
            {
                "qubits": circuit.num_qubits,
                "depth": circuit.depth(),
                "gate_count": sum(circuit.count_ops().values()),
            }
        )
    return max(item["depth"] for item in details), max(
        item["gate_count"] for item in details
    ), details


class CpuQuantumBackend:
    """Qiskit MLAE backend with finite shots and explicit table-oracle accounting.

    MLAE is used instead of QPE-based amplitude estimation because it needs no
    evaluation register and admits a strict precomputed oracle-call budget.
    """

    name = "cpu_quantum"

    def capability(self) -> BackendCapability:
        return BackendCapability(
            name=self.name,
            available=True,
            devices=("Qiskit StatevectorSampler on CPU",),
            details={
                "algorithm": "maximum_likelihood_amplitude_estimation",
                "finite_shots": True,
                "statevector_probabilities_read": False,
            },
        )

    def estimate(self, request: LightingRequest) -> LightingResult:
        started = perf_counter_ns()
        table = visibility_table(request)
        truth = sum(table) / len(table)
        budget = plan_budget(request.max_oracle_calls, request.desired_accuracy)
        problem = build_estimation_problem(table)
        sampler = StatevectorSampler(default_shots=budget.shots_per_circuit, seed=request.seed)
        algorithm = MaximumLikelihoodAmplitudeEstimation(
            evaluation_schedule=list(budget.schedule),
            sampler=sampler,
        )
        circuit_depth, gate_count, metric_details = _circuit_metrics(
            algorithm, problem, request.seed
        )
        initialized = perf_counter_ns()

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="divide by zero encountered in scalar divide",
                category=RuntimeWarning,
                module="qiskit_algorithms.amplitude_estimators.mlae",
            )
            algorithm_result = algorithm.estimate(problem)
        confidence = algorithm.compute_confidence_interval(
            algorithm_result,
            alpha=1 - request.confidence_level,
            kind="likelihood_ratio",
        )
        estimate = float(algorithm_result.estimation)
        completed = perf_counter_ns()

        qiskit_grover_queries = budget.shots_per_circuit * sum(budget.schedule)
        return result_for(
            request,
            backend=self.name,
            estimate=estimate,
            truth=truth,
            oracle_calls=budget.table_oracle_calls,
            initialization_ms=(initialized - started) / 1e6,
            simulation_ms=(completed - initialized) / 1e6,
            end_to_end_ms=(completed - started) / 1e6,
            confidence_interval=ConfidenceInterval(
                low=max(0.0, float(confidence[0])),
                high=min(1.0, float(confidence[1])),
                level=request.confidence_level,
                method="qiskit_mlae_likelihood_ratio",
            ),
            qubit_count=problem.state_preparation.num_qubits,
            shots=budget.shots_per_circuit * len(budget.schedule),
            circuit_executions=len(budget.schedule),
            circuit_depth=circuit_depth,
            gate_count=gate_count,
            warnings=[
                (
                    "The visibility table is classically generated; this is not reversible "
                    "ray marching."
                ),
                "StatevectorSampler simulates finite-shot circuit measurements on the CPU.",
                "Simulator runtime is not evidence of practical quantum speed-up.",
            ],
            metadata={
                "quantum_algorithm": "MLAE",
                "evaluation_schedule": list(budget.schedule),
                "shots_per_circuit": budget.shots_per_circuit,
                "qiskit_reported_grover_queries": qiskit_grover_queries,
                "oracle_accounting": "shots * sum(2*k + 1) visibility-table calls",
                "classical_table_build_rays": len(table),
                "statevector_probabilities_read": False,
                "per_circuit_transpiled_metrics": cast(list[dict[str, Any]], metric_details),
            },
        )
