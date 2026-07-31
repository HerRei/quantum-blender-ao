# 00-overview.md — Gesamtübersicht des Projekts `quantum-minecraft-rendering`

## 1. Einleitung und Projektbeschreibung

Das Projekt **`quantum-minecraft-rendering`** ist ein wissenschaftliches Untersuchungssystem an der Schnittstelle von Computergrafik, Quanteninformatik und Monte-Carlo-Simulation. Es evaluiert die Anwendbarkeit von **Quantum Amplitude Estimation (QAE)** — konkret der nicht-adaptiven **Maximum-Likelihood Amplitude Estimation (MLAE)** — zur Schätzung der diskreten Umgebungsverdeckung (**Ambient Visibility**) in 3D-Voxelstrukturen.

### Forschungsfrage
> Kann ein quantenmechanischer Schätzalgorithmus (MLAE) bei identischem Rechnerbudget an Oracelabfragen ($M$) eine geringere statistische Schätzabweichung (RMSE) als das klassische Monte-Carlo-Verfahren (MC) bei der Berechnung der Ambient Visibility erzielen?

### Zentrale Klarstellung: Simulation vs. Echte QPU
Eine fundamentale Erkenntnis der Quanteninformatik und dieses Projekts betrifft das Verhältnis von physikalischer Hardware zu klassischer Emulation:

> Eine auf einer klassischen GPU simulierte QPU erzeugt keinen echten Quantum Speed-up.

Jede Simulation von Quantenschaltungen auf klassischer Hardware (wie einer CPU oder GPU mittels Qiskit `StatevectorSampler`) erfordert einen Speicher- und Rechenaufwand, der exponentiell mit der Anzahl der Qubits skaliert ($\mathcal{O}(2^n)$ Zustandsamplituden). Der theoretische quadratische Vorteil von QAE ($\mathcal{O}(M^{-1})$ statt $\mathcal{O}(M^{-1/2})$) bezieht sich ausschließlich auf die Anzahl der benötigten **logischen Oracelabfragen**, nicht auf die klassische Ausführungszeit der Zustandsemulation.

### Rolle von Minecraft und synthetischen Szenerien
> Minecraft ist primär Demonstration und Datenquelle. Der wissenschaftliche Kern funktioniert auch mit synthetischen Voxelszenen.

Minecraft (über die Fabric-Mod `minecraft-mod/`) dient als interaktive Visualisierungsplattform und Schnittstelle zur Extraktion realer Block-Geometrien. Der wissenschaftliche Kern des Projekts — die exakte mathematische Auswertung, die Monte-Carlo-Schätzung und die MLAE-Quantenschaltungssynthese — arbeitet vollständig unabhängig von Minecraft auf deterministischen, synthetischen Testszenerien in `quantum-service/src/qmr/scenes.py` (Zeilen 22–177).

---

## 2. Systemarchitektur und Datenfluss

Das Gesamtsystem gliedert sich in einen Python-basierten Microservice (`quantum-service/`), eine Java-basierte Minecraft-Fabric-Mod (`minecraft-mod/`), ein Iris-Shaderpack-Gerüst (`shaderpack/`) sowie ein umfangreiches Experimentier- und Audit-Framework (`experiments/`).

### Systemarchitektur (Mermaid-Flussdiagramm)

