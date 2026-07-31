package ch.unibas.qmr.net;

import ch.unibas.qmr.model.LightingRequest;
import ch.unibas.qmr.model.LightingResult;
import java.util.concurrent.CompletableFuture;

@FunctionalInterface
public interface LightingGateway {
    CompletableFuture<LightingResult> estimate(LightingRequest request);
}

