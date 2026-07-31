# Minecraft-Mod-Architektur

## 1. Einleitung und Mod-Struktur

Die Komponente **`minecraft-mod`** ist als rein clientseitige Fabric-Modifikation für Minecraft 1.21 (Java 25) implementiert. Ihre Hauptaufgabe besteht darin, zur Laufzeit die Voxelgeometrie der direkten Spielumgebung zu erfassen, daraus strukturierte Beleuchtungsanfragen (`LightingRequest`) zu generieren, diese asynchron an den Python Quantum Service zu senden und die empfangenen Sichtbarkeitsergebnisse im Spiel-HUD flackerfrei anzuzeigen.

> Diese Komponente wurde nur statisch geprüft beziehungsweise kompiliert und noch nicht im laufenden Zielsystem validiert.

---

## 2. Fabric Mod-Initialisierung und Lifecycle

### 2.1 Metadaten (`fabric.mod.json`)
* **Datei**: `minecraft-mod/src/main/resources/fabric.mod.json` (Zeilen 1–25).
* **Mod-ID**: `quantum-minecraft-rendering`.
* **Umgebung**: `"environment": "client"` (Zeile 12) — Die Mod ist strikt clientseitig aufgebaut und erfordert keine serverseitige Installation auf Dedicated Servern.
* **Entry-Point**: `"client": ["ch.unibas.qmr.client.QuantumRenderingClient"]` (Zeilen 14–16).

### 2.2 Initialisierungsklasse (`QuantumRenderingClient`)
* **Datei**: `minecraft-mod/src/client/java/ch/unibas/qmr/client/QuantumRenderingClient.java`.
* **Klasse**: `QuantumRenderingClient` (implementiert `net.fabricmc.api.ClientModInitializer`, Zeile 46).
* **Initialisierungsmethode**: `onInitializeClient()` (Zeilen 65–84):
  1. **Konfigurationsladen**: Lädt Einstellungen aus `.minecraft/config/quantum-minecraft-rendering.json` via `ConfigStore` (Zeilen 66–69).
  2. **Netzwerk-Client Instanziierung**: Initialisiert `LightingServiceClient` mit dem asynchronen `JdkHttpTransport.createDefault()` (Zeilen 70–74).
  3. **Controller-Setup**: Erzeugt den `LightingController` zur Verwaltung in-flight Anfragen und Caching (Zeile 75).
  4. **Keybindings Registrierung**: Registriert Tastenzuweisungen via `registerKeys()` (Zeile 76).
  5. **Fabric Event-Hooks**:
     * `ClientTickEvents.END_CLIENT_TICK.register(this::onEndTick)` (Zeile 77): Aufruf am Ende jedes Game-Ticks.
     * `ClientLevelEvents.AFTER_CLIENT_LEVEL_CHANGE.register(...)` (Zeilen 78–79): Setzt bei Weltwechsel den Cache und Smoother zurück (`resetTransientState`).
     * `ClientLifecycleEvents.CLIENT_STOPPING.register(...)` (Zeile 80): Schließt Ressourcen beim Beenden des Spiels.
     * `HudElementRegistry.addLast(...)` (Zeilen 81–82): Registriert die HUD-Rendering-Funktion.

---

## 3. Ziel-Block-Auswertung und Raycasting (`queryTarget`)

Damit der Quanten-Service weiß, von welchem Punkt und in welche Richtung die Sichtbarkeitsstrahlen emittiert werden sollen, wertet die Mod in jedem Ausführungs-Intervall das Ziel des Spielers aus.

* **Datei**: `QuantumRenderingClient.java`, Methode `queryTarget(Minecraft minecraft)` (Zeilen 148–170).

