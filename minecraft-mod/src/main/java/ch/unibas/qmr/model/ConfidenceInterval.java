package ch.unibas.qmr.model;

public record ConfidenceInterval(double low, double high, double level, String method) {}

