"""TOML configuration with paths resolved independently of the launch directory."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import Field

from qmr.models import Algorithm, StrictModel


class BackendSettings(StrictModel):
    name: Literal["request"] | Algorithm = "request"
    device_index: int = Field(default=0, ge=0)
    precision: Literal["float32", "float64"] = "float32"
    max_qubits: int = Field(default=20, ge=1, le=30)


class ServiceSettings(StrictModel):
    host: str = "127.0.0.1"
    port: int = Field(default=8080, ge=1, le=65535)
    request_timeout_seconds: float = Field(default=30.0, gt=0)
    max_concurrent_requests: int = Field(default=2, ge=1, le=64)
    benchmark_output_dir: Path = Path("../experiments/results")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    backend: BackendSettings = Field(default_factory=BackendSettings)


def default_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config.toml"


def load_settings(path: Path | None = None) -> ServiceSettings:
    configured = os.environ.get("QMR_CONFIG")
    selected = path or (Path(configured) if configured else default_config_path())
    with selected.open("rb") as stream:
        settings = ServiceSettings.model_validate(tomllib.load(stream))
    output_dir = settings.benchmark_output_dir
    if not output_dir.is_absolute():
        output_dir = (selected.parent / output_dir).resolve()
    return settings.model_copy(update={"benchmark_output_dir": output_dir})

