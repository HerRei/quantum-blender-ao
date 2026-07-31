# 12 - Glossar

Dieses Glossar definiert über 40 zentrale Begriffe aus den Bereichen Quanteninformatik, klassische Beleuchtungsmathematik, Softwarearchitektur, Benchmarking und Minecraft-Modding mit exaktem Bezug zu dieser Codebasis.

---

## 1. Quantenmechanische Begriffe

### Amplitude
- **Definition:** Komplexe Zahl $\alpha_i \in \mathbb{C}$, welche den Quantenzustand eines Basiszustands $|i\rangle$ gewichtet. Das Betragsquadrat $|\alpha_i|^2$ ergibt die Messwahrscheinlichkeit.
- **Projektbezug:** In der Zustandspräparation $A|0\rangle$ entspricht die Amplitude des Systemzustands im "Good Subspace" exakt $\sqrt{a}$, wobei $a$ die exakte diskrete Ambient Visibility ist.

### Wahrscheinlichkeit ($P$)
- **Definition:** Die reelle Zahl $P \in [0, 1]$, mit der ein bestimmter Eigenzustand bei der Messung kollabiert.
- **Projektbezug:** Messwahrscheinlichkeit des Objective-Qubits $p_k(a) = \sin^2((2k+1)\arcsin(\sqrt{a}))$ nach $k$ Grover-Iterationen (`cpu_quantum.py:273`).

### Qubit
- **Definition:** Zweizustands-Quantensystem als elementare Informationseinheit im zweidimensionalen Hilbertraum $\mathbb{C}^2$.
- **Projektbezug:** Für $N=64$ Richtungen werden $n = \log_2(64) = 6$ Index-Qubits plus 1 Objective-Qubit (insgesamt 7 Qubits) in Qiskit instanziiert (`cpu_quantum.py:141`).

### Objective-Qubit
- **Definition:** Das spezifische Ziel-Qubit im Quantenregister, das den Erfolg oder Misserfolg einer Orakel-Auswertung durch seinen Zustand ($|1\rangle$ für "Good State", $|0\rangle$ für "Bad State") anzeigt.
- **Projektbezug:** Das höchstwertige Qubit (Index $n$) in `build_visibility_lookup_oracle` (`cpu_quantum.py:145`), welches den Sichtbarkeitswert $f(i)$ aufnimmt.

### Ancilla-Qubit
- **Definition:** Hilfs-Qubit im Quantenregister, das für Zwischenrechnungen oder mehrfach gesteuerte Gatter verwendet wird und am Ende zurückgesetzt werden muss (Uncomputation).
- **Projektbezug:** In der vorliegenden Implementierung wird auf Ancilla-Qubits verzichtet, indem Multi-Control-X-Gatter (`mcx`) direkt auf dem Indexregister arbeiten (`cpu_quantum.py:158`).

### Statevector
- **Definition:** Exakte mathematische Vektorrepräsentation $|\psi\rangle \in \mathbb{C}^{2^n}$ des Quantenzustands im vollständigen Hilbertraum ohne stochastisches Rauschen.
- **Projektbezug:** Verwendet in `Statevector.from_instruction()` im Backend `cpu_quantum` (`cpu_quantum.py:273`) sowie zur exakten Korrektheitsprüfung über alle 256 Acht-Bit-Tabellen (`test_backends.py:176`).

### Oracle ($U_f$)
- **Definition:** Eine als unitäre Matrix realisierte reversible Quantenschaltung, die eine klassische Funktion $f(x)$ quantenmechanisch auswertet: $U_f |i\rangle|y\rangle = |i\rangle|y \oplus f(i)\rangle$.
- **Projektbezug:** Synthetisiert in `build_visibility_lookup_oracle` (`cpu_quantum.py:141–161`), um die 3D-DDA-Visibility-Tabelle in die Quantenschaltung einzubinden.

### Lookup
- **Definition:** Der Zugriffsakt auf eine vorgegebene Datenstruktur (z. B. ein Array) zur Ermittlung eines Funktionswerts.
- **Projektbezug:** Im Quantendienst erfolgt der Lookup über die klassische Tabelle $f(i)$ beim Bau des $U_f$-Oracles sowie im klassisch-stochastischen Monte-Carlo-Backend (`monte_carlo.py:51`).

