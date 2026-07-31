package ch.unibas.qmr.state;

import ch.unibas.qmr.model.LightingRequest;
import ch.unibas.qmr.net.LightingGateway;

/** Coordinates futures and cache updates without blocking the caller. */
public final class LightingController {
    private final LightingGateway gateway;
    private final LightingResultCache cache;

    public LightingController(LightingGateway gateway, LightingResultCache cache) {
        this.gateway = gateway;
        this.cache = cache;
    }

    public boolean submit(LightingRequest request) {
        if (!cache.tryStart(request.requestId())) {
            return false;
        }
        long started = System.nanoTime();
        System.out.println("[QuantumClient] Submitting request " + request.requestId());
        try {
            gateway.estimate(request).whenComplete((result, error) -> {
                double roundTripMs = (System.nanoTime() - started) / 1_000_000.0;
                if (error != null) {
                    System.out.println("[QuantumClient] Request " + request.requestId() + " failed: " + error.getMessage());
                    cache.fail(request.requestId(), error);
                } else {
                    System.out.println("[QuantumClient] Request " + request.requestId() + " completed with " + result.backend() + ", visibility: " + result.estimate() + ", roundtrip: " + roundTripMs + "ms");
                    cache.complete(request.requestId(), result, roundTripMs);
                }
            });
        } catch (RuntimeException error) {
            cache.fail(request.requestId(), error);
        }
        return true;
    }
}

