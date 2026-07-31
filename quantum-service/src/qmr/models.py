"""Versioned transport models shared by all service components."""

from __future__ import annotations

import base64
import binascii
import math
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0"


class StrictModel(BaseModel):
    """Base class that rejects accidental wire-format extensions."""

    model_config = ConfigDict(extra="forbid")


class Algorithm(StrEnum):
    MOCK = "mock"
    EXACT = "exact"
    CLASSICAL_MONTE_CARLO = "classical_monte_carlo"
    CPU_QUANTUM = "cpu_quantum"
    INTEL_GPU = "intel_gpu"


class Dimensions(StrictModel):
    x: int = Field(ge=1, le=128)
    y: int = Field(ge=1, le=128)
    z: int = Field(ge=1, le=128)

    @property
    def volume(self) -> int:
        return self.x * self.y * self.z

    @property
    def encoded_bytes(self) -> int:
        return math.ceil(self.volume / 8)


class Vector3(StrictModel):
    x: float
    y: float
    z: float

    @property
    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)


class IntVector3(StrictModel):
    x: int
    y: int
    z: int


class EmissionValue(StrictModel):
    index: int = Field(ge=0)
    intensity: float = Field(ge=0)


class VoxelData(StrictModel):
    encoding: Literal["bitset-base64"] = "bitset-base64"
    bit_order: Literal["lsb0"] = "lsb0"
    solid: str
    transparent: str
    emissive: str
    emission_values: list[EmissionValue] = Field(default_factory=list)

    def decode(self, field: Literal["solid", "transparent", "emissive"]) -> bytes:
        try:
            return base64.b64decode(getattr(self, field), validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(f"voxel_data.{field} is not valid base64") from exc


class CoordinateFrame(StrictModel):
    origin_world_block: IntVector3 = Field(default_factory=lambda: IntVector3(x=0, y=0, z=0))
    axes: Literal["minecraft_x_east_y_up_z_south"] = "minecraft_x_east_y_up_z_south"
    voxel_size: float = Field(default=1.0, ge=1.0, le=1.0)


class LightingQuery(StrictModel):
    position_local: Vector3
    surface_normal: Vector3

    @model_validator(mode="after")
    def normal_must_be_nonzero(self) -> LightingQuery:
        if self.surface_normal.length <= 1e-12:
            raise ValueError("surface_normal must be non-zero")
        return self


class LightingRequest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    request_id: UUID
    voxel_dimensions: Dimensions
    voxel_data: VoxelData
    coordinate_frame: CoordinateFrame = Field(default_factory=CoordinateFrame)
    query: LightingQuery
    direction_count: Literal[8, 16, 32, 64] = 16
    algorithm: Algorithm = Algorithm.EXACT
    seed: int = Field(default=0, ge=0, le=2**32 - 1)
    desired_accuracy: float = Field(default=0.05, gt=0, le=1)
    confidence_level: float = Field(default=0.95, gt=0, lt=1)
    max_oracle_calls: int = Field(default=1024, ge=1)
    ray_max_distance: float = Field(default=128.0, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_voxel_payload(self) -> LightingRequest:
        expected = self.voxel_dimensions.encoded_bytes
        for field in ("solid", "transparent", "emissive"):
            actual = len(self.voxel_data.decode(field))
            if actual != expected:
                raise ValueError(
                    f"voxel_data.{field} decodes to {actual} bytes; expected {expected}"
                )
        volume = self.voxel_dimensions.volume
        indices = [item.index for item in self.voxel_data.emission_values]
        if any(index >= volume for index in indices):
            raise ValueError("emission_values index is outside the voxel volume")
        if len(indices) != len(set(indices)):
            raise ValueError("emission_values indices must be unique")
        position = self.query.position_local
        if not (
            0 <= position.x < self.voxel_dimensions.x
            and 0 <= position.y < self.voxel_dimensions.y
            and 0 <= position.z < self.voxel_dimensions.z
        ):
            raise ValueError("query.position_local must lie inside the voxel volume")
        return self


class ConfidenceInterval(StrictModel):
    low: float = Field(ge=0, le=1)
    high: float = Field(ge=0, le=1)
    level: float = Field(gt=0, lt=1)
    method: str

    @model_validator(mode="after")
    def ordered(self) -> ConfidenceInterval:
        if self.low > self.high:
            raise ValueError("confidence interval low must not exceed high")
        return self


class LightingResult(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    request_id: UUID
    backend: str
    estimate: float = Field(ge=0, le=1)
    ground_truth: float | None = Field(default=None, ge=0, le=1)
    absolute_error: float | None = Field(default=None, ge=0)
    relative_error: float | None = Field(default=None, ge=0)
    confidence_interval: ConfidenceInterval | None = None
    qubit_count: int | None = Field(default=None, ge=0)
    oracle_calls: int = Field(ge=0)
    shots: int | None = Field(default=None, ge=0)
    circuit_executions: int | None = Field(default=None, ge=0)
    circuit_depth: int | None = Field(default=None, ge=0)
    gate_count: int | None = Field(default=None, ge=0)
    initialization_ms: float = Field(ge=0)
    simulation_ms: float = Field(ge=0)
    transfer_ms: float | None = Field(default=None, ge=0)
    end_to_end_ms: float = Field(ge=0)
    peak_memory_bytes: int | None = Field(default=None, ge=0)
    warnings: list[str] = Field(default_factory=list)
    hardware: dict[str, Any] = Field(default_factory=dict)
    software: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