### Reversible Schaltung
- **Definition:** Quantenschaltung ohne Informationsverlust, deren Operationen durch unitäre Operatoren beschrieben werden und deren Eingangszustand aus dem Ausgangszustand eindeutig rekonstruierbar ist ($U^\dagger U = I$).
- **Projektbezug:** Jedes generierte Oracle $U_f$ und jeder Grover-Operator $Q$ in `cpu_quantum.py` ist streng reversibel aufgebaut.

### Zustandspräparation ($A$)
- **Definition:** Der unitäre Operator $A$, der den Initialzustand $|0\rangle^{\otimes (n+1)}$ in die gewichtete Superposition der Zielzustände überführt.
- **Projektbezug:** Aufgebaut in `build_state_preparation` (`cpu_quantum.py:164–171`) durch Anwendung von Hadamard-Gattern auf das Indexregister gefolgt vom Lookup-Oracle $U_f$.

### Grover-Operator ($Q$)
- **Definition:** Der unitäre Operator $Q = -A S_0 A^{-1} S_{\text{good}}$, der eine Drehung des Zustandsvektors in der von Good- und Bad-Subspace aufgespannten 2D-Ebene bewirkt.
- **Projektbezug:** Erzeugt in `build_visibility_operators` (`cpu_quantum.py:182–200`) mittels Qiskits `grover_operator()`.

### Grover-Potenz ($k$)
- **Definition:** Die Anzahl der aufeinanderfolgenden Wiederholungen des Grover-Operators $Q^k$ vor der Messung.
- **Projektbezug:** In `plan_budget` (`cpu_quantum.py:112–131`) wird der Schedule $K = (0, 1, 2, 4, 8)$ generiert, um die Amplitudenverstärkung stufenweise durchzuführen.

### Good State
- **Definition:** Ein Basiszustand im Hilbertraum, für den die Orakelfunktion den Wert $1$ liefert.
- **Projektbezug:** Alle Zustände $|i\rangle|1\rangle$, für die die Strahlrichtung $d_i$ ungehindert in den Himmel austritt ($f(i)=1$).

### Shot
- **Definition:** Eine einzelne Ausführung einer Quantenschaltung mit anschließender kollabierender Messung des Quantenregisters.
- **Projektbezug:** Die Anzahl der Messwiederholungen pro Schaltung `shots_per_circuit` in `QuantumBudget` (`cpu_quantum.py:24–78`).

### Circuit Execution
- **Definition:** Der einmalige Ablauf eines transpilierten Quantenschaltkreises auf einem Quantenprozessor oder Simulator.
- **Projektbezug:** Im Backend `cpu_quantum` entspricht dies der Ausführung der Schaltung $Q^k A|0\rangle$ im Qiskit `StatevectorSampler`.

### Sampler Job
- **Definition:** Eine an ein Backend übergebene Ausführungseinheit, die eine oder mehrere Quantenschaltungen mit einer vorgegebenen Zahl von Shots verarbeitet.
- **Projektbezug:** Im `cpu_quantum`-Backend wird pro `estimate()`-Aufruf exakt ein zusammenhängender Sampler-Job an Qiskit gesendet (`cpu_quantum.py:273`).

---

## 2. Mathematische & Statistische Begriffe

### Maximum Likelihood
- **Definition:** Statistisches Schätzprinzip, das denjenigen Parameterwert $\hat{a}$ bestimmt, der die beobachteten Messdaten unter dem zugrundeliegenden Wahrscheinlichkeitsmodell maximal wahrscheinlich macht.
- **Projektbezug:** Verwendet in Qiskit MLAE (`cpu_quantum.py:289`) sowie im Fixed-Grid-Optimizer (`audit_experiment.py:268–330`) zur Auswertung der Binomial-Log-Likelihood $\ell(a)$.

### MLAE (Maximum Likelihood Amplitude Estimation)
- **Definition:** Nicht-adaptive Variante der Quanten-Amplitudenschätzung, die ohne Phasenabschätzung (QPE) auskommt und stattdessen Schaltungen verschiedener Grover-Potenzen $k_j$ misst und statistisch maximiert.
- **Projektbezug:** Kernthema des Projekts, implementiert in `CpuQuantumBackend` (`cpu_quantum.py:256`).

