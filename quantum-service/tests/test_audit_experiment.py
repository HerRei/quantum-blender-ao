from __future__ import annotations

import csv
import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest
from qiskit_algorithms import MaximumLikelihoodAmplitudeEstimation

import qmr.audit_experiment as audit_experiment
from qmr.audit_experiment import (
    ANALYTICAL_MODEL,
    BASELINE_COMMIT,
    EXACT_ENUMERATION_CALLS,
    PLOT_NAMES,
    AuditExperimentConfig,
    FixedGridMlae,
    aggregate_analytical_records,
    aggregate_runtime_records,
    assert_clean_worktree,
    audit_designs,
    balanced_runtime_execution_plan,
    build_bundle_manifest,
    combine_exact_control_summary,
    contiguous_prefix_visibility_table,
    exact_statistical_control,
    generate_audit_plots,
    qae_good_probabilities,
    regenerate_audit_plots,
    run_actual_runtime_records,
    run_exact_control_records,
    run_scientific_audit,
    simulate_analytical_records,
    visibility_table_sha256,
    write_jsonl_csv,
)
from qmr.backends.cpu_quantum import build_estimation_problem

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPOSITORY_ROOT / "experiments/configs/scientific-audit.toml"


def _small_config(**updates: object) -> AuditExperimentConfig:
    defaults: dict[str, object] = {
        "amplitude_numerators": [8],
        "requested_oracle_budgets": [32, 64],
        "analytical_replicates": 2,
        "mle_grid_points": 1025,
        "runtime_warmup_repeats": 0,
        "runtime_measured_repeats": 1,
    }
    defaults.update(updates)
    return AuditExperimentConfig.load(CONFIG_PATH).model_copy(update=defaults)


def test_checked_in_audit_config_matches_preregistered_protocol() -> None:
    config = AuditExperimentConfig.load(CONFIG_PATH)

    config.validate_scientific_protocol()
    designs = audit_designs(config)

    assert [design.logical_lookup_oracle_calls for design in designs] == [
        18,
        35,
        105,
        245,
        490,
        1015,
    ]
    assert [design.schedule for design in designs] == [
        (0, 1, 2, 4),
        (0, 1, 2, 4, 8),
        (0, 1, 2, 4, 8),
        (0, 1, 2, 4, 8),
        (0, 1, 2, 4, 8),
        (0, 1, 2, 4, 8),
    ]
    assert EXACT_ENUMERATION_CALLS == config.amplitude_denominator == 64


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("schema_version", "2.0"),
        ("name", "smoke"),
        ("baseline_commit", "0" * 40),
        ("amplitude_denominator", 32),
        ("amplitude_numerators", [0, 64]),
        ("requested_oracle_budgets", [32, 64]),
        ("desired_accuracy", 0.1),
        ("confidence_level", 0.9),
        ("analytical_replicates", 255),
        ("mle_grid_points", 4097),
        ("base_seed", 1),
        ("bootstrap_replicates", 1000),
        ("bootstrap_confidence_level", 0.9),
        ("bootstrap_seed", 1),
        ("runtime_order_seed", 1),
        ("runtime_warmup_repeats", 0),
        ("runtime_measured_repeats", 4),
        ("runtime_fail_fast", True),
        ("table_layout", "not-the-preregistered-layout"),
        ("require_clean_worktree", False),
    ],
)
def test_scientific_protocol_rejects_every_preregistered_field_change(
    field_name: str, invalid_value: object
) -> None:
    config = AuditExperimentConfig.load(CONFIG_PATH).model_copy(update={field_name: invalid_value})

    with pytest.raises(ValueError, match=r"scientific audit requires|baseline_commit"):
        config.validate_scientific_protocol()


@pytest.mark.parametrize(
    ("good_count", "expected"),
    [(0, 0.0), (25, 0.25), (100, 1.0)],
)
def test_fixed_grid_global_mlae_matches_known_single_circuit_counts(
    good_count: int, expected: float
) -> None:
    estimator = FixedGridMlae(1025)

    result = estimator.estimate(
        schedule=(0,),
        shots_per_circuit=100,
        good_counts=[good_count],
        confidence_level=0.95,
    )

    assert result.estimate == pytest.approx(expected, abs=1 / 1024)
    assert result.confidence_low <= expected <= result.confidence_high


