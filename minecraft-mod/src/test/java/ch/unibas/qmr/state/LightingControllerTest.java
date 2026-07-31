package ch.unibas.qmr.state;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ch.unibas.qmr.TestFixtures;
import ch.unibas.qmr.model.LightingResult;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import org.junit.jupiter.api.Test;

class LightingControllerTest {
    @Test
    void returnsImmediatelyAndUpdatesCacheWhenFutureCompletes() {
        UUID id = UUID.randomUUID();
        CompletableFuture<LightingResult> future = new CompletableFuture<>();
        LightingResultCache cache = new LightingResultCache();
        LightingController controller = new LightingController(request -> future, cache);

        assertTrue(controller.submit(TestFixtures.request(id)));
        assertTrue(cache.isPending());
        assertFalse(controller.submit(TestFixtures.request(UUID.randomUUID())));

        future.complete(TestFixtures.result(id, 0.625));

        assertFalse(cache.isPending());
        assertEquals(0.625, cache.lastValid().orElseThrow().result().estimate());
    }

    @Test
    void storesAsynchronousFailureWithoutDiscardingCacheContract() {
        LightingResultCache cache = new LightingResultCache();
        LightingController controller = new LightingController(
                request -> CompletableFuture.failedFuture(new IllegalStateException("fixture")), cache);

        controller.submit(TestFixtures.request(UUID.randomUUID()));

        assertFalse(cache.isPending());
        assertTrue(cache.lastError().orElseThrow().contains("fixture"));
    }
}

