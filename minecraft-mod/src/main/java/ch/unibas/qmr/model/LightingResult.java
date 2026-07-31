package ch.unibas.qmr.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

public record LightingResult(
        @SerializedName("schema_version") String schemaVersion,
        @SerializedName("request_id") UUID requestId,
        String backend,
        double estimate,
        @SerializedName("ground_truth") Double groundTruth,
        @SerializedName("absolute_error") Double absoluteError,
        @SerializedName("relative_error") Double relativeError,
        @SerializedName("confidence_interval") ConfidenceInterval confidenceInterval,
        @SerializedName("qubit_count") Integer qubitCount,
        @SerializedName("oracle_calls") long oracleCalls,
        Long shots,
        @SerializedName("circuit_executions") Integer circuitExecutions,
        @SerializedName("circuit_depth") Integer circuitDepth,
        @SerializedName("gate_count") Integer gateCount,
        @SerializedName("initialization_ms") double initializationMs,
        @SerializedName("simulation_ms") double simulationMs,
        @SerializedName("transfer_ms") Double transferMs,
        @SerializedName("end_to_end_ms") double endToEndMs,
        @SerializedName("process_rss_bytes") Long processRssBytes,
        @SerializedName("peak_memory_bytes") Long peakMemoryBytes,
        List<String> warnings,
        Map<String, Object> hardware,
        Map<String, Object> software,
        Map<String, Object> metadata) {
    public LightingResult {
        if (!"1.0".equals(schemaVersion)) {
            throw new IllegalArgumentException("unsupported lighting result schema_version");
        }
        Objects.requireNonNull(requestId, "requestId");
        if (backend == null || backend.isBlank()) {
            throw new IllegalArgumentException("backend must be non-blank");
        }
        requireProbability("estimate", estimate);
        requireOptionalProbability("groundTruth", groundTruth);
        requireOptionalProbability("absoluteError", absoluteError);
        requireOptionalNonNegativeFinite("relativeError", relativeError);
        requireOptionalNonNegative("qubitCount", qubitCount);
        requireNonNegative("oracleCalls", oracleCalls);
        requireOptionalNonNegative("shots", shots);
        requireOptionalNonNegative("circuitExecutions", circuitExecutions);
        requireOptionalNonNegative("circuitDepth", circuitDepth);
        requireOptionalNonNegative("gateCount", gateCount);
        requireNonNegativeFinite("initializationMs", initializationMs);
        requireNonNegativeFinite("simulationMs", simulationMs);
        requireOptionalNonNegativeFinite("transferMs", transferMs);
        requireNonNegativeFinite("endToEndMs", endToEndMs);
        requireOptionalNonNegative("processRssBytes", processRssBytes);
        requireOptionalNonNegative("peakMemoryBytes", peakMemoryBytes);
        warnings = List.copyOf(Objects.requireNonNull(warnings, "warnings"));
        hardware = Map.copyOf(Objects.requireNonNull(hardware, "hardware"));
        software = Map.copyOf(Objects.requireNonNull(software, "software"));
        metadata = Map.copyOf(Objects.requireNonNull(metadata, "metadata"));
    }

    private static void requireProbability(String name, double value) {
        if (!Double.isFinite(value) || value < 0 || value > 1) {
            throw new IllegalArgumentException(name + " must be finite and lie in [0, 1]");
        }
    }

    private static void requireOptionalProbability(String name, Double value) {
        if (value != null) {
            requireProbability(name, value);
        }
    }

    private static void requireNonNegativeFinite(String name, double value) {
        if (!Double.isFinite(value) || value < 0) {
            throw new IllegalArgumentException(name + " must be finite and non-negative");
        }
    }

    private static void requireOptionalNonNegativeFinite(String name, Double value) {
        if (value != null) {
            requireNonNegativeFinite(name, value);
        }
    }

    private static void requireNonNegative(String name, long value) {
        if (value < 0) {
            throw new IllegalArgumentException(name + " must be non-negative");
        }
    }

    private static void requireOptionalNonNegative(String name, Number value) {
        if (value != null && value.longValue() < 0) {
            throw new IllegalArgumentException(name + " must be non-negative");
        }
    }
}
