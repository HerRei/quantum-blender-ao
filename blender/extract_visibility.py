"""Use Blender ray casts to export a binary hemisphere-visibility table per probe."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def script_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--directions", type=int, choices=(4, 8, 16), default=16)
    parser.add_argument("--max-distance", type=float, default=8.0)
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(arguments)


def fibonacci_hemisphere(count: int) -> list[Vector]:
    """Return deterministic, approximately uniform directions over +Z."""

    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    directions = []
    for index in range(count):
        z = (index + 0.5) / count
        radius = math.sqrt(max(0.0, 1.0 - z * z))
        angle = index * golden_angle
        directions.append(Vector((radius * math.cos(angle), radius * math.sin(angle), z)))
    return directions


def orient(direction: Vector, normal: Vector) -> Vector:
    normal = normal.normalized()
    helper = Vector((0.0, 0.0, 1.0)) if abs(normal.z) < 0.999 else Vector((1.0, 0.0, 0.0))
    tangent = helper.cross(normal).normalized()
    bitangent = normal.cross(tangent).normalized()
    return (tangent * direction.x + bitangent * direction.y + normal * direction.z).normalized()


def extract(output: Path, direction_count: int, max_distance: float) -> None:
    scene = bpy.context.scene
    dependency_graph = bpy.context.evaluated_depsgraph_get()
    local_directions = fibonacci_hemisphere(direction_count)
    probe_objects = sorted(
        (obj for obj in bpy.data.objects if bool(obj.get("qbao_probe"))),
        key=lambda obj: str(obj["qbao_id"]),
    )
    if not probe_objects:
        raise RuntimeError("scene has no objects marked with qbao_probe")

    probes = []
    for probe in probe_objects:
        normal = Vector(probe["qbao_normal"])
        origin = probe.matrix_world.translation + normal.normalized() * 0.025
        table = []
        for local_direction in local_directions:
            world_direction = orient(local_direction, normal)
            hit, *_ = scene.ray_cast(
                dependency_graph,
                origin,
                world_direction,
                distance=max_distance,
            )
            table.append(0 if hit else 1)

        probes.append(
            {
                "id": str(probe["qbao_id"]),
                "tile": str(probe["qbao_tile"]),
                "position": [round(float(value), 6) for value in origin],
                "normal": [float(value) for value in normal],
                "visibility_table": table,
            }
        )

    payload = {
        "schema_version": 1,
        "scene": Path(bpy.data.filepath).name,
        "direction_count": direction_count,
        "max_distance": max_distance,
        "directions": [[round(float(value), 8) for value in direction] for direction in local_directions],
        "probes": probes,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(probes)} probe tables to {output}")


if __name__ == "__main__":
    args = script_arguments()
    extract(args.output, args.directions, args.max_distance)
