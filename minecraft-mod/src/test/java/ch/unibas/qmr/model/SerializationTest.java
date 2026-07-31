package ch.unibas.qmr.model;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ch.unibas.qmr.TestFixtures;
import com.google.gson.Gson;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class SerializationTest {
    private final Gson gson = new Gson();

    @Test
    void requestUsesSnakeCaseWireNamesAndRoundTrips() {
        LightingRequest request = TestFixtures.request(UUID.fromString("00000000-0000-0000-0000-000000000001"));

        String json = gson.toJson(request);
        LightingRequest restored = gson.fromJson(json, LightingRequest.class);

        assertTrue(json.contains("\"schema_version\":\"1.0\""));
        assertTrue(json.contains("\"direction_count\":8"));
        assertTrue(json.contains("\"algorithm\":\"exact\""));
        assertEquals(request, restored);
    }

    @Test
    void resultDeserializesNullableMetrics() {
        LightingResult expected = TestFixtures.result(UUID.randomUUID(), 0.75);
        LightingResult restored = gson.fromJson(gson.toJson(expected), LightingResult.class);

        assertEquals(expected, restored);
        assertEquals(0.75, restored.estimate());
    }

    @Test
    void resultDeserializesCompleteServiceResponseContract() {
        String json = """
                {
                  "schema_version": "1.0",
                  "request_id": "00000000-0000-0000-0000-000000000002",
                  "backend": "cpu_quantum",
                  "estimate": 0.375,
                  "ground_truth": 0.375,
                  "absolute_error": 0.0,
                  "relative_error": 0.0,
                  "confidence_interval": {
                    "low": 0.25,
                    "high": 0.5,
                    "level": 0.95,
                    "method": "qiskit_mlae_likelihood_ratio"
                  },
                  "qubit_count": 7,
                  "oracle_calls": 245,
                  "shots": 35,
                  "circuit_executions": 5,
                  "circuit_depth": 1234,
                  "gate_count": 5678,
                  "initialization_ms": 1.25,
                  "simulation_ms": 42.5,
                  "transfer_ms": null,
                  "end_to_end_ms": 45.0,
                  "process_rss_bytes": 134217728,
                  "peak_memory_bytes": null,
                  "warnings": ["ideal noiseless simulation"],
                  "hardware": {"device_name": "CPU"},
                  "software": {"qiskit": "2.3.1"},
                  "metadata": {"qae_variant": "maximum_likelihood"}
                }
                """;

        LightingResult restored = gson.fromJson(json, LightingResult.class);

        assertEquals(UUID.fromString("00000000-0000-0000-0000-000000000002"), restored.requestId());
        assertEquals("cpu_quantum", restored.backend());
        assertEquals(245L, restored.oracleCalls());
        assertEquals(134217728L, restored.processRssBytes());
        assertNull(restored.peakMemoryBytes());
        assertEquals("qiskit_mlae_likelihood_ratio", restored.confidenceInterval().method());
        assertEquals("maximum_likelihood", restored.metadata().get("qae_variant"));
    }
}
