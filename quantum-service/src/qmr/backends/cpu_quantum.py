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

    @property
    def logical_lookup_oracle_calls(self) -> int:
        """Executed logical ``U_f``/``U_f^-1`` applications across all shots."""

        return self.shots_per_circuit * sum(2 * power + 1 for power in self.schedule)

    @property
    def table_oracle_calls(self) -> int:
        """Backward-compatible alias for logical lookup-oracle applications."""

        return self.logical_lookup_oracle_calls

    @property
    def state_preparation_applications(self) -> int:
        """Forward ``A`` applications, including the leading ``A`` in every circuit."""

        return self.shots_per_circuit * sum(power + 1 for power in self.schedule)

    @property
    def inverse_state_preparation_applications(self) -> int:
        """Inverse ``A^-1`` applications induced by the Grover powers."""

        return self.shots_per_circuit * sum(self.schedule)

    @property
    def grover_iterations(self) -> int:
        """Executed logical ``Q`` applications across all shots."""

        return self.shots_per_circuit * sum(self.schedule)

    @property
    def good_state_markings(self) -> int:
        """Executed ``S_good`` phase markings, one per Grover iteration."""

        return self.grover_iterations

    @property
    def total_shots(self) -> int:
        return self.shots_per_circuit * len(self.schedule)

    @property
    def distinct_circuits(self) -> int:
        return len(self.schedule)

    @property
    def sampler_jobs(self) -> int:
        """Sampler submissions made by one Qiskit MLAE estimate call."""

        return 1


@dataclass(frozen=True, slots=True)
class VisibilityOperators:
    """Named operators used by the visibility amplitude-estimation problem."""

    lookup_oracle: QuantumCircuit
    state_preparation: QuantumCircuit
    good_state_reflection: QuantumCircuit
    grover_operator: QuantumCircuit
    objective_qubit: int


@dataclass(frozen=True, slots=True)
class CircuitMetrics:
    """Analysis-only resource estimates for separately transpiled circuit copies."""

    max_quantum_depth: int
    max_quantum_gate_count: int
    schedule_quantum_gate_count: int
    shot_weighted_quantum_gate_count: int
    per_circuit: tuple[dict[str, Any], ...]


def _probability(value: float) -> float:
    """Clamp numerical optimizer residue at the physical probability boundaries."""

    if value <= 1e-15:
        return 0.0
    if value >= 1 - 1e-15:
        return 1.0
    return value


def plan_budget(max_oracle_calls: int, desired_accuracy: float) -> QuantumBudget:
    """Plan a power-of-two MLAE schedule that never exceeds the table-query budget."""

    if max_oracle_calls < 1:
        raise ValueError("max_oracle_calls must be at least 1")
    if not math.isfinite(desired_accuracy) or not 0 < desired_accuracy <= 1:
        raise ValueError("desired_accuracy must be finite and in (0, 1]")

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
    shots = max_oracle_calls // per_shot_calls
    return QuantumBudget(tuple(schedule), shots)


def _validate_visibility_table(table: list[int]) -> None:
    if not table or len(table) & (len(table) - 1):
        raise ValueError("visibility table length must be a non-zero power of two")
    if any(value not in {0, 1} for value in table):
        raise ValueError("visibility table must be binary")


def build_visibility_lookup_oracle(table: list[int]) -> QuantumCircuit:
    """Build ``U_f: |i,y> -> |i,y xor f(i)>`` from a classical truth table."""

    _validate_visibility_table(table)
    index_qubits = int(math.log2(len(table)))
    objective = index_qubits
    lookup = QuantumCircuit(index_qubits + 1, name="U_f_visibility")
    if all(table):
        lookup.x(objective)
    elif any(table):
        controls = list(range(index_qubits))
        for index, visible in enumerate(table):
            if not visible:
                continue
            zero_controls = [bit for bit in controls if not (index >> bit) & 1]
            if zero_controls:
                lookup.x(zero_controls)
            lookup.mcx(controls, objective)
            if zero_controls:
                lookup.x(zero_controls)
    return lookup


def build_state_preparation(lookup_oracle: QuantumCircuit) -> QuantumCircuit:
    """Build ``A = U_f (H^n tensor I)`` without direct statevector initialization."""

    index_qubits = lookup_oracle.num_qubits - 1
    preparation = QuantumCircuit(lookup_oracle.num_qubits, name="A_visibility")
    preparation.h(range(index_qubits))
    preparation.append(lookup_oracle.to_gate(), preparation.qubits)
    return preparation


