# 04-quantum-math.md — Quantenmechanische Mathematik und Amplitude Estimation

## 1. Einleitung

Dieses Dokument erklärt die mathematischen Grundlagen der **Quantum Amplitude Estimation (QAE)**, wie sie im Projekt `quantum-minecraft-rendering` zur Beschleunigung der Ambient-Visibility-Schätzung verwendet wird. Der Fokus liegt auf der algebraischen und geometrischen Herleitung der Zustandspräparation $A$, der Winkelparametrisierung, des Grover-Operators $Q$ und der Schätzdynamik unter Maximum-Likelihood Amplitude Estimation (MLAE).

---

## 2. Zustandspräparation (Operator $A$)

### 1. Intuition
In der klassischen Informatik testen wir Richtungen nacheinander. In der Quanteninformatik erstellen wir ein Quantenregister, das **alle $N$ Richtungen gleichzeitig** in einer gleichmäßigen Überlagerung (Superposition) enthält. Ein spezielles Hilfsqubit (das **Objective-Qubit**) markiert dann in jedem Überlagerungszustand automatisch, ob diese Richtung frei ($|1\rangle$) oder verdeckt ($|0\rangle$) ist.

### 2. Mathematische Form
Sei $N = 2^n$ die Anzahl der diskreten Richtungen (z.B. $N=64 \implies n=6$ Index-Qubits). Das Gesamtsystem besteht aus $(n + 1)$ Qubits:
- Indexregister: $n$ Qubits zur Kodierung der Richtung $i \in \{0, \dots, N-1\}$.
- Objective-Qubit: 1 Qubit an Index position $n$ zur Kodierung des Sichtbarkeitswerts $f(i) \in \{0, 1\}$.

Der Zustandspräparationsoperator $A$ ist definiert als:
$$A = U_f \cdot (H^{\otimes n} \otimes I)$$

1. **Anwendung der Hadamard-Transformation $H^{\otimes n}$ auf den Nullzustand $|0\rangle^{\otimes n}$**:
   $$(H^{\otimes n} \otimes I) |0\rangle^{\otimes n} |0\rangle = \frac{1}{\sqrt{N}} \sum_{i=0}^{N-1} |i\rangle |0\rangle$$

2. **Anwendung des reversiblen Sichtbarkeits-Orakels $U_f$**:
   Das Orakel $U_f$ bildet den Zustand $|i\rangle |y\rangle$ ab auf $|i\rangle |y \oplus f(i)\rangle$. Mit initialisiertem Objective-Qubit $|0\rangle$ ergibt sich:
   $$A |0\rangle^{\otimes (n+1)} = \frac{1}{\sqrt{N}} \sum_{i=0}^{N-1} |i\rangle |f(i)\rangle$$

3. **Zerlegung in „Good“ und „Bad“ Unterräume**:
   Wir teilen die Indizes $i$ in zwei disjunkte Mengen auf:
   - Freie Richtungen („Good States“): $G = \{i \mid f(i) = 1\}$, Anzahl $|G| = N \cdot a$.
   - Verdeckte Richtungen („Bad States“): $B = \{i \mid f(i) = 0\}$, Anzahl $|B| = N \cdot (1-a)$.

Wir definieren die normierten Zustände im Indexregister:
$$|\psi_1\rangle = \frac{1}{\sqrt{N a}} \sum_{i \in G} |i\rangle, \quad |\psi_0\rangle = \frac{1}{\sqrt{N (1-a)}} \sum_{i \in B} |i\rangle$$

Damit lässt sich der präparierte Gesamtzustand $A|0\rangle$ exakt als zweidimensionale Überlagerung schreiben:
$$A |0\rangle = \sqrt{1-a} \, |\psi_0\rangle |0\rangle + \sqrt{a} \, |\psi_1\rangle |1\rangle$$

- **Messwahrscheinlichkeit**:
  Wird das Objective-Qubit (letztes Qubit) im Zustand $A|0\rangle$ gemessen, ist die Wahrscheinlichkeit, das Ergebnis $|1\rangle$ zu erhalten:
  $$P(\text{Objective} = 1) = |\sqrt{a}|^2 = a$$

