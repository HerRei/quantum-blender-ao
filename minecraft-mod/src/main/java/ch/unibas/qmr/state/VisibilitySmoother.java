package ch.unibas.qmr.state;

/** Exponential transition that can reuse an old value while a request is pending. */
public final class VisibilitySmoother {
    private final double timeConstantSeconds;
    private double current;
    private long lastNanos;
    private boolean initialized;

    public VisibilitySmoother(double timeConstantSeconds) {
        if (timeConstantSeconds <= 0) {
            throw new IllegalArgumentException("time constant must be positive");
        }
        this.timeConstantSeconds = timeConstantSeconds;
    }

    public synchronized double update(double target, long nowNanos) {
        if (!initialized) {
            current = target;
            lastNanos = nowNanos;
            initialized = true;
            return current;
        }
        double elapsedSeconds = Math.max(0, nowNanos - lastNanos) / 1_000_000_000.0;
        double alpha = 1.0 - Math.exp(-elapsedSeconds / timeConstantSeconds);
        current += alpha * (target - current);
        lastNanos = nowNanos;
        return current;
    }
}

