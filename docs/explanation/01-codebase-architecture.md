# Codebasis und Architektur

## 1. Einleitung und Gesamtarchitektur

Das Projekt **`quantum-minecraft-rendering`** erforscht die Anwendung von Quanten-Algorithmen (speziell *Maximum Likelihood Amplitude Estimation*, MLAE) zur Berechnung diskreter Umgebungsverdeckung (*Ambient Visibility*) in Voxelszenen. Das Gesamtsystem ist als verteilte Microservice-Architektur konzipiert, die sich in eine Rendering- und Erfassungskomponente (Minecraft Client-Mod), einen Forschungs- und Berechnungsservice (Python FastAPI Quantum Service) sowie eine vorbereitete Visualisierungsschicht (Iris Shaderpack Scaffold) gliedert.

> **Zentrale wissenschaftliche Klarstellung**: Der Quanten-Backend-Simulator (`cpu_quantum`) führt **kein** reversibles Raymarching auf Qubits aus und erzeugt auf klassischer Hardware keinen physikalischen Quantenvorteil (*Quantum Speedup*). Stattdessen berechnet ein klassischer 3D-DDA-Raycaster auf der CPU eine 1D-Sichtbarkeitstabelle $f(i) \in \{0, 1\}$, die anschließend in ein Orakel $U_f$ synthetisiert und mittels Qiskit-Statevector-Simulation über MLAE geschätzt wird.

---

## 2. Aufschlüsselung aller Ordner im Repository

Die Codebasis ist klar in acht primäre Verzeichnisse unterteilt. Im Folgenden wird jedes Verzeichnis nach Zweck, Schlüsseldateien, Abhängigkeiten, Ein-/Ausgaben, Schnittstellen und Teststatus analysiert.

### 2.1 `quantum-service`
* **Zweck**: Der zentrale Python-basierte Microservice zur Ausführung von Beleuchtungsschätzungen und Benchmarks.
* **Wichtigste Dateien**:
  * `quantum-service/src/qmr/api.py` (Zeilen 1–186): FastAPI-Webserver-Schnittstelle mit den REST-Endpunkten `/health`, `/capabilities`, `/lighting/estimate` und `/benchmark/run`.
  * `quantum-service/src/qmr/models.py` (Zeilen 1–186): Pydantic-Datenmodelle (`LightingRequest`, `LightingResult`, `VoxelData`, `StrictModel`).
  * `quantum-service/src/qmr/raycast.py` (Zeilen 12–63): Klassischer 3D-DDA-Raycaster (`reaches_sky`, `visibility_table`).
  * `quantum-service/src/qmr/backends/base.py` (Zeilen 1–85): Schnittstellendefinition `LightingBackend` (Zeile 34) und Fehlerklassen (`BackendError`, `BackendUnavailableError`).
  * `quantum-service/src/qmr/backends/cpu_quantum.py` (Zeilen 1–422): Qiskit MLAE-Quantensimulations-Backend (`CpuQuantumBackend`, Zeile 256).
  * `quantum-service/src/qmr/backends/monte_carlo.py` (Zeilen 1–87): Klassisches Monte-Carlo-Backend mit Wilson-Konfidenzintervall (`ClassicalMonteCarloBackend`, Zeile 38).
  * `quantum-service/src/qmr/backends/exact.py` (Zeilen 1–45): Exaktes Ground-Truth-Backend (`ExactBackend`, Zeile 12).
  * `quantum-service/src/qmr/backends/mock.py` (Zeilen 1–37): Festwert-Fixture-Backend (`MockBackend`, Zeile 11).
  * `quantum-service/src/qmr/backends/intel_gpu.py` (Zeilen 1–67): Platzhalter-Backend für Intel SYCL/oneAPI (`IntelGpuBackend`, Zeile 23).
  * `quantum-service/src/qmr/audit_experiment.py` (Zeilen 1–570): Wissenschaftliche Audit-Umgebung und gitterbasierter MLE-Solver (`FixedGridMlae`, Zeile 268).