```mermaid
flowchart LR
    subgraph Client ["Client-Ebene (Minecraft / Test)"]
        MC[Minecraft Client / Fabric Mod]
        BenchScript[Benchmark / Audit Runner]
    end

    subgraph Service ["Python Microservice (quantum-service)"]
        API[FastAPI Router /api.py]
        Registry[Backend Registry /registry.py]
        Raycast[3D-DDA Raycaster /raycast.py]
        
        subgraph Backends ["Algorithmen-Backends"]
            Exact[ExactBackend /exact.py]
            MC_Backend[ClassicalMonteCarloBackend /monte_carlo.py]
            MLAE_Backend[CpuQuantumBackend /cpu_quantum.py]
            Mock[MockBackend /mock.py]
            IntelAdapter[IntelGpuBackend /intel_gpu.py]
        end

        Simulator[Qiskit StatevectorSampler]
    end

    MC -->|POST /lighting/estimate LightingRequest| API
    BenchScript -->|Direct Python Call / Audit| Registry
    API --> Registry
    Registry --> Raycast
    Raycast -->|Visibility Table f(i)| Exact
    Raycast -->|Visibility Table f(i)| MC_Backend
    Raycast -->|Visibility Table f(i)| MLAE_Backend
    
    MLAE_Backend -->|Quantum Circuit Q^k A| Simulator
    Simulator -->|Shot Measurements| MLAE_Backend
    
    Exact -->|LightingResult| API
    MC_Backend -->|LightingResult| API
    MLAE_Backend -->|LightingResult| API
    
    API -->|JSON LightingResult| MC
```

---

## 3. Rollenverteilung der Hardwarekomponenten

In der Konzeption und Durchführung des Projekts wurden verschiedene Hardware-Umgebungen betrachtet:

1. **Host-System mit AMD Radeon RX 9060 XT**:
   - Diente als primäres lokales Entwicklungssystem für die Ausführung der Python-basierten Microservice-Tests und lokalen Benchmarks.
   - Da Qiskit C++-Statevector-Simulationen primär auf der CPU ausführt, erfolgt der mathematische Kern der Zustandssimulation auf der CPU des Host-Systems.
2. **NVIDIA-GPU (Optionale zweite GPU)**:
   - Eine dedizierte NVIDIA-GPU mit CUDA-Unterstützung (z.B. RTX-Serie) könnte zur Beschleunigung von Qiskit Aer GPU-Simulationen (`cuStateVec`) eingesetzt werden.
   - Warum nicht zwingend erforderlich: Die Forschungsfrage bewertet die statistische Konvergenz bezüglich logischer Oracelabfragen $M$. Da $M$ auf dem exakten mathematischen Schaltungsmodell basiert, ändert die Ausführungsgeschwindigkeit der Simulation das mathematische Schätzergebnis nicht.
3. **Intel Arc A770 GPU (Ursprünglich geplantes Testbed)**:
   - Ursprünglich war die Arc A770 für Tests mit Intel oneAPI SYCL / Level Zero und dem `intel_gpu`-Backend vorgesehen.
   - Da kein SYCL-Qiskit-Provider im Zielsystem installiert ist, fungiert `IntelGpuBackend` in `quantum-service/src/qmr/backends/intel_gpu.py` (Zeilen 23–67) als Platzhalter-Adapter, der bei Aufruf kontrolliert `BackendUnavailableError` wirft.

---

## 4. Implementierungs- und Validierungsstatus

Zur Einhaltung strenger wissenschaftlicher Sorgfalt unterscheidet dieses Dokument präzise zwischen tatsächlich im Code implementierten Komponenten und bisher ungetesteten Systembereichen.

### Tatsächlich implementierte und verifizierte Komponenten
- **3D-DDA Raycaster**: Exakte klassische Sichtbarkeitsermittlung in `quantum-service/src/qmr/raycast.py` (Zeilen 12–58), verifiziert durch `tests/test_raycast.py`.
- **Exakte Auszählung (`exact`)**: `ExactBackend` in `quantum-service/src/qmr/backends/exact.py` (Zeilen 12–45).
- **Klassisches Monte Carlo (`classical_monte_carlo`)**: `ClassicalMonteCarloBackend` in `quantum-service/src/qmr/backends/monte_carlo.py` (Zeilen 38–87) mit Wilson-Score-Konfidenzintervallen.
- **Quanten-MLAE-Backend (`cpu_quantum`)**: `CpuQuantumBackend` in `quantum-service/src/qmr/backends/cpu_quantum.py` (Zeilen 256–422) mit automatischer Synthese des reversiblen Orakels $U_f$, der Zustandspräparation $A$, des Grover-Operators $Q$ und der Maximum-Likelihood-Schätzung.
- **Wissenschaftliches Audit-Framework**: Exakte Präregristrierungs- und Auswertungslogik in `quantum-service/src/qmr/audit_experiment.py` (Zeilen 98–553), getestet in `tests/test_audit_experiment.py`.
- **REST-API & Datenmodelle**: FastAPI-Server in `quantum-service/src/qmr/api.py` (Zeilen 68–166) und Pydantic-Modelle in `models.py`.

