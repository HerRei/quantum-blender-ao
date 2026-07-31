package ch.unibas.qmr.client;

import ch.unibas.qmr.config.ConfigStore;
import ch.unibas.qmr.config.ModConfig;
import ch.unibas.qmr.config.TargetMode;
import ch.unibas.qmr.model.IntVector3;
import ch.unibas.qmr.model.LightingRequest;
import ch.unibas.qmr.model.Vector3;
import ch.unibas.qmr.net.JdkHttpTransport;
import ch.unibas.qmr.net.LightingServiceClient;
import ch.unibas.qmr.request.RequestFactory;
import ch.unibas.qmr.scene.ExtractedScene;
import ch.unibas.qmr.scene.SceneExtractor;
import ch.unibas.qmr.state.LightingController;
import ch.unibas.qmr.state.LightingResultCache;
import ch.unibas.qmr.state.VisibilitySmoother;
import com.google.gson.Gson;
import com.mojang.blaze3d.platform.InputConstants;
import java.io.IOException;
import java.net.URI;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keymapping.v1.KeyMappingHelper;
import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElementRegistry;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.core.BlockPos;
import net.minecraft.resources.Identifier;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Client-only integration. No future is joined on Minecraft's render thread. */
public final class QuantumRenderingClient implements ClientModInitializer {
    public static final String MOD_ID = "quantum-minecraft-rendering";
    private static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);
    private static final KeyMapping.Category KEY_CATEGORY = KeyMapping.Category.register(
            Identifier.fromNamespaceAndPath(MOD_ID, "controls"));

    private final SceneExtractor extractor = new SceneExtractor();
    private final RequestFactory requestFactory = new RequestFactory();
    private final LightingResultCache cache = new LightingResultCache();
    private final VisibilitySmoother smoother = new VisibilitySmoother(0.25);
    private ConfigStore configStore;
    private ModConfig config;
    private LightingController controller;
    private KeyMapping toggleKey;
    private KeyMapping cycleKey;
    private int ticks;

    @Override
    public void onInitializeClient() {
        configStore = new ConfigStore(FabricLoader.getInstance()
                .getConfigDir()
                .resolve("quantum-minecraft-rendering.json"));
        config = loadConfig();
        LightingServiceClient service = new LightingServiceClient(
                URI.create(config.serviceUrl()),
                Duration.ofMillis(config.timeoutMs()),
                JdkHttpTransport.createDefault(),
                new Gson());
        controller = new LightingController(service, cache);
        registerKeys();
        ClientTickEvents.END_CLIENT_TICK.register(this::onEndTick);
        HudElementRegistry.addLast(
                Identifier.fromNamespaceAndPath(MOD_ID, "debug_hud"), this::renderHud);
        LOGGER.info("Quantum rendering client initialized; enabled={}", config.enabled());
    }

    private ModConfig loadConfig() {
        try {
            return configStore.loadOrCreate();
        } catch (IOException | RuntimeException error) {
            LOGGER.error("Could not read quantum rendering config; using in-memory defaults", error);
            return ModConfig.defaults();
        }
    }

    private void registerKeys() {
        toggleKey = KeyMappingHelper.registerKeyMapping(new KeyMapping(
                "key.quantum-minecraft-rendering.toggle",
                InputConstants.Type.KEYSYM,
                InputConstants.KEY_Q,
                KEY_CATEGORY));
        cycleKey = KeyMappingHelper.registerKeyMapping(new KeyMapping(
                "key.quantum-minecraft-rendering.cycle_algorithm",
                InputConstants.Type.KEYSYM,
                InputConstants.KEY_G,
                KEY_CATEGORY));
    }

    private void onEndTick(Minecraft minecraft) {
        while (toggleKey.consumeClick()) {
            config = config.withEnabled(!config.enabled());
            saveConfig();
        }
        while (cycleKey.consumeClick()) {
            config = config.cycleAlgorithm();
            saveConfig();
        }
        ticks++;
        if (!config.enabled()
                || cache.isPending()
                || ticks % config.requestIntervalTicks() != 0
                || minecraft.level == null
                || minecraft.player == null) {
            return;
        }
        try {
            QueryTarget target = queryTarget(minecraft);
            ExtractedScene scene = extractor.extract(
                    target.center(),
                    config.extractionRadius(),
                    new MinecraftVoxelSampler(minecraft.level),
                    target.queryPosition(),
                    target.normal());
            LightingRequest request = requestFactory.create(scene, config);
            controller.submit(request);
        } catch (RuntimeException error) {
            LOGGER.warn("Could not create lighting request", error);
        }
    }

    private QueryTarget queryTarget(Minecraft minecraft) {
        if (config.targetMode() == TargetMode.TARGETED_BLOCK
                && minecraft.hitResult instanceof BlockHitResult hit) {
            BlockPos block = hit.getBlockPos();
            double nx = hit.getDirection().getStepX();
            double ny = hit.getDirection().getStepY();
            double nz = hit.getDirection().getStepZ();
            Vec3 location = hit.getLocation();
            return new QueryTarget(
                    new IntVector3(block.getX(), block.getY(), block.getZ()),
                    new Vector3(
                            location.x + nx * 1.0e-4,
                            location.y + ny * 1.0e-4,
                            location.z + nz * 1.0e-4),
                    new Vector3(nx, ny, nz));
        }
        BlockPos block = minecraft.player.blockPosition();
        Vec3 position = minecraft.player.position();
        return new QueryTarget(
                new IntVector3(block.getX(), block.getY(), block.getZ()),
                new Vector3(position.x, position.y, position.z),
                new Vector3(0, 1, 0));
    }

    private void saveConfig() {
        try {
            configStore.save(config);
        } catch (IOException error) {
            LOGGER.error("Could not save quantum rendering config", error);
        }
    }

    private void renderHud(GuiGraphicsExtractor graphics, DeltaTracker ignored) {
        List<String> lines = new ArrayList<>();
        lines.add("Quantum rendering: " + (config.enabled() ? "ON" : "OFF"));
        lines.add("Mode: " + config.algorithm() + (cache.isPending() ? " (pending)" : ""));
        cache.lastValid().ifPresent(cached -> {
            double visible = smoother.update(cached.result().estimate(), System.nanoTime());
            lines.add(String.format(Locale.ROOT, "Visibility: %.4f", visible));
            lines.add("Backend: " + cached.result().backend());
            lines.add(String.format(
                    Locale.ROOT,
                    "Error: %s | service %.2f ms | RTT %.2f ms",
                    formatNullable(cached.result().absoluteError()),
                    cached.result().endToEndMs(),
                    cached.clientRoundTripMs()));
            lines.add("Oracle calls: " + cached.result().oracleCalls());
        });
        cache.lastError().ifPresent(error -> lines.add("Error: " + error));

        Minecraft minecraft = Minecraft.getInstance();
        int y = 8;
        for (String line : lines) {
            graphics.text(minecraft.font, line, 8, y, 0xFFFFFFFF, true);
            y += 10;
        }
    }

    private static String formatNullable(Double value) {
        return value == null ? "n/a" : String.format(Locale.ROOT, "%.4f", value);
    }

    private record QueryTarget(IntVector3 center, Vector3 queryPosition, Vector3 normal) {}
}
