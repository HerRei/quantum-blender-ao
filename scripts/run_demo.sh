#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
blender_executable="${BLENDER_BIN:-}"

if [[ -z "$blender_executable" ]] && command -v blender >/dev/null 2>&1; then
  blender_executable="$(command -v blender)"
fi
if [[ -z "$blender_executable" ]] && [[ -x /Applications/Blender.app/Contents/MacOS/Blender ]]; then
  blender_executable=/Applications/Blender.app/Contents/MacOS/Blender
fi
if [[ -z "$blender_executable" ]]; then
  echo "Blender was not found. Install it or set BLENDER_BIN." >&2
  exit 1
fi

mkdir -p "$repo_root/scenes" "$repo_root/generated"

"$blender_executable" --background --python-exit-code 1 \
  --python "$repo_root/blender/create_demo_scene.py" -- \
  --output "$repo_root/scenes/demo.blend"

"$blender_executable" --background "$repo_root/scenes/demo.blend" --python-exit-code 1 \
  --python "$repo_root/blender/extract_visibility.py" -- \
  --output "$repo_root/generated/visibility.json" \
  --directions 16

uv run --project "$repo_root" qbao estimate \
  --input "$repo_root/generated/visibility.json" \
  --output "$repo_root/generated/results.json" \
  --budget 64 \
  --seed 7

for method in exact monte_carlo qae; do
  "$blender_executable" --background "$repo_root/scenes/demo.blend" --python-exit-code 1 \
    --python "$repo_root/blender/render_results.py" -- \
    --results "$repo_root/generated/results.json" \
    --method "$method" \
    --output "$repo_root/generated/render_${method}.png"
done

uv run --project "$repo_root" qbao compose \
  --exact "$repo_root/generated/render_exact.png" \
  --monte-carlo "$repo_root/generated/render_monte_carlo.png" \
  --qae "$repo_root/generated/render_qae.png" \
  --results "$repo_root/generated/results.json" \
  --output "$repo_root/generated/comparison.png"

echo "Complete: $repo_root/generated/comparison.png"
