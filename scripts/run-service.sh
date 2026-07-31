#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/.." && pwd)"
service_dir="$project_root/quantum-service"
config_path="${1:-$service_dir/config.toml}"

if ! command -v uv >/dev/null 2>&1; then
  printf '%s\n' "uv is required; run scripts/bootstrap-macos.sh or bootstrap-linux.sh first" >&2
  exit 1
fi
if [ ! -f "$config_path" ]; then
  printf 'configuration not found: %s\n' "$config_path" >&2
  exit 1
fi

exec uv run --project "$service_dir" --frozen qmr serve --config "$config_path"