def test_fixed_grid_multi_power_mle_matches_qiskit_public_compute_mle() -> None:
    amplitude = 0.23
    schedule = (0, 1, 2, 4)
    shots = 400
    good_counts = [
        round(probability * shots) for probability in qae_good_probabilities(amplitude, schedule)
    ]
    fixed_grid = FixedGridMlae(65_537).estimate(
        schedule=schedule,
        shots_per_circuit=shots,
        good_counts=good_counts,
        confidence_level=0.95,
    )
    qiskit_mlae = MaximumLikelihoodAmplitudeEstimation(evaluation_schedule=list(schedule))
    problem = build_estimation_problem(contiguous_prefix_visibility_table(8))
    theta = qiskit_mlae.compute_mle(
        [{"1": good_count, "0": shots - good_count} for good_count in good_counts],
        problem,
    )

    assert isinstance(theta, float)
    assert fixed_grid.estimate == pytest.approx(math.sin(theta) ** 2, abs=3e-5)


def test_analytical_records_are_deterministic_and_mc_matches_realized_qae_calls() -> None:
    config = _small_config()
    designs = audit_designs(config)

    first = simulate_analytical_records(config, designs)
    second = simulate_analytical_records(config, designs)

    assert first == second
    assert len(first) == 8
    grouped: dict[tuple[int, int], list[dict[str, object]]] = {}
    for record in first:
        key = (int(record["requested_oracle_budget"]), int(record["replicate"]))
        grouped.setdefault(key, []).append(record)
    for records in grouped.values():
        qae = next(record for record in records if record["method"] == "analytical_mlae")
        mc = next(record for record in records if record["method"] == "classical_monte_carlo")
        assert qae["logical_lookup_oracle_calls"] == mc["logical_lookup_oracle_calls"]
        assert mc["classical_samples"] == qae["logical_lookup_oracle_calls"]
        assert len(qae["per_circuit_good_counts"]) == len(qae["evaluation_schedule"])
        assert qae["analysis_model"] == ANALYTICAL_MODEL
        assert "statevector" in str(qae["analysis_model"])
        expected_table = contiguous_prefix_visibility_table(8)
        assert expected_table == [1] * 8 + [0] * 56
        assert qae["table_layout"] == "contiguous_prefix_visible_then_blocked"
        assert qae["visibility_table_sha256"] == visibility_table_sha256(expected_table)
        assert qae["visibility_table_sha256"] == mc["visibility_table_sha256"]
        assert qae["confidence_interval_method"] == (
            "audit_fixed_grid_likelihood_ratio_envelope_not_qiskit_ci"
        )
        assert qae["requested_budget_ge_domain_size"] == (int(qae["requested_oracle_budget"]) >= 64)
        assert qae["realized_calls_ge_domain_size"] == (
            int(qae["logical_lookup_oracle_calls"]) >= 64
        )
        assert qae["status"] == mc["status"] == "ok"


@pytest.mark.parametrize("numerator", [0, 64])
def test_analytical_mc_interval_covers_exact_boundaries(numerator: int) -> None:
    config = _small_config(
        amplitude_numerators=[numerator],
        requested_oracle_budgets=[128],
        analytical_replicates=1,
    )

    records = simulate_analytical_records(config, audit_designs(config))
    mc = next(record for record in records if record["method"] == "classical_monte_carlo")

    assert mc["confidence_interval_covers_truth"] is True
    assert mc["confidence_interval_low"] <= numerator / 64 <= mc["confidence_interval_high"]


