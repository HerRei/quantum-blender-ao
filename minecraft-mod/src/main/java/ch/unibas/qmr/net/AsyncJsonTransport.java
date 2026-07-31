package ch.unibas.qmr.net;

import java.net.URI;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;

@FunctionalInterface
public interface AsyncJsonTransport extends AutoCloseable {
    CompletableFuture<HttpResponseData> post(URI uri, String json, Duration timeout);

    @Override
    default void close() {}
}
