package ch.unibas.qmr.model;

import static org.junit.jupiter.api.Assertions.assertEquals;
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
}