### 3.1 Zielmodi
1. **Target-Block-Modus (`TargetMode.TARGETED_BLOCK`)**:
   Schaut der Spieler auf einen Block, ist `minecraft.hitResult` eine Instanz von `BlockHitResult`.
   * **Ziel-Blockkoordinate**: `BlockPos block = hit.getBlockPos()` (Zeile 151).
   * **Oberflächennormale**: $nx, ny, nz$ werden aus der getroffenen Blockseite ermittelt (`hit.getDirection().getStepX()`, Zeilen 152–154).
   * **Prävention von Eigenkollisionen (Voxel Shift)**:
     ##### Intuition
     Würde der Lichtstrahl exakt auf der mathematischen Grenzfläche der Blockbox starten, könnte der 3D-DDA-Raycaster den getroffenen Block sofort fälschlicherweise selbst als Hindernis werten (*Self-Intersection*).
     ##### Mathematische Form
     Der Abfragepunkt $\mathbf{p}_{\text{query}}$ wird um $\epsilon = 1.0 \times 10^{-4}$ Einheiten entlang der Oberflächennormale $\mathbf{n}$ nach außen verschoben:
     $$\mathbf{p}_{\text{query}} = \mathbf{p}_{\text{hit}} + \epsilon \cdot \mathbf{n}$$
     ##### Umsetzung im Code
     In `QuantumRenderingClient.java` Zeilen 158–161:
     ```java
     new Vector3(
         location.x + nx * 1.0e-4,
         location.y + ny * 1.0e-4,
         location.z + nz * 1.0e-4)
     ```
2. **Spieler-Modus (`TargetMode.PLAYER`)**:
   Blickt der Spieler ins Leere, dienen die Fußkoordinaten des Spielers (`player.position()`) und eine nach oben gerichtete Normale $\mathbf{n} = (0, 1, 0)$ als Fallback (Zeilen 164–169).

---

## 4. Voxelszenen-Extraktion ($9 \times 9 \times 9$ Voxel)

### 4.1 Szenenextraktor (`SceneExtractor`)
* **Datei**: `minecraft-mod/src/main/java/ch/unibas/qmr/scene/SceneExtractor.java` (Zeilen 10–50).
* **Radius & Würfeldimensionen**:
  Für einen Radius $r$ (Standard $r=4$, konfigurierbar 1–16) beträgt die Kantenlänge des Voxel-Subgrids:
  $$\text{side} = 2 \cdot r + 1 = 2 \cdot 4 + 1 = 9 \text{ Voxels}$$
  Das Gesamtvolumen umfasst somit $9 \times 9 \times 9 = 729$ Voxels.
* **Bounding Box Ursprung**:
  Der minimale Eckenblock des Rasters in Weltkoordinaten lautet (Zeilen 21–22):
  $$\mathbf{o}_{\text{world}} = (x_{\text{center}} - r,\, y_{\text{center}} - r,\, z_{\text{center}} - r)$$
* **Koordinatentransformation**:
  `CoordinateTransform.java` (Zeilen 8–34) rechnet Welt-Blockkoordinaten in lokale Subgrid-Koordinaten um:
  $$\mathbf{coord}_{\text{local}} = \mathbf{coord}_{\text{world}} - \mathbf{o}_{\text{world}}$$

### 4.2 Chunk-Verfügbarkeitsprüfung (`ChunkFootprint`)
* **Datei**: `minecraft-mod/src/main/java/ch/unibas/qmr/scene/ChunkFootprint.java` (Zeilen 12–32).
* **Logik**: Vor der Extraktion prüft `allChunksLoaded`, ob alle Minecraft-Chunks, die das horizontale Quadrat $[x_{\text{center}} - r, x_{\text{center}} + r] \times [z_{\text{center}} - r, z_{\text{center}} + r]$ abdecken, geladen sind. Fehlt auch nur ein Chunk, wird die Extraktion abgebrochen (`QuantumRenderingClient.java`, Zeile 133), um unvollständige Voxeldaten zu vermeiden.

### 4.3 Welt-Sampling (`MinecraftVoxelSampler`)
* **Datei**: `minecraft-mod/src/client/java/ch/unibas/qmr/client/MinecraftVoxelSampler.java` (Zeilen 18–23).
* **Eigenschaftenabfrage**:
  ```java
  BlockState state = level.getBlockState(new BlockPos(worldX, worldY, worldZ));
  boolean occupied = !state.isAir();
  boolean transparent = occupied && !state.canOcclude();
  double emission = state.getLightEmission();
  ```
  * Luftblöcke (`isAir()`) gelten als nicht besetzt.
  * Solide Blöcke (`canOcclude() == true`) blockieren die Licht- und Sichtstrahlen vollständig.
  * Transparente Blöcke (z. B. Glas) sind besetzt, blockieren die Sichtbarkeit aber nicht.

---

## 5. Lineare Voxel-Indizierung und Bitpacking

### 5.1 Didaktische Aufbereitung der Indizierungsformel

#### Intuition
Ein 3D-Voxelgitter der Dimension $dx \times dy \times dz$ muss für die Übertragung über das Netz in ein eindimensionales Array serialisiert werden. Um auf jedes Voxel eindeutig zuzugreifen, durchlaufen wir die Achsen in einer festgelegten Reihenfolge (Standard: $X$ präferiert, dann $Y$, dann $Z$).

