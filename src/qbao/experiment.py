"""Run the three visibility estimators over ray tables exported by Blender."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Any

from qbao.estimators import (
    Estimate,
    exact_visibility,
    monte_carlo_visibility,
    simulated_qae_visibility,
    validate_table,
)


def _stable_seed(base_seed: int, table: tuple[int, ...]) -> int:
    digest = hashlib.sha256(bytes(table)).digest()
    return (base_seed + int.from_bytes(digest[:4], "big")) % (2**32)


def _rmse(values: list[float], references: list[float]) -> float:
    squared_error = sum(
        (value - ref) ** 2 for value, ref in zip(values, references, strict=True)
    )
    return math.sqrt(squared_error / len(values))


def _mae(values: list[float], references: list[float]) -> float:
    absolute_error = sum(
        abs(value - ref) for value, ref in zip(values, references, strict=True)
    )
    return absolute_error / len(values)


def _summary(records: list[dict[str, Any]], method: str) -> dict[str, float | int]:
    exact_values = [float(record["exact"]["value"]) for record in records]
    values = [float(record[method]["value"]) for record in records]
    result: dict[str, float | int] = {
        "mean_visibility": sum(values) / len(values),
        "mean_absolute_error_vs_exact": _mae(values, exact_values),
        "rmse_vs_exact": _rmse(values, exact_values),
        "logical_queries_per_probe": int(records[0][method]["logical_queries"]),
    }
    if method == "qae":
        result["max_circuit_depth"] = max(
            int(record[method]["max_circuit_depth"]) for record in records
        )
        result["max_circuit_gates"] = max(
            int(record[method]["max_circuit_gates"]) for record in records
        )
    return result


def estimate_dataset(
    dataset: dict[str, Any],
    max_logical_queries: int = 64,
    seed: int = 7,
    desired_accuracy: float = 0.125,
) -> dict[str, Any]:
    """Estimate all Blender probe tables, caching identical local geometries."""

    if dataset.get("schema_version") != 1:
        raise ValueError("unsupported visibility dataset schema")
    probes = dataset.get("probes")
    if not isinstance(probes, list) or not probes:
        raise ValueError("dataset must contain at least one probe")

    cache: dict[tuple[int, ...], tuple[Estimate, Estimate, Estimate]] = {}
    records: list[dict[str, Any]] = []
    started = perf_counter()

    for probe in probes:
        table = validate_table(probe["visibility_table"])
        cache_hit = table in cache
        if not cache_hit:
            probe_seed = _stable_seed(seed, table)
            exact = exact_visibility(table)
            qae = simulated_qae_visibility(
                table,
                max_logical_queries=max_logical_queries,
                seed=probe_seed,
                desired_accuracy=desired_accuracy,
            )
            monte_carlo = monte_carlo_visibility(
                table,
                samples=qae.logical_queries,
                seed=probe_seed,
            )
            cache[table] = (exact, monte_carlo, qae)

        exact, monte_carlo, qae = cache[table]
        records.append(
            {
                "id": probe["id"],
                "tile": probe["tile"],
                "position": probe["position"],
                "visibility_table": list(table),
                "cache_hit": cache_hit,
                "exact": exact.to_dict(),
                "monte_carlo": monte_carlo.to_dict(),
                "qae": qae.to_dict(),
            }
        )

    output: dict[str, Any] = {
        "schema_version": 1,
        "source_scene": dataset.get("scene"),
        "direction_count": dataset.get("direction_count"),
        "settings": {
            "requested_max_logical_queries": max_logical_queries,
            "desired_accuracy": desired_accuracy,
            "seed": seed,
        },
        "unique_visibility_tables": len(cache),
        "elapsed_seconds": perf_counter() - started,
        "probes": records,
    }
    output["summary"] = {
        method: _summary(records, method) for method in ("exact", "monte_carlo", "qae")
    }
    return output


def run_experiment(
    input_path: Path,
    output_path: Path,
    max_logical_queries: int,
    seed: int,
    desired_accuracy: float,
) -> dict[str, Any]:
    """Read a Blender export, run estimators, and write reproducible JSON."""

    dataset = json.loads(input_path.read_text(encoding="utf-8"))
    output = estimate_dataset(dataset, max_logical_queries, seed, desired_accuracy)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return output