def build_good_state_reflection(num_qubits: int, objective_qubit: int) -> QuantumCircuit:
    """Build ``S_good`` by phase-flipping states whose objective qubit is one."""

    reflection = QuantumCircuit(num_qubits, name="S_good_visibility")
    reflection.z(objective_qubit)
    return reflection


def build_visibility_operators(table: list[int]) -> VisibilityOperators:
    """Construct and name ``U_f``, ``A``, ``S_good``, and ``Q`` explicitly."""

    lookup = build_visibility_lookup_oracle(table)
    objective = lookup.num_qubits - 1
    preparation = build_state_preparation(lookup)
    good_state_reflection = build_good_state_reflection(lookup.num_qubits, objective)
    grover = grover_operator(
        good_state_reflection,
        state_preparation=preparation,
        name="Q_visibility",
    )
    return VisibilityOperators(
        lookup_oracle=lookup,
        state_preparation=preparation,
        good_state_reflection=good_state_reflection,
        grover_operator=grover,
        objective_qubit=objective,
    )


def build_estimation_problem(table: list[int]) -> EstimationProblem:
    """Encode f(i) in an index register and one objective qubit."""

    operators = build_visibility_operators(table)
    return EstimationProblem(
        state_preparation=operators.state_preparation,
        objective_qubits=operators.objective_qubit,
        grover_operator=operators.grover_operator,
    )


