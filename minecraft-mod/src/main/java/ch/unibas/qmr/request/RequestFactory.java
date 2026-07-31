package ch.unibas.qmr.request;

import ch.unibas.qmr.config.ModConfig;
import ch.unibas.qmr.model.CoordinateFrame;
import ch.unibas.qmr.model.LightingQuery;
import ch.unibas.qmr.model.LightingRequest;
import ch.unibas.qmr.scene.ExtractedScene;
import java.util.Map;
import java.util.UUID;
import java.util.function.Supplier;

public final class RequestFactory {
    private final Supplier<UUID> requestIds;

    public RequestFactory() {
        this(UUID::randomUUID);
    }

    public RequestFactory(Supplier<UUID> requestIds) {
        this.requestIds = requestIds;
    }

    public LightingRequest create(ExtractedScene scene, ModConfig config) {
        return new LightingRequest(
                "1.0",
                requestIds.get(),
                scene.grid().dimensions(),
                scene.grid().toVoxelData(),
                CoordinateFrame.minecraft(scene.transform().originWorldBlock()),
                new LightingQuery(scene.queryPositionLocal(), scene.surfaceNormal()),
                config.directionCount(),
                config.algorithm(),
                config.seed(),
                config.desiredAccuracy(),
                0.95,
                config.maxOracleCalls(),
                128.0,
                Map.of("source", "minecraft_fabric", "target_mode", config.targetMode().name()));
    }
}

