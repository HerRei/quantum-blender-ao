package ch.unibas.qmr.voxel;

import ch.unibas.qmr.model.Dimensions;
import ch.unibas.qmr.model.EmissionValue;
import ch.unibas.qmr.model.VoxelData;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Bit-packed grid matching schemas/README.md exactly. */
public final class CompactVoxelGrid {
    private final Dimensions dimensions;
    private final byte[] solid;
    private final byte[] transparent;
    private final byte[] emissive;
    private final Map<Integer, Double> emissionValues = new LinkedHashMap<>();

    public CompactVoxelGrid(Dimensions dimensions) {
        this.dimensions = dimensions;
        this.solid = new byte[dimensions.encodedBytes()];
        this.transparent = new byte[dimensions.encodedBytes()];
        this.emissive = new byte[dimensions.encodedBytes()];
    }

    public Dimensions dimensions() {
        return dimensions;
    }

    public int index(int x, int y, int z) {
        if (!contains(x, y, z)) {
            throw new IndexOutOfBoundsException("voxel coordinate lies outside grid");
        }
        return x + dimensions.x() * (y + dimensions.y() * z);
    }

    public int[] coordinates(int index) {
        if (index < 0 || index >= dimensions.volume()) {
            throw new IndexOutOfBoundsException("voxel index lies outside grid");
        }
        int plane = dimensions.x() * dimensions.y();
        int z = index / plane;
        int remainder = index % plane;
        int y = remainder / dimensions.x();
        int x = remainder % dimensions.x();
        return new int[] {x, y, z};
    }

    public boolean contains(int x, int y, int z) {
        return x >= 0
                && y >= 0
                && z >= 0
                && x < dimensions.x()
                && y < dimensions.y()
                && z < dimensions.z();
    }

    public void setVoxel(
            int x, int y, int z, boolean isSolid, boolean isTransparent, double emission) {
        if (isTransparent && !isSolid) {
            throw new IllegalArgumentException("transparent requires an occupied voxel");
        }
        if (emission < 0) {
            throw new IllegalArgumentException("emission must be non-negative");
        }
        int index = index(x, y, z);
        set(solid, index, isSolid);
        set(transparent, index, isTransparent);
        set(emissive, index, emission > 0);
        if (emission > 0) {
            emissionValues.put(index, emission);
        } else {
            emissionValues.remove(index);
        }
    }

    public boolean isSolid(int x, int y, int z) {
        return get(solid, index(x, y, z));
    }

    public boolean isTransparent(int x, int y, int z) {
        return get(transparent, index(x, y, z));
    }

    public VoxelData toVoxelData() {
        List<EmissionValue> values = new ArrayList<>();
        emissionValues.forEach((index, intensity) -> values.add(new EmissionValue(index, intensity)));
        return new VoxelData(
                "bitset-base64",
                "lsb0",
                Base64.getEncoder().encodeToString(solid),
                Base64.getEncoder().encodeToString(transparent),
                Base64.getEncoder().encodeToString(emissive),
                values);
    }

    private static boolean get(byte[] data, int index) {
        return (data[index >>> 3] & (1 << (index & 7))) != 0;
    }

    private static void set(byte[] data, int index, boolean value) {
        int mask = 1 << (index & 7);
        if (value) {
            data[index >>> 3] = (byte) (data[index >>> 3] | mask);
        } else {
            data[index >>> 3] = (byte) (data[index >>> 3] & ~mask);
        }
    }
}

