# 05-mlae-implementation.md — Konkrete MLAE-Implementierung

## 1. Einleitung

Diese Datei erklärt die praktische Implementierung der **Maximum-Likelihood Amplitude Estimation (MLAE)** im Python-Microservice `quantum-service`. Sie führt Schritt für Schritt durch den tatsächlichen Codepfad in `quantum-service/src/qmr/backends/cpu_quantum.py`, leitet die Binomial-Log-Likelihood mathematisch her, erklärt das detaillierte Orakel-Kostenmodell $M = s \cdot \sum(2k+1)$, definiert das Metrik-Trennungs-Schema und beschreibt die exhaustive Korrektheitsprüfung aller 256 8-Bit-Wahrheitstabellen.

---

## 2. Der vollständige Codepfad der Quantenschätzung

### Ablaufdiagramm des Datenflusses
```text
1. Visibility-Tabelle f(i)     [raycast.py: visibility_table]
   │
2. Reversibles Orakel U_f       [cpu_quantum.py: build_visibility_lookup_oracle, Zeilen 141-161]
   │
3. Zustandspräparation A        [cpu_quantum.py: build_state_preparation, Zeilen 164-171]
   │
4. Grover-Operator Q            [cpu_quantum.py: build_visibility_operators, Zeilen 182-200]
   │
5. Grover-Schedule (k_0, k_1..) [cpu_quantum.py: plan_budget, Zeilen 112-131]
   │
6. Finite Shots s               [cpu_quantum.py: StatevectorSampler Execution]
   │
7. Messzählungen h_j            [Anzahl 1-Messungen auf Objective-Qubit]
   │
8. Likelihood-Maximierung l(a)  [audit_experiment.py: FixedGridMlae, Zeilen 268-330 / Qiskit MLAE]
   │
9. Geschätzte Sichtbarkeit a    [LightingResult Objekt]
```

### Einzelschritte im Code

1. **Reversibles Sichtbarkeits-Orakel $U_f$**:
   - **Datei & Funktion**: `quantum-service/src/qmr/backends/cpu_quantum.py`, `build_visibility_lookup_oracle(table)` (Zeilen 141–161).
   - **Registergröße**: $(n + 1)$ Qubits für eine Tabelle der Länge $N = 2^n$.
   - **Objective-Qubit**: Das Qubit an Index $n$ (letztes Qubit).
   - **Synthese**: Für jeden Index $i$ mit $f(i) = 1$ werden Pauli-X Gates auf die Null-Bit-Steuereingänge angewendet, ein Multi-Controlled-X (`mcx`) Gate auf das Objective-Qubit geschaltet und die X-Gates zur Wiederherstellung des Indexregisters erneut angewendet.

2. **Zustandspräparationsoperator $A$**:
   - **Datei & Funktion**: `quantum-service/src/qmr/backends/cpu_quantum.py`, `build_state_preparation(lookup_oracle)` (Zeilen 164–171).
   - **Synthese**: Schaltet Hadamard-Gates $H$ auf alle Index-Qubits $0 \dots n-1$ und fügt anschließend das Orakel-Gate `U_f` an.

3. **Good-State Reflection $S_{\text{good}}$**:
   - **Datei & Funktion**: `quantum-service/src/qmr/backends/cpu_quantum.py`, `build_good_state_reflection(num_qubits, objective_qubit)` (Zeilen 174–179).
   - **Synthese**: wendet ein Pauli-Z-Gate direkt auf `objective_qubit` an ($Z|1\rangle = -|1\rangle$).

4. **Grover-Operator $Q$**:
   - **Datei & Funktion**: `quantum-service/src/qmr/backends/cpu_quantum.py`, `build_visibility_operators(table)` (Zeilen 182–200).
   - **Synthese**: Erzeugt $Q = -A S_0 A^{-1} S_{\text{good}}$ über Qiskit's `grover_operator(good_state_reflection, state_preparation=preparation)`.

5. **Budgetplanung und Grover-Schedule**:
   - **Datei & Funktion**: `quantum-service/src/qmr/backends/cpu_quantum.py`, `plan_budget(max_oracle_calls, desired_accuracy)` (Zeilen 112–131).
   - **Schedule-Generierung**: Erstellt eine Zweierpotenz-Folge $k \in (0, 1, 2, 4, 8, 16, \dots)$. Eine neue Power wird aufgenommen, solange die Summe der Orakel-Kosten $\sum (2k+1)$ das Gesamtbudget `max_oracle_calls` nicht übersteigt.
   - **Shot-Berechnung**: `shots = max_oracle_calls // sum(2k + 1)`.