* **Abhängigkeiten**: Python 3.11–3.13, `fastapi`, `pydantic`, `qiskit`, `qiskit-aer`, `numpy`, `scipy`, `matplotlib`.
* **Eingaben**: JSON-Beleuchtungsanfragen (`LightingRequest`) über HTTP POST oder CLI-Konfigurationsdateien (TOML/YAML).
* **Ausgaben**: JSON-Ergebnisse (`LightingResult`), Benchmark-CSV/JSONL-Dateien sowie Plot-Grafiken.
* **Beziehungen**: Empfängt Anfragen von `minecraft-mod` oder `scripts/run-benchmarks.sh`; validiert Einhaltung der Schemas aus `schemas/`.
* **Aktueller Teststatus**: Vollständig unit- und integrationsgetestet via `pytest quantum-service/tests` (31 Integrationstests).

### 2.2 `minecraft-mod`
* **Zweck**: Clientseitige Minecraft Fabric-Modifikation zur interaktiven Extraktion von Voxelszenen und Visualisierung der geschätzten Umgebungsverdeckung im HUD.
* **Wichtigste Dateien**:
  * `minecraft-mod/src/client/java/ch/unibas/qmr/client/QuantumRenderingClient.java` (Zeilen 46–224): Haupt-Mod-Initializer, Event-Registrierung, Raycasting (`queryTarget`), HUD-Rendering (`renderHud`).
  * `minecraft-mod/src/main/java/ch/unibas/qmr/scene/SceneExtractor.java` (Zeilen 10–50): Extraktion eines $9 \times 9 \times 9$-Voxelblocks um das Ziel-Blockpos.
  * `minecraft-mod/src/main/java/ch/unibas/qmr/voxel/CompactVoxelGrid.java` (Zeilen 12–115): Lineare Voxel-Indizierung und Base64-Bitpacking.
  * `minecraft-mod/src/main/java/ch/unibas/qmr/net/JdkHttpTransport.java` (Zeilen 10–41): Asynchroner HTTP-Client auf Basis von `java.net.http.HttpClient`.
  * `minecraft-mod/src/main/java/ch/unibas/qmr/net/LightingServiceClient.java` (Zeilen 14–53): REST-Client für Kommunikations-Payloads und Request-ID-Validierung.
  * `minecraft-mod/src/main/java/ch/unibas/qmr/state/LightingResultCache.java` (Zeilen 8–70): Thread-sicherer Resultat-Cache.
  * `minecraft-mod/src/main/java/ch/unibas/qmr/state/VisibilitySmoother.java` (Zeilen 4–36): Exponentielle Glättung von Visibilitätswerten.
* **Abhängigkeiten**: Java 25, Fabric Loader ($\ge 0.19.3$), Fabric API, Gson.
* **Eingaben**: Live-Weltzustand von Minecraft (Blöcke, Sichtstrahl des Spielers, Hotkey-Eingaben `Q` und `G`).
* **Ausgaben**: Asynchrone HTTP POST Anfragen an `/lighting/estimate`, HUD-Overlay-Anzeige.
* **Beziehungen**: Sendet Anfragen an `quantum-service` und liest lokale Mod-Konfigurationen (`quantum-minecraft-rendering.json`).
* **Aktueller Teststatus**: Unit-Tests für Logikkomponenten erfolgreich kompiliert und via `./gradlew test` verifiziert.
  > Diese Komponente wurde nur statisch geprüft beziehungsweise kompiliert und noch nicht im laufenden Zielsystem validiert.

### 2.3 `shaderpack`
* **Zweck**: Iris/OptiFine-kompatibles Shaderpack-Gerüst zur optischen Verrechnung der Ambient Visibility mit den Oberflächenfarben der Szene.
* **Wichtigste Dateien**:
  * `shaderpack/shaders/shaders.properties`: Iris-Konfigurationsdatei und Uniform-Deklarationen.
  * `shaderpack/shaders/composite.vsh`: Pass-through Vertex-Shader in GLSL 330 compatibility.
  * `shaderpack/shaders/composite.fsh`: Pass-through Fragment-Shader mit manuellen Diagnoseregler-Uniforms (`QMR_EXPERIMENTAL_LIGHTING`, `QMR_MANUAL_VISIBILITY`, `QMR_BLEND_PERCENT`).
  * `shaderpack/shaders/lib/qmr_visibility.glsl` (Zeilen 4–8): GLSL-Funktion `qmrApplyAmbientVisibility` zur Mischung von Grundfarbe und Sichtbarkeit.
