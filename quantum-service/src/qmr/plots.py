"""Headless PNG/PDF plots generated exclusively from measured raw records."""

from __future__ import annotations

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


def _metadata_scatter_by_backend(
    records: list[dict[str, Any]],
    metadata_key: str,
    xlabel: str,
    ylabel: str,
) -> Any | None:
    fig, axis = plt.subplots(figsize=(7, 4.5))
    plotted = False
    for backend in sorted({str(record["result"]["backend"]) for record in records}):
        pairs = []
        for record in records:
            result = record["result"]
            if result["backend"] != backend:
                continue
            metadata = result.get("metadata")
            value = metadata.get(metadata_key) if isinstance(metadata, dict) else None
            calls = result.get("oracle_calls")
            if calls is not None and value is not None:
                pairs.append((float(calls), float(value)))
        if pairs:
            axis.scatter(
                [item[0] for item in pairs],
                [item[1] for item in pairs],
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


def generate_plots(
    records: list[dict[str, Any]], output_dir: Path, stem: str = "benchmark"
) -> PlotReport:
    output_dir.mkdir(parents=True, exist_ok=True)
    status_counts = {
        status: sum(record.get("status") == status for record in records)
        for status in ("ok", "failed", "skipped")
    }
    records = _successful(records)
    builders: list[tuple[str, Callable[[], Any | None]]] = [
        (
            "raw-absolute-error-vs-logical-oracle-calls",
            lambda: _scatter_by_backend(
                records,
                "oracle_calls",
                "absolute_error",
                "Realized logical visibility-table lookup calls",
                "Raw absolute error (exploratory; no aggregation)",
            ),
        ),
        (
            "estimator-phase-vs-logical-oracle-calls",
            lambda: _scatter_by_backend(
                records,
                "oracle_calls",
                "simulation_ms",
                "Realized logical visibility-table lookup calls",
                "Backend estimator phase (ms)",
            ),
        ),
        (
            "end-to-end-vs-logical-oracle-calls",
            lambda: _scatter_by_backend(
                records,
                "oracle_calls",
                "end_to_end_ms",
                "Realized logical visibility-table lookup calls",
                "Backend end-to-end time (ms)",
            ),
        ),
        (
            "max-circuit-depth-vs-logical-oracle-calls",
            lambda: _scatter_by_backend(
                records,
                "oracle_calls",
                "circuit_depth",
                "Realized logical visibility-table lookup calls",
                "Maximum analysis-transpiled quantum depth",
            ),
        ),
        (
            "max-gate-count-vs-logical-oracle-calls",
            lambda: _scatter_by_backend(
                records,
                "oracle_calls",
                "gate_count",
                "Realized logical visibility-table lookup calls",
                "Maximum analysis-transpiled quantum gate count",
            ),
        ),
        (
            "shot-weighted-gates-vs-logical-oracle-calls",
            lambda: _metadata_scatter_by_backend(
                records,
                "shot_weighted_transpiled_quantum_gate_count",
                "Realized logical visibility-table lookup calls",
                "Shot-weighted analysis-transpiled quantum gates",
            ),
        ),
    ]
    generated: list[Path] = []
    skipped: list[str] = []
    for name, builder in builders:
        figure = builder()
        if figure is None:
            skipped.append(name)
            continue
        figure.suptitle(
            "Exploratory raw benchmark plot — "
            f"ok={status_counts['ok']}, failed={status_counts['failed']}, "
            f"skipped={status_counts['skipped']}",
            fontsize=9,
        )
        generated.extend(_save(figure, output_dir, stem, name))
    return PlotReport(tuple(generated), tuple(skipped))
