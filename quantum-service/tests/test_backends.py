from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any

import pytest
from qiskit.quantum_info import Statevector
from qiskit_algorithms import MaximumLikelihoodAmplitudeEstimation

import qmr.backends.cpu_quantum as cpu_quantum
from qmr.backends import (
    BackendUnavailableError,
    ClassicalMonteCarloBackend,
    CpuQuantumBackend,
    ExactBackend,
    IntelGpuBackend,
    MockBackend,
)
from qmr.backends.base import error_values
from qmr.backends.cpu_quantum import (
    CircuitMetrics,
    QuantumBudget,
    build_estimation_problem,
    build_visibility_lookup_oracle,
    build_visibility_operators,
    plan_budget,
)
from qmr.backends.monte_carlo import wilson_interval
from qmr.backends.registry import create_backend
from qmr.models import Algorithm
from qmr.scenes import closed_chamber, open_sky, single_wall


def test_exact_open_and_closed_baselines() -> None:
    backend = ExactBackend()
    opened = backend.estimate(open_sky().request(direction_count=8))
    closed = backend.estimate(closed_chamber().request(direction_count=8))

    assert opened.estimate == opened.ground_truth == 1
    assert closed.estimate == closed.ground_truth == 0
    assert opened.oracle_calls == closed.oracle_calls == 8
    assert closed.relative_error is None
    assert opened.process_rss_bytes is not None
    assert opened.peak_memory_bytes is None


def test_relative_error_is_undefined_for_zero_truth() -> None:
    assert error_values(0.0, 0.0) == (0.0, None)
    assert error_values(0.25, 0.0) == (0.25, None)


def test_monte_carlo_is_seeded_and_reports_wilson_interval() -> None:
    request = single_wall().request(
        direction_count=16,
        algorithm=Algorithm.CLASSICAL_MONTE_CARLO,
        seed=41,
        max_oracle_calls=37,
    )
    first = ClassicalMonteCarloBackend().estimate(request)
    second = ClassicalMonteCarloBackend().estimate(request)

    assert first.estimate == second.estimate
    assert first.oracle_calls == 37
    assert first.confidence_interval is not None
    assert first.confidence_interval.low <= first.estimate <= first.confidence_interval.high


@pytest.mark.parametrize(
    ("successes", "samples", "expected_endpoint"),
    [(0, 105, ("low", 0.0)), (490, 490, ("high", 1.0))],
)
def test_wilson_interval_contains_exact_bernoulli_boundaries(
    successes: int, samples: int, expected_endpoint: tuple[str, float]
) -> None:
    low, high = wilson_interval(successes, samples, 0.95)

    assert {"low": low, "high": high}[expected_endpoint[0]] == expected_endpoint[1]
    assert low <= successes / samples <= high


@pytest.mark.parametrize(("successes", "samples"), [(-1, 10), (11, 10), (0, 0)])
def test_wilson_interval_rejects_invalid_counts(successes: int, samples: int) -> None:
    with pytest.raises(ValueError):
        wilson_interval(successes, samples, 0.95)


def test_quantum_budget_is_monotone_and_never_exceeds_limit() -> None:
    budgets = []
    for maximum in range(1, 257):
        budget = plan_budget(maximum, 0.05)
        assert 1 <= budget.table_oracle_calls <= maximum
        assert budget.logical_lookup_oracle_calls == budget.shots_per_circuit * sum(
            2 * power + 1 for power in budget.schedule
        )
        budgets.append(budget)

    assert [budget.table_oracle_calls for budget in budgets] == sorted(
        budget.table_oracle_calls for budget in budgets
    )
    assert [max(budget.schedule) for budget in budgets] == sorted(
        max(budget.schedule) for budget in budgets
    )


@pytest.mark.parametrize(
    ("maximum", "accuracy"),
    [(0, 0.1), (-1, 0.1), (1, 0.0), (1, -0.1), (1, 1.1), (1, math.nan), (1, math.inf)],
)
def test_quantum_budget_rejects_invalid_inputs(maximum: int, accuracy: float) -> None:
    with pytest.raises(ValueError):
        plan_budget(maximum, accuracy)


def test_quantum_budget_cost_components_are_not_interchangeable() -> None:
    budget = QuantumBudget(schedule=(0, 1, 4), shots_per_circuit=3)

    assert budget.state_preparation_applications == 24
    assert budget.inverse_state_preparation_applications == 15
    assert budget.logical_lookup_oracle_calls == 39
    assert budget.grover_iterations == budget.good_state_markings == 15
    assert budget.total_shots == 9
    assert budget.distinct_circuits == 3
    assert budget.sampler_jobs == 1
    assert budget.total_shots != budget.logical_lookup_oracle_calls


