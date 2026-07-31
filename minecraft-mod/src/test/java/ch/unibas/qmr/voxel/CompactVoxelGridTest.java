package ch.unibas.qmr.voxel;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ch.unibas.qmr.model.Dimensions;
import org.junit.jupiter.api.Test;

class CompactVoxelGridTest {
    @Test
    void indexingMatchesCrossLanguageContract() {
        CompactVoxelGrid grid = new CompactVoxelGrid(new Dimensions(3, 4, 5));

        assertEquals(0, grid.index(0, 0, 0));
        assertEquals(1, grid.index(1, 0, 0));
        assertEquals(3, grid.index(0, 1, 0));
        assertEquals(12, grid.index(0, 0, 1));
        assertArrayEquals(new int[] {2, 3, 4}, grid.coordinates(59));
    }

    @Test
    void lsbBitsetEncodingHasFixedLength() {
        CompactVoxelGrid grid = new CompactVoxelGrid(new Dimensions(2, 2, 2));
        grid.setVoxel(0, 0, 0, true, false, 0);
        grid.setVoxel(1, 1, 1, true, true, 5);

        assertEquals("gQ==", grid.toVoxelData().solid());
        assertEquals("gA==", grid.toVoxelData().transparent());
        assertEquals("gA==", grid.toVoxelData().emissive());
        assertTrue(grid.isSolid(0, 0, 0));
        assertTrue(grid.isTransparent(1, 1, 1));
        assertFalse(grid.isTransparent(0, 0, 0));
    }

    @Test
    void rejectsOutOfBoundsAndInvalidTransparency() {
        CompactVoxelGrid grid = new CompactVoxelGrid(new Dimensions(2, 2, 2));
        assertThrows(IndexOutOfBoundsException.class, () -> grid.index(2, 0, 0));
        assertThrows(
                IllegalArgumentException.class,
                () -> grid.setVoxel(0, 0, 0, false, true, 0));
    }
}

