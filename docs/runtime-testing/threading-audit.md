# Threading-Audit der Runtime-Integration

Die Integration des lokalen Python-Services in den Minecraft-Client wurde bezüglich der Threading- und Concurrency-Sicherheit geprüft. Alle Kriterien sind erfüllt:

1. **Keine synchronen Aufrufe auf dem Clientthread**: Die Methode `LightingController.submit` nutzt `gateway.estimate().whenComplete(...)`, wodurch der Minecraft-Hauptthread (`Render thread`) nicht blockiert wird.
2. **Kein blockierendes Warten**: Weder `.join()` noch `.get()` werden in `QuantumRenderingClient` oder `LightingController` aufgerufen.
3. **Kopieren der Chunkdaten**: Die `SceneExtractor`-Klasse führt via `MinecraftVoxelSampler` einen Read-Only-Durchlauf durch die relevanten Chunks durch und kopiert alle benötigten Voxel in die `ExtractedScene`.
4. **Isolierte Referenzen**: Der Hintergrund-Task für den HTTP-Call operiert ausschließlich auf der abgekoppelten `ExtractedScene` sowie dem serialisierten `LightingRequest`. Weder `World`, `Chunk` noch `BlockEntity` werden weitergegeben.
5. **Requestfrequenz**: Die Frequenz ist im Client über `ticks % config.requestIntervalTicks() != 0` limitiert (standardmäßig alle 20 Ticks). Zudem verhindert `cache.isPending()`, dass ein neuer Call startet, solange der vorherige läuft.
6. **Stale Responses**: `cache.complete(requestId, ...)` validiert die `requestId`. Alte Antworten überschreiben neuere Ergebnisse nicht, da der Cache die ID abgleicht.
7. **Ressourcenfreigabe**: `QuantumRenderingClient.onClientStopping` ruft `serviceClient.close()` auf, was den `HttpClient` und alle Threads korrekt terminiert.