#### Mathematische Form
Die Abbildung von 3D-Koordinaten $(x, y, z)$ auf den linearen Index $\text{index} \in \{0, \dots, N-1\}$ lautet:
$$\text{index}(x, y, z) = x + dx \cdot (y + dy \cdot z) = x + dx \cdot y + dx \cdot dy \cdot z$$

Für die Rückrechnung (*Unpacking*) eines linearen Index auf 3D-Koordinaten gilt mit $plane = dx \cdot dy$:
$$z = \left\lfloor \frac{\text{index}}{plane} \right\rfloor$$
$$y = \left\lfloor \frac{\text{index} \pmod{plane}}{dx} \right\rfloor$$
$$x = (\text{index} \pmod{plane}) \pmod{dx}$$

#### Kleines Beispiel
Gegeben sei ein Raster der Kantenlängen $dx=9, dy=9, dz=9$ ($plane = 81$).
Wir berechnen den Index für das Voxel an Position $(x=2, y=3, z=4)$:
$$\text{index} = 2 + 9 \cdot (3 + 9 \cdot 4) = 2 + 9 \cdot (3 + 36) = 2 + 9 \cdot 39 = 2 + 351 = 353$$

Rückrechnung aus Index 353:
$$z = \lfloor 353 / 81 \rfloor = 4$$
$$\text{Rest} = 353 \pmod{81} = 29$$
$$y = \lfloor 29 / 9 \rfloor = 3$$
$$x = 29 \pmod{9} = 2$$
Die Koordinaten $(2, 3, 4)$ werden exakt rekonstruiert.

#### Umsetzung im Code
* **Indizierung**: `CompactVoxelGrid.java` (Zeile 35):
  ```java
  public int index(int x, int y, int z) {
      return x + dimensions.x() * (y + dimensions.y() * z);
  }
  ```
* **Bitpack-Operationen (LSB0)**: `CompactVoxelGrid.java` (Zeilen 98–109):
  Da 8 Bits in ein Byte passen, liegt das Bit für `index` im Byte-Array an Position `index >>> 3` (Division durch 8). Die Bitposition im Byte lautet `index & 7` (Modulo 8).
  * **Bit lesen** (Zeile 99):
    ```java
    (data[index >>> 3] & (1 << (index & 7))) != 0
    ```
  * **Bit setzen** (Zeile 105):
    ```java
    data[index >>> 3] |= (1 << (index & 7));
    ```

#### Häufiges Missverständnis
Oft wird fälschlicherweise angenommen, dass $z + dz \cdot (y + dy \cdot x)$ verwendet wird. Die gewählte Zeilen-Hauptordnung (*Row-Major*) im Projekt setzt $x$ als am schnellsten variierenden Index fest. Stimmte die Reihenfolge im Java-Mod und Python-Service nicht exakt überein, würden alle Voxelachsen spiegelbildlich verdreht verarbeitet werden.

---

## 6. Asynchrone Threading-Architektur und Netzwerktransport

Ein zentrales Designprinzip der Minecraft-Mod ist: **Kein Netzwerk-I/O und keine Quantensimulation darf jemals den Haupt-Renderthread von Minecraft blockieren.**

```text
[ Render- / Tick-Thread ] ──(Trigger onEndTick)──► [ RequestFactory ]
           │                                             │
           │ (non-blocking submit)                       ▼
           ├───────────────────────────────► [ LightingController ]
           │                                             │
           │                                             ▼ (CompletableFuture)
           │                                    [ JdkHttpTransport ]
           │                                             │
   (Frame Rendering)                                     ▼ (Async I/O Worker Thread)
           │                                  [ POST /lighting/estimate ]
           │                                             │
           │ (Polls cache)                               ▼
    [ renderHud ] ◄──(whenComplete)─────────── [ LightingResultCache ]
```

### 6.1 Komponenten der Threading-Architektur
1. **`JdkHttpTransport`**:
   `minecraft-mod/src/main/java/ch/unibas/qmr/net/JdkHttpTransport.java` (Zeilen 10–41).
   Verwendet den nicht-blockierenden Java 11+ `java.net.http.HttpClient` mit einem Verbindungs-Timeout von 2 Sekunden (`connectTimeout(Duration.ofSeconds(2))`). Die Methode `post(...)` ruft `sendAsync(...)` auf und gibt ein `CompletableFuture<HttpResponseData>` zurück.
