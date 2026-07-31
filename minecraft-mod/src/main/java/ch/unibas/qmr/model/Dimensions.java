package ch.unibas.qmr.model;

public record Dimensions(int x, int y, int z) {
    public Dimensions {
        if (x < 1 || y < 1 || z < 1 || x > 128 || y > 128 || z > 128) {
            throw new IllegalArgumentException("voxel dimensions must lie in [1, 128]");
        }
    }

    public int volume() {
        return Math.multiplyExact(Math.multiplyExact(x, y), z);
    }

    public int encodedBytes() {
        return Math.ceilDiv(volume(), 8);
    }
}

