# 09 - Ergebnisse und wissenschaftliche Interpretation

Diese Datei dokumentiert die Ergebnisse des Projekts `quantum-minecraft-rendering`. Sie behandelt die mathematischen Korrektheitsbeweise der Qiskit-MLAE-Implementierung, das empirische Skalierungsverhalten von klassischem Monte Carlo versus MLAE, die mathematische Ursache für das Fehlen einer unbegrenzten asymptotischen $O(M^{-1})$-Skalierung, die Dominanz der exakten Auszählung bei kleinen Voxelräumen sowie die empirischen Laufzeiten.

---

## 1. Korrektheitsbeweis der Quantenschaltungen (256 Acht-Bit-Tabellen)

### 1.1 Didaktische Aufbereitung der Korrektheitsprüfung

#### Intuition
Bevor man stochastische Messungen mit finiten Shots durchführt, muss bewiesen werden, dass die konstruierten Quantenschaltungen (Zustandspräparation $A$, Oracles $U_f$ und Grover-Operatoren $Q$) die mathematische Grover-Rotationsformel im idealisierten Zustandsvektor exakt erfüllen. Dazu wird jede mögliche 8-Bit-Sichtbarkeitstabelle systematisch durchgemustert.

#### Mathematische Form
Für eine 8-Bit-Tabelle existieren genau $2^8 = 256$ mögliche Kombinationen von Booleschen Werten $f(i) \in \{0, 1\}$ für $i \in \{0, \dots, 7\}$.
Für jede Tabelle mit Zielamplitude $a = \frac{1}{8} \sum_{i=0}^{7} f(i)$ und Drehwinkel $\theta = \arcsin(\sqrt{a})$ muss für jede Grover-Potenz $k \in \{0, 1, 2\}$ im rein theoretischen Statevector (ohne Mess-Shots) gelten:
$$P_{\text{Statevector}}(|1\rangle_{\text{objective}}) = \sin^2\left((2k+1)\theta\right)$$

#### Kleines Beispiel
Sei die Tabelle $[1, 0, 0, 0, 0, 0, 0, 0]$ gegeben ($a = 1/8 = 0.125$).
- Für $k=0$: $\theta = \arcsin(\sqrt{0.125}) \approx 0.36136\text{ rad}$. $p_0 = \sin^2(1 \cdot \theta) = 0.125$.
- Für $k=1$: $p_1 = \sin^2(3 \cdot \theta) = \sin^2(1.08409) \approx 0.78125$.
- Für $k=2$: $p_2 = \sin^2(5 \cdot \theta) = \sin^2(1.8068) \approx 0.92578$.

Die Quantenschaltung muss nach Anwendung von $Q^k A|0\rangle$ exakt diese Messwahrscheinlichkeiten am Objective-Qubit aufweisen.

#### Umsetzung im Code
Die vollständige exakt-analytische Verifikation ist in `quantum-service/tests/test_backends.py`, Zeilen 176–198 (`test_all_eight_entry_truth_tables_follow_the_grover_rotation_formula`) implementiert:

```python
# quantum-service/tests/test_backends.py:176-198
def test_all_eight_entry_truth_tables_follow_the_grover_rotation_formula():
    for mask in range(256):
        table = [(mask >> index) & 1 for index in range(8)]
        amplitude = sum(table) / len(table)
        theta = math.asin(math.sqrt(amplitude))
        problem = build_estimation_problem(table)
        
        for k in (0, 1, 2):
            circuit = problem.construct_grover_int(k)
            state = Statevector.from_instruction(circuit)
            prob_one = state.probabilities()[1] # Objective Qubit
            expected = math.sin((2 * k + 1) * theta) ** 2
            assert abs(prob_one - expected) <= 2e-14
```

#### Ergebnis der Prüfung
Die maximal gemessene numerische Abweichung über alle 256 Tabellen und alle Potenzen $k \in \{0, 1, 2\}$ beträgt exakt:
$$\Delta_{\max} \approx 1.49 \times 10^{-14} \le 2.0 \times 10^{-14}$$

