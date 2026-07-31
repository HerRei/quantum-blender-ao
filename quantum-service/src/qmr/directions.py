"""Deterministic, approximately uniform hemisphere direction sampling."""

from __future__ import annotations

import math

from qmr.models import Vector3


def normalize(vector: Vector3) -> tuple[float, float, float]:
    length = vector.length
    if length <= 1e-12:
        raise ValueError("cannot normalize a zero vector")
    return vector.x / length, vector.y / length, vector.z / length


def hemisphere_directions(normal: Vector3, count: int) -> list[tuple[float, float, float]]:
    """Return a deterministic Fibonacci lattice oriented around ``normal``."""

    if count not in {8, 16, 32, 64}:
        raise ValueError("direction count must be one of 8, 16, 32, or 64")
    nx, ny, nz = normalize(normal)
    helper = (0.0, 1.0, 0.0) if abs(ny) < 0.9 else (1.0, 0.0, 0.0)
    tx = helper[1] * nz - helper[2] * ny
    ty = helper[2] * nx - helper[0] * nz
    tz = helper[0] * ny - helper[1] * nx
    tangent_length = math.sqrt(tx * tx + ty * ty + tz * tz)
    tx, ty, tz = tx / tangent_length, ty / tangent_length, tz / tangent_length
    bx = ny * tz - nz * ty
    by = nz * tx - nx * tz
    bz = nx * ty - ny * tx

    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    result: list[tuple[float, float, float]] = []
    for index in range(count):
        normal_component = (index + 0.5) / count
        radius = math.sqrt(max(0.0, 1.0 - normal_component * normal_component))
        azimuth = index * golden_angle
        local_x = radius * math.cos(azimuth)
        local_z = radius * math.sin(azimuth)
        result.append(
            (
                local_x * tx + normal_component * nx + local_z * bx,
                local_x * ty + normal_component * ny + local_z * by,
                local_x * tz + normal_component * nz + local_z * bz,
            )
        )
    return result

