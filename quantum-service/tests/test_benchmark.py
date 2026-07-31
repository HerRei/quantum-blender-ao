from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from qmr.benchmark import BenchmarkConfig, load_jsonl, run_benchmark
from qmr.models import Algorithm
from qmr.plots import generate_plots


def test_benchmark_writes_csv_jsonl_and_plots(tmp_path: Path) -> None:
    config = BenchmarkConfig(
        name="test-fixture",
        scenes=["single_wall"],
        backends=[Algorithm.EXACT, Algorithm.CLASSICAL_MONTE_CARLO, Algorithm.CPU_QUANTUM],
        direction_counts=[8],
        oracle_budgets=[32],
        seeds=[5],
        desired_accuracy=0.25,
    )

    artifacts = run_benchmark(config, tmp_path / "results")

    assert artifacts.successful_runs == 3
    assert artifacts.skipped_runs == artifacts.failed_runs == 0
    assert artifacts.csv.is_file()
    records = load_jsonl(artifacts.jsonl)
    assert len(records) == 3
    assert all(record["status"] == "ok" for record in records)
    exact = next(record for record in records if record["requested_backend"] == "exact")
    assert exact["requested_oracle_budget"] is None
    assert exact["result"]["oracle_calls"] == 8
    assert artifacts.plots is not None
    assert any(path.suffix == ".png" for path in artifacts.plots.generated)
    assert any(path.suffix == ".pdf" for path in artifacts.plots.generated)


def test_toml_and_yaml_configs_are_supported(tmp_path: Path) -> None:
    payload = {
        "schema_version": "1.0",
        "name": "parser-test",
        "scenes": ["open_sky"],
        "backends": ["exact"],
        "direction_counts": [8],
        "oracle_budgets": [8],
        "seeds": [1],
    }
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        "schema_version: '1.0'\nname: parser-test\nscenes: [open_sky]\n"
        "backends: [exact]\ndirection_counts: [8]\noracle_budgets: [8]\nseeds: [1]\n",
        encoding="utf-8",
    )
    toml_path = tmp_path / "config.toml"
    toml_path.write_text(
        'schema_version = "1.0"\nname = "parser-test"\nscenes = ["open_sky"]\n'
        'backends = ["exact"]\ndirection_counts = [8]\noracle_budgets = [8]\nseeds = [1]\n',
        encoding="utf-8",
    )

    assert BenchmarkConfig.load(yaml_path).model_dump(mode="json") == payload | {
        "desired_accuracy": 0.05,
        "confidence_level": 0.95,
        "generate_plots": True,
        "fail_fast": False,
    }
    assert BenchmarkConfig.load(toml_path) == BenchmarkConfig.load(yaml_path)


@pytest.mark.parametrize("oracle_budgets", [[0], [-1]])
def test_benchmark_config_rejects_nonpositive_oracle_budgets(
    oracle_budgets: list[int],
) -> None:
    with pytest.raises(ValidationError):
        BenchmarkConfig(
            name="invalid-budget",
            scenes=["open_sky"],
            backends=[Algorithm.CLASSICAL_MONTE_CARLO],
            direction_counts=[8],
            oracle_budgets=oracle_budgets,
            seeds=[1],
        )


@pytest.mark.parametrize("seeds", [[-1], [2**32]])
def test_benchmark_config_rejects_out_of_range_seeds(seeds: list[int]) -> None:
    with pytest.raises(ValidationError):
        BenchmarkConfig(
            name="invalid-seed",
            scenes=["open_sky"],
            backends=[Algorithm.CLASSICAL_MONTE_CARLO],
            direction_counts=[8],
            oracle_budgets=[8],
            seeds=seeds,
        )


def test_benchmark_propagates_and_exports_requested_confidence_level(tmp_path: Path) -> None:
    config = BenchmarkConfig(
        name="confidence-level",
        scenes=["single_wall"],
        backends=[Algorithm.CLASSICAL_MONTE_CARLO],
        direction_counts=[8],
        oracle_budgets=[32],
        seeds=[1],
        confidence_level=0.8,
        generate_plots=False,
    )

    artifacts = run_benchmark(config, tmp_path / "results")
    record = load_jsonl(artifacts.jsonl)[0]
    interval = record["result"]["confidence_interval"]
    with artifacts.csv.open(encoding="utf-8", newline="") as stream:
        row = next(csv.DictReader(stream))

    assert record["requested_confidence_level"] == 0.8
    assert interval["level"] == 0.8
    assert float(row["requested_confidence_level"]) == 0.8
    assert float(row["result_confidence_interval_level"]) == 0.8
    assert "confidence_level" not in row


def test_exploratory_plotter_skips_missing_resource_data_without_fabricating(
    tmp_path: Path,
) -> None:
    result = {
        "backend": "cpu_quantum",
        "absolute_error": 0.1,
        "oracle_calls": 31,
        "end_to_end_ms": 4.0,
        "simulation_ms": 2.0,
        "qubit_count": 4,
        "circuit_depth": 20,
        "peak_memory_bytes": 1024,
    }
    records = [{"status": "ok", "result": result}]

    report = generate_plots(records, tmp_path, "fixture")

    assert "shot-weighted-gates-vs-logical-oracle-calls" in report.skipped
    assert not any("rmse" in path.name for path in report.generated)
    assert json.loads(json.dumps(result))["absolute_error"] == 0.1
