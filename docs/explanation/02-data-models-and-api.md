# Datenmodelle und REST-API

## 1. Einleitung und Spezifikationsgrundlagen

Die Kommunikation zwischen der Minecraft Fabric Client-Mod (Java) und dem Quantum Service (Python) erfolgt über eine genau definierte REST-Schnittstelle auf Basis von JSON-Payloads. Um eine strikte Abstraktion und Typsicherheit zwischen den Programmiersprachen zu gewährleisten, sind alle Transportdatenmodelle formal durch **JSON Schemas (Draft 2020-12)** spezifiziert.

Sowohl das Java-Frontend als auch das Python-Backend erzwingen das Schema-Attribut `additionalProperties: false`. Nicht spezifizierte oder fehlerhaft typisierte Felder führen unmittelbar zur Ablehnung der Netzwerkanfrage (HTTP 422 Unprocessable Entity in FastAPI bzw. `IllegalArgumentException` / `JsonSyntaxException` in Java).

---

## 2. Detaillierte Datenmodelle

### 2.1 `LightingRequest`
Das Modell `LightingRequest` kapselt alle Eingabedaten, die für eine Sichtbarkeitsschätzung erforderlich sind: die extrahierte Voxelszene, die Anfrageposition, die Oberflächennormale und die Parameter des gewählten Schätzalgorithmus.

* **Python-Definition**: `quantum-service/src/qmr/models.py`, Zeilen 98–137.
* **Java-Definition**: `minecraft-mod/src/main/java/ch/unibas/qmr/model/LightingRequest.java`.
* **JSON-Schema**: `schemas/lighting-request.schema.json`.

#### Wichtige Teilkomponenten:
1. **Voxelrepräsentation und Bitpacking**:
   Die Voxelszene wird in ein dreidimensionales Gitter der Klasse `VoxelGrid` (`quantum-service/src/qmr/voxel.py`, Zeilen 12–115) konvertiert. Um das Datenvolumen über HTTP minimal zu halten, wird der Zustand aller Voxels in kompakten LSB0-Bitsets gespeichert und Base64-kodiert.
   * `solid`: Base64-Bitset; Bit $i = 1$, falls Voxel $i$ blickdicht/solide ist.
   * `transparent`: Base64-Bitset; Bit $i = 1$, falls Voxel $i$ besetzt, aber lichtdurchlässig ist (z. B. Glas, Wasser).
   * `emissive`: Base64-Bitset; Bit $i = 1$, falls Voxel $i$ Licht emittiert.
   * `emission_values`: Liste von Emittenten-Objekten `{index, intensity}` für voxelspezifische Lichtstärken.
2. **Koordinatensystem und Ausrichtung**:
   Das Feld `coordinate_frame` definiert den Raumbezug:
   * `origin_world_block`: Ganzzahlige Weltkoordinaten `(x, y, z)` der minimalen Ecke des Voxel-Subgrids.
   * `axes`: Festgelegt auf `"minecraft_x_east_y_up_z_south"`.
   * `voxel_size`: $1.0$ Meter (1 Minecraft-Block).
3. **Abfrageposition und Normale**:
   Das Feld `query` (`LightingQuery`, `models.py` Zeile 87) spezifiziert:
   * `position_local`: Lokale Fließkomma-Koordinaten `(x, y, z)` innerhalb des Subgrids.
   * `surface_normal`: Normierter Richtungsvektor `(nx, ny, nz)` der getroffenen Blockoberfläche.
4. **Algorithmus- und Budget-Parameter**:
   * `algorithm`: Schätzverfahren (`"mock"`, `"exact"`, `"classical_monte_carlo"`, `"cpu_quantum"`, `"intel_gpu"`).
   * `direction_count`: Diskretisierungsgrad der Hemisphäre ($N \in \{8, 16, 32, 64\}$).
   * `max_oracle_calls`: Maximal zugelassenes Orakel- bzw. Evaluierungsbudget ($M$).
   * `seed`: Pseudozufallszahlengenerator-Seed $[0, 4294967295]$ für reproduzierbare Stochastik.
   * `desired_accuracy`: Ziel-Genauigkeit $(0, 1]$.
   * `confidence_level`: Statistisches Konfidenzniveau (z. B. $0.95$ für 95%).

---

### 2.2 `LightingResult`
Das Modell `LightingResult` enthält das Berechnungsergebnis des Service inklusive aller ermittelten Fehlergrenzen, Timing-Messungen und Quantenressourcen-Metriken.