* **Abhängigkeiten**: Iris Shader Mod / OptiFine, GLSL 330 compatibility.
* **Eingaben**: Render-Buffer von Minecraft, manuelle Diagnoseregler.
* **Ausgaben**: Modifizierter Framebuffer mit abgedunkelter Umgebungsverdeckung.
* **Beziehungen**: Sollte ursprünglich dynamische Uniforms der Mod empfangen; dient aktuell als statisches Diagnosegerüst.
* **Aktueller Teststatus**: Syntaktisch geprüft via Shell-Skript `scripts/check-shaders.sh`.
  > Diese Komponente wurde nur statisch geprüft beziehungsweise kompiliert und noch nicht im laufenden Zielsystem validiert.

### 2.4 `experiments`
* **Zweck**: Ablageort für Konfigurationsdateien, automatisierte Audit-Ergebnisse und generierte Benchmark-Diagramme.
* **Wichtigste Dateien**:
  * `experiments/configs/scientific-audit.toml`: Präregistrierte Konfiguration für das wissenschaftliche Audit.
  * `experiments/configs/smoke.toml`: Schnelle Rauchtest-Konfiguration für CI/CD.
  * `experiments/configs/course-study.yaml`: Konfiguration für Lehr- und Lernstudien.
  * `experiments/audit-results/2026-07-31/`: Archivierte CSV/JSONL-Rohdaten und Attestierungen des Audits.
  * `experiments/plots/`: Generierte Diagramme (RMSE vs. Oracle Calls, Latenz vs. Qubits etc.).
* **Abhängigkeiten**: Python `matplotlib`, `numpy`, `pandas`.
* **Eingaben**: Konfigurationsdateien, Laufzeitergebnisse des Quantum Service.
* **Ausgaben**: Vektorgrafiken (PDF/PNG) und strukturierte CSV/JSONL-Dateien.
* **Beziehungen**: Wird von `quantum-service/src/qmr/benchmark.py` und `scripts/run-benchmarks.sh` beschrieben und ausgelesen.
* **Aktueller Teststatus**: Datenbestand statisch validiert; Erzeugungsskripte in CI getestet.

### 2.5 `schemas`
* **Zweck**: Formalisierte JSON-Schema-Spezifikationen zur vertraglichen Fixierung der REST-Netzwerkschnittstelle.
* **Wichtigste Dateien**:
  * `schemas/lighting-request.schema.json`: Schema für Anfragen (Version `"1.0"`, Draft 2020-12).
  * `schemas/lighting-result.schema.json`: Schema für Ergebnisse (Version `"1.0"`, Draft 2020-12).
* **Abhängigkeiten**: JSON Schema Standard Draft 2020-12.
* **Eingaben**: Keines (Spezifikationsdateien).
* **Ausgaben**: Formale Validierungsvorgaben.
* **Beziehungen**: Garantiert Kompatibilität zwischen `minecraft-mod` (Java Gson) und `quantum-service` (Pydantic).
* **Aktueller Teststatus**: Automatiert validiert via `python3 -m json.tool` und `pytest quantum-service/tests/test_schemas.py`.

### 2.6 `scripts`
* **Zweck**: Hilfsskripte für Build, Test, Shader-Überprüfung und CI/CD-Prozesse.
* **Wichtigste Dateien**:
  * `scripts/check-shaders.sh`: Validierung von Shader-Dateien (Version-Header, Klammern-Balance, Include-Pfade).
  * `scripts/check-environment.sh`: Diagnose von System-Voraussetzungen (Java, Python, GPU-Tools wie `clinfo`, `sycl-ls`).
  * `scripts/run-service.sh`: Startet den Python-FastAPI-Service über `uv`.
  * `scripts/run-benchmarks.sh`: Führt Benchmark-Serien über `uv` aus.
  * `scripts/bootstrap-macos.sh` & `bootstrap-linux.sh`: Setup-Skripte für Entwicklerumgebungen.
