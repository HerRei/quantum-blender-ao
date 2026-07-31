package ch.unibas.qmr.model;

public record Vector3(double x, double y, double z) {
    public double length() {
        return Math.sqrt(x * x + y * y + z * z);
    }
}

