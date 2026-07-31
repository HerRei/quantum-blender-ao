# End-to-End Korrelation (Phase 7 & 8)

Die vollständige End-to-End-Pipeline wurde verifiziert. Die Request-ID wird zwischen Client und Service übertragen und geloggt.

## Beispiel-Korrelation (Backend: exact)

**Request-ID**: `ef8311bd-c6d5-4b46-a3e1-42ca6475d501`

**Im Client (Minecraft)**:
- Request-Zeitpunkt (Tick): `[00:44:52]`
- Log: `[QuantumClient] Submitting request ef8311bd-c6d5-4b46-a3e1-42ca6475d501`
- Log: `[QuantumClient] Request ef8311bd-c6d5-4b46-a3e1-42ca6475d501 completed with exact, visibility: 0.1875, roundtrip: 4.074417ms`
- Übernahme in Cache: Ja, der Client loggt direkt die Completion und aktualisiert den HUD-State.

**Im Service (Python Backend)**:
- Request-Zeitpunkt: `2026-07-31T22:44:52.918654+00:00`
- Log: `{"backend":"exact","elapsed_ms":1.708417,"level":"INFO","logger":"qmr.api","message":"lighting_estimate_completed","request_id":"ef8311bd-c6d5-4b46-a3e1-42ca6475d501","status":200,"timestamp":"2026-07-31T22:44:52.918654+00:00"}`
- Serviceberechnungszeit: `1.708 ms`

Der HTTP-Roundtrip (inkl. Netzwerk und JSON-Deserialisierung im Client) dauerte `4.074 ms`. Dies beweist eine erfolgreiche Kommunikation und sehr niedrige Latenz.
Die visuelle Darstellung im HUD wurde per Screenshot gesichert (`hud-improved-active.png`).
