package ch.unibas.qmr.model;

public record EmissionValue(int index, double intensity) {
    public EmissionValue {
        if (index < 0 || intensity < 0) {
            throw new IllegalArgumentException("emission index and intensity must be non-negative");
        }
    }
}

