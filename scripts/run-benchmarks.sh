#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/.." && pwd)"
service_dir="$project_root/quantum-service"
config_path="${1:-$project_root/experiments/configs/smoke.toml}"
output_dir="${2:-$project_root/experiments/results}"

if ! command -v uv >/dev/null 2>&1; then
  printf '%s\n' "uv is required; run a bootstrap script first" >&2
  exit 1
fi
if [ ! -f "$config_path" ]; then
  printf 'benchmark configuration not found: %s\n' "$config_path" >&2
  exit 1
fi

printf 'config: %s\n' "$config_path"
printf 'raw output: %s\n' "$output_dir"
printf '%s\n' "Generated measurements are machine-specific and ignored by Git."

exec uv run --project "$service_dir" --frozen qmr benchmark \
  --config "$config_path" \
  --output-dir "$output_dir"