* **Python-Definition**: `quantum-service/src/qmr/models.py`, Zeilen 152–186.
* **Java-Definition**: `minecraft-mod/src/main/java/ch/unibas/qmr/model/LightingResult.java`.
* **JSON-Schema**: `schemas/lighting-result.schema.json`.

#### Wichtige Teilkomponenten:
1. **Schätzwert und Fehler**:
   * `estimate`: Berechneter Ambient Visibility Wert $a \in [0, 1]$.
   * `ground_truth`: Exakter Referenzwert $a_{\text{exact}} \in [0, 1]$ (oder `null`, falls exakte Berechnung nicht gefordert).
   * `absolute_error`: $|a_{\text{estimate}} - a_{\text{exact}}|$.
   * `relative_error`: $|a_{\text{estimate}} - a_{\text{exact}}| / a_{\text{exact}}$.
   * `confidence_interval`: Intervallobjekt `{low, high, level, method}` (z. B. Wilson-Score oder Likelihood-Ratio Intervall).
2. **Quantenressourcen-Metriken**:
   * `qubit_count`: Anzahl benötigter Logik-Qubits ($n + 1$ mit $n = \log_2 N$).
   * `oracle_calls`: Verbrauchte $U_f$-Orakelaufrufe.
   * `shots`: Gesamtanzahl durchgeführter Messschüsse über alle Grover-Schaltkreise.
   * `circuit_executions`: Anzahl verschiedener Grover-Potenzen $k$.
   * `circuit_depth`: Maximale Gattertiefe der synthetisierten Grover-Schaltkreise.
   * `gate_count`: Gesamtanzahl elementarer Quantengatter.
3. **Timing-Metriken**:
   * `initialization_ms`: Dauer der Orakelsynthese und Budgetplanung.
   * `simulation_ms`: Reine Ausführungszeit der Simulation im Qiskit Statevector Sampler.
   * `transfer_ms`: Vom Client gemessene Netto-Übertragungszeit über HTTP.
   * `end_to_end_ms`: Gesamte serverseitige Bearbeitungszeit (`handler_ms`).

---

## 3. Übersichtstabelle aller Felder

| Feld | Datentyp | Bedeutung | Einheit | Erzeugt von | Verwendet von |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `schema_version` | `string` | Version des JSON-Spezifikationsstandards (`"1.0"`) | Version | Client / Service | Schema-Validator |
| `request_id` | `string (UUID)` | Eindeutige ID zur Zuordnung von Anfragen & Antworten | UUID | Client (`RequestFactory`) | Mod (`LightingResultCache`) |
| `voxel_dimensions` | `object {x,y,z}` | Gitterabmessungen (z. B. $9 \times 9 \times 9$) | Blöcke | Client (`SceneExtractor`) | Service (`VoxelGrid`) |
| `voxel_data.solid` | `string (Base64)`| Bitmaske für blickdichte Voxels | LSB0 Bits | Client (`CompactVoxelGrid`)| Service (`reaches_sky`) |
| `voxel_data.transparent` | `string (Base64)`| Bitmaske für transparente Voxels | LSB0 Bits | Client (`CompactVoxelGrid`)| Service (`reaches_sky`) |
| `voxel_data.emissive` | `string (Base64)`| Bitmaske für emittierende Voxels | LSB0 Bits | Client (`CompactVoxelGrid`)| Service (`VoxelGrid`) |
| `coordinate_frame` | `object` | Koordinatenursprung & Achsensystem | Weltblock | Client (`CoordinateTransform`)| Service (`VoxelGrid`) |
| `query.position_local` | `object {x,y,z}` | Startpunkt der Lichtstrahlen im Subgrid | Blöcke | Client (`queryTarget`) | Service (`reaches_sky`) |
| `query.surface_normal` | `object {x,y,z}` | Normenvektor der getroffenen Oberfläche | Vektor | Client (`queryTarget`) | Service (`directions.py`) |
| `direction_count` | `integer` | Richtungsanzahl auf der Hemisphäre ($N \in \{8,16,32,64\}$) | Strahlen | Client Mod-Config | Service (`directions.py`) |
| `algorithm` | `string (Enum)` | Gewähltes Backend (`"exact"`, `"cpu_quantum"` etc.) | Name | Client Mod-Config | Service (`api.py`) |
| `seed` | `integer` | Pseudozufalls-Seed für Monte Carlo / Shots | Zahl | Client Mod-Config | Service (`random`/Qiskit) |
| `max_oracle_calls` | `integer` | Orakel-Evaluierungsbudget $M$ | Aufrufe | Client Mod-Config | Service (`plan_budget`) |
| `estimate` | `number` | Geschätzte Ambient Visibility $a \in [0, 1]$ | Anteil | Service Backend | Mod (`VisibilitySmoother`) |
| `ground_truth` | `number \| null` | Exakte Referenz-Sichtbarkeit | Anteil | Service (`ExactBackend`) | Mod HUD / Benchmarks |
| `absolute_error` | `number \| null` | Absoluter Fehler $|a_{\text{est}} - a_{\text{exact}}|$ | Fehler | Service (`base.py`) | Mod HUD / Benchmarks |
| `oracle_calls` | `integer` | Verbrauchte Orakelaufrufe | Aufrufe | Service Backend | Mod HUD / Benchmarks |
| `qubit_count` | `integer` | Anzahl benötigter Logik-Qubits | Qubits | Service (`cpu_quantum.py`)| Benchmarks |
| `simulation_ms` | `number` | Dauer der Quantensimulation / Berechnung | Millisek. | Service Backend | Benchmarks |
| `end_to_end_ms` | `number` | Serverseitige Gesamtlaufzeit des Requests | Millisek. | Service (`api.py`) | Mod HUD / Benchmarks |

