from __future__ import annotations

import pytest
from qiskit.quantum_info import Statevector  # type: ignore[import-untyped]

from qbao.estimators import (
    build_lookup_oracle,
    exact_visibility,
    monte_carlo_visibility,
    plan_budget,
    simulated_qae_visibility,
)


def test_exact_visibility_is_binary_mean() -> None:
    result = exact_visibility((1, 0, 1, 0, 1, 1, 0, 0))
    assert result.value == 0.5
    assert result.logical_queries == 8


def test_monte_carlo_is_seeded_and_budgeted() -> None:
    first = monte_carlo_visibility((1, 0, 1, 0), samples=11, seed=42)
    second = monte_carlo_visibility((1, 0, 1, 0), samples=11, seed=42)
    assert first.value == second.value
    assert first.logical_queries == 11


def test_quantum_budget_never_exceeds_cap() -> None:
    for maximum in range(1, 100):
        budget = plan_budget(maximum)
        assert 1 <= budget.logical_queries <= maximum


def test_lookup_oracle_matches_every_truth_table_entry() -> None:
    table = (0, 1, 1, 0, 1, 0, 0, 1)
    oracle = build_lookup_oracle(table)
    index_qubits = 3
    for index, expected in enumerate(table):
        initial = index
        evolved = Statevector.from_int(initial, 2**oracle.num_qubits).evolve(oracle)
        probabilities = evolved.probabilities([index_qubits])
        assert probabilities[expected] == pytest.approx(1.0)


def test_simulated_qae_handles_visibility_endpoints() -> None:
    closed = simulated_qae_visibility((0, 0, 0, 0), 24, seed=3)
    open_sky = simulated_qae_visibility((1, 1, 1, 1), 24, seed=3)
    assert closed.value == 0.0
    assert open_sky.value == 1.0
    assert closed.qubits == open_sky.qubits == 3
