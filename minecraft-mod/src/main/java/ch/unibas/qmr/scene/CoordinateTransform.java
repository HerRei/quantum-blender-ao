package ch.unibas.qmr.scene;

import ch.unibas.qmr.model.Dimensions;
import ch.unibas.qmr.model.IntVector3;
import ch.unibas.qmr.model.Vector3;

/** Stable +X east, +Y up, +Z south world/local transform. */
public record CoordinateTransform(IntVector3 originWorldBlock, Dimensions dimensions) {
    public Vector3 worldToLocal(Vector3 world) {
        return new Vector3(
                world.x() - originWorldBlock.x(),
                world.y() - originWorldBlock.y(),
                world.z() - originWorldBlock.z());
    }

    public Vector3 localToWorld(Vector3 local) {
        return new Vector3(
                local.x() + originWorldBlock.x(),
                local.y() + originWorldBlock.y(),
                local.z() + originWorldBlock.z());
    }

    public int localX(int worldX) {
        return worldX - originWorldBlock.x();
    }

    public int localY(int worldY) {
        return worldY - originWorldBlock.y();
    }

    public int localZ(int worldZ) {
        return worldZ - originWorldBlock.z();
    }
}