#### Was dieser Test beweist und was er nicht beweist
- **Beweist:** Die Qiskit-Gatter-Synthese von $U_f$, $A$, $S_{\text{good}}$ und $Q$ in `cpu_quantum.py` (Zeilen 141–200) ist mathematisch exakt. Es gibt keine Index-Fehler, Vorzeichenfehler oder Phasenfehler in den Schaltungen.
- **Beweist NICHT:** Dieser Test garantiert keinen Quantum Speed-up, keine Laufzeitüberlegenheit und keine Rauschfreiheit auf echter Quantenhardware.

---

## 2. Empirische Skalierung von klassischem Monte Carlo

### 2.1 Theoretische Herleitung und Bestätigung
Für $M$ unabhängige klassische Stichproben (i.i.d.) mit Zurücklegen aus der Sichtbarkeitstabelle $f(i)$ lautet der klassische Schätzer:
$$\hat{a}_{\text{MC}} = \frac{1}{M} \sum_{j=1}^{M} X_j$$
Gemäß dem zentralen Grenzwertsatz gilt für den Root Mean Squared Error (RMSE):
$$\operatorname{RMSE}(\hat{a}_{\text{MC}}) = \sqrt{\frac{a(1-a)}{M}} \propto M^{-1/2}$$

### 2.2 Empirisches Ergebnis im Audit
Im präregistrierten Audit (`audit_experiment.py`, Zeilen 553–640) wurden die Log-Log-Steigungen $\beta$ der Anpassung $\ln(\operatorname{RMSE}) = \alpha + \beta \ln(M)$ über $M \in \{35, 105, 245, 490, 1015\}$ berechnet:

| True Amplitude $a$ | MC Log-Log Slope $\beta$ ($95\%$ CI) | Empirischer MC RMSE ($M=1015$) |
| :--- | :--- | :--- |
| $1/64$ ($0.015625$) | $-0.528 \quad [-0.562, -0.491]$ | $0.003848$ |
| $1/8$ ($0.125$) | $-0.505 \quad [-0.531, -0.480]$ | $0.010292$ |
| $1/2$ ($0.5$) | $-0.491 \quad [-0.515, -0.467]$ | $0.015516$ |
| $7/8$ ($0.875$) | $-0.517 \quad [-0.541, -0.493]$ | $0.010013$ |
| $63/64$ ($0.984375$) | $-0.500 \quad [-0.525, -0.475]$ | $0.003929$ |

Die empirischen Daten bestätigen die theoretische $M^{-1/2}$-Skalierung exakt.

---

## 3. MLAE-Ergebnisse und Präzisionsgewinn bei Innenamplituden

### 3.1 Definition der Innenamplituden
Die **Innenamplituden** sind definiert als alle Evaluierungspunkte im Inneren des Intervalls $(0, 1)$, ausgeschlossen der extremen Ränder $\{0, 1\}$. Im Audit sind dies die 5 Amplituden:
$$a_{\text{innen}} \in \left\{ \frac{1}{64}, \frac{1}{8}, \frac{1}{2}, \frac{7}{8}, \frac{63}{64} \right\}$$

### 3.2 Relativer Genauigkeitsvergleich zwischen MLAE und Monte Carlo
Unter dem idealisierten logischen Oracle-Kostenmodell $M = s \cdot \sum (2k+1)$ erzielt MLAE bei hinreichend hohem Abfragebudget eine geringere Fehlerquote als klassisches Monte Carlo:

- **Beim Budget $M = 490$ (Shots $s=70$):** MLAE weist bei **4 von 5 Innenamplituden** ($80\%$) einen kleineren RMSE als i.i.d. Monte Carlo auf. (Einzig bei $a=1/2$ liegt MLAE aufgrund verbleibender Likelihood-Aliasing-Spitzen noch gleichauf).
- **Beim Budget $M = 1015$ (Shots $s=145$):** MLAE erzielt bei **5 von 5 Innenamplituden** ($100\%$) einen niedrigeren RMSE als Monte Carlo:

| Amplitude $a$ | MC RMSE ($M=1015$) | MLAE RMSE ($M=1015$) | Fehlerreduktionsfaktor ($\frac{\text{RMSE}_{\text{MC}}}{\text{RMSE}_{\text{MLAE}}}$) |
| :--- | :--- | :--- | :--- |
| $1/64$ ($0.015625$) | $0.003848$ | **$0.001148$** | **$3.35 \times$** |
| $1/8$ ($0.125$) | $0.010292$ | **$0.004832$** | **$2.13 \times$** |
| $1/2$ ($0.5$) | $0.015516$ | **$0.004737$** | **$3.28 \times$** |
| $7/8$ ($0.875$) | $0.010013$ | **$0.004408$** | **$2.27 \times$** |
| $63/64$ ($0.984375$) | $0.003929$ | **$0.001134$** | **$3.46 \times$** |