### QAE (Quantum Amplitude Estimation)
- **Definition:** Überbegriff für Quantenalgorithmen zur Schätzung von Amplituden mit theoretisch quadratischem Geschwindigkeitsvorteil ($O(M^{-1})$ gegenüber $O(M^{-1/2})$).
- **Projektbezug:** Das theoretische Zielmodell, gegen das das implementierte MLAE verglichen wird.

### IQAE (Iterative Quantum Amplitude Estimation)
- **Definition:** Adaptive Variante von QAE, die Grover-Potenzen dynamisch basierend auf vorherigen Messungen anpasst, um optimale Konfidenzintervalle ohne Likelihood-Grid-Suche zu erreichen.
- **Projektbezug:** Wird in `docs/explanation/open-questions.md` als mögliche zukünftige Erweiterung diskutiert.

### QPE (Quantum Phase Estimation)
- **Definition:** Ursprünglicher QAE-Algorithmus basierend auf der Quanten-Fourier-Transformation (QFT) und zusätzlichen Evaluierungs-Qubits.
- **Projektbezug:** Aufgrund des hohen Qubit-Overheads nicht implementiert; stattdessen wurde MLAE gewählt.

### Bias (Systematischer Fehler)
- **Definition:** Die Differenz zwischen dem Erwartungswert des Schätzers und dem wahren Wert: $\operatorname{Bias}(\hat{a}) = \mathbb{E}[\hat{a}] - a$.
- **Projektbezug:** Detailliert evaluiert in `audit_experiment.py` (Zeilen 570–590) und dargestellt in Plot-Familie 2.

### Varianz ($\operatorname{Var}$)
- **Definition:** Die mittlere quadratische Abweichung des Schätzers von seinem eigenen Mittelwert: $\operatorname{Var}(\hat{a}) = \mathbb{E}[(\hat{a} - \mathbb{E}[\hat{a}])^2]$.
- **Projektbezug:** Bestandteil der Fehleranalyse in `audit_experiment.py` zur Trennung von Streuung und Bias.

### RMSE (Root Mean Squared Error)
- **Definition:** Die Quadratwurzel aus dem mittleren quadratischen Fehler: $\operatorname{RMSE} = \sqrt{\mathbb{E}[(\hat{a} - a)^2]} = \sqrt{\operatorname{Bias}^2 + \operatorname{Var}}$.
- **Projektbezug:** Das primäre Gütekriterium zur Bewertung von Schätzern in `audit_experiment.py` (Zeilen 580–600).

### Query Complexity (Abfragekomplexität)
- **Definition:** Die Anzahl der benötigten Aufrufe der Orakel-Funktion $U_f$ zur Erreichung einer vorgegebenen Genauigkeit $\epsilon$.
- **Projektbezug:** Beschrieben durch das realisierte logische Abfragebudget $M = s \cdot \sum (2k+1)$ in `plan_budget` (`cpu_quantum.py:112`).

### Wall-Clock Time (Echtzeit / Ausführungszeit)
- **Definition:** Die tatsächlich auf der physischen Uhr abgelaufene Zeit in Millisekunden vom Start bis zum Ende einer Operation.
- **Projektbezug:** Gemessen mittels `time.perf_counter_ns()` zur Ermittlung der Backend-Laufzeiten (`base.py:80`, `audit_experiment.py:411`).

---

## 3. Klassische Rendering- & Voxel-Begriffe

### DDA (Digital Differential Analyzer)
- **Definition:** Effizienter klassischer Algorithmus zum Durchwandern eines Rasters oder Voxel-Gitters entlang eines 3D-Strahls.
- **Projektbezug:** Implementiert in `quantum-service/src/qmr/raycast.py` (Zeilen 12–58) zur Bestimmung von $f(i)$.

### Voxel (Volumetric Pixel)
- **Definition:** Dreidimensionales Gitterelement in einem diskreten Raumvolumen.
- **Projektbezug:** Repräsentiert in `VoxelGrid` (`voxel.py:12`) und serialisiert in `CompactVoxelGrid.java` (`CompactVoxelGrid.java:35`).

