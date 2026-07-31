package ch.unibas.qmr.net;

import ch.unibas.qmr.model.LightingRequest;
import ch.unibas.qmr.model.LightingResult;
import com.google.gson.Gson;
import java.net.URI;
import java.time.Duration;
import java.util.Objects;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.TimeUnit;

/** Non-blocking JSON client; callers never join this future on the render thread. */
public final class LightingServiceClient implements LightingGateway {
    private final URI estimateUri;
    private final Duration timeout;
    private final AsyncJsonTransport transport;
    private final Gson gson;

    public LightingServiceClient(
            URI serviceBase, Duration timeout, AsyncJsonTransport transport, Gson gson) {
        this.estimateUri = serviceBase.resolve("/lighting/estimate");
        this.timeout = timeout;
        this.transport = transport;
        this.gson = gson;
    }

    @Override
    public CompletableFuture<LightingResult> estimate(LightingRequest request) {
        String json = gson.toJson(request);
        return transport.post(estimateUri, json, timeout)
                .orTimeout(timeout.toMillis(), TimeUnit.MILLISECONDS)
                .thenApply(response -> parseResponse(request, response));
    }

    private LightingResult parseResponse(LightingRequest request, HttpResponseData response) {
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new CompletionException(new LightingServiceException(
                    "lighting service returned HTTP " + response.statusCode()));
        }
        LightingResult result = gson.fromJson(response.body(), LightingResult.class);
        if (result == null || !Objects.equals(request.requestId(), result.requestId())) {
            throw new CompletionException(
                    new LightingServiceException("lighting response request_id mismatch"));
        }
        return result;
    }
}

