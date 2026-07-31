# macOS Runtime Testing Progress

| Phase | Aufgabe | Status | Evidenz | Offene Punkte |
| ----- | ------- | ------ | ------- | ------------- |
| 1 | Umgebung und Ausgangszustand | VERIFIED_RUNTIME | `macos-environment.md` | Keine |
| 2 | Baseline ohne Änderungen | VERIFIED_RUNTIME | `baseline-tests.md` | Keine |
| 3 | Service separat prüfen | VERIFIED_RUNTIME | `artifacts/runtime-tests/service/` | Keine |
| 4 | Fabric-Entwicklungsclient starten | VERIFIED_RUNTIME | `artifacts/runtime-tests/screenshots/main-menu-real.png`, `minecraft-mod/run/logs/latest.log` | Keine |
| 5 | Kontrollierte GUI-Nutzung | VERIFIED_RUNTIME | Automatisierter Direct-to-World-Start über `--quickPlaySingleplayer` ohne Menüautomation. Screenshot: `in-game.png`, `latest.log`. Commit: `24c23e2fc55b45f06d0a4f65fa521632d83ef8c4` | AppleScript-Interaktion mit GLFW-Menü unzuverlässig (Workaround angewandt) |
| 6 | Client-GameTests / Isolierte Welt | PARTIAL | Die Welt "TestWorld" wurde lokal in `minecraft-mod/run/saves/` generiert. Echte Client-GameTests fehlen. | Keine Fabric-Client-GameTests vorhanden/implementiert |
| 7 | End-to-End-Test | VERIFIED_RUNTIME | `end-to-end.md` / `cpu-quantum-test.md` | Request-IDs erfolgreich korreliert |
| 8 | Threading-Audit der Runtime-Integration | VERIFIED_RUNTIME | `threading-audit.md` | Keine synchronen Aufrufe oder geleakten Referenzen |
| 9 | Zugänglichkeit verbessern (HUD) | VERIFIED_RUNTIME | `QuantumRenderingClient.java` | HUD abgedunkelt, Tastenbelegung `Q` auf `V` geändert |
| 10 | Runtime-Metriken | VERIFIED_RUNTIME | `end-to-end.md` / `cpu-quantum-test.md` | Keine |
| 11 | Shadergerüst | VERIFIED_RUNTIME | `shader-audit.md` | Keine Integration von Shadern |
| 12 | Fehlerbehebung | VERIFIED_RUNTIME | `runtime-error-tests.md` | Alle Fehlerarten behandelt (Timeout, HTTP 500, Offline, Invalid JSON) |
| 13 | Abschlussvalidierung | VERIFIED_RUNTIME | Pytests (104 passed), Ruff, MyPy, Gradle Tests passed | Alle Tests sind ok |

## Nachweis: Isolierte Umgebung
Es wurde bestätigt, dass der gesamte Client-Status in `minecraft-mod/run/` gekapselt ist. Persönliche Welten unter `~/Library/Application Support/minecraft` wurden nicht gelesen oder geschrieben.
Die Datei `minecraft-mod/run/eula.txt` sowie `minecraft-mod/run/saves/TestWorld/` werden durch die `.gitignore` (`minecraft-mod/run/`) korrekt von Git ausgeschlossen.
