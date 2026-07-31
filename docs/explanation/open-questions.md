# Offene technische und wissenschaftliche Fragen

Diese Datei dokumentiert alle bestätigten offenen technischen Punkte, wissenschaftlichen Forschungsfragen sowie ungeklärten Code-Fragen des Projekts `quantum-minecraft-rendering`. Sie dient als Referenz für zukünftige Arbeiten und verhindert, dass nicht getestete oder geplante Komponenten als funktionsfähig missverstanden werden.

---

## 1. Bestätigte offene technische Punkte

Folgende Komponenten und Systemzustände sind im Code statisch angelegt oder kompiliert, wurden jedoch im laufenden Zielsystem noch **nicht** praktisch validiert:

> Diese Komponente wurde nur statisch geprüft beziehungsweise kompiliert und noch nicht im laufenden Zielsystem validiert.

### 1.1 Minecraft-Laufzeittest (In-World Playtest)
- **Status:** Ungetestet im Live-Spiel.
- **Beschreibung:** Die Java-Klassen des Fabric-Mods (`QuantumRenderingClient.java`, `SceneExtractor.java`) wurden mittels Unit-Tests (`./gradlew test`) geprüft und erfolgreich kompiliert. Eine vollständige interaktive Spielsitzung im laufenden Minecraft-Client zur Messung von Frame-Zeiten und Client-Latenzen steht noch aus.

### 1.2 Chunkgrenzen und Weltwechsel (Chunk Footprint Boundary Validation)
- **Status:** Statisch abgesichert, nicht im Live-Spielszenario erprobt.
- **Beschreibung:** `ChunkFootprint.allChunksLoaded()` (`minecraft-mod/src/main/java/ch/unibas/qmr/scene/ChunkFootprint.java`, Zeilen 12–32) prüft das Vorhandensein geladener Chunks. Das Verhalten bei schnellen Teleportationen oder Weltwechseln (z. B. Betreten des Nethers) wurde noch nicht unter realer Spiellast validiert.

### 1.3 Live-HUD-Validierung
- **Status:** Statisch kompiliert, visuell im Zielsystem unbestätigt.
- **Beschreibung:** Der Registrierungscode für das Debug-HUD (`QuantumRenderingClient.java`, Zeilen 81–82, `renderHud()`) ist korrekter Fabric-Code, wurde aber im laufenden Render-GUI noch nicht optisch inspiziert.

### 1.4 Dynamic Shader Bridge (Iris Custom Uniform Integration)
- **Status:** Nur als statisches Pass-through-Gerüst vorhanden (`shaderpack/shaders/composite.fsh`).
- **Beschreibung:** Iris bietet aktuell keine öffentliche Fabric-API, über die eine externe Java-Mod zur Laufzeit pro Frame eine dynamische `uniform float`-Variable an ein Shaderpack übergeben kann. Die Anbindung des Sichtbarkeitswerts an den Fragment-Shader bleibt somit eine ungeklärte Schnittstellenaufgabe.

### 1.5 GPU-Backend (`intel_gpu`)
- **Status:** Reiner Schnittstellen-Adapter (`quantum-service/src/qmr/backends/intel_gpu.py`, Zeilen 23–67).
- **Beschreibung:** Bei Aufruf von `estimate()` wirft das Backend eine `BackendUnavailableError`, da noch kein SYCL/oneAPI- oder Level-Zero-Provider angebunden ist (`intel_gpu.py:62-66`).

### 1.6 Linux-Zielsystem & Hardware-Testbed
- **Status:** Ungetestet.
- **Beschreibung:** Das geplante Zielsystem (Ubuntu Linux mit dedizierten Grafikbeschleunigern wie RX 9060 XT oder Arc A770) steht laut `.github/workflows/hardware-capabilities.yml` nur als manueller `workflow_dispatch` zur Verfügung und wurde im Audit noch nicht ausgeführt.

### 1.7 PCIe 4.0 x2 Latenz- und Bandbreitenmessung
- **Status:** Theoretisches Zielmodell (`docs/hardware-target.md`), noch keine Hardware-Messungen.
- **Beschreibung:** Die Übertragungszeiten für Voxel-Daten über eine physikalische PCIe-Schnittstelle konnten mangels QPU/GPU-Testbed nicht gemessen werden.

---

## 2. Wissenschaftliche offene Fragen