6. **Ausführung im Backend**:
   - **Datei & Klasse**: `quantum-service/src/qmr/backends/cpu_quantum.py`, `CpuQuantumBackend.estimate(request)` (Zeilen 256–422).
   - **Ablauf**: Baut `EstimationProblem` auf, ruft Qiskit `MaximumLikelihoodAmplitudeEstimation` auf und wertet das Ergebnis aus.

---

## 3. Binomial-Log-Likelihood Mathematik

### 1. Intuition
Nachdem wir für verschiedene Schaltungen mit Grover-Iterationen $k_0, k_1, \dots, k_{m-1}$ jeweils $s$ Mess-Shots auf dem Objective-Qubit durchgeführt haben, erhalten wir eine Trefferanzahl $h_j$ von Einsen. Die Likelihood-Funktion fragt: „Welche wahre Sichtbarkeit $a \in [0, 1]$ macht das Auftreten genau dieser gemessenen Treffermengen $h_0, h_1, \dots, h_{m-1}$ am wahrscheinlichsten?“

### 2. Mathematische Form
Sei $K = (k_0, k_1, \dots, k_{m-1})$ der Vektor der verwendeten Grover-Potenzen. Für jede Schaltung $j \in \{0, \dots, m-1\}$ führen wir $s_j$ Shots aus.
Die Erfolgswahrscheinlichkeit $p_{k_j}(a)$ für einen einzelnen Shot lautet:
$$p_{k_j}(a) = \sin^2\left( (2k_j + 1) \arcsin(\sqrt{a}) \right)$$

Die beobachtete Anzahl guter Zustände $h_j$ folgt einer Binomialverteilung:
$$h_j \sim \operatorname{Binomial}(s_j, p_{k_j}(a))$$

Die Wahrscheinlichkeit (Likelihood) $L(a)$ für das Gesamtergebnis ist das Produkt der Einzelwahrscheinlichkeiten:
$$L(a) = \prod_{j=0}^{m-1} \binom{s_j}{h_j} \left[ p_{k_j}(a) \right]^{h_j} \left[ 1 - p_{k_j}(a) \right]^{s_j - h_j}$$

Da Produkte numerisch leicht zu Unterläufen (Underflow) führen, verwenden wir die **Log-Likelihood** $\ell(a) = \ln L(a)$ (unter Weglassen der additiven Binomialkoeffizienten-Konstanten):
$$\ell(a) = \sum_{j=0}^{m-1} \left\{ h_j \ln\left[ p_{k_j}(a) \right] + (s_j - h_j) \ln\left[ 1 - p_{k_j}(a) \right] \right\}$$

#### Parameterbedeutungen
- $h_j \in [0, s_j]$: Anzahl der gemessenen Einsen (Good States) im $j$-ten Experiment.
- $s_j \in \mathbb{N}^+$: Anzahl der Messungen (Shots) des $j$-ten Schaltkreises.
- $k_j \in \mathbb{N}_0$: Grover-Iterationszahl ($Q^{k_j}$).
- $\ell(a)$: Logarithmische Plausibilität der Sichtbarkeit $a$.

#### Maximum-Likelihood-Schätzer (MLE)
Der geschätzte Wert $\hat{a}$ ist der Wert auf dem Intervall $a \in [0, 1]$, der die Log-Likelihood maximiert:
$$\hat{a} = \arg\max_{a \in [0, 1]} \ell(a)$$

#### Numerische Optimierung im Audit-Grid (`FixedGridMlae`)
Im wissenschaftlichen Audit (`quantum-service/src/qmr/audit_experiment.py`, Klasse `FixedGridMlae`, Zeilen 268–330) wird das Maximum durch eine hochpräzise Vektorauswertung über $8193$ gleichmäßig verteilte Punkte $a \in [0, 1]$ bestimmt:
- **Epsilon-Clipping** (Zeilen 288–289): Um $\ln(0)$ bei $p_{k_j}(a) = 0$ oder $p_{k_j}(a) = 1$ zu verhindern, werden die Wahrscheinlichkeiten auf den Bereich $[\epsilon_{\text{tiny}}, 1 - \epsilon_{\text{eps}}]$ beschränkt (`np.clip(probabilities, tiny, 1.0 - eps)`).
- **Likelihood-Ratio-Konfidenzintervall** (Zeilen 319–325):
  Basierend auf der Asymptotik des Likelihood-Quotienten-Tests ($\chi^1_1$-Verteilung) wird ein Cutoff berechnet:
  $$\ell_{\text{cutoff}} = \ell(\hat{a}) - \frac{1}{2} z_{1 - \alpha/2}^2$$
  Das Konfidenzintervall $[a_{\text{low}}, a_{\text{high}}]$ ist die äußere Hülle aller Grid-Punkte mit $\ell(a) \ge \ell_{\text{cutoff}}$.

