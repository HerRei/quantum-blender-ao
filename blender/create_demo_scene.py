"""Build the reproducible Blender scene used by the experiment."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def script_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--grid-size", type=int, default=6)
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(arguments)


def make_material(
    name: str,
    color: tuple[float, float, float, float],
    metallic: float = 0.0,
    roughness: float = 0.6,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Metallic"].default_value = metallic
    principled.inputs["Roughness"].default_value = roughness
    return material


def add_box(
    name: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    material: bpy.types.Material,
    bevel: float = 0.04,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    if bevel > 0:
        modifier = obj.modifiers.new("Soft edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 3
    return obj


def point_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def build_scene(output: Path, grid_size: int) -> None:
    if grid_size < 2:
        raise ValueError("grid size must be at least 2")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for material in tuple(bpy.data.materials):
        bpy.data.materials.remove(material)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 720
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    world = bpy.data.worlds.new("QBAO World") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.012, 0.018, 0.035, 1.0)
    background.inputs["Strength"].default_value = 0.35

    stone = make_material("Stone", (0.13, 0.15, 0.20, 1.0), roughness=0.72)
    copper = make_material("Copper", (0.24, 0.085, 0.035, 1.0), metallic=0.6, roughness=0.3)
    tile_default = make_material("Probe default", (0.18, 0.24, 0.34, 1.0), roughness=0.42)

    spacing = 0.88
    floor_extent = grid_size * spacing
    add_box("Floor base", (0, 0, -0.09), (floor_extent + 0.35, floor_extent + 0.35, 0.18), stone)

    probes = bpy.data.collections.new("AO Probes")
    scene.collection.children.link(probes)
    for row in range(grid_size):
        for column in range(grid_size):
            x = (column - (grid_size - 1) / 2) * spacing
            y = (row - (grid_size - 1) / 2) * spacing
            probe_id = f"p_{row:02d}_{column:02d}"
            tile = add_box(
                f"AO_TILE_{probe_id}",
                (x, y, 0.035),
                (spacing - 0.055, spacing - 0.055, 0.07),
                tile_default,
                bevel=0.025,
            )
            tile["qbao_tile"] = True

            probe = bpy.data.objects.new(f"AO_PROBE_{probe_id}", None)
            probe.location = (x, y, 0.105)
            probe.empty_display_type = "PLAIN_AXES"
            probe.empty_display_size = 0.12
            probe["qbao_probe"] = True
            probe["qbao_id"] = probe_id
            probe["qbao_tile"] = tile.name
            probe["qbao_normal"] = [0.0, 0.0, 1.0]
            probes.objects.link(probe)

    half = floor_extent / 2
    add_box("Back wall", (0, half + 0.04, 1.65), (floor_extent + 0.35, 0.22, 3.3), stone)
    add_box("Left wall", (-half - 0.04, 0, 1.65), (0.22, floor_extent + 0.35, 3.3), stone)
    add_box("Canopy", (-1.25, 1.25, 2.25), (2.55, 2.55, 0.22), stone)
    add_box("Canopy column", (-0.12, 0.20, 1.12), (0.42, 0.42, 2.24), copper, bevel=0.08)
    add_box("Floating beam", (1.35, 1.38, 1.45), (2.15, 0.42, 0.48), copper, bevel=0.10)
    add_box("Low shelter", (1.72, -0.72, 1.05), (1.45, 1.55, 0.18), stone, bevel=0.08)
    add_box("Shelter leg A", (1.18, -1.25, 0.53), (0.20, 0.20, 1.06), copper)
    add_box("Shelter leg B", (2.25, -1.25, 0.53), (0.20, 0.20, 1.06), copper)

    bpy.ops.object.light_add(type="AREA", location=(0.6, -2.3, 7.3))
    key = bpy.context.object
    key.name = "Key light"
    key.data.energy = 950
    key.data.shape = "DISK"
    key.data.size = 5.5

    bpy.ops.object.light_add(type="AREA", location=(-4.0, -2.0, 3.5))
    fill = bpy.context.object
    fill.name = "Fill light"
    fill.data.energy = 420
    fill.data.color = (0.22, 0.42, 1.0)
    fill.data.size = 4.0
    point_at(fill, (0, 0, 0.5))

    bpy.ops.object.camera_add(location=(7.6, -9.2, 7.4))
    camera = bpy.context.object
    camera.name = "Experiment camera"
    camera.data.lens = 52
    point_at(camera, (0, 0.35, 0.55))
    scene.camera = camera

    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output.resolve()))
    print(f"Created {output} with {grid_size * grid_size} visibility probes")


if __name__ == "__main__":
    args = script_arguments()
    build_scene(args.output, args.grid_size)
