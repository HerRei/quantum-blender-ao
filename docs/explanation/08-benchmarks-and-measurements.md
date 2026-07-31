# 08 - Benchmarks und Messmethodik

Diese Datei erklärt die vollständige Benchmark- und Messmethodik des Projektes `quantum-minecraft-rendering`. Sie stellt die mathematischen Definitionen aller Fehler- und Laufzeitmetriken bereit, erklärt die synthetischen Testszenerien, analysiert das Datenformat der Audit-Artefakte und dokumentiert die sechs zugelassenen Grafikfamilien sowie die Gründe für das Verwerfen früherer Vorab-Diagramme.

---

## 1. Benchmark-Eingaben und Versuchsdesign

Die Benchmark-Pipeline (implementiert in `quantum-service/src/qmr/audit_experiment.py`, Zeilen 98–265) evaluiert Schätzverfahren unter kontrollierten synthetischen Bedingungen. Um faire Vergleiche zwischen klassischem i.i.d. Monte Carlo (MC) und Quantum Amplitude Estimation (MLAE) zu ermöglichen, werden alle Eingabeparameter exakt parametrisiert.

### Parameterraum der Benchmarks
- **Richtungsanzahl ($N$):** $N \in \{8, 16, 32, 64\}$ diskrete Richtungen auf der Halbkugel. Im Haupt-Audit wird präregistriert $N=64$ als Standard verwendet (`directions.py`, Zeilen 17–48).
- **Zielamplituden ($a$):** Exakte Sichtbarkeitsverhältnisse $a = \frac{1}{N} \sum_{i=0}^{N-1} f(i) \in [0, 1]$. Im synthetischen Haupt-Audit werden präzise Präfix-Tabellen mit 7 festen Amplituden evaluiert:
  $$a \in \left\{ 0, \frac{1}{64}, \frac{1}{8}, \frac{1}{2}, \frac{7}{8}, \frac{63}{64}, 1 \right\}$$
  wobei $a=0$ und $a=1$ die Randamplituden bilden und die verbleibenden 5 Amplituden die sogenannten **Innenamplituden** darstellen (`audit_experiment.py`, Zeilen 242–265).
- **Zufallssamen (Seeds):** 256 unabhängige Seeds pro Amplituden- und Budget-Zelle für analytische Fehlerstatistiken, um statistisch valide Bootstrap-Konfidenzintervalle (95 %) zu berechnen.
- **Oracle-Query-Budgets ($M$):** Das realisierte logische Abfragebudget $M$, definiert als Anzahl der Aufrufe des reversiblen Sichtbarkeits-Oracles $U_f$ beziehungsweise $U_f^\dagger$:
  $$M = s \cdot \sum_{j=0}^{m-1} (2k_j + 1)$$
  Evaluierte Zielbudgets umfassen $M \in \{35, 105, 245, 490, 1015\}$.
- **Shots ($s$):** Anzahl der Messwiederholungen pro Quantenschaltung ($s \in \{5, 15, 35, 70, 145\}$).
- **Grover-Potenzen ($k$):** Vorgegebene Potenzen der Grover-Rotations-Operatoren $Q^k$. Im präregistrierten Schedule wird ein konstanter Exponential-Schedule $K = (0, 1, 2, 4, 8)$ verwendet ($k_{\max} = 8$).
- **Evaluierte Backends:** 
  1. `cpu_quantum` (`CpuQuantumBackend` in `cpu_quantum.py`, Zeilen 256–422): Qiskit `StatevectorSampler` basierte finite-shot MLAE-Simulation.
  2. `classical_monte_carlo` (`ClassicalMonteCarloBackend` in `monte_carlo.py`, Zeilen 38–87): Klassische Monte-Carlo-Stichprobenziehung mit Zurücklegen und Wilson-Score-Konfidenzintervall.
  3. `exact` (`ExactBackend` in `exact.py`, Zeilen 12–45): Exakte vollständige Auszählung aller $N$ Richtungen.

> **Status-Hinweis:**
> Diese Komponente wurde nur statisch geprüft beziehungsweise kompiliert und noch nicht im laufenden Zielsystem validiert. (Bezieht sich auf hardwarebeschleunigte QPU- oder GPU-Ausführungen wie `intel_gpu.py`).

---

