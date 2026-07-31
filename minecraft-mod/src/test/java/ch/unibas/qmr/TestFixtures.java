package ch.unibas.qmr;

import ch.unibas.qmr.model.Algorithm;
import ch.unibas.qmr.model.CoordinateFrame;
import ch.unibas.qmr.model.Dimensions;
import ch.unibas.qmr.model.IntVector3;
import ch.unibas.qmr.model.LightingQuery;
import ch.unibas.qmr.model.LightingRequest;
import ch.unibas.qmr.model.LightingResult;
import ch.unibas.qmr.model.Vector3;
import ch.unibas.qmr.voxel.CompactVoxelGrid;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class TestFixtures {
    private TestFixtures() {}

    public static LightingRequest request(UUID id) {
        CompactVoxelGrid grid = new CompactVoxelGrid(new Dimensions(2, 2, 2));
        return new LightingRequest(
                "1.0",
                id,
                grid.dimensions(),
                grid.toVoxelData(),
                CoordinateFrame.minecraft(new IntVector3(10, 20, 30)),
                new LightingQuery(new Vector3(0.5, 0.5, 0.5), new Vector3(0, 1, 0)),
                8,
                Algorithm.EXACT,
                7,
                0.1,
                0.95,
                64,
                128,
                Map.of("fixture", true));
    }

    public static LightingResult result(UUID id, double estimate) {
        return new LightingResult(
                "1.0",
                id,
                "exact",
                estimate,
                estimate,
                0.0,
                0.0,
                null,
                null,
                8,
                null,
                null,
                null,
                null,
                0.1,
                0.2,
                null,
                0.3,
                4096L,
                1024L,
                List.of(),
                Map.of("device_name", "CPU"),
                Map.of("java", "25"),
                Map.of("fixture", true));
    }
}
