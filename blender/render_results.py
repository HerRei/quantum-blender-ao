"""Apply estimated visibility values to Blender tiles and render one method."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


def script_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--method", choices=("exact", "monte_carlo", "qae"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(arguments)


def visibility_color(value: float) -> tuple[float, float, float, float]:
    """Map enclosed points to near-black violet and open points to pale cyan."""

    bounded = min(1.0, max(0.0, value))
    low = (0.012, 0.006, 0.035)
    high = (0.45, 0.82, 1.0)
    return tuple(low[i] + bounded * (high[i] - low[i]) for i in range(3)) + (1.0,)


def probe_material(name: str, value: float) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    color = visibility_color(value)
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Roughness"].default_value = 0.38
    principled.inputs["Metallic"].default_value = 0.1
    if "Emission Color" in principled.inputs:
        principled.inputs["Emission Color"].default_value = tuple(channel * 0.22 for channel in color[:3]) + (1.0,)
        principled.inputs["Emission Strength"].default_value = 0.35
    return material


def render(results_path: Path, method: str, output: Path) -> None:
    results = json.loads(results_path.read_text(encoding="utf-8"))
    for probe in results["probes"]:
        tile = bpy.data.objects.get(probe["tile"])
        if tile is None:
            raise RuntimeError(f"scene is missing tile {probe['tile']}")
        value = float(probe[method]["value"])
        material = probe_material(f"{method}_{probe['id']}", value)
        tile.data.materials.clear()
        tile.data.materials.append(material)

    scene = bpy.context.scene
    scene.render.filepath = str(output.resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print(f"Rendered {method} visibility to {output}")


if __name__ == "__main__":
    args = script_arguments()
    render(args.results, args.method, args.output)
