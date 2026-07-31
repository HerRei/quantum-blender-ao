package ch.unibas.qmr.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;

public record VoxelData(
        String encoding,
        @SerializedName("bit_order") String bitOrder,
        String solid,
        String transparent,
        String emissive,
        @SerializedName("emission_values") List<EmissionValue> emissionValues) {
    public VoxelData {
        emissionValues = List.copyOf(emissionValues);
    }
}

