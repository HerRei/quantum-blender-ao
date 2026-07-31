#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/.." && pwd)"
service_dir="$project_root/quantum-service"
mod_dir="$project_root/minecraft-mod"
run_tests=0

usage() {
  printf '%s\n' "usage: $0 [--test]"
  printf '%s\n' "  --test  also run Python checks/tests and the complete Fabric build"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --test)
      run_tests=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [ "$(uname -s)" != "Linux" ]; then
  printf '%s\n' "bootstrap-linux.sh must run on Linux; use bootstrap-macos.sh on macOS" >&2
  exit 1
fi

"$script_dir/check-environment.sh"

java_line="$(java -version 2>&1 | sed -n '1p')"
java_major="$(printf '%s\n' "$java_line" | sed -E 's/.*version "([0-9]+).*/\1/')"
if [ "$java_major" != "25" ]; then
  printf 'Java 25 is required by Minecraft 26.1; found: %s\n' "$java_line" >&2
  exit 1
fi

printf '%s\n' "Preparing repository-local Python environment..."
uv python install 3.13
uv sync --project "$service_dir" --python 3.13 --extra dev --frozen

printf '%s\n' "Checking the pinned Gradle wrapper..."
(cd "$mod_dir" && ./gradlew --version --no-daemon)
"$script_dir/check-shaders.sh"

if [ "$run_tests" -eq 1 ]; then
  printf '%s\n' "Running CPU-only validation; no GPU backend is implied..."
  uv run --project "$service_dir" --frozen ruff check "$service_dir/src" "$service_dir/tests"
  uv run --project "$service_dir" --frozen mypy "$service_dir/src"
  uv run --project "$service_dir" --frozen pytest "$service_dir/tests"
  (cd "$mod_dir" && ./gradlew build --no-daemon)
fi

printf '%s\n' "Linux bootstrap complete; no driver or system package was changed"
printf '%s\n' "Follow docs/linux-setup.md before making any GPU capability claim."

