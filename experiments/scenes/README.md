# Synthetic scenes

The canonical scenes are generated in `qmr.scenes`; this keeps geometry,
query coordinates, and bitset encoding identical for exact, Monte Carlo, and
quantum experiments. The generators are deterministic and covered by tests.

Included scene IDs: `open_sky`, `closed_chamber`, `single_wall`,
`two_wall_corner`, `tunnel`, `narrow_opening`, `random_occupancy` (seed
`20260731`), and `minecraft_cave`.