### 3. Kleines Beispiel
Angenommen $K = (0, 1)$ mit $s = 100$ Shots.
- Schaltung 0 ($k_0=0$): Gemessen $h_0 = 25$ Einsen.
- Schaltung 1 ($k_1=1$): Gemessen $h_1 = 100$ Einsen.
1. Für $a=0,25 \implies p_0(0.25) = 0,25$ und $p_1(0.25) = 1,0$.
   - Log-Likelihood für $a=0,25$:
     $$\ell(0.25) = 25 \ln(0.25) + 75 \ln(0.75) + 100 \ln(1.0) + 0 \ln(0.0) \approx 25(-1.386) + 75(-0.287) + 0 = -56.175$$
2. Für $a=0,50 \implies p_0(0.50) = 0,50$ und $p_1(0.50) = 0,50$.
   - Log-Likelihood für $a=0,50$:
     $$\ell(0.50) = 25 \ln(0.5) + 75 \ln(0.5) + 100 \ln(0.5) + 0 = 200 \ln(0.5) = -138.629$$
Da $-56.175 \gg -138.629$, bewertet der Likelihood-Test $a=0,25$ als weitaus plausibler als $a=0,50$.

### 4. Häufiges Missverständnis
*Missverständnis*: „Die Log-Likelihood $\ell(a)$ besitzt immer genau ein einziges globales Maximum ohne lokale Nebenmaxima.“  
*Korrektur*: Wegen der oszillierenden $\sin^2((2k+1)\theta)$-Terme ist $\ell(a)$ für große $k$ stark multimodal (vielgipflig). Bei zu kleinen Shot-Zahlen kann ein lokales Nebenmaximum (Alias) fälschlicherweise höher liegen als das echte Maximum. Erst durch die Kombination kleinerer und größerer $k$-Werte werden die Aliase eliminiert.

---

## 4. Das Oracle-Kostenmodell

### 1. Herleitung der Audit-Formel $M = s \cdot \sum_k (2k+1)$
Wie viele logische Abfragen an das Sichtbarkeits-Orakel $U_f$ verursacht eine Ausführung des Quantenschaltkreises?

1. **Ein Aufruf der Zustandspräparation $A$**:
   $$A = U_f (H^{\otimes n} \otimes I) \implies 1 \text{ Aufruf von } U_f$$
2. **Ein Aufruf des Grover-Operators $Q$**:
   $$Q = -A \cdot S_0 \cdot A^{-1} \cdot S_{\text{good}}$$
   Da $Q$ sowohl $A$ (enthält $U_f$) als auch $A^{-1}$ (enthält $U_f^\dagger$) enthält, verursacht jedes $Q$ exakt **2 logische Orakelaufrufe** ($1 \cdot U_f + 1 \cdot U_f^\dagger$).
3. **Ein Schaltkreis mit Grover-Power $k$ ($Q^k A |0\rangle$)**:
   $$\text{Orakelaufrufe pro Shot} = 1 \text{ (für initiales } A) + k \cdot 2 \text{ (für } Q^k) = 2k + 1$$
4. **Bei $s$ Mess-Shots**:
   $$\text{Orakelaufrufe für Schaltung } k = s \cdot (2k + 1)$$
5. **Gesamtbudget über den gesamten Schedule $\mathbf{k}$**:
   $$M = s \cdot \sum_{j=0}^{m-1} (2k_j + 1)$$

### 2. Exakte Trennung der Ressourcen- und Laufzeitmetriken

Zur Vermeidung irreführender Angaben unterscheidet das Projekt strikt zwischen folgenden Kennzahlen:

