from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from qmr.scenes import open_sky


def test_request_round_trip_is_stable() -> None:
    request = open_sky().request(direction_count=32, seed=17)
    encoded = request.model_dump_json()
    decoded = request.model_validate_json(encoded)

    assert decoded == request
    assert json.loads(encoded)["schema_version"] == "1.0"


def test_wrong_bitset_length_is_rejected() -> None:
    payload = open_sky().request().model_dump(mode="json")
    payload["voxel_data"]["solid"] = ""

    with pytest.raises(ValidationError, match="expected"):
        type(open_sky().request()).model_validate(payload)


def test_zero_normal_is_rejected() -> None:
    payload = open_sky().request().model_dump(mode="json")
    payload["query"]["surface_normal"] = {"x": 0, "y": 0, "z": 0}

    with pytest.raises(ValidationError, match="non-zero"):
        type(open_sky().request()).model_validate(payload)