### Statisch vorhandene, aber ungetestete Komponenten
Folgende Systemkomponenten sind im Quelltext angelegt, wurden jedoch nicht im laufenden Zielsystem oder auf echter Hardware validiert:

> Diese Komponente wurde nur statisch geprüft beziehungsweise kompiliert und noch nicht im laufenden Zielsystem validiert.

Insbesondere betrifft dieser Vorbehalt:
1. Interaktive Minecraft-Laufzeit und Fabric-Client-Session im aktiven Spielbetrieb.
2. Fabric HUD-Overlay während des laufenden Spiels.
3. Iris-Shaderpack-Laden und Live-Injektion von Uniforms.
4. GPU-beschleunigte QPU-Simulation auf AMD Radeon RX 9060 XT.
5. Hardware-Ausführung auf Intel Arc A770 (Intel SYCL/oneAPI).
6. Optionale zweite NVIDIA GPU Execution.
7. Physikalische QPU-Ausführung (echte Quantenhardware).
8. PCIe 4.0 x2 Bus-Performanz und ReBAR (Resizable BAR) Systemzustand.
9. Das `intel_gpu`-Backend (`quantum-service/src/qmr/backends/intel_gpu.py`).

---

## 5. Wichtigste bisherige wissenschaftliche Ergebnisse

Aus dem unabhängigen wissenschaftlichen Audit (`docs/scientific-audit.md` und `experiments/audit-results/2026-07-31/`) gehen drei zentrale Kernergebnisse hervor:

1. **Dominanz der exakten Auszählung bei kleinen Zielräumen ($N=64$)**:
   - Da der Richtungsraum auf $N=64$ diskrete Richtungen beschränkt ist, ermittelt die exakte klassische Auszählung (`exact`) mit genau $M=64$ Oracelabfragen den Fehler $e=0$.
   - Für Budgets $M \ge 64$ ist die exakte Auszählung jedem stochastischen Schätzer (MC oder MLAE) bezüglich Fehler und Laufzeit strikt überlegen.

2. **Skalierung von Klassischem Monte Carlo**:
   - Monte Carlo bestätigt empirisch exakt das theoretische $\mathcal{O}(M^{-1/2})$-Fehlerskalierungsgesetz (gemessene Regressionssteigung auf log-log Skala: $-0.505$ bis $-0.528$).

3. **Verhalten von MLAE bei festem Schaltungs-Schedule ($k_{\max}=8$)**:
   - MLAE zeigt bei Budgeterhöhung von $M=245$ auf $M=490$ einen steilen Fehlerabfall durch die Auflösung lokaler Likelihood-Aliasing-Maxima.
   - Da die Schaltungstiefe im implementierten Setup bei $k_{\max}=8$ gedeckelt ist ($M \ge 35$), erhöht ein weiteres Ansteigen des Budgets $M$ lediglich die Anzahl der Mess-Shots $s$. Dadurch geht die asymptotische Fehlerskalierung von MLAE für große $M$ wieder in das klassische $\mathcal{O}(M^{-1/2})$-Regime über.
   - Der klassische Rechenaufwand der Qiskit CPU-Simulation ist dabei um den Faktor **$\approx 43.800\times$** langsamer als das klassische Monte-Carlo-Sampling (2.147 ms vs. 0,059 ms).