def _aggregate_fixture_record(
    *, requested: int, calls: int, estimate: float, replicate: int
) -> dict[str, object]:
    truth = 0.5
    error = estimate - truth
    return {
        "method": "classical_monte_carlo",
        "amplitude_numerator": 32,
        "amplitude_denominator": 64,
        "requested_oracle_budget": requested,
        "logical_lookup_oracle_calls": calls,
        "evaluation_schedule": None,
        "shots_per_circuit": None,
        "replicate": replicate,
        "status": "ok",
        "estimate": estimate,
        "signed_error": error,
        "absolute_error": abs(error),
        "squared_error": error * error,
        "confidence_interval_low": max(0.0, estimate - 0.2),
        "confidence_interval_high": min(1.0, estimate + 0.2),
        "confidence_interval_covers_truth": True,
        "requested_confidence_level": 0.95,
    }


def test_aggregation_computes_bias_rmse_sample_std_and_full_range_slope() -> None:
    records = [
        _aggregate_fixture_record(requested=10, calls=10, estimate=0.4, replicate=0),
        _aggregate_fixture_record(requested=10, calls=10, estimate=0.6, replicate=1),
        _aggregate_fixture_record(requested=20, calls=20, estimate=0.45, replicate=0),
        _aggregate_fixture_record(requested=20, calls=20, estimate=0.55, replicate=1),
    ]

    summary = aggregate_analytical_records(records, bootstrap_replicates=500, bootstrap_seed=1234)
    repeated = aggregate_analytical_records(records, bootstrap_replicates=500, bootstrap_seed=1234)

    assert summary == repeated
    assert len(summary) == 2
    assert summary[0]["bias"] == pytest.approx(0.0)
    assert summary[0]["rmse"] == pytest.approx(0.1)
    assert summary[0]["sample_std"] == pytest.approx(math.sqrt(0.02))
    assert summary[1]["rmse"] == pytest.approx(0.05)
    assert summary[0]["full_range_loglog_rmse_slope"] == pytest.approx(-1.0)
    assert summary[0]["full_range_loglog_rmse_slope_bootstrap_ci_low"] == pytest.approx(-1.0)
    assert summary[0]["full_range_loglog_rmse_slope_bootstrap_ci_high"] == pytest.approx(-1.0)
    assert summary[0]["slope_bootstrap_valid_resamples"] == 500
    assert summary[0]["slope_bootstrap_joint_replicates"] == 2
    assert summary[0]["bias_bootstrap_ci_low"] <= summary[0]["bias"]
    assert summary[0]["bias"] <= summary[0]["bias_bootstrap_ci_high"]
    assert summary[0]["rmse_bootstrap_ci_low"] <= summary[0]["rmse"]
    assert summary[0]["rmse"] <= summary[0]["rmse_bootstrap_ci_high"]
    assert summary[1]["slope_point_count"] == 2


def test_runtime_summary_bootstraps_end_to_end_and_preserves_phase_medians_and_failures() -> None:
    common: dict[str, object] = {
        "method": "qiskit_statevector_mlae",
        "execution_model": "test statevector execution",
        "amplitude_numerator": 8,
        "amplitude_denominator": 64,
        "requested_oracle_budget": 32,
        "logical_lookup_oracle_calls": 18,
        "oracle_domain_size": 64,
        "requested_budget_ge_domain_size": False,
        "realized_calls_ge_domain_size": False,
        "warmup": False,
        "max_transpiled_quantum_depth": 100,
        "max_transpiled_quantum_gate_count": 200,
        "schedule_transpiled_quantum_gate_count": 300,
        "shot_weighted_transpiled_quantum_gate_count": 600,
    }
    records = [
        {
            **common,
            "repeat": 0,
            "status": "ok",
            "estimator_runtime_ms": 10.0,
            "audit_end_to_end_ms": 20.0,
            "oracle_synthesis_ms": 1.0,
            "sampler_algorithm_setup_ms": 2.0,
            "analysis_copy_transpilation_ms": 3.0,
            "confidence_interval_postprocessing_ms": 4.0,
        },
        {
            **common,
            "repeat": 1,
            "status": "ok",
            "estimator_runtime_ms": 20.0,
            "audit_end_to_end_ms": 40.0,
            "oracle_synthesis_ms": 3.0,
            "sampler_algorithm_setup_ms": 4.0,
            "analysis_copy_transpilation_ms": 5.0,
            "confidence_interval_postprocessing_ms": 6.0,
        },
        {
            **common,
            "repeat": 2,
            "status": "failed",
            "error": "SyntheticError: expected test failure",
            "audit_end_to_end_ms": 5.0,
        },
    ]

    summary = aggregate_runtime_records(records, bootstrap_replicates=500, bootstrap_seed=77)
    repeated = aggregate_runtime_records(records, bootstrap_replicates=500, bootstrap_seed=77)

    assert summary == repeated
    assert len(summary) == 1
    row = summary[0]
    assert row["n"] == 2
    assert row["n_requested"] == 3
    assert row["n_failed"] == 1
    assert row["failure_messages"] == ["SyntheticError: expected test failure"]
    assert row["median_estimator_runtime_ms"] == 15.0
    assert row["median_audit_end_to_end_ms"] == 30.0
    assert row["median_oracle_synthesis_ms"] == 2.0
    assert row["median_sampler_algorithm_setup_ms"] == 3.0
    assert row["median_analysis_copy_transpilation_ms"] == 4.0
    assert row["median_confidence_interval_postprocessing_ms"] == 5.0
    assert row["median_audit_end_to_end_ms_bootstrap_ci_low"] <= 30.0
    assert row["median_audit_end_to_end_ms_bootstrap_ci_high"] >= 30.0


