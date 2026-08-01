from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from qbao.compose import compose_comparison
from qbao.experiment import estimate_dataset


def fixture_dataset() -> dict[str, object]:
    return {
        "schema_version": 1,
        "scene": "test.blend",
        "direction_count": 4,
        "probes": [
            {
                "id": "open",
                "tile": "tile_open",
                "position": [0, 0, 0],
                "visibility_table": [1, 1, 1, 1],
            },
            {
                "id": "closed",
                "tile": "tile_closed",
                "position": [1, 0, 0],
                "visibility_table": [0, 0, 0, 0],
            },
        ],
    }


def test_estimate_dataset_produces_comparable_methods() -> None:
    result = estimate_dataset(fixture_dataset(), max_logical_queries=8, seed=9)
    assert len(result["probes"]) == 2
    assert result["unique_visibility_tables"] == 2
    assert result["probes"][0]["exact"]["value"] == 1.0
    assert result["summary"]["qae"]["logical_queries_per_probe"] <= 8


def test_compose_writes_labelled_three_panel_image(tmp_path: Path) -> None:
    image_paths = []
    for index in range(3):
        path = tmp_path / f"render_{index}.png"
        Image.new("RGB", (32, 24), (index * 30, 20, 40)).save(path)
        image_paths.append(path)

    results = estimate_dataset(fixture_dataset(), max_logical_queries=8, seed=9)
    results_path = tmp_path / "results.json"
    results_path.write_text(json.dumps(results), encoding="utf-8")
    output_path = tmp_path / "comparison.png"

    compose_comparison(*image_paths, results_path, output_path)

    with Image.open(output_path) as output:
        assert output.width == 96
        assert output.height > 24
