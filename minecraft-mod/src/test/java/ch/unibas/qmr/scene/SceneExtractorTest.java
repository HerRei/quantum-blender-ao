package ch.unibas.qmr.scene;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ch.unibas.qmr.model.IntVector3;
import ch.unibas.qmr.model.Vector3;
import org.junit.jupiter.api.Test;

class SceneExtractorTest {
    @Test
    void extractsMaterialFlagsAndLocalQuery() {
        SceneExtractor extractor = new SceneExtractor();
        ExtractedScene scene = extractor.extract(
                new IntVector3(10, 20, 30),
                1,
                (x, y, z) -> x == 10
                        ? new VoxelMaterial(true, y == 20, z == 30 ? 4 : 0)
                        : VoxelMaterial.empty(),
                new Vector3(10.5, 20.5, 30.5),
                new Vector3(0, 1, 0));

        assertEquals(new IntVector3(9, 19, 29), scene.transform().originWorldBlock());
        assertEquals(new Vector3(1.5, 1.5, 1.5), scene.queryPositionLocal());
        assertTrue(scene.grid().isSolid(1, 1, 1));
        assertTrue(scene.grid().isTransparent(1, 1, 1));
        assertEquals(4, scene.grid().toVoxelData().emissionValues().getFirst().intensity());
    }
}