def _plot_summaries() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    analytical: list[dict[str, object]] = [
        {
            "method": "exact_enumeration",
            "amplitude_numerator": numerator,
            "amplitude_denominator": 64,
            "logical_lookup_oracle_calls": 64,
            "rmse": 0.0,
            "bias": 0.0,
            "sample_std": 0.0,
            "rmse_bootstrap_ci_low": 0.0,
            "rmse_bootstrap_ci_high": 0.0,
            "bias_bootstrap_ci_low": 0.0,
            "bias_bootstrap_ci_high": 0.0,
            "sample_std_bootstrap_ci_low": 0.0,
            "sample_std_bootstrap_ci_high": 0.0,
            "n": 1,
            "n_requested": 1,
            "n_failed": 0,
        }
        for numerator in (0, 8)
    ]
    runtime: list[dict[str, object]] = [
        {
            "method": "exact_enumeration",
            "amplitude_numerator": numerator,
            "amplitude_denominator": 64,
            "logical_lookup_oracle_calls": 64,
            "median_estimator_runtime_ms": 0.01,
            "median_audit_end_to_end_ms": 0.01,
            "median_audit_end_to_end_ms_bootstrap_ci_low": 0.009,
            "median_audit_end_to_end_ms_bootstrap_ci_high": 0.011,
            "n": 5,
            "n_requested": 5,
            "n_failed": 0,
            "max_transpiled_quantum_depth": None,
            "max_transpiled_quantum_gate_count": None,
            "shot_weighted_transpiled_quantum_gate_count": None,
        }
        for numerator in (0, 8)
    ]
    for method in ("classical_monte_carlo", "analytical_mlae"):
        for numerator in (0, 8):
            for requested, calls in ((32, 18), (64, 35)):
                rmse = 0.0 if numerator == 0 else 0.1 / math.sqrt(calls)
                std = 0.0 if numerator == 0 else 0.08 / math.sqrt(calls)
                analytical.append(
                    {
                        "method": method,
                        "amplitude_numerator": numerator,
                        "amplitude_denominator": 64,
                        "requested_oracle_budget": requested,
                        "logical_lookup_oracle_calls": calls,
                        "rmse": rmse,
                        "bias": 0.0,
                        "sample_std": std,
                        "rmse_bootstrap_ci_low": max(0.0, rmse * 0.9),
                        "rmse_bootstrap_ci_high": rmse * 1.1,
                        "bias_bootstrap_ci_low": -0.001,
                        "bias_bootstrap_ci_high": 0.001,
                        "sample_std_bootstrap_ci_low": max(0.0, std * 0.9),
                        "sample_std_bootstrap_ci_high": std * 1.1,
                        "n": 256,
                        "n_requested": 256,
                        "n_failed": 0,
                    }
                )
    for method in ("classical_monte_carlo", "qiskit_statevector_mlae"):
        for numerator in (0, 8):
            for requested, calls in ((32, 18), (64, 35)):
                runtime.append(
                    {
                        "method": method,
                        "amplitude_numerator": numerator,
                        "amplitude_denominator": 64,
                        "requested_oracle_budget": requested,
                        "logical_lookup_oracle_calls": calls,
                        "median_estimator_runtime_ms": 0.2
                        if method == "classical_monte_carlo"
                        else 20.0,
                        "median_audit_end_to_end_ms": 0.3
                        if method == "classical_monte_carlo"
                        else 30.0,
                        "median_audit_end_to_end_ms_bootstrap_ci_low": 0.25
                        if method == "classical_monte_carlo"
                        else 25.0,
                        "median_audit_end_to_end_ms_bootstrap_ci_high": 0.35
                        if method == "classical_monte_carlo"
                        else 35.0,
                        "n": 5,
                        "n_requested": 5,
                        "n_failed": 0,
                        "max_transpiled_quantum_depth": 100 + numerator
                        if method == "qiskit_statevector_mlae"
                        else None,
                        "max_transpiled_quantum_gate_count": 200 + numerator
                        if method == "qiskit_statevector_mlae"
                        else None,
                        "shot_weighted_transpiled_quantum_gate_count": 400 + numerator
                        if method == "qiskit_statevector_mlae"
                        else None,
                    }
                )
    return analytical, runtime


