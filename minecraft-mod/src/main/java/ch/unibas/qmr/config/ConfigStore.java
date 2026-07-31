package ch.unibas.qmr.config;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import java.io.IOException;
import java.io.Reader;
import java.io.Writer;
import java.nio.file.Files;
import java.nio.file.Path;

public final class ConfigStore {
    private final Path path;
    private final Gson gson = new GsonBuilder().setPrettyPrinting().create();

    public ConfigStore(Path path) {
        this.path = path;
    }

    public ModConfig loadOrCreate() throws IOException {
        if (!Files.exists(path)) {
            ModConfig defaults = ModConfig.defaults();
            save(defaults);
            return defaults;
        }
        try (Reader reader = Files.newBufferedReader(path)) {
            return gson.fromJson(reader, ModConfig.class);
        }
    }

    public void save(ModConfig config) throws IOException {
        Files.createDirectories(path.getParent());
        try (Writer writer = Files.newBufferedWriter(path)) {
            gson.toJson(config, writer);
        }
    }
}