@pytest.mark.parametrize("table", [[0, 0], [1, 1], [0, 1, 1, 0]])
def test_visibility_lookup_oracle_maps_every_basis_state(table: list[int]) -> None:
    oracle = build_visibility_lookup_oracle(table)
    index_qubits = int(math.log2(len(table)))

    for index in range(len(table)):
        for objective in (0, 1):
            initial = index | (objective << index_qubits)
            expected = index | ((objective ^ table[index]) << index_qubits)
            evolved = Statevector.from_int(initial, 2**oracle.num_qubits).evolve(oracle)
            assert evolved.probabilities()[expected] == pytest.approx(1.0, abs=1e-12)


@pytest.mark.parametrize("table", [[], [0, 1, 0], [0, 2]])
def test_visibility_lookup_oracle_rejects_invalid_tables(table: list[int]) -> None:
    with pytest.raises(ValueError):
        build_visibility_lookup_oracle(table)


@pytest.mark.parametrize(
    "table",
    [[0] * 8, [1] * 8, [1, 1, 1, 0, 0, 0, 0, 0]],
)
def test_state_preparation_probability_is_exact_table_mean(table: list[int]) -> None:
    problem = build_estimation_problem(table)
    probability = Statevector.from_instruction(problem.state_preparation).probabilities(
        problem.objective_qubits
    )[1]

    assert probability == pytest.approx(sum(table) / len(table), abs=1e-12)


def test_grover_powers_follow_the_amplitude_amplification_formula() -> None:
    table = [0, 1, 0, 0]
    amplitude = sum(table) / len(table)
    theta = math.asin(math.sqrt(amplitude))
    problem = build_estimation_problem(table)
    schedule = [0, 1, 2]
    algorithm = MaximumLikelihoodAmplitudeEstimation(schedule)

    for power, circuit in zip(
        schedule, algorithm.construct_circuits(problem, measurement=False), strict=True
    ):
        measured = Statevector.from_instruction(circuit).probabilities(problem.objective_qubits)[1]
        expected = math.sin((2 * power + 1) * theta) ** 2
        assert measured == pytest.approx(expected, abs=1e-12)


def test_all_eight_entry_truth_tables_follow_the_grover_rotation_formula() -> None:
    schedule = [0, 1, 2]
    algorithm = MaximumLikelihoodAmplitudeEstimation(schedule)
    tolerance = 2e-14

    for mask in range(2**8):
        table = [(mask >> index) & 1 for index in range(8)]
        amplitude = sum(table) / len(table)
        theta = math.asin(math.sqrt(amplitude))
        problem = build_estimation_problem(table)
        circuits = algorithm.construct_circuits(problem, measurement=False)

        for power, circuit in zip(schedule, circuits, strict=True):
            measured = Statevector.from_instruction(circuit).probabilities(
                problem.objective_qubits
            )[1]
            expected = math.sin((2 * power + 1) * theta) ** 2
            error = abs(float(measured) - expected)
            assert error <= tolerance, (
                f"floating-point tolerance {tolerance:g} exceeded for "
                f"table mask={mask}, Grover power={power}: error={error}"
            )


def test_visibility_operators_have_explicit_scientific_roles() -> None:
    operators = build_visibility_operators([0, 1, 0, 0])

    assert operators.lookup_oracle.name == "U_f_visibility"
    assert operators.state_preparation.name == "A_visibility"
    assert operators.good_state_reflection.name == "S_good_visibility"
    assert operators.grover_operator.name == "Q_visibility"
    assert operators.objective_qubit == 2


@pytest.mark.parametrize(("scene_factory", "expected"), [(open_sky, 1.0), (closed_chamber, 0.0)])
def test_cpu_quantum_uses_finite_shots_without_statevector_read(
    scene_factory: object, expected: float
) -> None:
    request = scene_factory().request(  # type: ignore[operator]
        direction_count=8,
        algorithm=Algorithm.CPU_QUANTUM,
        seed=9,
        desired_accuracy=0.2,
        max_oracle_calls=96,
    )
    result = CpuQuantumBackend().estimate(request)

    assert result.estimate == pytest.approx(expected, abs=0.05)
    assert result.ground_truth == expected
    assert result.oracle_calls <= request.max_oracle_calls
    assert result.qubit_count == 4
    assert result.shots is not None and result.shots > 0
    assert result.circuit_executions is not None and result.circuit_executions > 0
    assert result.metadata["statevector_probabilities_read"] is False
    assert result.confidence_interval is not None
    assert result.confidence_interval.low <= expected <= result.confidence_interval.high
    assert result.confidence_interval.level == request.confidence_level
    assert result.confidence_interval.method == "qiskit_mlae_asymptotic_likelihood_ratio_outer"


