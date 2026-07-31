package ch.unibas.qmr.scene;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ch.unibas.qmr.model.IntVector3;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class ChunkFootprintTest {
    @Test
    void checksEveryChunkCrossedByTheExtractionCube() {
        List<String> visited = new ArrayList<>();

        boolean loaded = ChunkFootprint.allChunksLoaded(new IntVector3(15, 64, 15), 1, (x, z) -> {
            visited.add(x + "," + z);
            return true;
        });

        assertTrue(loaded);
        assertEquals(List.of("0,0", "0,1", "1,0", "1,1"), visited);
    }

    @Test
    void usesFloorDivisionForNegativeBlockCoordinates() {
        List<String> visited = new ArrayList<>();

        assertTrue(ChunkFootprint.allChunksLoaded(new IntVector3(0, 64, 0), 1, (x, z) -> {
            visited.add(x + "," + z);
            return true;
        }));

        assertEquals(List.of("-1,-1", "-1,0", "0,-1", "0,0"), visited);
    }

    @Test
    void rejectsFootprintWhenAnyRequiredChunkIsMissing() {
        assertFalse(ChunkFootprint.allChunksLoaded(
                new IntVector3(15, 64, 8), 1, (x, z) -> x != 1));
    }

    @Test
    void rejectsNegativeRadius() {
        assertThrows(
                IllegalArgumentException.class,
                () -> ChunkFootprint.allChunksLoaded(
                        new IntVector3(0, 0, 0), -1, (x, z) -> true));
    }
}
