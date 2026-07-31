package ch.unibas.qmr.model;

import com.google.gson.annotations.SerializedName;

public enum Algorithm {
    @SerializedName("mock")
    MOCK,
    @SerializedName("exact")
    EXACT,
    @SerializedName("classical_monte_carlo")
    CLASSICAL_MONTE_CARLO,
    @SerializedName("cpu_quantum")
    CPU_QUANTUM,
    @SerializedName("intel_gpu")
    INTEL_GPU;

    public Algorithm nextInteractive() {
        return switch (this) {
            case EXACT -> CLASSICAL_MONTE_CARLO;
            case CLASSICAL_MONTE_CARLO -> CPU_QUANTUM;
            default -> EXACT;
        };
    }
}

