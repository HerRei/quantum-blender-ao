package ch.unibas.qmr.model;

import com.google.gson.annotations.SerializedName;

public record CoordinateFrame(
        @SerializedName("origin_world_block") IntVector3 originWorldBlock,
        String axes,
        @SerializedName("voxel_size") double voxelSize) {
    public static CoordinateFrame minecraft(IntVector3 origin) {
        return new CoordinateFrame(origin, "minecraft_x_east_y_up_z_south", 1.0);
    }
}

