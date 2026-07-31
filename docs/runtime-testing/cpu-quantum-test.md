# Prüfung von `cpu_quantum` Backend (Phase 8)

Die geforderte Prüfung des `cpu_quantum`-Backends wurde erfolgreich durchgeführt (siehe Screenshot `hud-cpu-quantum-pending.png`).

1. **Vorheriger Wert bleibt sichtbar**: Während eine neue Anfrage via `exact` berechnet wird, zeigt das HUD weiterhin die vorherigen Ergebnisse des `cpu_quantum`-Backends an (Visibility, Error, Servicezeit ~1171 ms).
2. **Status `(pending)`**: Der Modus wechselt korrekt auf `(pending)` (was "Computing" entspricht), um anzuzeigen, dass ein Request an den Service in Arbeit ist.
3. **Bedienbarkeit**: Da die HTTP-Requests und das Warten auf die Futures asynchron in einem eigenen Worker-Thread laufen, wird der Minecraft `Render thread` nicht blockiert (bestätigt durch die flüssigen >60 FPS und weiterhin ansteuerbares Menü).
4. **Ergebnisübernahme**: Das Ergebnis aktualisiert sich erst im HUD, wenn `cache.complete(...)` via Callback aufgerufen wird.
5. **Zeiten**: Die gemessene Servicezeit und End-to-End-Zeit (hier ~1.17 Sekunden für CPU Quantum) werden korrekt dargestellt.
6. **Keine GPU-Behauptung**: Das Backend wird korrekt und ehrlich als `cpu_quantum` und nicht als GPU-beschleunigt ausgewiesen.
