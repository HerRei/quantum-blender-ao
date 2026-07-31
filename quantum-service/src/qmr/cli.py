"""Command-line entry point for local, Minecraft-independent workflows."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from qmr.benchmark import BenchmarkConfig, load_jsonl, run_benchmark
from qmr.plots import generate_plots
from qmr.scenes import all_scenes


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qmr")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list-scenes", help="list deterministic synthetic scenes")

    benchmark = commands.add_parser("benchmark", help="run a YAML/TOML benchmark matrix")
    benchmark.add_argument("--config", type=Path, required=True)
    benchmark.add_argument("--output-dir", type=Path, required=True)

    plot = commands.add_parser("plot", help="regenerate plots from JSON Lines")
    plot.add_argument("--input", type=Path, required=True)
    plot.add_argument("--output-dir", type=Path, required=True)
    plot.add_argument("--stem", default="benchmark")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "list-scenes":
        for scene in all_scenes().values():
            print(f"{scene.name}: {scene.description}")
        return 0
    if args.command == "benchmark":
        artifacts = run_benchmark(BenchmarkConfig.load(args.config), args.output_dir)
        print(
            json.dumps(
                {
                    "jsonl": str(artifacts.jsonl),
                    "csv": str(artifacts.csv),
                    "successful_runs": artifacts.successful_runs,
                    "skipped_runs": artifacts.skipped_runs,
                    "failed_runs": artifacts.failed_runs,
                    "plots": [str(path) for path in artifacts.plots.generated]
                    if artifacts.plots
                    else [],
                    "skipped_plots": list(artifacts.plots.skipped) if artifacts.plots else [],
                },
                indent=2,
            )
        )
        return int(artifacts.failed_runs > 0)
    if args.command == "plot":
        report = generate_plots(load_jsonl(args.input), args.output_dir, args.stem)
        payload = {
            "generated": [str(path) for path in report.generated],
            "skipped": report.skipped,
        }
        print(json.dumps(payload, indent=2))
        return 0
    raise AssertionError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