- **Warum einfaches Messen von $A|0\rangle$ nur Bernoulli-Sampling ist**:
  Wenn wir lediglich den Zustand $A|0\rangle$ präparieren und das Objective-Qubit messen, erhalten wir eine 1 mit Wahrscheinlichkeit $a$ und eine 0 mit Wahrscheinlichkeit $1-a$. Dies entspricht **exakt** dem klassischen Bernoulli-Münzwurf (Monte Carlo). Der Quantenvorteil entsteht erst durch die Anwendung von Wiederholungen des Grover-Operators $Q$.

### 3. Kleines Beispiel
Sei $N=4$ ($n=2$ Qubits) und $f = [1, 0, 0, 0] \implies a = 1/4 = 0,25$.
$$A|00\rangle|0\rangle = \frac{1}{2} |00\rangle|1\rangle + \frac{1}{2} |01\rangle|0\rangle + \frac{1}{2} |10\rangle|0\rangle + \frac{1}{2} |11\rangle|0\rangle$$
$$\text{Good State: } |\psi_1\rangle = |00\rangle, \quad \text{Bad State: } |\psi_0\rangle = \frac{1}{\sqrt{3}}(|01\rangle + |10\rangle + |11\rangle)$$
$$A|0\rangle = \sqrt{\frac{3}{4}} \, |\psi_0\rangle|0\rangle + \sqrt{\frac{1}{4}} \, |\psi_1\rangle|1\rangle$$
Die Wahrscheinlichkeit $P(1)$ beträgt $(\sqrt{1/4})^2 = 1/4 = 0,25$.

### 4. Umsetzung im Code
Die Zustandspräparation wird in `quantum-service/src/qmr/backends/cpu_quantum.py` synthetisiert:
- `build_visibility_lookup_oracle(table)` (Zeilen 141–161): Baut $U_f$ mittels Multi-Controlled Pauli-X (`mcx`) Gates.
- `build_state_preparation(lookup_oracle)` (Zeilen 164–171): Wendet $H^{\otimes n}$ auf das Indexregister an und schaltet $U_f$ nach.

---

## 3. Winkelparametrisierung

### 1. Intuition
In der Quantenmechanik sind Zustandstransformationen durch unitäre Operatoren reine **Rotationen** in einem Vektorraum. Wenn wir die Amplitude $a$ als Quadrat einer Sinusfunktion $\sin^2(\theta)$ ausdrücken, verwandeln sich komplizierte algebraische Verstärkungen in einfache Winkeladditionen.

### 2. Mathematische Form
Wir definieren den Rotationswinkel $\theta \in [0, \pi/2]$ durch:
$$a = \sin^2(\theta) \iff \theta = \arcsin(\sqrt{a})$$
Entsprechend gilt:
$$\sqrt{1-a} = \sqrt{1 - \sin^2\theta} = \cos(\theta)$$

Der Präparationszustand $A|0\rangle$ lautet in der zweidimensionalen orthogonalen Basis $\{|\text{Bad}\rangle, |\text{Good}\rangle\} = \{|\psi_0\rangle|0\rangle, |\psi_1\rangle|1\rangle\}$:
$$A|0\rangle = \cos(\theta) \, |\psi_0\rangle|0\rangle + \sin(\theta) \, |\psi_1\rangle|1\rangle$$

Geometrisch bildet der Zustandsvektor $A|0\rangle$ den Winkel $\theta$ mit der horizontalen „Bad State“-Achse.

---

## 4. Der Grover-Operator ($Q$)

### 1. Intuition
Der Grover-Operator $Q$ wirkt wie eine „Verstärker-Linse“. Bei jeder Anwendung von $Q$ wird der Zustandsvektor um einen festen Winkel $2\theta$ in Richtung des Zielzustands („Good State“) gedreht. Dadurch steigt die Wahrscheinlichkeit, bei einer Messung $|1\rangle$ zu erhalten, drastisch an.

### 2. Mathematische Form
Der Grover-Operator $Q$ ist definiert als:
$$Q = -A \cdot S_0 \cdot A^{-1} \cdot S_{\text{good}}$$

Wobei:
- $S_{\text{good}} = I - 2 (I \otimes |1\rangle\langle 1|)$: Invertiert das Vorzeichen (Phasenflip) des Zielzustands $|1\rangle$ auf dem Objective-Qubit.
- $S_0 = I - 2 |0\rangle^{\otimes (n+1)}\langle 0|^{\otimes (n+1)}$: Invertiert das Vorzeichen des Nullzustands (Reflexion um den Ursprung).
- $A^{-1}$: Inverse Zustandspräparation (macht $A$ rückgängig).
- Das führende Minuszeichen $-A$ sorgt zusammen mit $S_0$ für die korrekte Rotationsausrichtung.

