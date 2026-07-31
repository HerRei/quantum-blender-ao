package ch.unibas.qmr.config;

import com.google.gson.annotations.SerializedName;

public enum TargetMode {
    @SerializedName("player")
    PLAYER,
    @SerializedName("targeted_block")
    TARGETED_BLOCK
}