* **Abhängigkeiten**: Bash, POSIX-Utilities, `uv`.
* **Eingaben**: Systemumgebung, Befehlszeilenparameter.
* **Ausgaben**: Konsolenausgaben, Prozess-Invocations.
* **Beziehungen**: Werden von Entwicklern und GitHub-Workflows aufgerufen.
* **Aktueller Teststatus**: Syntaktisch geprüft via `bash -n` und in CI ausgeführt.

### 2.7 `.github/workflows`
* **Zweck**: Automatisierte CI/CD-Pipelines für Qualitätskontrolle, Tests und Hardware-Diagnose.
* **Wichtigste Dateien**:
  * `.github/workflows/ci.yml`: Multi-Plattform CI (Ubuntu 24.04, macOS 15) für Python-Tests (`pytest`, `mypy`, `ruff`), Fabric-Mod-Build (`./gradlew build`) und Schema/Shader-Checks.
  * `.github/workflows/hardware-capabilities.yml`: Manuell auslösbarer Workflow für Self-Hosted GPU-Runner zur Abfrage von Vulkan/OpenCL/SYCL-Fähigkeiten.
* **Abhängigkeiten**: GitHub Actions Runner infrastructure.
* **Aktueller Teststatus**: In GitHub Actions aktiv eingebunden.

### 2.8 `docs`
* **Zweck**: Umfassende Projektdokumentation, Forschungsberichte, Vorlesungsentwürfe und detaillierte Erklärungsdateien (`docs/explanation/`).
* **Wichtigste Dateien**:
  * `docs/scientific-audit.md`: Der unabhängige wissenschaftliche Audit-Bericht.
  * `docs/explanation/00-overview.md` bis `12-glossary.md` sowie `open-questions.md`: Das didaktische Dokumentationssystem.
* **Aktueller Teststatus**: Markdown-Links und Pfadverweise manuell und automatisiert verifiziert.

---

## 3. Komponentenfluss (End-to-End Flow)

Der Daten- und Steuerfluss zwischen den einzelnen Modulen verläuft nach dem folgenden Schema:

```text
  [ Minecraft-Welt / Voxel Scene ]
                 │
                 ▼ (SceneExtractor.java & MinecraftVoxelSampler.java)
       [ ExtractedScene ]
                 │
                 ▼ (RequestFactory.java & CompactVoxelGrid.java)
       [ LightingRequest ] ──(JSON / HTTP POST via JdkHttpTransport)──► [ FastAPI Service (api.py) ]
                                                                                   │
                                                                                   ▼ (resolve_backend)
                                                                       [ ausgewähltes Backend ]
                                                                       (mock / exact / mc / cpu_quantum)
                                                                                   │
                                                                                   ▼
       [ LightingResult ] ◄──(JSON / HTTP Response)────────────────────────────────┘
                 │
                 ▼ (LightingServiceClient.java & LightingResultCache.java)
       [ VisibilitySmoother.java ]
                 │
                 ├──────────────────────────────┐
                 ▼                              ▼
          [ In-Game HUD ]           [ Shaderpack Scaffold ]
     (renderHud in Client)       (manuelle Regler / Ausblick)
```

