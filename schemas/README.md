# Wire schemas

Version `1.0` uses JSON and three fixed-size base64 bitsets. A bit at linear
index `x + size_x * (y + size_y * z)` represents one voxel; bit zero is the
least-significant bit of byte zero (`lsb0`). Each bitset must contain exactly
`ceil(size_x * size_y * size_z / 8)` decoded bytes.

- `solid=1, transparent=0`: blocks visibility rays.
- `solid=1, transparent=1`: represented but does not block v1 visibility rays.
- `emissive=1`: identifies an emitting voxel; its non-negative strength is in
  `emission_values`. Emission is transported but not yet part of ambient
  visibility estimation.

Coordinates use Minecraft's axes: +X east, +Y up, +Z south. Query coordinates
are local to `origin_world_block`. Unknown fields are rejected so incompatible
wire changes require a new `schema_version`.

