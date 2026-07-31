package ch.unibas.qmr.model;

import static org.junit.jupiter.api.Assertions.assertAll;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class LightingResultValidationTest {
    @Test
    void rejectsInvalidSchemaProbabilitiesAndCosts() {
        assertAll(
                () -> assertThrows(
                        IllegalArgumentException.class,
                        () -> result("2.0", "cpu_quantum", 0.5, 10, 1)),
                () -> assertThrows(
                        IllegalArgumentException.class,
                        () -> result("1.0", " ", 0.5, 10, 1)),
                () -> assertThrows(
                        IllegalArgumentException.class,
                        () -> result("1.0", "cpu_quantum", Double.NaN, 10, 1)),
                () -> assertThrows(
                        IllegalArgumentException.class,
                        () -> result("1.0", "cpu_quantum", 1.01, 10, 1)),
                () -> assertThrows(
                        IllegalArgumentException.class,
                        () -> result("1.0", "cpu_quantum", 0.5, -1, 1)),
                () -> assertThrows(
                        IllegalArgumentException.class,
                        () -> result("1.0", "cpu_quantum", 0.5, 10, -0.1)),
                () -> assertThrows(
                        IllegalArgumentException.class,
                        () -> result("1.0", "cpu_quantum", 0.5, 10, 1, -1L)));
    }

    @Test
    void rejectsInvalidConfidenceIntervals() {
        assertAll(
                () -> assertThrows(
                        IllegalArgumentException.class,
                        () -> new ConfidenceInterval(-0.1, 0.5, 0.95, "wilson")),
                () -> assertThrows(
                        IllegalArgumentException.class,
                        () -> new ConfidenceInterval(0.8, 0.2, 0.95, "wilson")),
                () -> assertThrows(
                        IllegalArgumentException.class,
                        () -> new ConfidenceInterval(0.2, 0.8, 1.0, "wilson")),
                () -> assertThrows(
                        IllegalArgumentException.class,
                        () -> new ConfidenceInterval(0.2, 0.8, 0.95, " ")));
    }

    @Test
    void requiresAndDefensivelyCopiesCollections() {
        List<String> warnings = new ArrayList<>(List.of("fixture"));
        Map<String, Object> hardware = new HashMap<>(Map.of("device", "CPU"));
        Map<String, Object> software = new HashMap<>(Map.of("java", "25"));
        Map<String, Object> metadata = new HashMap<>(Map.of("fixture", true));
        LightingResult result = result(warnings, hardware, software, metadata);

        warnings.clear();
        hardware.clear();
        software.clear();
        metadata.clear();

        assertEquals(List.of("fixture"), result.warnings());
        assertEquals(Map.of("device", "CPU"), result.hardware());
        assertEquals(Map.of("java", "25"), result.software());
        assertEquals(Map.of("fixture", true), result.metadata());
        assertAll(
                () -> assertThrows(
                        UnsupportedOperationException.class,
                        () -> result.warnings().add("mutation")),
                () -> assertThrows(
                        UnsupportedOperationException.class,
                        () -> result.hardware().put("mutation", true)),
                () -> assertThrows(
                        NullPointerException.class,
                        () -> result(null, Map.of(), Map.of(), Map.of())),
                () -> assertThrows(
                        NullPointerException.class,
                        () -> result(List.of(), null, Map.of(), Map.of())));
    }

    private static LightingResult result(
            String schemaVersion,
            String backend,
            double estimate,
            long oracleCalls,
            double endToEndMs) {
        return result(schemaVersion, backend, estimate, oracleCalls, endToEndMs, 4096L);
    }

    private static LightingResult result(
            String schemaVersion,
            String backend,
            double estimate,
            long oracleCalls,
            double endToEndMs,
            Long processRssBytes) {
        return new LightingResult(
                schemaVersion,
                UUID.randomUUID(),
                backend,
                estimate,
                0.5,
                0.0,
                0.0,
                new ConfidenceInterval(0.25, 0.75, 0.95, "fixture"),
                4,
                oracleCalls,
                100L,
                2,
                10,
                20,
                0.1,
                0.2,
                null,
                endToEndMs,
                processRssBytes,
                1024L,
                List.of(),
                Map.of(),
                Map.of(),
                Map.of());
    }

    private static LightingResult result(
            List<String> warnings,
            Map<String, Object> hardware,
            Map<String, Object> software,
            Map<String, Object> metadata) {
        return new LightingResult(
                "1.0",
                UUID.randomUUID(),
                "exact",
                0.5,
                0.5,
                0.0,
                0.0,
                null,
                null,
                8,
                null,
                null,
                null,
                null,
                0.1,
                0.2,
                null,
                0.3,
                4096L,
                1024L,
                warnings,
                hardware,
                software,
                metadata);
    }
}
