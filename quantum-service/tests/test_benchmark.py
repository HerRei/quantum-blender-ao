from __future__ import annotations

import json
from pathlib import Path

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


def test_plotter_skips_gpu_comparison_without_fabricating_data(tmp_path: Path) -> None:
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

    assert "cpu-vs-intel-gpu" in report.skipped
    assert not any("cpu-vs-intel-gpu" in path.name for path in report.generated)
    assert json.loads(json.dumps(result))["absolute_error"] == 0.1