## 2. Synthetische Szenen

Die synthetischen Testszenerien sind in `quantum-service/src/qmr/scenes.py` (Zeilen 22–180) als deterministische Voxel-Geometrien definiert. Sie ermöglichen reproduzierbare Tests ohne laufenden Minecraft-Client.

| Szenen-ID | Funktion & Dateipfad | Voxel-Dimensionen | Abfrageposition & Normale | Erwartete Visibility ($a$) | Geometrische Beschreibung & Testzweck |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `open_sky` | `scenes.py:78` (`open_sky`) | $9 \times 9 \times 9$ | Pos: $(4.5, 4.5, 4.5)$, Normal: $(0,1,0)$ | $1.0$ ($64/64$) | Vollständig leerer Voxelraum. Jeder Strahl erreicht den Himmel. Dient als oberer Randwert-Test ($a=1$). |
| `closed_chamber` | `scenes.py:82` (`closed_chamber`) | $9 \times 9 \times 9$ | Pos: $(4.5, 4.5, 4.5)$, Normal: $(0,1,0)$ | $0.0$ ($0/64$) | Der Abfragepunkt befindet sich in einem 6-seitig verschlossenen opaken Raum. Testet unteren Randwert ($a=0$). |
| `single_wall` | `scenes.py:93` (`single_wall`) | $9 \times 9 \times 9$ | Pos: $(4.5, 4.5, 4.5)$, Normal: $(0,1,0)$ | $\approx 0.75 - 0.875$ | Eine einzelne opake Wand befindet sich östlich des Abfragepunkts. Blendet ca. $12.5\%$ bis $25\%$ der Richtungen ab. |
| `two_wall_corner` | `scenes.py:102` (`two_wall_corner`) | $9 \times 9 \times 9$ | Pos: $(4.5, 4.5, 4.5)$, Normal: $(0,1,0)$ | $\approx 0.50 - 0.75$ | Zwei rechtwinklig aneinanderstoßende opake Wände (Eckszene). Verdeckt etwa ein Viertel bis die Hälfte der Halbkugel. |
| `tunnel` | `scenes.py:114` (`tunnel`) | $9 \times 9 \times 9$ | Pos: $(4.5, 4.5, 4.5)$, Normal: $(0,1,0)$ | $\approx 0.125 - 0.25$ | Ein $3 \times 3$ Luftkanal in einem ansonsten opaken Block. Nur Strahlen entlang der Kanalachse treten aus. |
| `narrow_opening` | `scenes.py:125` (`narrow_opening`) | $9 \times 9 \times 9$ | Pos: $(4.5, 4.5, 4.5)$, Normal: $(0,1,0)$ | $\frac{1}{64} = 0.015625$ | Verschlossene Kammer mit genau einem geöffneten Dach-Voxel. Testet extreme Schwachsignal-Detektion. |
| `random_occupancy` | `scenes.py:134` (`random_occupancy`) | $9 \times 9 \times 9$ | Pos: $(4.5, 4.5, 4.5)$, Normal: $(0,1,0)$ | Variable (Zufall $p=0.22$) | Voxel werden mit Wahrscheinlichkeit $p=0.22$ und Seed `20260731` besetzt. Testet stochastische Geometrien. |
| `minecraft_cave` | `scenes.py:151` (`minecraft_cave`) | $11 \times 11 \times 11$ | Pos: $(5.5, 5.5, 5.5)$, Normal: $(0,1,0)$ | Niedrig ($\approx 0.125$) | Nachbildung eines Minecraft-Höhlensystems mit vertikalem Lichtschacht zur Oberfläche. |

---

## 3. Gemessene Fehler- und Statistikmetriken

Zur wissenschaftlichen Bewertung der Schätzgüte von $\hat{a}$ gegenüber dem wahren Wert $a$ werden sechs mathematische Metriken präzise getrennt.

### 3.1 Absoluter Fehler ($e$)

#### Intuition
Der absolute Abstand zwischen dem geschätzten Sichtbarkeitswert und dem exakten Ground-Truth-Wert einer einzelnen Messung.

#### Mathematische Form
$$e = |\hat{a} - a|$$

#### Kleines Beispiel
Sei $a = 0.75$ und der Schätzer liefert $\hat{a} = 0.70$. Dann ist $e = |0.70 - 0.75| = 0.05$.

