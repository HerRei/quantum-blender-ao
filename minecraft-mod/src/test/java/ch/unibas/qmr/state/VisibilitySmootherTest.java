package ch.unibas.qmr.state;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class VisibilitySmootherTest {
    @Test
    void movesTowardNewTargetWithoutJumping() {
        VisibilitySmoother smoother = new VisibilitySmoother(1.0);
        assertEquals(0.0, smoother.update(0.0, 0));

        double halfway = smoother.update(1.0, 1_000_000_000L);

        assertTrue(halfway > 0 && halfway < 1);
        assertTrue(smoother.update(1.0, 2_000_000_000L) > halfway);
    }
}

