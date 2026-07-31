package ch.unibas.qmr.model;

public record ConfidenceInterval(double low, double high, double level, String method) {
    public ConfidenceInterval {
        requireProbability("low", low);
        requireProbability("high", high);
        if (low > high) {
            throw new IllegalArgumentException("confidence interval low must not exceed high");
        }
        if (!Double.isFinite(level) || level <= 0 || level >= 1) {
            throw new IllegalArgumentException("confidence interval level must lie in (0, 1)");
        }
        if (method == null || method.isBlank()) {
            throw new IllegalArgumentException("confidence interval method must be non-blank");
        }
    }

    private static void requireProbability(String name, double value) {
        if (!Double.isFinite(value) || value < 0 || value > 1) {
            throw new IllegalArgumentException(name + " must be finite and lie in [0, 1]");
        }
    }
}