#### Umsetzung im Code
In `quantum-service/src/qmr/backends/base.py` (Zeilen 72–78):
```python
abs_err = abs(estimate - truth) if truth is not None else None
```

#### Häufiges Missverständnis
Absoluter Fehler ist keine statistische Verteilungseigenschaft, sondern das Ergebnis eines einzelnen Versuchs.

---

### 3.2 Relativer Fehler ($e_{\text{rel}}$)

#### Intuition
Der absolute Fehler ins Verhältnis gesetzt zum wahren Wert. Zeigt die prozentuale Abweichung.

#### Mathematische Form
$$e_{\text{rel}} = \begin{cases} \frac{|\hat{a} - a|}{a}, & \text{falls } a > 0 \\ \text{null}, & \text{falls } a = 0 \end{cases}$$

#### Kleines Beispiel
Für $a = 0.50$ und $\hat{a} = 0.55$ gilt $e_{\text{rel}} = \frac{|0.55 - 0.50|}{0.50} = \frac{0.05}{0.50} = 0.10$ ($10\%$).

#### Umsetzung im Code
In `quantum-service/src/qmr/backends/base.py` (Zeilen 72–78):
```python
rel_err = abs(estimate - truth) / truth if truth is not None and truth > 0 else None
```

#### Häufiges Missverständnis
Wenn $a = 0$, ist die Division durch Null mathematisch undefiniert. Frühere Codeversionen setzten $e_{\text{rel}} = 0$, was fälschlicherweise perfekte Präzision bei $a=0$ signalisierte. Im Scientific Audit (SA-13) wurde dies auf `null` korrigiert.

---

### 3.3 Bias (Systematischer Fehler)

#### Intuition
Der Bias gibt an, ob ein Schätzer im statistischen Mittel den wahren Wert systematisch überschätzt ($\text{Bias} > 0$) oder unterschätzt ($\text{Bias} < 0$). Unverzerrte Schätzer haben einen Bias von $0$.

#### Mathematische Form
$$\text{Bias}(\hat{a}) = \mathbb{E}[\hat{a}] - a \approx \frac{1}{R} \sum_{r=1}^{R} \hat{a}_r - a$$
wobei $R$ die Anzahl der Wiederholungen (Replikate, z. B. $R=256$) ist.

#### Kleines Beispiel
Sei $a = 0.25$. Über 4 Läufe erhalten wir $\hat{a} \in \{0.30, 0.28, 0.32, 0.30\}$. Der Mittelwert ist $\bar{\hat{a}} = 0.30$.
$$\text{Bias} = 0.30 - 0.25 = +0.05 \quad (\text{systematische Überschätzung})$$

#### Umsetzung im Code
In `audit_experiment.py` (Zeilen 570–590):
```python
mean_estimate = np.mean(estimates)
bias = mean_estimate - true_amplitude
```

#### Häufiges Missverständnis
Klassisches Monte Carlo ist streng unverzerrt ($\text{Bias} = 0$). Finite-shot MLAE kann bei kleinen Budgets ($M \le 245$) aufgrund von Likelihood-Aliasing und Randeffekten einen signifikanten Bias aufweisen.

---

### 3.4 Varianz ($\operatorname{Var}$) und Standardabweichung ($\sigma$)

#### Intuition
Die Varianz misst die Streuung der Schätzwerte um ihren eigenen Mittelwert $\mathbb{E}[\hat{a}]$ über viele unabhängige Durchläufe. Die Standardabweichung $\sigma$ ist die Quadratwurzel der Varianz und besitzt dieselbe Einheit wie der Schätzer.

#### Mathematische Form
$$\operatorname{Var}(\hat{a}) = \mathbb{E}\left[ (\hat{a} - \mathbb{E}[\hat{a}])^2 \right] \approx \frac{1}{R-1} \sum_{r=1}^{R} (\hat{a}_r - \bar{\hat{a}})^2$$
$$\sigma(\hat{a}) = \sqrt{\operatorname{Var}(\hat{a})}$$

#### Kleines Beispiel
Für $\hat{a} \in \{0.4, 0.6\}$ bei $\bar{\hat{a}} = 0.5$:
$$\operatorname{Var} = \frac{(0.4-0.5)^2 + (0.6-0.5)^2}{2-1} = \frac{0.01 + 0.01}{1} = 0.02 \implies \sigma = \sqrt{0.02} \approx 0.1414$$

