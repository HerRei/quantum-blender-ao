package ch.unibas.qmr.net;

import java.net.URI;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;

@FunctionalInterface
public interface AsyncJsonTransport {
    CompletableFuture<HttpResponseData> post(URI uri, String json, Duration timeout);
}

