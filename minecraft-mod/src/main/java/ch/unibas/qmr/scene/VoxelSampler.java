package ch.unibas.qmr.scene;

@FunctionalInterface
public interface VoxelSampler {
    VoxelMaterial sample(int worldX, int worldY, int worldZ);
}

