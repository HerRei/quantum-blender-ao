from __future__ import annotations

from qmr.raycast import visibility_table
from qmr.scenes import all_scenes


def test_all_required_scenes_are_reproducible() -> None:
    scenes_a = all_scenes()
    scenes_b = all_scenes()

    assert set(scenes_a) == {
        "open_sky",
        "closed_chamber",
        "single_wall",
        "two_wall_corner",
        "tunnel",
        "narrow_opening",
        "random_occupancy",
        "minecraft_cave",
    }
    for name in scenes_a:
        assert scenes_a[name].grid.to_payload() == scenes_b[name].grid.to_payload()


def test_every_scene_produces_binary_table_of_requested_size() -> None:
    for scene in all_scenes().values():
        table = visibility_table(scene.request(direction_count=16))
        assert len(table) == 16
        assert set(table) <= {0, 1}