### 2.1 Adaptive vs. Nicht-adaptive Quanten-Amplitudenschätzung
- **Frage:** Wäre eine adaptive QAE-Variante wie Iterative Quantum Amplitude Estimation (IQAE) oder Faster Amplitude Estimation (FAE) besser geeignet als das implementierte nicht-adaptive MLAE mit festem Gitter?
- **Kontext:** Das nicht-adaptive MLAE leidet bei kleinen Budgets ($M \le 245$) unter Likelihood-Aliasing und lokalen Maxima. IQAE wählt Grover-Potenzen dynamisch basierend auf vorangegangenen Shots und könnte die Anzahl unproduktiver Log-Likelihood-Auswertungen reduzieren.

### 2.2 Skalierung der Quanten-Oracle-Synthese
- **Frage:** Wie skaliert der Aufwand für den Bau des reversiblen Sichtbarkeits-Oracles $U_f$ (`cpu_quantum.py:141-161`), wenn die Richtungsanzahl $N$ von 64 auf $1024$ oder $1.048.576$ erhöht wird?
- **Kontext:** Aktuell wächst die Anzahl der Multi-Control-X-Gatter (`mcx`) linear mit den Einsen in der Sichtbarkeitstabelle. Für große $N$ könnte die klassische Synthesezeit des Oracles die gesamte Einsparung bei der Schätzung dominieren.

### 2.3 Evaluierung in großen Suchräumen ($N \gg 64$)
- **Frage:** Ab welcher Problemgröße $N$ übertrifft die Abfragekomplexität von QAE die exakte klassische Auszählung?
- **Kontext:** Wie in `09-results-and-interpretation.md` gezeigt, dominiert die exakte Auszählung bei $N=64$ völlig ($0.00025\text{ ms}$). Um ein Regimewechsel zu demonstrieren, müsste die Sichtbarkeitstabelle durch eine implizite, mathematisch bewertbare Voxel-Szenenfunktion im Quantenregister ersetzt werden, damit $N \ge 2^{20}$ evaluiert werden kann.

### 2.4 Reversibles Voxel-Ray-Tracing auf QPUs
- **Frage:** Wie müsste eine voll-reversible 3D-DDA-Quantenschaltung aufgebaut sein, die Voxel-Daten direkt aus einem Quantenspeicher (QRAM) liest, ohne dass eine klassische Tabelle vorab erstellt werden muss?
- **Kontext:** Erst ein solches end-to-end reversibles Quanten-Raytracing würde das klassische Pre-Processing eliminieren und einen theoretisch vollwertigen Quantum Speed-up ermöglichen.

---

## 3. Ungeklärte Punkte im Code und Dokumentation

Beim systematischen Review der Codebasis wurden folgende Stellen identifiziert, bei denen Fragen oder Unklarheiten bestehen:

### 3.1 `quantum-service/src/qmr/backends/intel_gpu.py`, Zeilen 33–36
- **Unklarheit:** Der Code sucht nach CLI-Diagnose-Werkzeugen (`clinfo`, `sycl-ls`, `zeinfo`, `vulkaninfo`), stellt jedoch selbst bei Vorhandensein dieser Tools keine Anbindung an ein Qiskit-C++-GPU-Backend (wie `qiskit-aer-gpu`) her.
- **Einordnung:** Bestätigter Platzhalter-Adapter. Es ist unklar, welches C++/Python-Binding für ein echtes SYCL-Backend geplant war.

### 3.2 `shaderpack/shaders/shaders.properties`, Zeile 8
- **Unklarheit:** Zeile 8 deklariert `uniform.float.qmrReservedVisibility = smooth(9001, 1.0, 8.0, 8.0)`.
- **Einordnung:** Dies ist ein synthetischer Ausdruck in Iris, der sich statisch zu `1.0` auswertet. Im Code existieren keine Hinweise darauf, wie hier ein Java-Wert injiziert werden soll.

### 3.3 `quantum-service/src/qmr/audit_experiment.py`, Zeilen 118–125
- **Unklarheit:** In der Audit-Konfiguration wird `desired_accuracy = 0.05` fest vorgegeben.
- **Einordnung:** Gemäß Scientific Audit SA-03 führt dieser feste Wert dazu, dass das Grover-Schedule für alle Budgets $M \ge 35$ bei $k_{\max}=8$ saturiert. Es ist im Code nicht dokumentiert, warum kein dynamisch mit $M$ wachsendes Schedule (z. B. $k \in \{0, 1, 2, 4, 8, 16, 32\}$) gewählt wurde, um echtes $O(M^{-1})$-Skalieren zu testen.
