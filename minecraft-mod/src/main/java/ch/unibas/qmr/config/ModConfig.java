package ch.unibas.qmr.config;

import ch.unibas.qmr.model.Algorithm;
import java.net.URI;
import java.util.Objects;

public record ModConfig(
        boolean enabled,
        String serviceUrl,
        int timeoutMs,
        int extractionRadius,
        TargetMode targetMode,
        int directionCount,
        Algorithm algorithm,
        long seed,
        double desiredAccuracy,
        int maxOracleCalls,
        int requestIntervalTicks) {
    public ModConfig {
        Objects.requireNonNull(serviceUrl, "serviceUrl");
        Objects.requireNonNull(targetMode, "targetMode");
        Objects.requireNonNull(algorithm, "algorithm");
        URI.create(serviceUrl);
        if (timeoutMs < 1
                || extractionRadius < 1
                || extractionRadius > 16
                || !java.util.Set.of(8, 16, 32, 64).contains(directionCount)
                || seed < 0
                || desiredAccuracy <= 0
                || desiredAccuracy > 0.5
                || maxOracleCalls < 1
                || requestIntervalTicks < 1) {
            throw new IllegalArgumentException("invalid quantum rendering configuration");
        }
    }

    public static ModConfig defaults() {
        return new ModConfig(
                false,
                "http://127.0.0.1:8080",
                5000,
                4,
                TargetMode.TARGETED_BLOCK,
                16,
                Algorithm.EXACT,
                7,
                0.05,
                256,
                20);
    }

    public ModConfig withEnabled(boolean value) {
        return new ModConfig(
                value,
                serviceUrl,
                timeoutMs,
                extractionRadius,
                targetMode,
                directionCount,
                algorithm,
                seed,
                desiredAccuracy,
                maxOracleCalls,
                requestIntervalTicks);
    }

    public ModConfig cycleAlgorithm() {
        return new ModConfig(
                enabled,
                serviceUrl,
                timeoutMs,
                extractionRadius,
                targetMode,
                directionCount,
                algorithm.nextInteractive(),
                seed,
                desiredAccuracy,
                maxOracleCalls,
                requestIntervalTicks);
    }
}

