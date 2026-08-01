"""Command-line interface for estimation and image composition."""

from __future__ import annotations

import argparse
from pathlib import Path

from qbao.compose import compose_comparison
from qbao.experiment import run_experiment


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qbao")
    subparsers = parser.add_subparsers(dest="command", required=True)

    estimate = subparsers.add_parser("estimate", help="estimate Blender visibility tables")
    estimate.add_argument("--input", type=Path, required=True)
    estimate.add_argument("--output", type=Path, required=True)
    estimate.add_argument("--budget", type=int, default=64)
    estimate.add_argument("--seed", type=int, default=7)
    estimate.add_argument("--accuracy", type=float, default=0.125)

    compose = subparsers.add_parser("compose", help="compose three rendered images")
    compose.add_argument("--exact", type=Path, required=True)
    compose.add_argument("--monte-carlo", type=Path, required=True)
    compose.add_argument("--qae", type=Path, required=True)
    compose.add_argument("--results", type=Path, required=True)
    compose.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "estimate":
        result = run_experiment(args.input, args.output, args.budget, args.seed, args.accuracy)
        print(
            f"Estimated {len(result['probes'])} probes "
            f"({result['unique_visibility_tables']} unique tables)."
        )
        for method, summary in result["summary"].items():
            print(
                f"{method:>13}: mean={summary['mean_visibility']:.4f}, "
                f"RMSE={summary['rmse_vs_exact']:.4f}, "
                f"queries/probe={summary['logical_queries_per_probe']}"
            )
        print(f"Wrote {args.output}")
        return

    compose_comparison(
        args.exact,
        args.monte_carlo,
        args.qae,
        args.results,
        args.output,
    )
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
