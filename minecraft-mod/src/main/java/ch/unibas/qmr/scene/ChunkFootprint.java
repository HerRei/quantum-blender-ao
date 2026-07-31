package ch.unibas.qmr.scene;

import ch.unibas.qmr.model.IntVector3;
import java.util.Objects;

/** Computes the horizontal Minecraft chunks required by a cubic scene extraction. */
public final class ChunkFootprint {
    private static final long CHUNK_SIDE = 16L;

    private ChunkFootprint() {}

    public static boolean allChunksLoaded(
            IntVector3 center, int radius, ChunkAvailability availability) {
        Objects.requireNonNull(center, "center");
        Objects.requireNonNull(availability, "availability");
        if (radius < 0) {
            throw new IllegalArgumentException("radius must be non-negative");
        }

        int minChunkX = chunkCoordinate((long) center.x() - radius);
        int maxChunkX = chunkCoordinate((long) center.x() + radius);
        int minChunkZ = chunkCoordinate((long) center.z() - radius);
        int maxChunkZ = chunkCoordinate((long) center.z() + radius);
        for (int chunkX = minChunkX; chunkX <= maxChunkX; chunkX++) {
            for (int chunkZ = minChunkZ; chunkZ <= maxChunkZ; chunkZ++) {
                if (!availability.isLoaded(chunkX, chunkZ)) {
                    return false;
                }
            }
        }
        return true;
    }

    private static int chunkCoordinate(long blockCoordinate) {
        return Math.toIntExact(Math.floorDiv(blockCoordinate, CHUNK_SIDE));
    }

    @FunctionalInterface
    public interface ChunkAvailability {
        boolean isLoaded(int chunkX, int chunkZ);
    }
}