#### Umsetzung im Code
In `audit_experiment.py` (Zeilen 575–595):
```python
sample_var = np.var(estimates, ddof=1)
std_dev = np.sqrt(sample_var)
```

#### Häufiges Missverständnis
Varianz misst nur die Streuung um den Mittelwert der Schätzungen, nicht den Abstand zum echten Ground-Truth-Wert $a$. Ein Schätzer kann geringe Varianz, aber einen hohen Bias aufweisen.

---

### 3.5 Root Mean Squared Error (RMSE) und mathematischer Beweis der Zerlegung

#### Intuition
Der RMSE ist das primäre Gütemaß in Benchmarks. Er kombiniert sowohl den systematischen Fehler (Bias) als auch die zufällige Streuung (Varianz) in einer einzigen Kennzahl.

#### Mathematische Form
$$\operatorname{RMSE}(\hat{a}) = \sqrt{\mathbb{E}\left[(\hat{a} - a)^2\right]} \approx \sqrt{\frac{1}{R} \sum_{r=1}^{R} (\hat{a}_r - a)^2}$$

#### Mathematischer Beweis der Bias-Varianz-Zerlegung
$$\begin{aligned}
\operatorname{RMSE}^2 &= \mathbb{E}\left[(\hat{a} - a)^2\right] \\
&= \mathbb{E}\left[\left( (\hat{a} - \mathbb{E}[\hat{a}]) + (\mathbb{E}[\hat{a}] - a) \right)^2\right] \\
&= \mathbb{E}\left[ (\hat{a} - \mathbb{E}[\hat{a}])^2 + 2(\hat{a} - \mathbb{E}[\hat{a}])(\mathbb{E}[\hat{a}] - a) + (\mathbb{E}[\hat{a}] - a)^2 \right] \\
&= \mathbb{E}\left[ (\hat{a} - \mathbb{E}[\hat{a}])^2 \right] + 2(\mathbb{E}[\hat{a}] - a)\underbrace{\mathbb{E}[\hat{a} - \mathbb{E}[\hat{a}]]}_{= 0} + (\mathbb{E}[\hat{a}] - a)^2 \\
&= \operatorname{Var}(\hat{a}) + \operatorname{Bias}(\hat{a})^2
\end{aligned}$$
Somit gilt exakt:
$$\operatorname{RMSE}^2 = \operatorname{Bias}^2 + \operatorname{Var}$$

#### Umsetzung im Code
In `audit_experiment.py` (Zeilen 580–600):
```python
mse = np.mean((estimates - true_amplitude) ** 2)
rmse = np.sqrt(mse)
```

#### Häufiges Missverständnis
Man darf RMSE und Standardabweichung nur dann gleichsetzen, wenn der Schätzer bewiesen unverzerrt ist ($\text{Bias} = 0$). Bei verzerrten Quantenschätzern ist $\text{RMSE} > \sigma$.

---

## 4. Aufschlüsselung der Laufzeiten (Timing Breakdown)

Um Messverfälschungen zu vermeiden, unterscheidet das Projekt streng zwischen verschiedenen Zeitabschnitten (`audit_experiment.py`, Zeilen 411–550; `models.py`, Zeilen 152–175).

```text
Audit End-to-End-Laufzeit (audit_end_to_end_ms)
  ├── Operationale Methodenlaufzeit (operational_method_runtime_ms)
  │     ├── Oracle-Synthese (oracle_synthesis_ms): Erzeugung der U_f Logik
  │     ├── Sampler/Setup (sampler_algorithm_setup_ms): Initialisierung von Qiskit / Sampler
  │     ├── Schätzer-Kernel (estimator_runtime_ms): Simulator-Ausführung & MLE-Optimierung
  │     └── CI-Postprocessing (confidence_interval_postprocessing_ms): Likelihood-Ratio Hull
  └── Analyse-Transpilation (analysis_copy_transpilation_ms): Nachträgliche u/cx Transpilation (Nur Audit!)
```

