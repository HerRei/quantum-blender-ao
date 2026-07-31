"""Small deterministic voxel scenes that do not require Minecraft."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from qmr.models import (
    Algorithm,
    CoordinateFrame,
    Dimensions,
    IntVector3,
    LightingQuery,
    LightingRequest,
    Vector3,
)
from qmr.voxel import VoxelGrid


@dataclass(frozen=True, slots=True)
class SyntheticScene:
    name: str
    description: str
    grid: VoxelGrid
    query_position: Vector3
    surface_normal: Vector3

    def request(
        self,
        *,
        direction_count: Literal[8, 16, 32, 64] = 16,
        algorithm: Algorithm = Algorithm.EXACT,
        seed: int = 0,
        desired_accuracy: float = 0.05,
        max_oracle_calls: int = 1024,
    ) -> LightingRequest:
        return LightingRequest(
            request_id=uuid5(
                NAMESPACE_URL,
                f"qmr:{self.name}:{direction_count}:{algorithm}:{seed}:{max_oracle_calls}",
            ),
            voxel_dimensions=self.grid.dimensions,
            voxel_data=self.grid.to_payload(),
            coordinate_frame=CoordinateFrame(origin_world_block=IntVector3(x=0, y=0, z=0)),
            query=LightingQuery(
                position_local=self.query_position,
                surface_normal=self.surface_normal,
            ),
            direction_count=direction_count,
            algorithm=algorithm,
            seed=seed,
            desired_accuracy=desired_accuracy,
            max_oracle_calls=max_oracle_calls,
            ray_max_distance=128.0,
            metadata={"scene": self.name, "synthetic": True},
        )


def _empty(name: str, description: str, size: int = 9) -> SyntheticScene:
    grid = VoxelGrid(Dimensions(x=size, y=size, z=size))
    center = size / 2
    return SyntheticScene(
        name=name,
        description=description,
        grid=grid,
        query_position=Vector3(x=center, y=center, z=center),
        surface_normal=Vector3(x=0, y=1, z=0),
    )


def open_sky() -> SyntheticScene:
    return _empty("open_sky", "Empty finite volume; every ray exits to sky.")


def closed_chamber() -> SyntheticScene:
    scene = _empty("closed_chamber", "Opaque shell enclosing the query point.")
    dims = scene.grid.dimensions
    for z in range(dims.z):
        for y in range(dims.y):
            for x in range(dims.x):
                if x in {0, dims.x - 1} or y in {0, dims.y - 1} or z in {0, dims.z - 1}:
                    scene.grid.set_voxel(x, y, z, solid=True)
    return scene


def single_wall() -> SyntheticScene:
    scene = _empty("single_wall", "One opaque vertical wall east of the query point.")
    wall_x = scene.grid.dimensions.x - 2
    for z in range(scene.grid.dimensions.z):
        for y in range(scene.grid.dimensions.y):
            scene.grid.set_voxel(wall_x, y, z, solid=True)
    return scene


def two_wall_corner() -> SyntheticScene:
    scene = _empty("two_wall_corner", "Two perpendicular opaque walls form a corner.")
    wall = scene.grid.dimensions.x - 2
    for z in range(scene.grid.dimensions.z):
        for y in range(scene.grid.dimensions.y):
            scene.grid.set_voxel(wall, y, z, solid=True)
    for x in range(scene.grid.dimensions.x):
        for y in range(scene.grid.dimensions.y):
            scene.grid.set_voxel(x, y, wall, solid=True)
    return scene


def tunnel() -> SyntheticScene:
    scene = _empty("tunnel", "Three-by-three air tunnel through an opaque volume.")
    dims = scene.grid.dimensions
    for z in range(dims.z):
        for y in range(dims.y):
            for x in range(dims.x):
                if not (3 <= x <= 5 and 3 <= y <= 5):
                    scene.grid.set_voxel(x, y, z, solid=True)
    return scene


def narrow_opening() -> SyntheticScene:
    scene = closed_chamber()
    object.__setattr__(scene, "name", "narrow_opening")
    object.__setattr__(scene, "description", "Closed chamber with one voxel open in its roof.")
    center = scene.grid.dimensions.x // 2
    scene.grid.set_voxel(center, scene.grid.dimensions.y - 1, center, solid=False)
    return scene


def random_occupancy(seed: int = 20260731, probability: float = 0.22) -> SyntheticScene:
    scene = _empty("random_occupancy", f"Random opaque voxels with fixed seed {seed}.")
    rng = random.Random(seed)
    dims = scene.grid.dimensions
    for z in range(dims.z):
        for y in range(dims.y):
            for x in range(dims.x):
                if rng.random() < probability:
                    scene.grid.set_voxel(x, y, z, solid=True)
    center = dims.x // 2
    for z in range(center - 1, center + 2):
        for y in range(center - 1, center + 2):
            for x in range(center - 1, center + 2):
                scene.grid.set_voxel(x, y, z, solid=False)
    return scene


def minecraft_cave() -> SyntheticScene:
    scene = _empty("minecraft_cave", "Blocky cave with a crooked shaft to the surface.", size=11)
    dims = scene.grid.dimensions
    for z in range(dims.z):
        for y in range(dims.y):
            for x in range(dims.x):
                scene.grid.set_voxel(x, y, z, solid=True)
    center = dims.x // 2
    for z in range(2, 9):
        for y in range(3, 8):
            for x in range(2, 9):
                if (x - center) ** 2 + (y - center) ** 2 + (z - center) ** 2 <= 14:
                    scene.grid.set_voxel(x, y, z, solid=False)
    for y in range(center, dims.y):
        shaft_x = center + (1 if y >= 8 else 0)
        scene.grid.set_voxel(shaft_x, y, center, solid=False)
        scene.grid.set_voxel(shaft_x, y, center + 1, solid=False)
    return SyntheticScene(
        name=scene.name,
        description=scene.description,
        grid=scene.grid,
        query_position=Vector3(x=center + 0.5, y=center + 0.5, z=center + 0.5),
        surface_normal=scene.surface_normal,
    )


def all_scenes() -> dict[str, SyntheticScene]:
    scenes = [
        open_sky(),
        closed_chamber(),
        single_wall(),
        two_wall_corner(),
        tunnel(),
        narrow_opening(),
        random_occupancy(),
        minecraft_cave(),
    ]
    return {scene.name: scene for scene in scenes}
