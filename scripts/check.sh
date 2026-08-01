#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${CONDA_DEFAULT_ENV:-}" != "quantum-blender-ao" ]]; then
  echo "Activate the project environment first: conda activate quantum-blender-ao" >&2
  exit 1
fi

python -m ruff check "$repo_root/src" "$repo_root/tests"
python -m pytest
python -m compileall -q "$repo_root/blender"