### Ambient Visibility (Umgebungssichtbarkeit)
- **Definition:** Der Anteil der ungehinderten Richtungen auf der Halbkugel über einem Punkt, aus denen Umgebungslicht einfallen kann.
- **Projektbezug:** Der zentrale Zielwert $a = \frac{1}{N}\sum f(i)$, der vom Quantendienst geschätzt wird.

### Ambient Occlusion (Umgebungsverdeckung)
- **Definition:** Schattierungstechnik in der Computergrafik, die dunkle Bereiche an Ecken und Spalten basierend auf der Umgebungsverdeckung berechnet (Komplementärwert $1 - a$).
- **Projektbezug:** Visueller Ziel-Effekt für die Shader-Verarbeitung.

### Shader
- **Definition:** Kleinprogramm, das auf der GPU ausgeführt wird, um Eckpunkte (Vertex Shader) oder Fragmente/Pixel (Fragment Shader) zu verarbeiten.
- **Projektbezug:** Vorhanden als Pass-through-Gerüst unter `shaderpack/shaders/composite.fsh`.

### Uniform
- **Definition:** Globale Schreib-Lese-Variable in GLSL-Shadern, die von der CPU pro Frame an die GPU übergeben wird.
- **Projektbezug:** Geplante Schnittstelle für die Übergabe des Sichtbarkeitswerts an den Iris-Shader.

### Light Probe
- **Definition:** Diskreter Messpunkt im Raum, an dem Licht- und Sichtbarkeitsinformationen für umgebende Objekte abgetastet werden.
- **Projektbezug:** Die Abfrageposition `position_local` im `LightingQuery` (`models.py:87`).

---

## 4. Softwarearchitektur- & System-Begriffe

### Fabric
- **Definition:** Modding-Framework für Minecraft Java Edition, das das Laden und Verwalten von Client- und Server-Mods ermöglicht.
- **Projektbezug:** Das Java-Projekt unter `minecraft-mod/` basiert auf Fabric (Minecraft 26.1.2, Java 25).

### Iris
- **Definition:** Open-Source-Mod für Minecraft Fabric, die das Laden von OptiFine-kompatiblen Shaderpacks ermöglicht.
- **Projektbezug:** Das Gerüst unter `shaderpack/` ist für Iris strukturiert.

### Backend
- **Definition:** Konkrete Implementierung des Schätz-Interfaces `LightingBackend` (`base.py:34`).
- **Projektbezug:** Das System umfasst die Backends `mock`, `exact`, `classical_monte_carlo`, `cpu_quantum` und den Adapter `intel_gpu`.

### PCIe (Peripheral Component Interconnect Express)
- **Definition:** Hochgeschwindigkeits-Busstandard zur Verbindung von Hauptprozessor (CPU) und Grafikkarte/QPU.
- **Projektbezug:** Bezieht sich auf geplante Latenzmessungen beim Transfer von Voxel-Daten an GPU/QPU-Beschleuniger (`docs/hardware-target.md`).

### VRAM Residency
- **Definition:** Der Zustand, bei dem Daten permanent im Grafikspeicher (VRAM) verbleiben, um teure PCIe-Transfers zu vermeiden.
- **Projektbezug:** Geplantes Konzept für hochperformante Shader-Textur-Einspeisung.

### Quantum Speed-up
- **Definition:** Die nachweisbare Verringerung der asymptotischen Ausführungszeit oder Abfragekomplexität eines Quantenalgorithmus gegenüber dem besten bekannten klassischen Algorithmus.
- **Projektbezug:** Es konnte gezeigt werden, dass für das vorliegende Voxel-Visibility-Problem **kein** praktischer Quantum Speed-up erzielt wird (`09-results-and-interpretation.md`).

### QPU-Simulation
- **Definition:** Die klassische Nachbildung eines Quantenprozessors auf einer konventionellen CPU oder GPU durch Matrizen- und Vektormultiplikation.
- **Projektbezug:** Die Arbeitsweise von Qiskits `StatevectorSampler` im Backend `cpu_quantum` (`cpu_quantum.py:256`).
