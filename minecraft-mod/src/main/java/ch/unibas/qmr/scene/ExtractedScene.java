package ch.unibas.qmr.scene;

import ch.unibas.qmr.model.Vector3;
import ch.unibas.qmr.voxel.CompactVoxelGrid;

public record ExtractedScene(
        CompactVoxelGrid grid,
        CoordinateTransform transform,
        Vector3 queryPositionLocal,
        Vector3 surfaceNormal) {}

