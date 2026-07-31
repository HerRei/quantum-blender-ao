package ch.unibas.qmr.model;

import com.google.gson.annotations.SerializedName;
import java.util.Map;
import java.util.UUID;

public record LightingRequest(
        @SerializedName("schema_version") String schemaVersion,
        @SerializedName("request_id") UUID requestId,
        @SerializedName("voxel_dimensions") Dimensions voxelDimensions,
        @SerializedName("voxel_data") VoxelData voxelData,
        @SerializedName("coordinate_frame") CoordinateFrame coordinateFrame,
        LightingQuery query,
        @SerializedName("direction_count") int directionCount,
        Algorithm algorithm,
        long seed,
        @SerializedName("desired_accuracy") double desiredAccuracy,
        @SerializedName("confidence_level") double confidenceLevel,
        @SerializedName("max_oracle_calls") int maxOracleCalls,
        @SerializedName("ray_max_distance") double rayMaxDistance,
        Map<String, Object> metadata) {
    public LightingRequest {
        metadata = Map.copyOf(metadata);
    }
}

