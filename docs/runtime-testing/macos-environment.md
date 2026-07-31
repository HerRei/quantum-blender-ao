# macOS Environment

* **macOS Version:** 26.4.1 (Build 25E253), arm64 (Apple Silicon)
* **Java Version:** 25.0.4+7-LTS-189
* **Python Version:** 3.14.6
* **Git Version:** 2.55.0
* **Gradle Version:** 9.5.1
* **Minecraft Version:** 26.1.2
* **Fabric Loader Version:** 0.19.3
* **Fabric API Version:** 0.155.2+26.1.2
* **Loom Version:** 1.17.17
* **Service Port:** 8080 (from `config.toml`)
* **Mod ID:** quantum-minecraft-rendering (from `fabric.mod.json`)
* **Client Entrypoint:** `ch.unibas.qmr.client.QuantumRenderingClient`
* **HUD Classes:** Handled directly in `QuantumRenderingClient::renderHud` via `HudElementRegistry.addLast`.
* **Keybindings:**
  * Toggle QMR (`Q`): `key.quantum-minecraft-rendering.toggle`
  * Cycle Algorithm (`G`): `key.quantum-minecraft-rendering.cycle_algorithm`
* **Backend Configuration:** `"request"` (Algorithm specified by request is honored).
* **Start Scripts:** 
  * `./scripts/bootstrap-macos.sh`
  * `./scripts/check-environment.sh`
  * `./scripts/check-shaders.sh`
  * `./scripts/run-benchmarks.sh`
  * `./scripts/run-service.sh`
* **Test Commands:**
  * Python: `pytest`, `mypy`, `ruff` (run via `./scripts/bootstrap-macos.sh`)
  * Java: `./gradlew build` / `./gradlew test`