| Metrik | Definition / Formel | Einheit | Wissenschaftliche Bedeutung |
| :--- | :--- | :--- | :--- |
| **Visibility Lookups** | $f(i)$ Auswertungen im DDA | Bit-Reads | Klassische Strahlenauswertung zur Erstellung der Tabelle. |
| **Oracle Calls ($M$)** | $s \cdot \sum_j (2k_j + 1)$ | $U_f / U_f^\dagger$ Calls | Theoretisches logisches Abfragebudget im Quantenmodell. |
| **State Preparations** | $s \cdot \sum_j (k_j + 1)$ | $A$-Aufrufe | Gesamtzahl der angewendeten Präparationsschritte. |
| **Inverse Preparations** | $s \cdot \sum_j k_j$ | $A^{-1}$-Aufrufe | Gesamtzahl der angewendeten inversen Präparationsschritte. |
| **Grover Iterations** | $s \cdot \sum_j k_j$ | $Q$-Iterationen | Gesamtzahl der angewendeten Grover-Rotationsschritte. |
| **Shots ($s$)** | Konfigurierte Replikation | Wiederholungen | Klassische Stichprobenmessungen des Zielqubits. |
| **Circuit Templates** | $m = \|\mathbf{k}\|$ | Schaltungen | Anzahl eindeutiger Grover-Potenz-Schaltkreise. |
| **Sampler Jobs** | Anzahl Backend-Aufrufe | Jobs | Anzahl der an den Simulator übergebenen Batch-Jobs. |
| **Gate Count** | $s \cdot \sum \text{gates}(A Q^{k_j})$ | Elementar-Gates | Fiktive Gesamtzahl elementarer Quantengatter ($u, cx$). |
| **Circuit Depth** | $\max_j \text{depth}(A Q^{k_j})$ | Gattertiefe | Längster serieller Pfad von Quantengattern. |
| **Oracle Synthesis Time** | Dauer von `build_visibility_lookup_oracle` | ms | Klassische CPU-Zeit zur Erzeugung des $U_f$-Schaltkreises. |
| **Simulation Time** | Dauer der `StatevectorSampler` Ausführung | ms | Klassische CPU-Zeit zur Matrix-Vektor-Zustandsevolution. |
| **End-to-End Time** | Gesamtzeit von Request bis LightingResult | ms | Vollständige Systemlaufzeit inklusive I/O und Parsing. |

*Warum diese Trennung zwingend ist*: Ein Vergleich von *Simulationszeit* (Klassische Rechenzeit) mit *Oracle Calls* (Logische Quantenabfragen) würde Äpfel mit Birnen vergleichen. Nur die logischen Oracelabfragen $M$ erlauben einen fairen mathematischen Vergleich zwischen Quanten-MLAE und klassischem Monte Carlo.

---

## 5. Exhaustive Korrektheitsprüfung (256 8-Bit-Tabellentest)

### 1. Zweck und mathematische Grundlage
Um die mathematische Exaktheit der Quantenschaltkreiskonstruktion und der Grover-Rotationsformel zweifelsfrei zu beweisen, enthält die Testsuite eine vollständige **exhaustive Verifikation** aller möglichen 8-Bit-Sichtbarkeitstabellen.

Für eine Voxel-Sichtbarkeitstabelle der Länge $N=8$ ($n=3$ Index-Qubits) existieren genau:
$$2^8 = 256 \text{ verschiedene Boolesche Wahrheitstabellen}$$

### 2. Funktionsweise im Testcode
- **Datei & Testfunktion**: `quantum-service/tests/test_backends.py`, `test_all_eight_entry_truth_tables_follow_the_grover_rotation_formula()` (Zeilen 176–198).
- **Ablauf**:
  1. Schleife über alle Bitmasken `mask` von `0` bis `255` (Zeile 181).
  2. Dekodierung der Maske in eine 8-elementige binäre Tabelle: `table = [(mask >> index) & 1 for index in range(8)]` (Zeile 182).
  3. Berechnung der exakten Amplitude $a = \frac{\text{sum(table)}}{8}$ und des Winkels $\theta = \arcsin(\sqrt{a})$ (Zeilen 183–184).
  4. Konstruktion der quantenmechanischen Schätzaufgabe mittels `build_estimation_problem(table)` (Zeile 185).
  5. Erzeugung der Schaltungen für den Schedule $k \in \{0, 1, 2\}$ ohne Mess-Gates (Zeilen 177, 186).
  6. Auswertung der exakten Zustandsvektor-Wahrscheinlichkeit $P(1)$ auf dem Objective-Qubit mittels `Statevector.from_instruction(circuit).probabilities(objective)[1]` (Zeilen 189–191).
  7. Überprüfung der exakten mathematischen Gleichheit mit der Grover-Formel:
     $$\left| P_{\text{gemessen}}(1) - \sin^2((2k+1)\theta) \right| \le 2 \times 10^{-14}$$

Dieser Test garantiert mit einer Maschinengenauigkeit von $2 \cdot 10^{-14}$, dass die automatische Gatter-Synthese von $U_f$, $A$ und $Q$ im gesamten Zustandsraum exakt der theoretischen Quantenmechanik folgt.