def _circuit_metrics(
    algorithm: MaximumLikelihoodAmplitudeEstimation,
    problem: EstimationProblem,
    budget: QuantumBudget,
    seed: int,
) -> CircuitMetrics:
    circuits = algorithm.construct_circuits(problem, measurement=True)
    transpiled = cast(
        list[QuantumCircuit],
        transpile(circuits, basis_gates=["u", "cx"], optimization_level=0, seed_transpiler=seed),
    )
    details: list[dict[str, Any]] = []
    excluded_operations = {"barrier", "measure"}
    for power, circuit in zip(budget.schedule, transpiled, strict=True):
        operation_counts = {str(name): int(count) for name, count in circuit.count_ops().items()}
        quantum_gate_count = sum(
            count for name, count in operation_counts.items() if name not in excluded_operations
        )
        quantum_depth = circuit.depth(
            filter_function=lambda instruction: (
                instruction.operation.name not in excluded_operations
            )
        )
        details.append(
            {
                "grover_power": power,
                "qubits": circuit.num_qubits,
                "quantum_depth": quantum_depth,
                "quantum_gate_count": quantum_gate_count,
                "operation_counts_including_non_gates": operation_counts,
            }
        )
    schedule_gate_count = sum(int(item["quantum_gate_count"]) for item in details)
    return CircuitMetrics(
        max_quantum_depth=max(int(item["quantum_depth"]) for item in details),
        max_quantum_gate_count=max(int(item["quantum_gate_count"]) for item in details),
        schedule_quantum_gate_count=schedule_gate_count,
        shot_weighted_quantum_gate_count=budget.shots_per_circuit * schedule_gate_count,
        per_circuit=tuple(details),
    )


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
        table_completed = perf_counter_ns()
        visible_count = sum(table)
        truth = visible_count / len(table)
        truth_completed = perf_counter_ns()
        budget = plan_budget(request.max_oracle_calls, request.desired_accuracy)
        budget_completed = perf_counter_ns()
        problem = build_estimation_problem(table)
        oracle_completed = perf_counter_ns()
        sampler = StatevectorSampler(default_shots=budget.shots_per_circuit, seed=request.seed)
        algorithm = MaximumLikelihoodAmplitudeEstimation(
            evaluation_schedule=list(budget.schedule),
            sampler=sampler,
        )
        estimator_setup_completed = perf_counter_ns()
        circuit_metrics = _circuit_metrics(algorithm, problem, budget, request.seed)
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
        estimate = _probability(float(algorithm_result.estimation))
        completed = perf_counter_ns()

        qiskit_grover_queries = int(algorithm_result.num_oracle_queries)
        if qiskit_grover_queries != budget.grover_iterations:
            raise RuntimeError(
                "Qiskit's reported Grover-query count disagrees with the planned schedule"
            )
        return result_for(
            request,
            backend=self.name,
            estimate=estimate,
            truth=truth,
            oracle_calls=budget.logical_lookup_oracle_calls,
            initialization_ms=(initialized - started) / 1e6,
            simulation_ms=(completed - initialized) / 1e6,
            end_to_end_ms=(completed - started) / 1e6,
            confidence_interval=ConfidenceInterval(
                low=_probability(float(confidence[0])),
                high=_probability(float(confidence[1])),
                level=request.confidence_level,
                method="qiskit_mlae_asymptotic_likelihood_ratio_outer",
            ),
            qubit_count=problem.state_preparation.num_qubits,
            shots=budget.total_shots,
            circuit_executions=budget.distinct_circuits,
            circuit_depth=circuit_metrics.max_quantum_depth,
            gate_count=circuit_metrics.max_quantum_gate_count,
            warnings=[
                (
                    "The visibility table is classically generated; this is not reversible "
                    "ray marching."
                ),
                "StatevectorSampler simulates finite-shot circuit measurements on the CPU.",
                (
                    "The likelihood-ratio interval uses asymptotic chi-square calibration and "
                    "an outer hull; finite-shot and boundary coverage is not guaranteed."
                ),
                "Simulator runtime is not evidence of practical quantum speed-up.",
            ],
            metadata={
                "quantum_algorithm": "MLAE",
                "evaluation_schedule": list(budget.schedule),
                "shots_per_circuit": budget.shots_per_circuit,
                "requested_max_oracle_calls": request.max_oracle_calls,
                "unused_logical_oracle_budget": (
                    request.max_oracle_calls - budget.logical_lookup_oracle_calls
                ),
                "desired_accuracy_role": (
                    "non-adaptive heuristic cap on maximum Grover power; not an "
                    "achieved-error guarantee"
                ),
                "stopping_criterion": "none; the circuit schedule is fixed before sampling",
                "confidence_level_affects_schedule": False,
                "adaptive_iterations": 0,
                "classical_postprocessing": (
                    "global maximum-likelihood estimation from objective-qubit shot counts"
                ),
                "qiskit_reported_grover_queries": qiskit_grover_queries,
                "oracle_accounting": (
                    "logical U_f/U_f^-1 calls = shots_per_circuit * sum(2*k + 1)"
                ),
                "quantum_costs": {
                    "logical_lookup_oracle_calls": budget.logical_lookup_oracle_calls,
                    "state_preparation_A_applications": budget.state_preparation_applications,
                    "inverse_state_preparation_A_dagger_applications": (
                        budget.inverse_state_preparation_applications
                    ),
                    "grover_Q_iterations": budget.grover_iterations,
                    "good_state_S_good_markings": budget.good_state_markings,
                    "total_measurement_shots": budget.total_shots,
                    "distinct_power_circuits": budget.distinct_circuits,
                    "sampler_jobs": budget.sampler_jobs,
                },
                "classical_table_build_rays": len(table),
                "classical_ground_truth_table_reads": len(table),
                "oracle_synthesis_table_entries_examined": len(table),
                "oracle_synthesis_marked_states": visible_count,
                "statevector_probabilities_read": False,
                "confidence_interval_semantics": (
                    "Qiskit MLAE likelihood-ratio outer interval with asymptotic chi-square "
                    "calibration; not an exact finite-sample interval"
                ),
                "resource_metric_scope": (
                    "analysis-only transpilation of circuit copies to all-to-all u/cx at "
                    "optimization_level=0; StatevectorSampler receives untranspiled circuits"
                ),
                "transpilation_basis_gates": ["u", "cx"],
                "transpilation_optimization_level": 0,
                "max_transpiled_quantum_depth": circuit_metrics.max_quantum_depth,
                "max_transpiled_quantum_gate_count": (circuit_metrics.max_quantum_gate_count),
                "schedule_transpiled_quantum_gate_count": (
                    circuit_metrics.schedule_quantum_gate_count
                ),
                "shot_weighted_transpiled_quantum_gate_count": (
                    circuit_metrics.shot_weighted_quantum_gate_count
                ),
                "per_circuit_transpiled_metrics": cast(
                    list[dict[str, Any]], list(circuit_metrics.per_circuit)
                ),
                "phase_timings_ms": {
                    "classical_visibility_table_dda": (table_completed - started) / 1e6,
                    "ground_truth_reduction": (truth_completed - table_completed) / 1e6,
                    "budget_planning": (budget_completed - truth_completed) / 1e6,
                    "oracle_and_problem_construction": (oracle_completed - budget_completed) / 1e6,
                    "sampler_and_estimator_setup": (estimator_setup_completed - oracle_completed)
                    / 1e6,
                    "analysis_metric_transpilation": (initialized - estimator_setup_completed)
                    / 1e6,
                    "estimator_execution_and_confidence_interval": (completed - initialized) / 1e6,
                },
            },
        )