### Getrennte Phasen
1. **Circuit Construction / Oracle Synthesis (`oracle_synthesis_ms`):** Zeit zur Synthese des reversiblen $U_f$-Schaltkreises aus der 3D-DDA-Visibility-Tabelle (`cpu_quantum.py`, Zeilen 141–161).
2. **Simulator Initialization (`sampler_algorithm_setup_ms`):** Instanziierung des Qiskit `StatevectorSampler`.
3. **Simulation / Estimator Execution (`estimator_runtime_ms`):** Zustandsvektor-Evolution und Ausführung der Mess-Shots im Simulator sowie Lösung des Maximum-Likelihood-Optimierungsproblems.
4. **Klassische DDA-Zeit (`dda_raycast_ms`):** Zeit für das klassische 3D-DDA-Raycasting zur Erzeugung der Sichtbarkeits-Tabelle (`raycast.py`, Zeilen 12–58).
5. **HTTP-Übertragungszeit (`transfer_ms`):** Netzwerklatenz zwischen Fabric-Mod und Python-Service (`JdkHttpTransport.java`, Zeilen 10–41).
6. **End-to-End-Zeit (`end_to_end_ms`):** Gesamtdauer vom Empfang des Requests bis zur Rückgabe des `LightingResult`.

> **Wissenschaftliche Relevanz:** In früheren Messungen wurde das klassische Raycasting versehentlich innerhalb des getimten Quantenschätzers ausgeführt (Scientific Audit SA-04). Im finalen Audit wurde das DDA-Raycasting strikt aus der Zeitmessung des Quantenschätzers isoliert.

---

## 5. Rohdaten, Formate und Manifest

Die Ergebnisse des präregistrierten wissenschaftlichen Audits sind im Archivpfad `experiments/audit-results/2026-07-31/` abgelegt.

### Struktur der Audit-Artefakte
- **`manifest.json`:** Enthält SHA-256-Prüfsummen aller Konfigurations- und Datendateien, Software-Versionen (Qiskit, Python, NumPy), System-Hardware-Informationen sowie Start- und Endzeitstempel des Audits.
- **`scientific-audit.toml`:** Präregistrierte Konfigurationsdatei mit allen Versuchsparametern.
- **`analytical-raw.csv` & `analytical-raw.jsonl`:** Enthält alle 256 Einzel-Replikate pro Versuchszelle mit exaktem Seed, geschätztem Wert $\hat{a}$, Likelihood-Ratio-Intervall $[a_{\text{low}}, a_{\text{high}}]$ und realisierten Abfragekosten.
- **`analytical-summary.csv`:** Aggregierte Kennzahlen (Bias, Varianz, Standardabweichung, RMSE, Bootstrap 95 % CIs) pro Versuchszelle.
- **`runtime-raw.csv` & `runtime-summary.csv`:** Detaillierte Laufzeitmessungen aller Teilphasen für Qiskit MLAE und klassisches Monte Carlo.
- **`exact-control-raw.csv` & `exact-control-summary.csv`:** Kontrollmessungen des exakten Auszählverfahrens (`ExactBackend`).

> **Paper-Readiness:** Nur das vollständige, per SHA-256 kryptografisch gebundene Audit-Bundle `experiments/audit-results/2026-07-31/` erfüllt die Anforderungen für wissenschaftliche Veröffentlichungen.

---

## 6. Die sechs Audit-Plotfamilien

Das Scientific Audit definiert exakt sechs zugelassene Grafikfamilien (`audit_experiment.py`, Zeilen 650–820), die im Verzeichnis `experiments/audit-results/2026-07-31/plots/` in den Formaten `.png` und `.pdf` generiert werden.

```text
experiments/audit-results/2026-07-31/plots/
├── rmse-vs-logical-oracle-calls.{png,pdf}
├── bias-vs-logical-oracle-calls.{png,pdf}
├── std-vs-logical-oracle-calls.{png,pdf}
├── runtime-vs-logical-oracle-calls.{png,pdf}
├── circuit-depth-vs-logical-oracle-calls.{png,pdf}
└── gate-count-vs-logical-oracle-calls.{png,pdf}
```

### Details der Grafikfamilien

