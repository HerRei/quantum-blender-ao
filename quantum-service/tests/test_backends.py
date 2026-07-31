from __future__ import annotations

import pytest

from qmr.backends import (
    BackendUnavailableError,
    ClassicalMonteCarloBackend,
    CpuQuantumBackend,
    ExactBackend,
    IntelGpuBackend,
    MockBackend,
)
from qmr.backends.cpu_quantum import plan_budget
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


def test_quantum_budget_never_exceeds_limit() -> None:
    for maximum in (1, 8, 64, 1024):
        budget = plan_budget(maximum, 0.05)
        assert 1 <= budget.table_oracle_calls <= maximum


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
    assert result.oracle_calls <= request.max_oracle_calls
    assert result.qubit_count == 4
    assert result.shots is not None and result.shots > 0
    assert result.circuit_executions is not None and result.circuit_executions > 0
    assert result.metadata["statevector_probabilities_read"] is False


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

    assert first.estimate == second.estimate
    assert first.oracle_calls <= request.max_oracle_calls
    assert 0 < first.estimate < 1


def test_mock_and_registry_are_deterministic() -> None:
    request = open_sky().request()
    assert MockBackend(0.25).estimate(request).estimate == 0.25
    assert create_backend("exact").name == "exact"


def test_unconfigured_intel_backend_fails_explicitly() -> None:
    backend = IntelGpuBackend()
    assert not backend.capability().available
    with pytest.raises(BackendUnavailableError, match="No Intel GPU simulator provider"):
        backend.estimate(open_sky().request(algorithm=Algorithm.INTEL_GPU))
