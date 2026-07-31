package ch.unibas.qmr.state;

import ch.unibas.qmr.model.LightingResult;

public record CachedLightingResult(LightingResult result, double clientRoundTripMs, long receivedNanos) {}

