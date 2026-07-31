from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from qmr.models import LightingResult
from qmr.scenes import open_sky

SCHEMAS = Path(__file__).parents[2] / "schemas"


def _validate(schema_name: str, instance: object) -> None:
    schema = json.loads((SCHEMAS / schema_name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(instance)


def test_request_matches_checked_in_schema() -> None:
    request = open_sky().request(direction_count=8)
    _validate("lighting-request.schema.json", request.model_dump(mode="json"))


def test_result_matches_checked_in_schema() -> None:
    request = open_sky().request()
    result = LightingResult(
        request_id=request.request_id,
        backend="exact",
        estimate=1.0,
        ground_truth=1.0,
        absolute_error=0.0,
        relative_error=0.0,
        confidence_interval=None,
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
        warnings=[],
        hardware={},
        software={},
    )
    _validate("lighting-result.schema.json", result.model_dump(mode="json"))