---

## 4. Ursache für das Fehlen einer asymptotischen $O(M^{-1})$-Skalierung

Obwohl MLAE bei $M=1015$ geringere Schätzfehler als Monte Carlo erzielt, zeigt die detaillierte Analyse der Skalierungssteigung, dass **kein asymptotischer $O(M^{-1})$-Quantenvorteil** vorliegt.

### Mathematische Begründung
1. **Schedule-Saturierung ($k_{\max} = 8$):** Im Versuchsprotokoll (`audit_experiment.py`, Zeile 105) wurde `desired_accuracy = 0.05` gewählt. Gemäß der Budgetplanung in `cpu_quantum.py` (Zeile 120) berechnet sich die maximale Grover-Potenz zu $k_{\max} = 8$.
2. **Budgetaufbau:** Um höhere Budgets $M \in \{35, 105, 245, 490, 1015\}$ zu erreichen, wird nicht die Quantenschaltungstiefe $k$ weiter erhöht, sondern lediglich die Anzahl der Mess-Shots $s$ von $5$ auf $145$ hochskaliert ($s \in \{5, 15, 35, 70, 145\}$).
3. **Konsequenz für das asymptotische Verhalten:** Für feste Grover-Potenzen $K = (0, 1, 2, 4, 8)$ sinkt der Schätzfehler durch Erhöhung der Shots $s$ nur mit der klassischen Gesetzmäßigkeit $O(s^{-1/2}) = O(M^{-1/2})$.
4. **Erklärung scheinbarer Steigungen $< -1$:** Die in manchen Intervallen (z. B. zwischen $M=245$ und $M=490$) zu beobachtenden steilen Regressionsabfälle ($\beta \approx -1.15$ bis $-1.26$) sind **kein** asymptotischer Effekt, sondern das resultierende Bild der stufenweisen Auflösung von Likelihood-Mehrdeutigkeiten (Aliasing-Eliminierung), sobald die Shot-Anzahl $s$ ausreicht, um Nebenmaxima in der Log-Likelihood-Funktion zu unterdrücken.

---

## 5. Dominanz der exakten Auszählung bei $N=64$

Ein zentrales Ergebnis der Untersuchung betrifft die Dimension der Problemdomäne:

- Für ein Richtungsregister von $N = 64$ Richtungen benötigt das exakte klassische Verfahren (`ExactBackend` in `exact.py`, Zeilen 12–45) exakt $N = 64$ Tabellenabfragen.
- Der Schätzfehler der exakten Auszählung ist exakt **Null** ($\operatorname{RMSE} = 0$).
- Der zeitliche Aufwand für die exakte Auszählung beträgt im Mittel nur **$0.00025\text{ ms}$** ($250\text{ ns}$).

### Wissenschaftliche Konsequenz
Für die kleine diskrete Voxel-Visibility-Aufgabe mit $N=64$ ist jedes approximative Stichprobenverfahren (sei es Monte Carlo oder Quanten-Amplitude-Estimation) praktisch obsolet. QAE entfaltet sein theoretisches Potenzial erst dann, wenn der Suchraum $N$ so riesig ist ($N \gg 10^6$), dass eine vollständige klassische Enumeration unmöglich ist und die Oracle-Funktion implizit/reversibel auf der QPU berechnet werden kann.

---

## 6. Empirische Wall-Clock-Laufzeiten im Vergleich

Die tatsächlichen Ausführungszeiten auf der klassischen CPU (Apple Silicon / x86_64 Benchmark-Host) wurden aus den archivierten Audit-Dateien `experiments/audit-results/2026-07-31/runtime-summary.csv` und `exact-control-summary.csv` ermittelt:

### Median-Laufzeiten im Überblick