def test_plotter_generates_exactly_six_preregistered_png_pdf_pairs(tmp_path: Path) -> None:
    analytical, runtime = _plot_summaries()

    generated = generate_audit_plots(analytical, runtime, tmp_path)

    assert len(generated) == 12
    assert {path.name for path in generated} == {
        f"{name}.{suffix}" for name in PLOT_NAMES for suffix in ("png", "pdf")
    }
    assert all(path.is_file() for path in generated)


def test_plots_can_be_regenerated_from_archived_config_and_three_raw_jsonl_files(
    tmp_path: Path,
) -> None:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    shutil.copy2(CONFIG_PATH, bundle_dir / "scientific-audit.toml")
    small_config = _small_config(
        requested_oracle_budgets=[32],
        analytical_replicates=2,
        runtime_measured_repeats=1,
    )
    write_jsonl_csv(
        simulate_analytical_records(small_config),
        bundle_dir / "analytical-raw.jsonl",
        bundle_dir / "analytical-raw.csv",
    )
    write_jsonl_csv(
        run_exact_control_records(small_config),
        bundle_dir / "exact-control-raw.jsonl",
        bundle_dir / "exact-control-raw.csv",
    )
    runtime_records = [
        {
            "method": method,
            "execution_model": "archived synthetic plot-regeneration fixture",
            "amplitude_numerator": 8,
            "amplitude_denominator": 64,
            "requested_oracle_budget": 32,
            "logical_lookup_oracle_calls": 18,
            "oracle_domain_size": 64,
            "requested_budget_ge_domain_size": False,
            "realized_calls_ge_domain_size": False,
            "repeat": 0,
            "warmup": False,
            "status": "ok",
            "estimator_runtime_ms": 1.0 if method == "classical_monte_carlo" else 10.0,
            "audit_end_to_end_ms": 2.0 if method == "classical_monte_carlo" else 20.0,
            "max_transpiled_quantum_depth": 100 if method == "qiskit_statevector_mlae" else None,
            "max_transpiled_quantum_gate_count": 200
            if method == "qiskit_statevector_mlae"
            else None,
            "schedule_transpiled_quantum_gate_count": 300
            if method == "qiskit_statevector_mlae"
            else None,
            "shot_weighted_transpiled_quantum_gate_count": 600
            if method == "qiskit_statevector_mlae"
            else None,
        }
        for method in ("classical_monte_carlo", "qiskit_statevector_mlae")
    ]
    write_jsonl_csv(
        runtime_records,
        bundle_dir / "runtime-raw.jsonl",
        bundle_dir / "runtime-raw.csv",
    )

    regenerated = regenerate_audit_plots(bundle_dir, tmp_path / "regenerated")

    assert {path.name for path in regenerated} == {
        f"{name}.{suffix}" for name in PLOT_NAMES for suffix in ("png", "pdf")
    }
    assert all(path.is_file() for path in regenerated)


