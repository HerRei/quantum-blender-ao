package ch.unibas.qmr.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class ConfigStoreTest {
    @Test
    void createsAndRoundTripsLocalConfig(@TempDir Path directory) throws Exception {
        Path path = directory.resolve("nested/config.json");
        ConfigStore store = new ConfigStore(path);

        ModConfig defaults = store.loadOrCreate();
        ModConfig changed = defaults.withEnabled(true).cycleAlgorithm();
        store.save(changed);

        assertTrue(changed.enabled());
        assertEquals(changed, store.loadOrCreate());
    }
}

