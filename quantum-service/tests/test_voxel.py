from __future__ import annotations

import pytest

from qmr.models import Dimensions
from qmr.voxel import VoxelGrid


def test_index_and_coordinate_round_trip() -> None:
    grid = VoxelGrid(Dimensions(x=3, y=4, z=5))
    for z in range(5):
        for y in range(4):
            for x in range(3):
                assert grid.coordinates(grid.index(x, y, z)) == (x, y, z)


def test_payload_round_trip_preserves_flags_and_emission() -> None:
    dimensions = Dimensions(x=9, y=2, z=1)
    grid = VoxelGrid(dimensions)
    grid.set_voxel(0, 0, 0, solid=True)
    grid.set_voxel(8, 1, 0, solid=True, transparent=True, emission=7.5)

    restored = VoxelGrid.from_payload(dimensions, grid.to_payload())

    assert restored.blocks_visibility(0, 0, 0)
    assert restored.is_transparent(8, 1, 0)
    assert not restored.blocks_visibility(8, 1, 0)
    assert restored.emission_values[17] == 7.5


def test_invalid_coordinate_is_rejected() -> None:
    grid = VoxelGrid(Dimensions(x=2, y=2, z=2))
    with pytest.raises(IndexError):
        grid.index(2, 0, 0)

