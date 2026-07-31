package ch.unibas.qmr.state;

import ch.unibas.qmr.model.LightingResult;
import java.util.Optional;
import java.util.UUID;

/** Thread-safe cache that preserves the last valid result across failures. */
public final class LightingResultCache {
    private CachedLightingResult lastValid;
    private UUID inFlight;
    private String lastError;

    public synchronized boolean tryStart(UUID requestId) {
        if (inFlight != null) {
            return false;
        }
        inFlight = requestId;
        lastError = null;
        return true;
    }

    public synchronized void complete(UUID requestId, LightingResult result, double roundTripMs) {
        if (!requestId.equals(inFlight)) {
            return;
        }
        inFlight = null;
        if (!requestId.equals(result.requestId())) {
            lastError = "response request_id mismatch";
            return;
        }
        lastValid = new CachedLightingResult(result, roundTripMs, System.nanoTime());
        lastError = null;
    }

    public synchronized void fail(UUID requestId, Throwable error) {
        if (!requestId.equals(inFlight)) {
            return;
        }
        inFlight = null;
        lastError = rootMessage(error);
    }

    public synchronized Optional<CachedLightingResult> lastValid() {
        return Optional.ofNullable(lastValid);
    }

    public synchronized Optional<String> lastError() {
        return Optional.ofNullable(lastError);
    }

    public synchronized boolean isPending() {
        return inFlight != null;
    }

    private static String rootMessage(Throwable error) {
        Throwable current = error;
        while (current.getCause() != null) {
            current = current.getCause();
        }
        return current.getClass().getSimpleName() + ": " + current.getMessage();
    }
}

