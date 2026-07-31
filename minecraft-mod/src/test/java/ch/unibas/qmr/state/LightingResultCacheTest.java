package ch.unibas.qmr.state;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ch.unibas.qmr.TestFixtures;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class LightingResultCacheTest {
    @Test
    void preservesLastValidResultAcrossFailure() {
        LightingResultCache cache = new LightingResultCache();
        UUID first = UUID.randomUUID();
        assertTrue(cache.tryStart(first));
        cache.complete(first, TestFixtures.result(first, 0.75), 4.5);

        UUID second = UUID.randomUUID();
        assertTrue(cache.tryStart(second));
        assertFalse(cache.tryStart(UUID.randomUUID()));
        cache.fail(second, new IllegalStateException("offline"));

        assertEquals(0.75, cache.lastValid().orElseThrow().result().estimate());
        assertTrue(cache.lastError().orElseThrow().contains("offline"));
        assertFalse(cache.isPending());
    }

    @Test
    void ignoresStaleCompletion() {
        LightingResultCache cache = new LightingResultCache();
        UUID active = UUID.randomUUID();
        UUID stale = UUID.randomUUID();
        cache.tryStart(active);

        cache.complete(stale, TestFixtures.result(stale, 0.1), 1);

        assertTrue(cache.isPending());
        assertTrue(cache.lastValid().isEmpty());
    }

    @Test
    void resetRemovesLastGoodErrorAndInFlightRequest() {
        LightingResultCache cache = new LightingResultCache();
        UUID first = UUID.randomUUID();
        cache.tryStart(first);
        cache.complete(first, TestFixtures.result(first, 0.75), 1);
        UUID second = UUID.randomUUID();
        cache.tryStart(second);

        cache.reset();

        assertFalse(cache.isPending());
        assertTrue(cache.lastValid().isEmpty());
        assertTrue(cache.lastError().isEmpty());
    }
}