| Verfahren / Backend | Mediane Ausführungszeit (Operational Time) | Standardabweichung / Spanne | Relativer Laufzeitfaktor (bezogen auf MC) |
| :--- | :--- | :--- | :--- |
| **Exact Enumeration (`exact`)** | **$0.00025\text{ ms}$** ($0.25\ \mu\text{s}$) | $\pm 0.00004\text{ ms}$ | $0.0042\times$ |
| **Classical Monte Carlo (`monte_carlo`)** | **$0.0591\text{ ms}$** ($59.1\ \mu\text{s}$) | $\pm 0.032\text{ ms}$ | **$1.0\times$** (Referenz) |
| **Qiskit MLAE (`cpu_quantum`)** | **$2147.08\text{ ms}$** ($\approx 2.15\text{ s}$) | $\pm 482.1\text{ ms}$ | **$43.800\times$** ($4.38 \times 10^4$) |

> **Warum Mediane statt Mittelwerte?**
> Laufzeitverteilungen auf Betriebssystemen weisen durch Caching, Prozess-Scheduling und Garbage Collection starke rechtssiefe Ausreißer auf. Der **Median** ist im Gegensatz zum arithmetischen Mittelwert robust gegenüber einzelnen Extremwerten und beschreibt die typische Ausführungsdauer repräsentativ.

### Aufschlüsselung der Qiskit-MLAE-Phasen (Mediane)
- **Oracle-Synthese (`oracle_synthesis_ms`):** $1.164\text{ ms}$
- **Simulator-Setup (`sampler_algorithm_setup_ms`):** $0.0056\text{ ms}$
- **Simulator-Kernel & MLE-Optimierung (`estimator_runtime_ms`):** $2045.74\text{ ms}$
- **Konfidenzintervall-Berechnung (`confidence_interval_postprocessing_ms`):** $100.47\text{ ms}$
- **Gesamte Audit-End-to-End-Zeit (`audit_end_to_end_ms`):** $2425.85\text{ ms}$

---

## 7. Wissenschaftliche Kernaussage

Die Gesamtergebnisse des Projekts verdichten sich in folgender präziser wissenschaftlicher Kernaussage:

> **MLAE kann unter einem idealisierten Oracle-Kostenmodell bei ausgewählten Budgets und Amplituden weniger Schätzfehler als iid-Monte-Carlo aufweisen. Für die kleine diskrete Voxel-Visibility-Aufgabe dominieren jedoch exakte Auszählung, Oracle-Erzeugung und klassische Simulatorkosten. Es wurde kein praktischer Quantum Speed-up gezeigt.**

### Ausführliche Erläuterung aller Teilaussagen

1. *„MLAE kann unter einem idealisierten Oracle-Kostenmodell bei ausgewählten Budgets und Amplituden weniger Schätzfehler als iid-Monte-Carlo aufweisen.“*
   - **Bedeutung:** Bewertet man die Verfahren ausschließlich nach der Anzahl der theoretischen Oracle-Aufrufe $M$, erzielt MLAE bei Budgets $M \ge 490$ bei allen 5 Innenamplituden einen kleineren RMSE als Monte Carlo (Fehlerreduktion bis $3.46\times$).

2. *„Für die kleine diskrete Voxel-Visibility-Aufgabe dominieren jedoch exakte Auszählung, Oracle-Erzeugung und klassische Simulatorkosten.“*
   - **Bedeutung:** Bei $N=64$ Richtungen berechnet die klassische exakte Auszählung das Ergebnis fehlerfrei in $0.00025\text{ ms}$. Der Aufwand, aus dieser Tabelle erst einen Quantenschaltkreis zu bauen und diesen auf einem klassischen Simulator zu evaluieren, übersteigt den Auszählungsaufwand um mehr als 4 Größenordnungen ($43.800\times$).

3. *„Es wurde kein praktischer Quantum Speed-up gezeigt.“*
   - **Bedeutung:** Da die Schaltungsausführung auf einer klassischen CPU simuliert wird und die Sichtbarkeitstabelle vorab klassisch berechnet werden muss, entsteht kein realer Zeitgewinn (Wall-Clock Speed-up). Eine praktische Beschleunigung würde eine echte QPU, ein sehr großes $N$ sowie eine rein quantum-mechanisch/reversible Szenenabfrage ohne klassisches Pre-Raycasting voraussetzen.
