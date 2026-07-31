"""Headless PNG/PDF plots generated exclusively from measured raw records."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


@dataclass(frozen=True, slots=True)
class PlotReport:
    generated: tuple[Path, ...]
    skipped: tuple[str, ...]


def _successful(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if record.get("status") == "ok" and isinstance(record.get("result"), dict)
    ]


def _save(fig: Any, output_dir: Path, stem: str, plot_name: str) -> tuple[Path, Path]:
    png = output_dir / f"{stem}-{plot_name}.png"
    pdf = output_dir / f"{stem}-{plot_name}.pdf"
    fig.tight_layout()
    fig.savefig(png, dpi=160)
    fig.savefig(pdf)
    plt.close(fig)
    return png, pdf


def _scatter_by_backend(
    records: list[dict[str, Any]],
    x_key: str,
    y_key: str,
    xlabel: str,
    ylabel: str,
) -> Any | None:
    fig, axis = plt.subplots(figsize=(7, 4.5))
    plotted = False
    for backend in sorted({str(record["result"]["backend"]) for record in records}):
        pairs = [
            (record["result"].get(x_key), record["result"].get(y_key))
            for record in records
            if record["result"]["backend"] == backend
        ]
        valid = [(float(x), float(y)) for x, y in pairs if x is not None and y is not None]
        if valid:
            axis.scatter(
                [item[0] for item in valid],
                [item[1] for item in valid],
                alpha=0.75,
                label=backend,
            )
            plotted = True
    if not plotted:
        plt.close(fig)
        return None
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.grid(alpha=0.25)
    axis.legend()
    return fig


def _rmse_plot(records: list[dict[str, Any]]) -> Any | None:
    groups: dict[tuple[str, int], list[float]] = defaultdict(list)
    for record in records:
        result = record["result"]
        error = result.get("absolute_error")
        calls = result.get("oracle_calls")
        if error is not None and calls is not None:
            groups[(str(result["backend"]), int(calls))].append(float(error))
    if not groups:
        return None
    fig, axis = plt.subplots(figsize=(7, 4.5))
    for backend in sorted({key[0] for key in groups}):
        points = sorted(
            (
                calls,
                math.sqrt(sum(value * value for value in values) / len(values)),
            )
            for (candidate, calls), values in groups.items()
            if candidate == backend
        )
        axis.plot(
            [item[0] for item in points],
            [item[1] for item in points],
            marker="o",
            label=backend,
        )
    axis.set_xlabel("Visibility-table oracle calls")
    axis.set_ylabel("RMSE")
    axis.grid(alpha=0.25)
    axis.legend()
    return fig


def _latency_plot(records: list[dict[str, Any]]) -> Any | None:
    groups: dict[str, list[float]] = defaultdict(list)
    for record in records:
        result = record["result"]
        latency = result.get("end_to_end_ms")
        if latency is not None:
            groups[str(result["backend"])].append(float(latency))
    if not groups:
        return None
    names = sorted(groups)
    fig, axis = plt.subplots(figsize=(7, 4.5))
    axis.boxplot([groups[name] for name in names], tick_labels=names)
    axis.set_ylabel("End-to-end latency (ms)")
    axis.tick_params(axis="x", rotation=20)
    axis.grid(axis="y", alpha=0.25)
    return fig


def _cpu_gpu_plot(records: list[dict[str, Any]]) -> Any | None:
    selected = [
        record
        for record in records
        if record["result"].get("backend") in {"cpu_quantum", "intel_gpu"}
    ]
    if {record["result"]["backend"] for record in selected} != {"cpu_quantum", "intel_gpu"}:
        return None
    return _scatter_by_backend(
        selected,
        "qubit_count",
        "simulation_ms",
        "Qubits",
        "Simulation time (ms)",
    )


def generate_plots(
    records: list[dict[str, Any]], output_dir: Path, stem: str = "benchmark"
) -> PlotReport:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = _successful(records)
    builders: list[tuple[str, Callable[[], Any | None]]] = [
        (
            "absolute-error-vs-oracle-calls",
            lambda: _scatter_by_backend(
                records,
                "oracle_calls",
                "absolute_error",
                "Visibility-table oracle calls",
                "Absolute error",
            ),
        ),
        ("rmse-vs-oracle-calls", lambda: _rmse_plot(records)),
        (
            "error-vs-runtime",
            lambda: _scatter_by_backend(
                records, "end_to_end_ms", "absolute_error", "End-to-end time (ms)", "Absolute error"
            ),
        ),
        (
            "runtime-vs-qubits",
            lambda: _scatter_by_backend(
                records, "qubit_count", "simulation_ms", "Qubits", "Simulation time (ms)"
            ),
        ),
        (
            "runtime-vs-circuit-depth",
            lambda: _scatter_by_backend(
                records,
                "circuit_depth",
                "simulation_ms",
                "Maximum transpiled circuit depth",
                "Simulation time (ms)",
            ),
        ),
        (
            "memory-vs-qubits",
            lambda: _scatter_by_backend(
                records,
                "qubit_count",
                "peak_memory_bytes",
                "Qubits",
                "Process RSS after run (bytes)",
            ),
        ),
        ("end-to-end-latency", lambda: _latency_plot(records)),
        ("cpu-vs-intel-gpu", lambda: _cpu_gpu_plot(records)),
    ]
    generated: list[Path] = []
    skipped: list[str] = []
    for name, builder in builders:
        figure = builder()
        if figure is None:
            skipped.append(name)
            continue
        generated.extend(_save(figure, output_dir, stem, name))
    return PlotReport(tuple(generated), tuple(skipped))
