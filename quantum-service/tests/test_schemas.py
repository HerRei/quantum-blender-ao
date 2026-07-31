from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import ValidationError as PydanticValidationError

from qmr.models import ConfidenceInterval, LightingResult
from qmr.scenes import open_sky

SCHEMAS = Path(__file__).parents[2] / "schemas"


def _validate(schema_name: str, instance: object) -> None:
    schema = json.loads((SCHEMAS / schema_name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(instance)


def _valid_result() -> LightingResult:
    request = open_sky().request()
    return LightingResult(
        request_id=request.request_id,
        backend="exact",
        estimate=1.0,
        ground_truth=1.0,
        absolute_error=0.0,
        relative_error=0.0,
        confidence_interval=ConfidenceInterval(
            low=0.9,
            high=1.0,
            level=0.95,
            method="fixture",
        ),
        qubit_count=None,
        oracle_calls=16,
        shots=None,
        circuit_executions=None,
        circuit_depth=None,
        gate_count=None,
        initialization_ms=0.1,
        simulation_ms=0.2,
        transfer_ms=None,
        end_to_end_ms=0.3,
        process_rss_bytes=1024,
        peak_memory_bytes=None,
        warnings=[],
        hardware={},
        software={},
        metadata={},
    )


def test_request_matches_checked_in_schema() -> None:
    request = open_sky().request(direction_count=8)
    _validate("lighting-request.schema.json", request.model_dump(mode="json"))


def test_result_matches_checked_in_schema() -> None:
    _validate("lighting-result.schema.json", _valid_result().model_dump(mode="json"))


def test_result_schema_requires_metadata() -> None:
    payload = _valid_result().model_dump(mode="json")
    payload.pop("metadata")

    with pytest.raises(JsonSchemaValidationError):
        _validate("lighting-result.schema.json", payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("backend", " \t"),
        (
            "confidence_interval",
            {"low": 0.9, "high": 1.0, "level": 0.95, "method": " \t"},
        ),
    ],
)
def test_result_contract_rejects_blank_identifiers(field: str, value: object) -> None:
    payload = _valid_result().model_dump(mode="json")
    payload[field] = value

    with pytest.raises(JsonSchemaValidationError):
        _validate("lighting-result.schema.json", payload)
    with pytest.raises(PydanticValidationError):
        LightingResult.model_validate(payload)
