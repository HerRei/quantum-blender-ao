"""Configuration-driven, append-free benchmark execution and raw result export."""

from __future__ import annotations

import csv
import json
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import yaml
from pydantic import Field

from qmr.backends.base import BackendUnavailableError
from qmr.backends.registry import create_backend
from qmr.models import Algorithm, LightingResult, StrictModel
from qmr.plots import PlotReport, generate_plots
from qmr.scenes import all_scenes


class BenchmarkConfig(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    name: str = Field(min_length=1)
    scenes: list[str] = Field(min_length=1)
    backends: list[Algorithm] = Field(min_length=1)
    direction_counts: list[Literal[8, 16, 32, 64]] = Field(min_length=1)
    oracle_budgets: list[int] = Field(min_length=1)
    seeds: list[int] = Field(min_length=1)
    desired_accuracy: float = Field(default=0.05, gt=0, le=0.5)
    confidence_level: float = Field(default=0.95, gt=0, lt=1)
    generate_plots: bool = True
    fail_fast: bool = False

    @classmethod
    def load(cls, path: Path) -> BenchmarkConfig:
        with path.open("rb") as stream:
            if path.suffix.lower() == ".toml":
                data = tomllib.load(stream)
            elif path.suffix.lower() in {".yaml", ".yml"}:
                data = yaml.safe_load(stream)
            else:
                raise ValueError("benchmark config must use .toml, .yaml, or .yml")
        return cls.model_validate(data)


@dataclass(frozen=True, slots=True)
class BenchmarkArtifacts:
    jsonl: Path
    csv: Path
    plots: PlotReport | None
    successful_runs: int
    skipped_runs: int
    failed_runs: int


def _record(
    *,
    config: BenchmarkConfig,
    scene: str,
    direction_count: int,
    backend: Algorithm,
    seed: int,
    budget: int,
    status: str,
    result: LightingResult | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "run_id": str(uuid4()),
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "benchmark_name": config.name,
        "scene": scene,
        "direction_count": direction_count,
        "requested_backend": str(backend),
        "seed": seed,
        "requested_oracle_budget": budget,
        "desired_accuracy": config.desired_accuracy,
        "confidence_level": config.confidence_level,
        "status": status,
        "error": error,
        "result": result.model_dump(mode="json") if result else None,
    }


def _flatten(record: dict[str, Any]) -> dict[str, Any]:
    flat = {key: value for key, value in record.items() if key != "result"}
    result = record.get("result")
    if not isinstance(result, dict):
        return flat
    interval = result.pop("confidence_interval", None)
    for key, value in result.items():
        if isinstance(value, (dict, list)):
            flat[key] = json.dumps(value, sort_keys=True, separators=(",", ":"))
        else:
            flat[key] = value
    if isinstance(interval, dict):
        flat.update({f"confidence_{key}": value for key, value in interval.items()})
    return flat


def _write_records(records: list[dict[str, Any]], jsonl_path: Path, csv_path: Path) -> None:
    with jsonl_path.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")

    rows = [_flatten(json.loads(json.dumps(record))) for record in records]
    fieldnames: list[str] = []
    for row in rows:
        fieldnames.extend(key for key in row if key not in fieldnames)
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_benchmark(config: BenchmarkConfig, output_dir: Path) -> BenchmarkArtifacts:
    """Execute the requested matrix and write new timestamped CSV/JSONL files."""

    known_scenes = all_scenes()
    missing = sorted(set(config.scenes) - set(known_scenes))
    if missing:
        raise ValueError(f"unknown synthetic scenes: {missing}")
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    stem = f"{config.name}-{stamp}-{uuid4().hex[:8]}"
    jsonl_path = output_dir / f"{stem}.jsonl"
    csv_path = output_dir / f"{stem}.csv"

    records: list[dict[str, Any]] = []
    for scene_name, direction_count, backend_name in product(
        config.scenes, config.direction_counts, config.backends
    ):
        scene = known_scenes[scene_name]
        backend = create_backend(backend_name)
        capability = backend.capability()
        combinations: list[tuple[int, int]]
        if backend_name == Algorithm.EXACT:
            combinations = [(config.seeds[0], direction_count)]
        else:
            combinations = list(product(config.seeds, config.oracle_budgets))

        for seed, budget in combinations:
            if not capability.available:
                records.append(
                    _record(
                        config=config,
                        scene=scene_name,
                        direction_count=direction_count,
                        backend=backend_name,
                        seed=seed,
                        budget=budget,
                        status="skipped",
                        error=capability.reason,
                    )
                )
                continue
            request = scene.request(
                direction_count=direction_count,
                algorithm=backend_name,
                seed=seed,
                desired_accuracy=config.desired_accuracy,
                max_oracle_calls=budget,
            )
            try:
                result = backend.estimate(request)
                records.append(
                    _record(
                        config=config,
                        scene=scene_name,
                        direction_count=direction_count,
                        backend=backend_name,
                        seed=seed,
                        budget=budget,
                        status="ok",
                        result=result,
                    )
                )
            except BackendUnavailableError as exc:
                records.append(
                    _record(
                        config=config,
                        scene=scene_name,
                        direction_count=direction_count,
                        backend=backend_name,
                        seed=seed,
                        budget=budget,
                        status="skipped",
                        error=str(exc),
                    )
                )
            except Exception as exc:
                if config.fail_fast:
                    raise
                records.append(
                    _record(
                        config=config,
                        scene=scene_name,
                        direction_count=direction_count,
                        backend=backend_name,
                        seed=seed,
                        budget=budget,
                        status="failed",
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )

    _write_records(records, jsonl_path, csv_path)
    plot_report = (
        generate_plots(records, output_dir.parent / "plots", stem)
        if config.generate_plots
        else None
    )
    return BenchmarkArtifacts(
        jsonl=jsonl_path,
        csv=csv_path,
        plots=plot_report,
        successful_runs=sum(record["status"] == "ok" for record in records),
        skipped_runs=sum(record["status"] == "skipped" for record in records),
        failed_runs=sum(record["status"] == "failed" for record in records),
    )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]
