package ch.unibas.qmr.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;
import java.util.Map;
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
        @SerializedName("peak_memory_bytes") Long peakMemoryBytes,
        List<String> warnings,
        Map<String, Object> hardware,
        Map<String, Object> software,
        Map<String, Object> metadata) {}