### Schritt-für-Schritt-Ablauf:
1. **Szenenextraktion**: `QuantumRenderingClient.onEndTick` ermittelt die Blickrichtung (`queryTarget`) und ruft `SceneExtractor.extract` auf. `MinecraftVoxelSampler` liest Blöcke im Umkreis $r=4$ aus der Welt ab.
2. **Serialisierung**: `CompactVoxelGrid` konvertiert die $9 \times 9 \times 9$ Blöcke in drei LSB0-Bitsets (`solid`, `transparent`, `emissive`) und kodiert diese in Base64. `RequestFactory.create` baut ein `LightingRequest`-Objekt mit eindeutiger UUID.
3. **Netzwerktransport**: `JdkHttpTransport` sendet das JSON-Payload asynchron per POST an den Endpunkt `/lighting/estimate` des Python-Service. Der Render-Thread von Minecraft wird **nicht** blockiert.
4. **Backend-Routing**: FastAPI (`api.py:lighting_estimate`) empfängt den Request, prüft die Semaphore-Belegung und löst über `resolve_backend` das gewünschte Backend aus (`quantum-service/src/qmr/backends/registry.py`).
5. **Berechnung**:
   * Bei `cpu_quantum`: `raycast.py:visibility_table` berechnet per DDA die exakte Binärtabelle $f(i)$. `cpu_quantum.py:build_visibility_lookup_oracle` synthetisiert das Quantenorakel $U_f$. `StatevectorSampler` führt die Grover-Schaltkreise aus, gefolgt von Maximum Likelihood Estimation.
   * Bei `classical_monte_carlo`: Die Sichtbarkeitstabelle wird stochastisch abgetastet und ein Wilson-Intervall berechnet.
   * Bei `exact`: Die Tabelle wird vollständig ausgewertet.
6. **Antwort-Verarbeitung**: FastAPI gibt ein `LightingResult` als JSON zurück. `LightingServiceClient` verifiziert die `request_id` gegen die gesendete Anfragen-UUID zur Vermeidung veralteter Datenzuordnungen.
7. **Glättung & HUD**: `VisibilitySmoother` aktualisiert den exponentiellen Mittelwert mit der Zeitkonstanten $\tau=0.25\,\text{s}$. `renderHud` zeichnet den Schätzwert, Latenz und Orakelaufrufe auf dem Bildschirm.

---

## 4. Übersichtstabelle aller Komponenten

| Komponente | Sprache | Aufgabe | Aktuell getestet? | Abhängigkeiten |
| :--- | :--- | :--- | :--- | :--- |
| **`QuantumRenderingClient`** | Java 25 | Mod-Lifecycle, Event-Handling, HUD-Rendering, Keybindings | Ja (Kompilierung/Unit-Tests)* | Fabric API, Minecraft Client |
| **`SceneExtractor`** | Java 25 | Extraktion des $9 \times 9 \times 9$ Voxel-Würfels | Ja (`SceneExtractorTest.java`) | Minecraft World State |
| **`CompactVoxelGrid`** | Java 25 | Lineare Indizierung & Base64-LSB0-Bitpacking | Ja (`CompactVoxelGridTest.java`) | Base64-Encoder |
| **`JdkHttpTransport`** | Java 25 | Asynchroner HTTP POST Netzwerktransport | Ja (`LightingServiceClientTest.java`) | `java.net.http.HttpClient` |
| **`LightingResultCache`** | Java 25 | Thread-sichere Cache-Verwaltung & UUID-Matching | Ja (`LightingResultCacheTest.java`) | Java Concurrency |
| **`VisibilitySmoother`** | Java 25 | Exponentielle Glättung für flackerfreies HUD | Ja (`VisibilitySmootherTest.java`) | Math Utility |
| **Shaderpack Scaffold** | GLSL 330 | Optisches Blending (Grundfarbe $\times$ Sichtbarkeit) | Ja (Statisch via `check-shaders.sh`)* | Iris / OptiFine |
| **FastAPI Server (`api.py`)** | Python 3.13 | REST-API Schnittstelle & Timeout-Handling | Ja (`test_api.py`) | FastAPI, Uvicorn, Pydantic |
| **`3D-DDA Raycaster`** | Python 3.13 | 3D-DDA-Strahlverfolgung zur Sichtbarkeitsprüfung | Ja (`test_raycast.py`) | NumPy |
| **`ExactBackend`** | Python 3.13 | Exakte Auszählung aller $N$ Sichtbarkeitsstrahlen | Ja (`test_backends.py`) | DDA-Raycaster |
| **`ClassicalMonteCarloBackend`**| Python 3.13 | Monte-Carlo Sampling mit Wilson-Intervall | Ja (`test_backends.py`) | Python `random` |
| **`CpuQuantumBackend`** | Python 3.13 | Qiskit MLAE Quantensimulation (Finite Shots) | Ja (`test_backends.py`) | Qiskit, Qiskit-Aer |
| **`IntelGpuBackend`** | Python 3.13 | Adapter/Platzhalter für Intel GPU SYCL Simulation | Ja (Statische Struktur)* | None (Adapter) |
| **`MockBackend`** | Python 3.13 | Deterministischer Test-Fixture-Dummy | Ja (`test_backends.py`) | None |