def test_raw_archive_and_manifest_preserve_required_semantics(tmp_path: Path) -> None:
    config = _small_config(requested_oracle_budgets=[32], analytical_replicates=1)
    design = audit_designs(config)[0]
    records = simulate_analytical_records(config, [design])
    jsonl_path = tmp_path / "analytical-raw.jsonl"
    csv_path = tmp_path / "analytical-raw.csv"

    write_jsonl_csv(records, jsonl_path, csv_path)
    with csv_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    decoded = [json.loads(line) for line in jsonl_path.read_text().splitlines()]

    required = {
        "analysis_model",
        "method",
        "logical_lookup_oracle_calls",
        "replicate",
        "sampling_seed",
        "status",
        "confidence_interval_low",
        "confidence_interval_high",
        "confidence_interval_covers_truth",
        "table_layout",
        "visibility_table_sha256",
    }
    assert required <= rows[0].keys()
    assert decoded == records
    encoded_schedule = next(
        row["evaluation_schedule"] for row in rows if row["evaluation_schedule"]
    )
    assert json.loads(encoded_schedule)

    config_copy = tmp_path / "scientific-audit.toml"
    shutil.copy2(CONFIG_PATH, config_copy)
    manifest = build_bundle_manifest(
        config=config,
        repository_root=REPOSITORY_ROOT,
        output_dir=tmp_path,
        config_copy=config_copy,
        artifact_paths=[jsonl_path, csv_path],
        analytical_records=records,
        exact_records=[],
        runtime_records=[],
        designs=[design],
    )
    assert manifest["baseline_commit"] == BASELINE_COMMIT
    assert len(manifest["current_head_tree"]) == 40
    assert manifest["config_sha256"] == manifest["artifact_sha256"][config_copy.name]
    assert manifest["artifact_sha256"][jsonl_path.name]
    assert manifest["analytical_execution_model"] == ANALYTICAL_MODEL
    assert "logical_lookup_oracle_calls" in manifest["cost_model"]
    assert manifest["exact_enumeration_calls"] == 64
    assert manifest["budget_designs"][0]["requested_budget_ge_domain_size"] is False
    assert manifest["budget_designs"][0]["realized_calls_ge_domain_size"] is False
    assert set(manifest["source_sha256"]) == {
        "quantum-service/src/qmr/audit_experiment.py",
        "quantum-service/src/qmr/backends/cpu_quantum.py",
    }
    assert all(len(digest) == 64 for digest in manifest["source_sha256"].values())
    assert len(manifest["source_bundle_sha256"]) == 64
    assert manifest["truth_tables"] == [
        {
            "amplitude_numerator": 8,
            "amplitude_denominator": 64,
            "marked_count": 8,
            "table_layout": "contiguous_prefix_visible_then_blocked",
            "visibility_table_sha256": visibility_table_sha256(
                contiguous_prefix_visibility_table(8)
            ),
        }
    ]
    assert "bytes(table)" in manifest["truth_table_hash_encoding"]


def test_clean_worktree_guard_runs_before_long_run_writes_output(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "audit@example.invalid"],
        cwd=repository,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "Audit Test"], cwd=repository, check=True)
    tracked = repository / "tracked.txt"
    tracked.write_text("clean\n")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repository, check=True)

    assert_clean_worktree(repository)
    tracked.write_text("dirty\n")
    output_dir = repository / "audit-output"

    with pytest.raises(RuntimeError, match="clean Git worktree"):
        run_scientific_audit(CONFIG_PATH, output_dir, repository)
    assert not output_dir.exists()