#### Wirkung auf den Rotationswinkel
Im zweidimensionalen Unterraum wirkt $Q$ als ebene Drehung um den Winkel $2\theta$:
$$Q \begin{pmatrix} \cos(\alpha) \\ \sin(\alpha) \end{pmatrix} = \begin{pmatrix} \cos(\alpha + 2\theta) \\ \sin(\alpha + 2\theta) \end{pmatrix}$$

Da der Initialzustand $A|0\rangle$ bereits den Winkel $\theta$ hat, befindet sich der Zustand nach $k$ Grover-Iterationen $Q^k A |0\rangle$ im Winkel:
$$\alpha_k = \theta + k \cdot 2\theta = (2k + 1)\theta$$

Der Quantenzustand lautet somit:
$$Q^k A |0\rangle = \cos((2k+1)\theta) \, |\psi_0\rangle|0\rangle + \sin((2k+1)\theta) \, |\psi_1\rangle|1\rangle$$

#### Erfolgswahrscheinlichkeit $p_k(a)$
Die Wahrscheinlichkeit, nach $k$ Grover-Iterationen auf dem Objective-Qubit eine 1 zu messen, lautet:
$$p_k(a) = \sin^2((2k+1)\theta) = \sin^2\left( (2k+1) \arcsin(\sqrt{a}) \right)$$

### 3. Kleines Numerisches Beispiel ($a = 1/4$)
Sei $a = \frac{1}{4} = 0,25$.
$$\theta = \arcsin\left(\sqrt{\frac{1}{4}}\right) = \arcsin\left(\frac{1}{2}\right) = \frac{\pi}{6} \quad (30^\circ)$$

Wir berechnen die Trefferwahrscheinlichkeiten für $k=0, 1, 2$:

1. **$k = 0$ (Nur $A|0\rangle$, 0 Grover-Iterationen)**:
   $$p_0(1/4) = \sin^2(1 \cdot \pi/6) = \sin^2(30^\circ) = \left(\frac{1}{2}\right)^2 = \frac{1}{4} = 0,25$$
2. **$k = 1$ (1 Grover-Iteration $Q^1 A|0\rangle$)**:
   $$p_1(1/4) = \sin^2(3 \cdot \pi/6) = \sin^2(\pi/2) = \sin^2(90^\circ) = 1^2 = 1,0$$
   **Die Trefferwahrscheinlichkeit beträgt exakt 100%!** Die Amplitude wurde perfekt verstärkt.
3. **$k = 2$ (2 Grover-Iterationen $Q^2 A|0\rangle$)**:
   $$p_2(1/4) = \sin^2(5 \cdot \pi/6) = \sin^2(150^\circ) = \left(\frac{1}{2}\right)^2 = \frac{1}{4} = 0,25$$
   **Überrotation**: Der Vektor hat sich an der Zielachse vorbeigedreht ($150^\circ$), die Messwahrscheinlichkeit sinkt wieder auf $25\%$.

### 4. Sensitivität, Periodizität und Aliasing

- **Sensitivitätsgewinn für große $k$**:
  Die Ableitung der Erfolgswahrscheinlichkeit nach $a$ lautet:
  $$\frac{d p_k(a)}{d a} = (2k+1) \frac{\sin(2(2k+1)\theta)}{2\sqrt{a(1-a)}}$$
  Der Faktor $(2k+1)$ bedeutet, dass für große $k$ winzige Änderungen in $a$ zu riesigen Änderungen in der Messwahrscheinlichkeit $p_k(a)$ führen. Dies ermöglicht die $\mathcal{O}(M^{-1})$-Skalierung.

- **Periodizität und Aliasing (Mehrdeutigkeit)**:
  Da die $\sin^2$-Funktion periodisch ist, erzeugen für ein festes $k \ge 1$ mehrere verschiedene Amplituden $a$ **exakt dieselbe** Trefferwahrscheinlichkeit $p_k(a)$.
  *Beispiel bei $k=1$*: Sowohl $a=1/4$ ($\theta=\pi/6 \implies 3\theta=\pi/2 \implies p_1=1$) als auch $a=3/4$ ($\theta=\pi/3 \implies 3\theta=\pi \implies p_1=0$, ungeeignet) bzw. andere Winkel erzeugen Mehrdeutigkeiten.
  Ohne Auswertung mehrerer verschiedener $k$-Werte (oder kleinerer $k$-Startwerte) ist ein eindeutiger Rückschluss auf $a$ unmöglich.