*\* Hinweis: Komponenten mit Sternchen wurden nur statisch geprüft beziehungsweise kompiliert und noch nicht im laufenden Zielsystem (Live-Minecraft-Spiel / Echte GPU) validiert.*

---

## 5. Abstrakte Schnittstelle: Das Backend-Interface

Das Backend-System basiert auf dem Python-`Protocol`-Designmuster zur strikten Entkopplung von API-Schicht und Berechnungslogik.

### 5.1 Schnittstellendefinition (`base.py`)
In `quantum-service/src/qmr/backends/base.py` wird die abstrakte Schnittstelle `LightingBackend` definiert (Zeilen 34–46):

```python
class LightingBackend(Protocol):
    @property
    def name(self) -> str:
        ...

    def estimate(self, request: LightingRequest) -> LightingResult:
        ...

    def capability(self) -> BackendCapability:
        ...
```

Jedes Backend muss drei Eigenschaften/Methoden implementieren:
1. `name`: Eindeutiger Kennstring des Backends (z. B. `"cpu_quantum"`).
2. `estimate(request)`: Führt die Sichtbarkeitsschätzung durch und gibt ein standardisiertes `LightingResult`-Objekt zurück.
3. `capability()`: Liefert Metadaten zur Verfügbarkeit, unterstützten Hardware-Geräten und Einschränkungen (`BackendCapability`, Zeile 24).

### 5.2 Backend-Registrierung und Erzeugung (`registry.py`)
Die Erzeugung von Backend-Instanzen erfolgt zentral über die Fabrikfunktion `create_backend` in `quantum-service/src/qmr/backends/registry.py` (Zeilen 14–27):

```python
def create_backend(name: str | Algorithm) -> LightingBackend:
    key = str(name).lower()
    if key == Algorithm.MOCK:
        return MockBackend()
    if key == Algorithm.EXACT:
        return ExactBackend()
    if key == Algorithm.CLASSICAL_MONTE_CARLO:
        return ClassicalMonteCarloBackend()
    if key == Algorithm.CPU_QUANTUM:
        return CpuQuantumBackend()
    if key == Algorithm.INTEL_GPU:
        return IntelGpuBackend()
    raise ValueError(f"Unknown backend name: {name}")
```

### 5.3 Backend-Auswahl und Overrides (`api.py`)
In `quantum-service/src/qmr/api.py` (Zeilen 52–65 & 145–149) wird bestimmt, welches Backend aufgerufen wird:
* Ist in den Service-Einstellungen `settings.backend.name == "request"` konfiguriert, richtet sich die Wahl dynamisch nach dem Feld `request.algorithm` des Clients.
* Ist im Service ein festes Backend vordefiniert (z. B. `exact`), wird die Wahl des Requests überschrieben und eine entsprechende Warnung im `LightingResult.warnings`-Feld angefügt.

### 5.4 Fehlerbehandlungshierarchie
Das Backend-Interface definiert eine klare Ausnahmekaskade:
1. `BackendError(RuntimeError)` (`base.py`, Zeile 16): Basisklasse für alle backend-spezifischen Fehler.
2. `BackendUnavailableError(BackendError)` (`base.py`, Zeile 20): Wird geworfen, wenn ein gefordertes Hardware- oder Software-Backend nicht einsatzbereit ist (z. B. `intel_gpu`). FastAPI übersetzt dies in einen HTTP 503 Service Unavailable Status (`api.py`, Zeile 125).
3. **Timeout Handling**: Läuft die Berechnung länger als `settings.request_timeout_seconds`, bricht `asyncio.wait_for` die Ausführung ab und wirft ein HTTP 504 Gateway Timeout (`api.py`, Zeilen 113–124).
4. **Allgemeine Fehler**: Unerwartete Laufzeitfehler werden protokolliert und führen zu HTTP 500 Internal Server Error (`api.py`, Zeilen 127–136).