def test_runtime_order_is_deterministic_and_balanced_per_phase() -> None:
    config = AuditExperimentConfig.load(CONFIG_PATH)
    designs = audit_designs(config)

    first = balanced_runtime_execution_plan(config, designs)
    second = balanced_runtime_execution_plan(config, designs)

    assert first == second
    assert [task["runtime_execution_sequence"] for task in first] == list(range(len(first)))
    assert len(first) == 2 * len(config.amplitude_numerators) * len(designs) * 6
    for phase in ("warmup", "measured"):
        first_positions = [
            task
            for task in first
            if task["runtime_order_phase"] == phase and task["runtime_within_pair_position"] == 0
        ]
        assert sum(task["method"] == "classical_monte_carlo" for task in first_positions) == (
            len(first_positions) // 2
        )
        assert sum(task["method"] == "qiskit_statevector_mlae" for task in first_positions) == (
            len(first_positions) // 2
        )
    assert all(
        first[index]["runtime_pair_id"] == first[index + 1]["runtime_pair_id"]
        for index in range(0, len(first), 2)
    )


def test_runtime_records_archive_the_actual_balanced_execution_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _small_config(runtime_measured_repeats=2)
    designs = audit_designs(config)

    def fake_record(*, method: str, **kwargs: object) -> dict[str, object]:
        return {
            "method": method,
            "amplitude_numerator": kwargs["numerator"],
            "repeat": kwargs["repeat"],
            "warmup": kwargs["warmup"],
            "status": "ok",
        }

    monkeypatch.setattr(
        audit_experiment,
        "_run_classical_runtime_record",
        lambda **kwargs: fake_record(method="classical_monte_carlo", **kwargs),
    )
    monkeypatch.setattr(
        audit_experiment,
        "_run_qiskit_runtime_record",
        lambda **kwargs: fake_record(method="qiskit_statevector_mlae", **kwargs),
    )

    plan = balanced_runtime_execution_plan(config, designs)
    records = run_actual_runtime_records(config, designs)

    assert len(records) == len(plan)
    archived_keys = {
        "runtime_execution_sequence",
        "runtime_phase_pair_sequence",
        "runtime_pair_id",
        "runtime_within_pair_position",
        "runtime_paired_method_order",
        "runtime_order_seed",
        "runtime_order_phase_seed",
        "runtime_order_phase",
    }
    assert [{key: record[key] for key in archived_keys} for record in records] == [
        {key: task[key] for key in archived_keys} for task in plan
    ]


def test_exact_control_has_zero_error_64_reads_and_marked_warmup() -> None:
    config = _small_config(
        amplitude_numerators=[0, 8, 64],
        runtime_warmup_repeats=1,
        runtime_measured_repeats=2,
    )

    raw = run_exact_control_records(config)
    runtime_summary = aggregate_runtime_records(raw, bootstrap_replicates=500, bootstrap_seed=99)
    repeated_runtime_summary = aggregate_runtime_records(
        raw, bootstrap_replicates=500, bootstrap_seed=99
    )
    statistical = exact_statistical_control(config)
    combined = combine_exact_control_summary(statistical, runtime_summary)

    assert len(raw) == 9
    assert sum(bool(record["warmup"]) for record in raw) == 3
    assert all(record["logical_lookup_oracle_calls"] == 64 for record in raw)
    assert all(record["absolute_error"] == 0 for record in raw)
    assert all(record["table_layout"] == "contiguous_prefix_visible_then_blocked" for record in raw)
    assert runtime_summary == repeated_runtime_summary
    assert all(row["rmse"] == row["bias"] == row["sample_std"] == 0 for row in combined)
    assert all(row["runtime_n"] == 2 for row in combined)
    assert all(row["median_audit_end_to_end_ms"] is not None for row in combined)
    assert all(
        row["median_audit_end_to_end_ms_bootstrap_ci_low"]
        <= row["median_audit_end_to_end_ms"]
        <= row["median_audit_end_to_end_ms_bootstrap_ci_high"]
        for row in combined
    )
