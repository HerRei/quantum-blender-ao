package ch.unibas.qmr.scene;

public record VoxelMaterial(boolean solid, boolean transparent, double emission) {
    public static VoxelMaterial empty() {
        return new VoxelMaterial(false, false, 0.0);
    }
}

