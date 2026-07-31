package ch.unibas.qmr.net;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;

import ch.unibas.qmr.TestFixtures;
import com.google.gson.Gson;
import java.net.URI;
import java.time.Duration;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.TimeoutException;
import org.junit.jupiter.api.Test;

class LightingServiceClientTest {
    private final Gson gson = new Gson();

    @Test
    void serializesRequestAndParsesMatchingResponse() {
        UUID id = UUID.randomUUID();
        AsyncJsonTransport transport = (uri, json, timeout) -> {
            assertEquals("/lighting/estimate", uri.getPath());
            return CompletableFuture.completedFuture(
                    new HttpResponseData(200, gson.toJson(TestFixtures.result(id, 0.75))));
        };
        LightingServiceClient client = client(Duration.ofSeconds(1), transport);

        assertEquals(0.75, client.estimate(TestFixtures.request(id)).join().estimate());
    }

    @Test
    void mapsHttpErrorsToExplicitFailure() {
        LightingServiceClient client = client(
                Duration.ofSeconds(1),
                (uri, json, timeout) ->
                        CompletableFuture.completedFuture(new HttpResponseData(503, "unavailable")));

        CompletionException error = assertThrows(
                CompletionException.class,
                () -> client.estimate(TestFixtures.request(UUID.randomUUID())).join());

        assertInstanceOf(LightingServiceException.class, rootCause(error));
    }

    @Test
    void appliesTimeoutToTransportFuture() {
        CompletableFuture<HttpResponseData> pending = new CompletableFuture<>();
        LightingServiceClient client = client(Duration.ofMillis(10), (uri, json, timeout) -> pending);

        CompletionException error = assertThrows(
                CompletionException.class,
                () -> client.estimate(TestFixtures.request(UUID.randomUUID())).join());

        assertInstanceOf(TimeoutException.class, rootCause(error));
    }

    @Test
    void rejectsMismatchedRequestId() {
        LightingServiceClient client = client(
                Duration.ofSeconds(1),
                (uri, json, timeout) -> CompletableFuture.completedFuture(new HttpResponseData(
                        200, gson.toJson(TestFixtures.result(UUID.randomUUID(), 0.5)))));

        CompletionException error = assertThrows(
                CompletionException.class,
                () -> client.estimate(TestFixtures.request(UUID.randomUUID())).join());

        assertInstanceOf(LightingServiceException.class, rootCause(error));
    }

    private LightingServiceClient client(Duration timeout, AsyncJsonTransport transport) {
        return new LightingServiceClient(URI.create("http://127.0.0.1:8080"), timeout, transport, gson);
    }

    private static Throwable rootCause(Throwable error) {
        Throwable current = error;
        while (current.getCause() != null) {
            current = current.getCause();
        }
        return current;
    }
}

