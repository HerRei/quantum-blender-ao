package ch.unibas.qmr.net;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;

public final class JdkHttpTransport implements AsyncJsonTransport {
    private final HttpClient client;

    public JdkHttpTransport(HttpClient client) {
        this.client = client;
    }

    public static JdkHttpTransport createDefault() {
        return new JdkHttpTransport(HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(2))
                .build());
    }

    @Override
    public CompletableFuture<HttpResponseData> post(URI uri, String json, Duration timeout) {
        HttpRequest request = HttpRequest.newBuilder(uri)
                .timeout(timeout)
                .header("Content-Type", "application/json")
                .header("Accept", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json))
                .build();
        return client.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .thenApply(response -> new HttpResponseData(response.statusCode(), response.body()));
    }
}

