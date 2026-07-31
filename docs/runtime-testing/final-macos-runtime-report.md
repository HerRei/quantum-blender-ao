# Finale macOS Runtime-Prüfung

| Anforderung | Status | Evidenz | Einschränkung |
| ----------- | ------ | ------- | ------------- |
| 1. Client-GameTests | PARTIAL | `minecraft-mod/run/saves/TestWorld` | Echte Fabric-Client-GameTests nicht implementiert, nur lokale Testwelt verwendet |
| 2. Weltwechsel / Leave World | VERIFIED_RUNTIME | `client.log` (Logout-Sequence bei laufendem Delayed-Response) | Keine |
| 3. Clean Shutdown | VERIFIED_RUNTIME | Keine blockierenden Threads (Executor ist daemon-basiert / HTTP-Client wird aufgeräumt) | Gradle Launcher Threads bleiben bestehen (bekanntes Gradle-Verhalten) |
| 4. CPU-MLAE-End-to-End | VERIFIED_RUNTIME | `cpu-quantum-test.md`, Log-Matching, Latenz: 1.2s Service, 1.4s Roundtrip | Keine echte GPU verwendet |
| 5. Semantische Validierung | VERIFIED_RUNTIME | `test_error_modes.py`, `client.log` | `missing_visibility` (wird 0.0), `out_of_bounds` (scheitert), `wrong_schema` (scheitert), `negative_time` (scheitert), `old_request_id` (scheitert) |
| 6. HUD Skalierung | VERIFIED_RUNTIME | `guiScale: 0` und `guiScale: 3` (Large) getestet (`gui-scale-test.md`) | Keine |
| 7. Datei- und Prozess-Hygiene | VERIFIED_STATIC | `.gitignore` für `run/logs`, `run/eula.txt` & `artifacts` ist korrekt gesetzt. Audit-Daten unverändert. | Keine |
| 8. Abschlusslauf (Ruff, MyPy, Tests) | VERIFIED_AUTOMATED | 104 Pytests Passed, 0 Ruff-Fehler, MyPy-Typing korrigiert, Gradle `build test` Passed (6s) | Qiskit Missing Stubs Warnung ignoriert |
