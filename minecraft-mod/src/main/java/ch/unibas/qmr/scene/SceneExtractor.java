package ch.unibas.qmr.scene;

import ch.unibas.qmr.model.Dimensions;
import ch.unibas.qmr.model.IntVector3;
import ch.unibas.qmr.model.Vector3;
import ch.unibas.qmr.voxel.CompactVoxelGrid;

/** Extracts a small cube synchronously; network and simulation remain asynchronous. */
public final class SceneExtractor {
    public ExtractedScene extract(
            IntVector3 center,
            int radius,
            VoxelSampler sampler,
            Vector3 queryPositionWorld,
            Vector3 surfaceNormal) {
        if (radius < 1 || radius > 16) {
            throw new IllegalArgumentException("extraction radius must lie in [1, 16]");
        }
        int side = radius * 2 + 1;
        Dimensions dimensions = new Dimensions(side, side, side);
        IntVector3 origin =
                new IntVector3(center.x() - radius, center.y() - radius, center.z() - radius);
        CoordinateTransform transform = new CoordinateTransform(origin, dimensions);
        CompactVoxelGrid grid = new CompactVoxelGrid(dimensions);
        for (int z = 0; z < side; z++) {
            for (int y = 0; y < side; y++) {
                for (int x = 0; x < side; x++) {
                    VoxelMaterial material = sampler.sample(
                            origin.x() + x, origin.y() + y, origin.z() + z);
                    grid.setVoxel(
                            x,
                            y,
                            z,
                            material.solid(),
                            material.transparent(),
                            material.emission());
                }
            }
        }
        Vector3 localQuery = transform.worldToLocal(queryPositionWorld);
        if (localQuery.x() < 0
                || localQuery.y() < 0
                || localQuery.z() < 0
                || localQuery.x() >= side
                || localQuery.y() >= side
                || localQuery.z() >= side) {
            throw new IllegalArgumentException("query point must lie inside extracted scene");
        }
        return new ExtractedScene(grid, transform, localQuery, surfaceNormal);
    }
}