---

## 6. Detaillierte Analyse aller 5 Backends

### 6.1 Mock Backend (`mock`)
* **Datei**: `quantum-service/src/qmr/backends/mock.py`
* **Klasse**: `MockBackend` (Zeilen 11–37)
* **Funktionsweise**: Gibt sofort ein vordefiniertes Testergebnis mit dem Schätzwert $0.5$ (oder einem in den Metadaten konfigurierten Festwert) zurück.
* **Ressourcenaufwand**: 0 Orakelaufrufe (`oracle_calls=0`), 0 Shots, Ausführungszeit $< 1\,\text{ms}$.
* **Einsatzgebiet**: Schnelle Integrationstests des REST-APIs, Validierung der Mod-Verbindung und Client-Timeout-Prüfungen.
* **Warnhinweis**: Enthält standardmäßig die Warnung: `"Mock backend value is deterministic fixture data, not a measurement."`

### 6.2 Exaktes Ground-Truth Backend (`exact`)
* **Datei**: `quantum-service/src/qmr/backends/exact.py`
* **Klasse**: `ExactBackend` (Zeilen 12–45)
* **Mathematisches Konzept**:
  ##### Intuition
  Das Backend ermittelt die exakte Sichtbarkeit, indem es alle $N$ diskreten Fibonacci-Hemisphärenstrahlen einzeln per DDA-Raycasting bis zum Himmelsrand verfolgt und das Verhältnis der unbehinderten Strahlen berechnet.
  ##### Mathematische Form
  $$a_{\text{exact}} = \frac{1}{N} \sum_{i=0}^{N-1} f(i), \quad f(i) \in \{0, 1\}$$
  ##### Kleines Beispiel
  Bei $N=8$ Richtungen und 6 unbehinderten Strahlen ($f(i)=1$ für 6 Indizes) ergibt sich exakt:
  $$a_{\text{exact}} = \frac{6}{8} = 0.75$$
  ##### Umsetzung im Code
  In `exact.py` Zeilen 20–22:
  ```python
  table = visibility_table(request)
  estimate = sum(table) / len(table)
  ```
  ##### Häufiges Missverständnis
  Das exakte Backend liefert keinen Näherungswert mit Varianz, sondern die mathematisch exakte Referenz (*Ground Truth*) für die gegebene Richtungsdiskretisierung $N$.

### 6.3 Klassisches Monte-Carlo Backend (`classical_monte_carlo`)
* **Datei**: `quantum-service/src/qmr/backends/monte_carlo.py`
* **Klasse**: `ClassicalMonteCarloBackend` (Zeilen 38–87)
* **Mathematisches Konzept**:
  ##### Intuition
  Statt alle $N$ Strahlen auszuwerten oder systematisch vorzugehen, zieht Monte Carlo zufällig mit Zurücklegen $M$ Strahlenindizes und schätzt die Gesamtsichtbarkeit aus dem Stichprobenmittelwert.
  ##### Mathematische Form
  Für $M$ unabhängige Zufallsvariablen $X_j = f(I_j)$ mit $I_j \sim \text{Uniform}(\{0, \dots, N-1\})$:
  $$\hat{a}_{\text{MC}} = \frac{1}{M} \sum_{j=1}^{M} X_j, \quad \operatorname{Var}(\hat{a}_{\text{MC}}) = \frac{a(1-a)}{M}, \quad \text{RMSE} = \mathcal{O}(M^{-1/2})$$
  Das Konfidenzintervall wird über das Wilson-Score-Intervall berechnet (`wilson_interval`, Zeilen 15–35).
  ##### Kleines Beispiel
  Soll bei $a=0.5$ ein absoluter Fehler von $< 0.05$ erreicht werden, benötigt Monte Carlo ca. $M \approx 400$ Stichproben ($1/\sqrt{400} = 0.05$).
  ##### Umsetzung im Code
  In `monte_carlo.py` Zeilen 50–55:
  ```python
  rng = random.Random(request.seed)
  table = visibility_table(request)
  samples = [table[rng.randrange(len(table))] for _ in range(request.max_oracle_calls)]
  successes = sum(samples)
  estimate = successes / len(samples)
  ```
  ##### Häufiges Missverständnis
  Monte Carlo zählt jeden einzelnen zufälligen Strahltest als einen Orakelaufruf (`oracle_calls = M`). Es nutzt keine Quantenüberlagerung.