| Grafikdatei | x-Achse | y-Achse | Aggregation & Kurven | Zulässige wissenschaftliche Aussage | Unzulässige Interpretation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `rmse-vs-logical-oracle-calls` | Logische Oracle-Aufrufe $M$ (log-skaliert) | RMSE ($\operatorname{RMSE}$, log-skaliert) | Pro Amplitude $a$; getrennte Kurven für MC und MLAE mit $95\%$-Bootstrap-Bändern. | Zeigt das $M^{-1/2}$-Skalierungsverhalten von MC sowie die stufenweise Alias-Auflösung von MLAE. | Es darf **kein** asymptotischer $O(M^{-1})$-Vorteil für MLAE behauptet werden, da der Schedule bei $k_{\max}=8$ saturiert. |
| `bias-vs-logical-oracle-calls` | Logische Oracle-Aufrufe $M$ | Absoluter Bias $|\operatorname{Bias}|$ | Getrennte Plots pro Amplitude $a$. | Dokumentiert, dass MC streng unverzerrt ist, während MLAE bei kleinen Budgets ($M \le 245$) verzerrt ist. | Bias darf nicht mit Varianz gleichgesetzt werden. |
| `std-vs-logical-oracle-calls` | Logische Oracle-Aufrufe $M$ (log-skaliert) | Standardabweichung $\sigma$ (log-skaliert) | Getrennte Kurven pro Schätzer und Amplitude. | Zeigt die reinen Streuungseigenschaften der Schätzer ohne Biaseinfluss. | Keinesfalls als RMSE interpretieren. |
| `runtime-vs-logical-oracle-calls` | Logische Oracle-Aufrufe $M$ | Operational Time in ms (log-skaliert) | Per-Method Mediane und Perzentilbänder. | Beweist den realen Laufzeitunterschied ($\approx 4.38 \times 10^4 \times$) zwischen klassischem MC und CPU-Quantensimulation. | Darf nicht als Performanzbeweis für echte Quantenhardware missverstanden werden. |
| `circuit-depth-vs-logical-oracle-calls` | Logische Oracle-Aufrufe $M$ | Maximale Quantenschaltungstiefe | Transpiliert auf $u/cx$-Basis. | Beweist, dass die Schaltungstiefe ab $M \ge 35$ wegen $k_{\max}=8$ konstant bleibt. | Nicht auf physikalische Fehlergrenzen echter QPUs verallgemeinern. |
| `gate-count-vs-logical-oracle-calls` | Logische Oracle-Aufrufe $M$ | Single-Circuit & Shot-Weighted Gate-Count | Summiert über alle Transpilate. | Quantifiziert den exakten Gatteraufwand der synthetisierten Schaltungen. | Gatteranzahl ist nicht gleich Anzahl logischer Oracle-Aufrufe. |

---

## 7. Begründung für das Verwerfen früherer Vorab-Diagramme

Im Scientific Audit (Abschnitt SA-02) wurden alle vor dem Audit-Commit `24c23e2fc55b45f06d0a4f65fa521632d83ef8c4` existierenden Diagramme und Plots verworfen und als wissenschaftlich ungültig deklariert.

### Ursachen für das Verwerfen
1. **Methodisch unzulässiges Pooling (SA-02):** In früheren Plots wurden Schätzergebnisse über unterschiedliche Richtungsanzahlen ($N=16, 32, 64$) und voneinander abweichende geometrische Szenen gemittelt. Dadurch wurden unterschiedliche Amplituden $a$ in einen einzigen Datenpunkt vermengt, was jegliche mathematische Steigungsaussage entwertete.
2. **Unzureichende Stichprobengröße:** Frühere Tests verwendeten teilweise nur $R=5$ bis $R=10$ Seeds, was keine verlässliche Schätzung von Bias und Varianz erlaubte.
3. **Fehlende Konfidenzintervalle:** Vorab-Diagramme zeigten einfache Punkt-Mittelwerte ohne Bootstrap-Fehlerbalken oder Streuungsbänder.
4. **Verwechselung von Metriken:** In einigen frühen Berichten wurden Standardabweichung $\sigma$ und RMSE fälschlicherweise synonym verwendet, wodurch der systematische Bias von MLAE kaschiert wurde.

Erst durch die Implementierung des präregistrierten Audits in `audit_experiment.py` mit 256 Seeds pro Zelle, strikter Trennung nach Amplituden $a$ und getrennter Ausweisung von Bias, Varianz, RMSE und Laufzeiten liegen wissenschaftlich belegbare Daten vor.