- **Warum ein festes $k_{\max}$ keine unbegrenzte $\mathcal{O}(M^{-1})$-Skalierung garantiert**:
  Wird die Grover-Power bei einem festen $k_{\max}$ gedeckelt (z.B. $k \in \{0, 1, 2, 4, 8\}$ wie im Projekt-Budgetplan `plan_budget`), kann die Schaltungstiefe für höhere Budgets $M$ nicht weiter wachsen. Höhere $M$ werden dann nur noch durch mehr Mess-Shots $s$ erreicht. Dadurch geht die Konvergenzrate für große $M$ wieder in das klassische $\mathcal{O}(M^{-1/2})$-Regime über.

### 5. Umsetzung im Code
In `quantum-service/src/qmr/backends/cpu_quantum.py`:
- `build_good_state_reflection` (Zeilen 174–179): Erzeugt $S_{\text{good}}$ durch Pauli-Z Gate auf dem Objective-Qubit.
- `build_visibility_operators` (Zeilen 182–200): Konstruiert den Grover-Operator $Q$ mittels Qiskit `grover_operator`.

---

## 5. Vergleich verschiedener Quanten-Amplitude-Estimation-Verfahren

In der Literatur existieren verschiedene Varianten der Amplitude Estimation. Dieses Projekt verwendet **Maximum-Likelihood Amplitude Estimation (MLAE)**.

| Verfahren | Beschreibung | Benötigte Qubits | Adaptivität | QFT erforderlich? | Besonderheiten im Vergleich zu diesem Projekt |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **QPE-basierte QAE** (Brassard et al. 2002) | Verwendet Quantum Phase Estimation mit einem Anzille-Register und inverser QFT. | $n + 1 + m$ (viele Zusatzqubits) | Nein (statisch) | **Ja** | Benötigt sehr tiefe Schaltungen und Quanten-Fourier-Transformation; auf Near-Term hardware unpraktisch. |
| **Iterative QAE (IQAE)** (Grinko et al. 2021) | Wählt $k$-Werte dynamisch während der Messung basierend auf Konfidenzintervallen. | $n + 1$ (keine Zusatzqubits) | **Ja** (interaktiv) | Nein | Optimal für Noisy-Intermediate-Scale-Quantum (NISQ); im Projekt nicht verwendet. |
| **MLAE** (Suzuki et al. 2020) | Führt Schaltungen mit einem festen Schedule von $k$-Potenzen aus und wertet Ergebnisse über Maximum-Likelihood-Schätzung aus. | $n + 1$ (keine Zusatzqubits) | Nein (nicht-adaptiv) | Nein | **Im Projekt implementiert!** Extrem geringer Qubit-Overhead, sehr gut für Simulator-Evaluation. |
| **Bernoulli-Sampling** | Schaltung $k=0$ wird $M$-mal gemessen. | $n + 1$ | Nein | Nein | Entspricht mathematisch exakt dem klassischen Monte Carlo ($p_0(a) = a$). |
| **Exaktes Statevector-Auslesen** | Vektoramplituden werden direkt aus dem Simulatorspeicher gelesen (ohne Shots). | $n + 1$ | Nein | Nein | Rein klassisches Hilfsmittel zur Verifizierung in Unit-Tests (`test_backends.py`). |

### 6. Häufiges Missverständnis
*Missverständnis*: „Weil QAE einen theoretischen Speed-up von $\mathcal{O}(M^{-1})$ besitzt, läuft die Quantensimulation im Projekt schneller ab als das Python Monte-Carlo-Skript.“  
*Korrektur*: Die $\mathcal{O}(M^{-1})$-Skalierung spart **logische Oracelabfragen $M$**. Auf klassischer Hardware erfordert die Simulation des Quantenzustands $Q^k A |0\rangle$ jedoch Matrix-Vektor-Multiplikationen der Größe $2^{n+1} \times 2^{n+1}$. Die klassische Simulationszeit pro Schaltung dominiert daher die Gesamtlaufzeit bei weitem.
