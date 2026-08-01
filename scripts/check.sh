#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
uv run --project "$repo_root" ruff check "$repo_root/src" "$repo_root/tests"
uv run --project "$repo_root" pytest
python3 -m compileall -q "$repo_root/blender"