2. **`LightingServiceClient`**:
   `minecraft-mod/src/main/java/ch/unibas/qmr/net/LightingServiceClient.java` (Zeilen 14–53).
   Erzwingt ein internes Anfragen-Timeout via `.orTimeout(timeout.toMillis(), TimeUnit.MILLISECONDS)` (Zeile 32), deserialisiert das JSON mit Gson und prüft die `request_id` (Zeile 42).
3. **`LightingController`**:
   `minecraft-mod/src/main/java/ch/unibas/qmr/state/LightingController.java` (Zeilen 7–35).
   Empfängt Anfragen aus dem Tick-Thread. Wenn `cache.tryStart(requestId)` fehlschlägt (weil bereits eine Anfrage läuft), bricht `submit` sofort ab. Bei Erfolg wird ein asynchroner Callback `.whenComplete(...)` angefügt, der nach Eintreffen der Antwort den `LightingResultCache` aktualisiert.
4. **`LightingResultCache` & `VisibilitySmoother`**:
   * `LightingResultCache.java` (Zeilen 8–70): Thread-sicherer Speicher (`synchronized`), der bei Fehlern oder ausstehenden Anfragen den letzten gültigen Stand (`lastValid`) behält und somit HUD-Flackern verhindert.
   * `VisibilitySmoother.java` (Zeilen 4–36): Berechnet eine zeitabhängige exponentielle Glättung des Sichtbarkeitswerts $v_t$ zur Vermeidung harter Beleuchtungssprünge zwischen Schätzintervallen:
     $$\alpha = 1.0 - e^{-\Delta t / \tau}, \quad \tau = 0.25 \text{ Sekunden}$$

---

## 7. HUD-Rendering und Hotkeys

### 7.1 Hotkey-Steuerung
In `QuantumRenderingClient.java` (Zeilen 95–117) sind zwei zentral gesteuerte Tasten registriert:
* **Taste `Q`** (`key.quantum-minecraft-rendering.toggle`): Schaltet das Quanten-Rendering (Anfragegenerierung) an oder aus.
* **Taste `G`** (`key.quantum-minecraft-rendering.cycle_algorithm`): Schaltet durch die verfügbaren Schätzalgorithmen.
  * Umschaltreihenfolge (`Algorithm.java`, Zeilen 17–23): `EXACT` $\rightarrow$ `CLASSICAL_MONTE_CARLO` $\rightarrow$ `CPU_QUANTUM` $\rightarrow$ `EXACT`.

---

### 7.2 HUD-Übersichtstabelle (`renderHud`)
Das Debug-HUD wird über `renderHud` (`QuantumRenderingClient.java`, Zeilen 192–216) direkt auf dem Bildschirm gerendert.

| Element / Zeile im HUD | Datenquelle / Berechnung | Format / Beispiel | Bedeutung |
| :--- | :--- | :--- | :--- |
| `Quantum rendering: ON/OFF` | `config.enabled()` | `"Quantum rendering: ON"` | Status der Mod (Aktiviert/Deaktiviert via Taste `Q`) |
| `Mode: <ALGORITHM> (pending)`| `config.algorithm()` & `cache.isPending()` | `"Mode: CPU_QUANTUM (pending)"` | Aktueller Schätzmodus und ausstehender Netzwerkstatus |
| `Visibility: %.4f` | `VisibilitySmoother.update(...)` | `"Visibility: 0.7500"` | Exponentiell geglätteter Sichtbarkeitswert $a \in [0, 1]$ |
| `Backend: <NAME>` | `cached.result().backend()` | `"Backend: cpu_quantum"` | Tatsächlich vom Service ausgeführtes Backend |
| `Error: %s \| service %.2f ms \| RTT %.2f ms` | `result.absoluteError()`, `result.endToEndMs()`, `clientRoundTripMs` | `"Error: 0.0125 \| service 45.20 ms \| RTT 52.10 ms"` | Absoluter Schätzfehler, serverseitige und Gesamtlaufzeit |
| `Oracle calls: %d` | `cached.result().oracleCalls()` | `"Oracle calls: 48"` | Vom Backend verbrauchte Sichtbarkeits-Orakelaufrufe $M$ |
| `Error: <MSG>` | `cache.lastError()` | `"Error: TimeoutError"` | Fehlermeldung bei Netzwerk- oder Service-Problemen |
