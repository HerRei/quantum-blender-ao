"""Classical 3D-DDA ray casting used to construct the visibility oracle table."""

from __future__ import annotations

import math

from qmr.directions import hemisphere_directions
from qmr.models import LightingRequest
from qmr.voxel import VoxelGrid


def reaches_sky(
    grid: VoxelGrid,
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    max_distance: float,
) -> bool:
    """Trace until an opaque voxel, volume exit, or conservative distance limit.

    Exiting the finite extracted volume is defined as reaching sky in schema v1.
    Reaching ``max_distance`` while still inside returns false.
    """

    magnitude = math.sqrt(sum(component * component for component in direction))
    if magnitude <= 1e-15:
        raise ValueError("ray direction must be non-zero")
    ray = tuple(component / magnitude for component in direction)
    position = tuple(origin[axis] + ray[axis] * 1e-9 for axis in range(3))
    cell = [math.floor(component) for component in position]
    if not grid.contains(*cell):
        return True

    step = [1 if component > 0 else -1 if component < 0 else 0 for component in ray]
    t_delta = [math.inf if component == 0 else abs(1.0 / component) for component in ray]
    t_max: list[float] = []
    for axis, component in enumerate(ray):
        if step[axis] > 0:
            boundary = cell[axis] + 1.0
            t_max.append((boundary - position[axis]) / component)
        elif step[axis] < 0:
            boundary = float(cell[axis])
            t_max.append((boundary - position[axis]) / component)
        else:
            t_max.append(math.inf)

    while True:
        travel = min(t_max)
        if travel > max_distance:
            return False
        tied_axes = [axis for axis, value in enumerate(t_max) if abs(value - travel) <= 1e-12]
        for axis in tied_axes:
            cell[axis] += step[axis]
            t_max[axis] += t_delta[axis]
        if not grid.contains(*cell):
            return True
        if grid.blocks_visibility(*cell):
            return False


def visibility_table(request: LightingRequest) -> list[int]:
    """Build the classical truth table used by every v1 backend."""

    grid = VoxelGrid.from_payload(request.voxel_dimensions, request.voxel_data)
    origin = request.query.position_local
    directions = hemisphere_directions(request.query.surface_normal, request.direction_count)
    return [
        int(
            reaches_sky(
                grid,
                (origin.x, origin.y, origin.z),
                direction,
                request.ray_max_distance,
            )
        )
        for direction in directions
    ]