### 6.4 CPU Quanten-Backend (`cpu_quantum`)
* **Datei**: `quantum-service/src/qmr/backends/cpu_quantum.py`
* **Klasse**: `CpuQuantumBackend` (Zeilen 256–422)
* **Mathematisches Konzept**:
  ##### Intuition
  Das Quantenbackend codiert die Sichtbarkeitstabelle $f(i)$ in einen reversiblen Quantenschaltkreis $U_f$. Durch wiederholtes Anwenden des Grover-Rotationsoperators $Q = -A S_0 A^\dagger S_{\text{good}}$ wird die Amplitude des Ziel-Qubits verstärkt. Anschließend schätzt ein Maximum-Likelihood-Schätzer (MLAE) den Parameter $a = \sin^2(\theta)$ aus den Messzählungen endlicher Shots.
  ##### Mathematische Form
  Die Erfolgswahrscheinlichkeit nach $k$ Grover-Iterationen lautet:
  $$p_k(a) = \sin^2\left((2k+1)\arcsin(\sqrt{a})\right)$$
  Die Log-Likelihood-Funktion über ein Powers-Schema $\mathbf{k} = (k_0, k_1, \dots)$ mit $S$ Shots ist:
  $$\ell(a) = \sum_{j} \left[ h_j \ln p_{k_j}(a) + (S - h_j) \ln(1 - p_{k_j}(a)) \right]$$
  ##### Kleines Beispiel
  Für $a = 0.25$ ist $\theta = \arcsin(\sqrt{0.25}) = \pi/6 = 30^\circ$.
  Für $k=0$: $p_0(0.25) = \sin^2(1 \cdot 30^\circ) = 0.25$.
  Für $k=1$: $p_1(0.25) = \sin^2(3 \cdot 30^\circ) = \sin^2(90^\circ) = 1.0$ (vollständige Amplitudenvorstärkung auf 100%).
  ##### Umsetzung im Code
  In `cpu_quantum.py` Zeilen 277–340:
  `build_visibility_lookup_oracle` (Zeile 141) baut $U_f$, `plan_budget` (Zeile 112) plant den Grover-Plan $k \in (0, 1, 2, \dots)$, und Qiskits `MaximumLikelihoodAmplitudeEstimation` (Zeile 289) führt die Optimierung durch.
  ##### Häufiges Missverständnis
  Die Simulation läuft auf der klassischen CPU mittels Qiskit `StatevectorSampler`. Sie bietet **keinen** Laufzeitvorteil in Sekunden, sondern dient der wissenschaftlichen Erforschung des Orakel-Budgets $M = S \cdot \sum (2k+1)$.

### 6.5 Intel GPU Backend Adapter (`intel_gpu`)
* **Datei**: `quantum-service/src/qmr/backends/intel_gpu.py`
* **Klasse**: `IntelGpuBackend` (Zeilen 23–67)
* **Funktionsweise**: Dient als strukturierter Adapter/Platzhalter für zukünftige Quantensimulations-Engines auf Intel Arc GPUs via SYCL/oneAPI oder Intel Quantum SDK.
* **Status und Verhalten**:
  Beim Aufruf von `capability()` (Zeilen 46–60) prüft die Klasse, ob ein externer `provider` injiziert wurde. Fehlt dieser, wird `available=False` zurückgegeben. Wird `estimate()` aufgerufen (Zeilen 62–66), wirft das Backend direkt eine `BackendUnavailableError`-Ausnahme.
* **Testhinweis**:
  > Diese Komponente wurde nur statisch geprüft beziehungsweise kompiliert und noch nicht im laufenden Zielsystem validiert.
