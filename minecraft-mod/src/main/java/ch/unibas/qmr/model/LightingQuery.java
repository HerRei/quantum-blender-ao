package ch.unibas.qmr.model;

import com.google.gson.annotations.SerializedName;

public record LightingQuery(
        @SerializedName("position_local") Vector3 positionLocal,
        @SerializedName("surface_normal") Vector3 surfaceNormal) {
    public LightingQuery {
        if (surfaceNormal.length() <= 1.0e-12) {
            throw new IllegalArgumentException("surface normal must be non-zero");
        }
    }
}