---

## 4. HTTP-Endpunkte im Detail

Alle REST-Endpunkte sind in `quantum-service/src/qmr/api.py` (Zeilen 68–186) definiert.

### 4.1 `GET /health`
* **Zweck**: Liveness- und Readiness-Überprüfung des Service.
* **Codepfad**: `api.py`, Zeilen 85–91 (`health()`).
* **Request**: Keiner (GET ohne Parameter).
* **Response (HTTP 200 OK)**:
  ```json
  {
    "status": "ok",
    "schema_version": "1.0",
    "backend_policy": "request"
  }
  ```
* **Fehlerfälle**: Keine unter normalen Bedingungen.

---

### 4.2 `GET /capabilities`
* **Zweck**: Abfrage aller auf dem Server verfügbaren Hardware- und Software-Backends sowie deren Systemmetadaten.
* **Codepfad**: `api.py`, Zeilen 93–101 (`capabilities()`).
* **Request**: Keiner (GET ohne Parameter).
* **Response (HTTP 200 OK)**:
  ```json
  {
    "backend_policy": "request",
    "configured_device_index": 0,
    "configured_precision": "single",
    "configured_max_qubits": 28,
    "backends": [
      {
        "name": "mock",
        "available": true,
        "reason": null,
        "devices": ["CPU"],
        "details": {}
      },
      {
        "name": "exact",
        "available": true,
        "reason": null,
        "devices": ["CPU"],
        "details": {}
      },
      {
        "name": "classical_monte_carlo",
        "available": true,
        "reason": null,
        "devices": ["CPU"],
        "details": {}
      },
      {
        "name": "cpu_quantum",
        "available": true,
        "reason": null,
        "devices": ["CPU (Qiskit StatevectorSampler)"],
        "details": {"qiskit_version": "1.3.2"}
      },
      {
        "name": "intel_gpu",
        "available": false,
        "reason": "No Intel GPU simulator provider is installed...",
        "devices": [],
        "details": {}
      }
    ]
  }
  ```

---

### 4.3 `POST /lighting/estimate`
* **Zweck**: Zentraler Endpunkt zur Ausführung einer Umgebungsverdeckungsschätzung.
* **Codepfad**: `api.py`, Zeilen 103–166 (`lighting_estimate(request)`).
* **Request**: JSON-Payload eines `LightingRequest`.
* **Response (HTTP 200 OK)**: JSON-Payload eines `LightingResult`.
* **Fehlerfälle**:
  * **HTTP 422 Unprocessable Entity**: Validierungsfehler des JSON-Schemas.
  * **HTTP 503 Service Unavailable**: Gewähltes Backend nicht verfügbar (z. B. `intel_gpu`, geworfen von `BackendUnavailableError`, Zeile 125).
  * **HTTP 504 Gateway Timeout**: Berechnungsdauer überschreitet `request_timeout_seconds` (geworfen von `asyncio.TimeoutError`, Zeile 113).
  * **HTTP 500 Internal Server Error**: Unerwarteter interner Ausführungsfehler (Zeile 127).

---

### 4.4 `POST /benchmark/run`
* **Zweck**: Ausführung ganzer Benchmark-Matrizen über vordefinierte Konfigurationsdateien (TOML/YAML) und Rückgabe generierter Artefakte.
* **Codepfad**: `api.py`, Zeilen 168–185 (`benchmark_run(request)`).
* **Request**: JSON-Payload mit Benchmark-Konfiguration `{ "config": { ... } }`.
* **Response (HTTP 200 OK)**: `BenchmarkRunResponse` mit Dateipfaden zu JSONL-, CSV- und Diagramm-Dateien.

