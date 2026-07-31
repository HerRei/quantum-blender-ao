"""Compact voxel storage with the cross-language v1 index convention."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field

from qmr.models import Dimensions, EmissionValue, VoxelData


@dataclass(slots=True)
class VoxelGrid:
    """Mutable bit-packed voxel grid.

    Linear indices use ``x + size_x * (y + size_y * z)`` and each byte uses
    least-significant-bit first ordering.
    """

    dimensions: Dimensions
    solid: bytearray = field(init=False)
    transparent: bytearray = field(init=False)
    emissive: bytearray = field(init=False)
    emission_values: dict[int, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        size = self.dimensions.encoded_bytes
        self.solid = bytearray(size)
        self.transparent = bytearray(size)
        self.emissive = bytearray(size)

    def index(self, x: int, y: int, z: int) -> int:
        if not self.contains(x, y, z):
            raise IndexError(f"voxel coordinate {(x, y, z)} is outside {self.dimensions}")
        return x + self.dimensions.x * (y + self.dimensions.y * z)

    def coordinates(self, index: int) -> tuple[int, int, int]:
        if not 0 <= index < self.dimensions.volume:
            raise IndexError(f"voxel index {index} is outside the grid")
        z, remainder = divmod(index, self.dimensions.x * self.dimensions.y)
        y, x = divmod(remainder, self.dimensions.x)
        return x, y, z

    def contains(self, x: int, y: int, z: int) -> bool:
        return (
            0 <= x < self.dimensions.x
            and 0 <= y < self.dimensions.y
            and 0 <= z < self.dimensions.z
        )

    @staticmethod
    def _get(bits: bytearray, index: int) -> bool:
        return bool(bits[index >> 3] & (1 << (index & 7)))

    @staticmethod
    def _set(bits: bytearray, index: int, value: bool) -> None:
        mask = 1 << (index & 7)
        if value:
            bits[index >> 3] |= mask
        else:
            bits[index >> 3] &= ~mask

    def set_voxel(
        self,
        x: int,
        y: int,
        z: int,
        *,
        solid: bool,
        transparent: bool = False,
        emission: float = 0.0,
    ) -> None:
        if transparent and not solid:
            raise ValueError("transparent is a property of an occupied voxel")
        if emission < 0:
            raise ValueError("emission must be non-negative")
        index = self.index(x, y, z)
        self._set(self.solid, index, solid)
        self._set(self.transparent, index, transparent)
        self._set(self.emissive, index, emission > 0)
        if emission > 0:
            self.emission_values[index] = emission
        else:
            self.emission_values.pop(index, None)

    def is_solid(self, x: int, y: int, z: int) -> bool:
        return self._get(self.solid, self.index(x, y, z))

    def is_transparent(self, x: int, y: int, z: int) -> bool:
        return self._get(self.transparent, self.index(x, y, z))

    def blocks_visibility(self, x: int, y: int, z: int) -> bool:
        index = self.index(x, y, z)
        return self._get(self.solid, index) and not self._get(self.transparent, index)

    def to_payload(self) -> VoxelData:
        return VoxelData(
            solid=base64.b64encode(self.solid).decode("ascii"),
            transparent=base64.b64encode(self.transparent).decode("ascii"),
            emissive=base64.b64encode(self.emissive).decode("ascii"),
            emission_values=[
                EmissionValue(index=index, intensity=intensity)
                for index, intensity in sorted(self.emission_values.items())
            ],
        )

    @classmethod
    def from_payload(cls, dimensions: Dimensions, payload: VoxelData) -> VoxelGrid:
        grid = cls(dimensions)
        for name in ("solid", "transparent", "emissive"):
            decoded = payload.decode(name)
            if len(decoded) != dimensions.encoded_bytes:
                raise ValueError(f"{name} bitset has an invalid decoded length")
            setattr(grid, name, bytearray(decoded))
        grid.emission_values = {item.index: item.intensity for item in payload.emission_values}
        return grid

