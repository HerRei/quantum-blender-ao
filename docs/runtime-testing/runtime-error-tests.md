# Runtime-Fehler- und Resilienztests (Phase 10)

Um die Stabilität der Client-Service-Kommunikation unter widrigen Bedingungen zu garantieren, wurden mittels eines isolierten Mock-Servers (`test_error_modes.py`) verschiedene Ausfallszenarien simuliert und verifiziert:

1. **Service offline**
   - **Verhalten**: Der Client fängt sofort eine `java.net.ConnectException` ab.
   - **Effekt**: Der HUD-Status wechselt auf "Error", der Rendering-Thread wird nicht beeinträchtigt.

2. **HTTP-Fehler (z. B. 500 Internal Server Error)**
   - **Verhalten**: Der Service antwortete gezielt mit 500. Der Client wirft eine `ch.unibas.qmr.net.LightingServiceException: lighting service returned HTTP 500`.
   - **Effekt**: Die Exception wird im Callback sauber geloggt und verworfen, der Client re-pollt danach regulär.

3. **Ungültige Response (z. B. fehlerhaftes JSON / falsches Schema)**
   - **Verhalten**: Der Service antwortete mit `{"not_an_estimate": "hello"}`.
   - **Effekt**: Gson schlägt bei der Deserialisierung von `LightingResult` fehl. Der Fehler (`Failed to invoke constructor ...`) wird gefangen und nicht an den Render-Thread propagiert.

4. **Timeout und verzögerte Antworten (Stale Responses)**
   - **Verhalten**: Der Mock-Server verzögerte die Antwort künstlich um 6 Sekunden. Da in `quantum-minecraft-rendering.json` das Timeout auf 5000 ms konfiguriert ist, feuert der Java `HttpClient` pünktlich eine `java.net.http.HttpTimeoutException: request timed out`.
   - **Effekt**: Die Verbindung wird getrennt, das Future scheitert sicher. Später eintreffende Antworten vom Backend (sogenannte "Stale Responses") würden ohnehin vom `LightingResultCache` anhand der `requestId` verworfen werden.

5. **Weltwechsel**
   - **Verhalten**: Wird beim Verlassen der Welt oder dem Betreten einer neuen Welt getriggert.
   - **Effekt**: Die Event-Registrierung `ClientLevelEvents.AFTER_CLIENT_LEVEL_CHANGE` ruft `resetTransientState()` auf, wodurch der Cache sowie der Smoother-Status gelöscht und keine alten (falschen) Chunks mehr referenziert werden.