---

## 5. Konkretes Beispiel: Request & Result

### 5.1 Beispiel `LightingRequest`
```json
{
  "schema_version": "1.0",
  "request_id": "a5d8b4e2-7f3a-4c1d-8e9b-0c2d4e6f8a1b",
  "voxel_dimensions": {
    "x": 3,
    "y": 3,
    "z": 3
  },
  "voxel_data": {
    "encoding": "bitset-base64",
    "bit_order": "lsb0",
    "solid": "AAAA",
    "transparent": "AAAA",
    "emissive": "AAAA",
    "emission_values": []
  },
  "coordinate_frame": {
    "origin_world_block": {
      "x": 100,
      "y": 64,
      "z": -200
    },
    "axes": "minecraft_x_east_y_up_z_south",
    "voxel_size": 1.0
  },
  "query": {
    "position_local": {
      "x": 1.5,
      "y": 1.5,
      "z": 1.5
    },
    "surface_normal": {
      "x": 0.0,
      "y": 1.0,
      "z": 0.0
    }
  },
  "direction_count": 8,
  "algorithm": "exact",
  "seed": 42,
  "desired_accuracy": 0.05,
  "confidence_level": 0.95,
  "max_oracle_calls": 64,
  "ray_max_distance": 128.0,
  "metadata": {}
}
```

### 5.2 Beispiel `LightingResult`
```json
{
  "schema_version": "1.0",
  "request_id": "a5d8b4e2-7f3a-4c1d-8e9b-0c2d4e6f8a1b",
  "backend": "exact",
  "estimate": 1.0,
  "ground_truth": 1.0,
  "absolute_error": 0.0,
  "relative_error": 0.0,
  "confidence_interval": {
    "low": 1.0,
    "high": 1.0,
    "level": 0.95,
    "method": "exact"
  },
  "qubit_count": null,
  "oracle_calls": 8,
  "shots": null,
  "circuit_executions": null,
  "circuit_depth": null,
  "gate_count": null,
  "initialization_ms": 0.02,
  "simulation_ms": 0.15,
  "transfer_ms": 0.0,
  "end_to_end_ms": 0.18,
  "warnings": [],
  "hardware": {
    "device_name": "CPU"
  },
  "software": {
    "python_version": "3.13.0"
  },
  "metadata": {
    "backend_end_to_end_ms": 0.18,
    "service_handler_ms": 0.25
  }
}
```

---

## 6. Request-ID UUID-Matching zur Vermeidung veralteter Daten

Da die Quantensimulation oder komplexe Monte-Carlo-Berechnungen asynchron im Hintergrund ablaufen, kann es bei schwankenden Netzwerk-Latenzen zu Verzögerungen kommen. Ein kritischer Fehler in Echtzeit-Spielen wie Minecraft wäre es, wenn das Ergebnis einer älteren Blickposition (z. B. vor einer Spielerbewegung) fälschlicherweise auf die neue Position angewendet wird.

### Implementierter Schutzmechanismus:
1. **UUID-Generierung**:
   Die Minecraft-Mod erzeugt bei jeder Erstellung einer Anfrageszene eine kryptografisch eindeutige Version-4-UUID:
   `RequestFactory.java`, Zeile 26:
   ```java
   String requestId = UUID.randomUUID().toString();
   ```
2. **In-Flight Sperre im Cache**:
   Vor dem Absenden registriert der `LightingController` die UUID im `LightingResultCache`:
   `LightingResultCache.java`, Zeilen 17–20 (`tryStart(requestId)`). Solange eine Anfrage mit einer UUID aussteht (`isPending() == true`), wird das Absenden neuer Anfragen blockiert.
3. **Serverseitiges Durchreichen**:
   Der Python FastAPI Service übernimmt das Feld `request_id` unverändert aus dem `LightingRequest` in das `LightingResult` (`models.py`, Zeile 154).
4. **Validierung beim Empfang**:
   Nach dem Eintreffen der HTTP-Antwort prüft der REST-Client explizit die Übereinstimmung der IDs:
   `LightingServiceClient.java`, Zeilen 42–45:
   ```java
   if (!Objects.equals(request.requestId(), result.requestId())) {
       throw new IOException("Mismatched request ID in service response");
   }
   ```
   Stimmt die empfangene `request_id` nicht exakt mit der ausstehenden Anfrage-UUID überein, wird die Antwort verworfen. Dadurch wird garantiert, dass veraltete Daten niemals im HUD angezeigt oder im Smoother verarbeitet werden.
