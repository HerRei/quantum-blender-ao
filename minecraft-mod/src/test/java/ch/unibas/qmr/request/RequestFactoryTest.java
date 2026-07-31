package ch.unibas.qmr.request;

import static org.junit.jupiter.api.Assertions.assertEquals;

import ch.unibas.qmr.config.ModConfig;
import ch.unibas.qmr.model.Dimensions;
import ch.unibas.qmr.model.IntVector3;
import ch.unibas.qmr.model.Vector3;
import ch.unibas.qmr.scene.CoordinateTransform;
import ch.unibas.qmr.scene.ExtractedScene;
import ch.unibas.qmr.voxel.CompactVoxelGrid;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class RequestFactoryTest {
    @Test
    void buildsStableVersionedRequest() {
        UUID id = UUID.fromString("00000000-0000-0000-0000-000000000042");
        CompactVoxelGrid grid = new CompactVoxelGrid(new Dimensions(3, 3, 3));
        ExtractedScene scene = new ExtractedScene(
                grid,
                new CoordinateTransform(new IntVector3(7, 8, 9), grid.dimensions()),
                new Vector3(1.5, 1.5, 1.5),
                new Vector3(0, 1, 0));

        var request = new RequestFactory(() -> id).create(scene, ModConfig.defaults());

        assertEquals("1.0", request.schemaVersion());
        assertEquals(id, request.requestId());
        assertEquals(new IntVector3(7, 8, 9), request.coordinateFrame().originWorldBlock());
        assertEquals(ModConfig.defaults().directionCount(), request.directionCount());
        assertEquals("minecraft_fabric", request.metadata().get("source"));
    }
}