def test_cpu_quantum_handles_nonconstant_oracle_reproducibly() -> None:
    request = single_wall().request(
        direction_count=8,
        algorithm=Algorithm.CPU_QUANTUM,
        seed=11,
        desired_accuracy=0.2,
        max_oracle_calls=96,
    )
    first = CpuQuantumBackend().estimate(request)
    second = CpuQuantumBackend().estimate(request)
    pinned_seed_estimates = [
        first.estimate,
        *(
            CpuQuantumBackend().estimate(request.model_copy(update={"seed": seed})).estimate
            for seed in (12, 13, 17)
        ),
    ]

    assert first.estimate == second.estimate
    # Different seeds may legitimately collide; this pinned ensemble only diagnoses
    # that finite-shot variation remains observable in the current implementation.
    assert len(set(pinned_seed_estimates)) >= 2
    assert first.oracle_calls <= request.max_oracle_calls
    assert 0 < first.estimate < 1
    assert first.shots is not None and first.oracle_calls != first.shots
    costs = first.metadata["quantum_costs"]
    assert costs["logical_lookup_oracle_calls"] == first.oracle_calls
    assert costs["total_measurement_shots"] == first.shots
    assert costs["distinct_power_circuits"] == first.circuit_executions
    assert (
        costs["state_preparation_A_applications"]
        + costs["inverse_state_preparation_A_dagger_applications"]
        == first.oracle_calls
    )

    metrics = first.metadata["per_circuit_transpiled_metrics"]
    assert first.circuit_depth == max(item["quantum_depth"] for item in metrics)
    assert first.gate_count == max(item["quantum_gate_count"] for item in metrics)
    for item in metrics:
        operation_counts = item["operation_counts_including_non_gates"]
        expected_gate_count = sum(
            count
            for operation, count in operation_counts.items()
            if operation not in {"barrier", "measure"}
        )
        assert item["quantum_gate_count"] == expected_gate_count
    schedule_gate_count = sum(item["quantum_gate_count"] for item in metrics)
    assert first.metadata["schedule_transpiled_quantum_gate_count"] == schedule_gate_count
    assert first.metadata["shot_weighted_transpiled_quantum_gate_count"] == (
        first.metadata["shots_per_circuit"] * schedule_gate_count
    )
    assert "analysis-only" in first.metadata["resource_metric_scope"]
    assert first.metadata["requested_max_oracle_calls"] == request.max_oracle_calls
    assert first.metadata["unused_logical_oracle_budget"] == (
        request.max_oracle_calls - first.oracle_calls
    )
    assert first.metadata["stopping_criterion"].startswith("none")
    assert first.metadata["confidence_level_affects_schedule"] is False
    assert first.metadata["adaptive_iterations"] == 0


def test_cpu_quantum_estimates_known_intermediate_amplitude(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = [1, 1, 1, 0, 0, 0, 0, 0]
    monkeypatch.setattr(cpu_quantum, "visibility_table", lambda _request: table)
    request = open_sky().request(
        direction_count=8,
        algorithm=Algorithm.CPU_QUANTUM,
        seed=17,
        desired_accuracy=0.2,
        max_oracle_calls=900,
    )

    result = CpuQuantumBackend().estimate(request)

    assert result.ground_truth == 3 / 8
    assert result.estimate == pytest.approx(3 / 8, abs=0.03)
    assert result.confidence_interval is not None
    assert result.confidence_interval.low <= 3 / 8 <= result.confidence_interval.high


def test_cpu_quantum_returns_estimator_output_not_exact_truth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeMlae:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        def estimate(self, _problem: object) -> SimpleNamespace:
            return SimpleNamespace(estimation=0.25, num_oracle_queries=2)

        def compute_confidence_interval(
            self, _result: object, *, alpha: float, kind: str
        ) -> tuple[float, float]:
            assert alpha == pytest.approx(0.05)
            assert kind == "likelihood_ratio"
            return 0.2, 0.3

    monkeypatch.setattr(cpu_quantum, "visibility_table", lambda _request: [1] * 8)
    monkeypatch.setattr(cpu_quantum, "MaximumLikelihoodAmplitudeEstimation", FakeMlae)
    monkeypatch.setattr(
        cpu_quantum,
        "_circuit_metrics",
        lambda *_args: CircuitMetrics(0, 0, 0, 0, ()),
    )
    request = open_sky().request(
        direction_count=8,
        algorithm=Algorithm.CPU_QUANTUM,
        max_oracle_calls=8,
    )

    result = CpuQuantumBackend().estimate(request)

    assert result.ground_truth == 1.0
    assert result.estimate == 0.25
    assert result.confidence_interval is not None
    assert (result.confidence_interval.low, result.confidence_interval.high) == (0.2, 0.3)


def test_mock_and_registry_are_deterministic() -> None:
    request = open_sky().request()
    assert MockBackend(0.25).estimate(request).estimate == 0.25
    assert create_backend("exact").name == "exact"


def test_unconfigured_intel_backend_fails_explicitly() -> None:
    backend = IntelGpuBackend()
    assert not backend.capability().available
    with pytest.raises(BackendUnavailableError, match="No Intel GPU simulator provider"):
        backend.estimate(open_sky().request(algorithm=Algorithm.INTEL_GPU))
