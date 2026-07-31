package ch.unibas.qmr.scene;

import static org.junit.jupiter.api.Assertions.assertEquals;

import ch.unibas.qmr.model.Dimensions;
import ch.unibas.qmr.model.IntVector3;
import ch.unibas.qmr.model.Vector3;
import org.junit.jupiter.api.Test;

class CoordinateTransformTest {
    @Test
    void worldLocalRoundTripPreservesMinecraftAxes() {
        CoordinateTransform transform =
                new CoordinateTransform(new IntVector3(-10, 64, 25), new Dimensions(9, 9, 9));
        Vector3 world = new Vector3(-7.25, 66.5, 30.75);

        Vector3 local = transform.worldToLocal(world);

        assertEquals(new Vector3(2.75, 2.5, 5.75), local);
        assertEquals(world, transform.localToWorld(local));
    }
}

