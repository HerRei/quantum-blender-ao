# Fabric client mod

Pinned toolchain (verified against official Fabric 26.1.2 project metadata on
2026-07-31):

- Minecraft Java Edition 26.1.2
- Java 25
- Fabric Loader 0.19.3
- Fabric API 0.155.2+26.1.2
- Fabric Loom 1.17.17 (stable release, not the template's snapshot)
- Gradle Wrapper 9.5.1
- JUnit 6.1.0

Build and test without a locally installed Minecraft client:

```bash
./gradlew build
```

The client extracts a configurable cube around the targeted block (fallback:
player), maps occupied/transparent/emissive states into the v1 bitsets, and
submits requests through Java's asynchronous `HttpClient`. It keeps the last
valid result across failures and never waits for HTTP or simulation on the
render thread.

Default controls:

- `Q`: enable/disable requests
- `G`: cycle Exact → Classical Monte Carlo → CPU Quantum

The config is created at
`config/quantum-minecraft-rendering.json`. The HUD shows visibility, backend,
absolute error, service latency, client round-trip latency, oracle calls,
pending state, and the latest error.

## Validation status

Pure Java models, indexing, extraction, request construction, cache behavior,
serialization, and asynchronous error/timeout paths have unit tests. The Loom
build downloads Minecraft development artifacts. The actual client entrypoint,
world extraction, keys, and HUD have not been run in Minecraft on this Mac.

