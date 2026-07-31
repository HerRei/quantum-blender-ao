from __future__ import annotations

from qmr.models import Dimensions
from qmr.raycast import reaches_sky, visibility_table
from qmr.scenes import closed_chamber, open_sky
from qmr.voxel import VoxelGrid


def test_ray_exits_empty_volume() -> None:
    grid = VoxelGrid(Dimensions(x=3, y=3, z=3))
    assert reaches_sky(grid, (1.5, 1.5, 1.5), (1, 0, 0), 10)


def test_ray_stops_at_opaque_but_passes_transparent_voxel() -> None:
    grid = VoxelGrid(Dimensions(x=4, y=3, z=3))
    grid.set_voxel(2, 1, 1, solid=True)
    assert not reaches_sky(grid, (1.5, 1.5, 1.5), (1, 0, 0), 10)
    grid.set_voxel(2, 1, 1, solid=True, transparent=True)
    assert reaches_sky(grid, (1.5, 1.5, 1.5), (1, 0, 0), 10)


def test_open_and_closed_scene_truth_tables() -> None:
    assert visibility_table(open_sky().request(direction_count=64)) == [1] * 64
    assert visibility_table(closed_chamber().request(direction_count=64)) == [0] * 64


def test_distance_limit_is_conservative() -> None:
    grid = VoxelGrid(Dimensions(x=10, y=2, z=2))
    assert not reaches_sky(grid, (1.5, 1.5, 1.5), (1, 0, 0), 0.25)

