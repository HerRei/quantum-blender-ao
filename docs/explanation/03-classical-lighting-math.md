# 03-classical-lighting-math.md — Klassische Beleuchtungsmathematik

## 1. Einleitung und Übersicht

Diese Datei beschreibt die mathematischen und algorithmischen Grundlagen der klassischen Beleuchtungsberechnung im Projekt `quantum-minecraft-rendering`. Der Fokus liegt auf der Bestimmung der **Ambient Visibility** (Umgebungsverdeckung) auf Voxelgittern mittels eines **3D Digital Differential Analyzer (3D-DDA)** Raycasters sowie auf den statistischen Eigenschaften der exakten Auszählung und des klassischem **Monte-Carlo-Samplings (MC)**.

---

## 2. Ambient Visibility (Umgebungsverdeckung)

### 1. Intuition
Stellen Sie sich vor, Sie stehen an einem Punkt in einer Voxel-Welt (z.B. in Minecraft auf dem Boden eines Canyons oder in einer Höhle) und blicken nach oben in den Himmel. Manche Blickrichtungen sind frei und führen direkt in den offenen Himmel, während andere Blickrichtungen durch Voxel-Blöcke (Felsen, Erde, Gebäude) verdeckt werden. 

Die **Ambient Visibility** misst den Anteil der freien Blickrichtungen auf der sichtbaren Halbkugel (Hemisphäre) über einer Oberfläche. Sie ist ein Maß dafür, wie stark ein Punkt dem Umgebungslicht ausgesetzt ist.

### 2. Mathematische Form
Gegeben sei eine Menge von $N$ diskreten Richtungsvektoren auf der oberen Hemisphäre bezüglich einer Oberflächennormale $\mathbf{n}$:
$$d_0, d_1, \dots, d_{N-1} \in \mathbb{R}^3, \quad \|d_i\| = 1$$

Für jede Richtung $d_i$ wird eine binäre Indikatorfunktion $f(i)$ definiert:
$$f(i) = \begin{cases} 1, & \text{falls der Strahl in Richtung } d_i \text{ ungehindert den Himmel erreicht,} \\ 0, & \text{falls der Strahl durch einen opaken Voxel blockiert wird.} \end{cases}$$

Die **exakte diskrete Ambient Visibility** $a$ ist der arithmetische Mittelwert dieser Indikatorwerte:
$$a = \frac{1}{N} \sum_{i=0}^{N-1} f(i)$$

- **Eigenschaften von $a$**:
  - $a \in [0, 1]$, da $f(i) \in \{0, 1\}$.
  - $a = 0$: Der Punkt ist vollständig verdeckt (z.B. im Inneren eines geschlossenen Raumes).
  - $a = 0,5$: Die Hälfte aller Richtungen ist frei (z.B. an einer glatten vertikalen Wand).
  - $a = 1$: Alle Richtungen sind frei (z.B. auf einer flachen Ebene unter freiem Himmel).

- **Unterschied zum kontinuierlichen Integral**:
  Das kontinuierliche Gegenstück ist das physikalische Hemisphärenintegral für ungehindertes Licht:
  $$a_{\text{cont}} = \frac{1}{\pi} \int_{\Omega} V(\mathbf{\omega}) \, (\mathbf{n} \cdot \mathbf{\omega}) \, d\omega$$
  wobei $V(\mathbf{\omega}) \in \{0, 1\}$ die kontinuierliche Sichtbarkeit und $(\mathbf{n} \cdot \mathbf{\omega})$ der Lambert'sche Kosinus-Gewichtungsfaktor ist. Die diskrete Form $a = \frac{1}{N}\sum f(i)$ ist eine gleichgewichtete, diskrete N-Punkt-Approximation auf dem Fibonacci-Gitter.

- **Abgrenzung zu vollständiger Global Illumination (GI)**:
  Ambient Visibility ist **keine** vollständige globale Beleuchtung:
  1. Keine Lichtfarben oder Intensitäten von Lichtquellen.
  2. Keine Materialeigenschaften (BRDF / Reflektionsverhalten).
  3. Keine Distanzabschwächung ($\frac{1}{r^2}$).
  4. Keine Mehrfachreflektionen (indirekte Bounces).
  Es handelt sich um ein rein geometrisches Erreichbarkeitsmaß.

### 3. Kleines Beispiel
Angenommen, $N = 4$ Richtungen werden geprüft. Strahlen $d_0, d_1, d_2$ erreichen den Himmel ($f(0)=1, f(1)=1, f(2)=1$), während $d_3$ auf eine Wand trifft ($f(3)=0$).
$$a = \frac{1 + 1 + 1 + 0}{4} = \frac{3}{4} = 0,75$$

### 4. Umsetzung im Code
Die Generierung der Richtungsvektoren erfolgt über ein Fibonacci-Gitter in `quantum-service/src/qmr/directions.py` (Zeilen 17–48):
```python
def hemisphere_directions(normal: Vector3, count: int) -> list[tuple[float, float, float]]:
```
Die Auswertung von $f(i)$ für alle Richtungen erfolgt in `quantum-service/src/qmr/raycast.py` in der Funktion `visibility_table` (Zeilen 60–76).

### 5. Häufiges Missverständnis
*Missverständnis*: „Ambient Visibility ist das Gleiche wie Ambient Occlusion (AO).“  
*Korrektur*: Ambient Occlusion misst die Verdeckung (Occlusion, $1 - a$), oft gewichtet mit kurzen Distanzen. Ambient Visibility misst die Sichtbarkeit des Himmels ($a$). Zudem berücksichtigt AO in Shadern meist Weichzeichnung und Abstands-Fading, während hier eine binäre Geometrieentscheidung vorliegt.

---

## 3. Der 3D-DDA-Raycaster (Digital Differential Analyzer)

### 1. Intuition
Wie stellt ein Computer fest, ob ein Lichtstrahl durch ein Voxel-Raster ungehindert ins Freie gelangt? Das Durchsuchen aller Voxel in kleinen Schrittweiten währe ineffizient und ungenau. Der 3D-DDA-Algorithmus springt exakt von einer Voxel-Grenzfläche zur nächsten entlang des Strahls. Dadurch wird jeder durchquerte Voxel garantiert exakt einmal besucht, ohne Voxel zu überspringen.

### 2. Mathematische Form
Sei $\mathbf{p}_0 = (x_0, y_0, z_0)$ die Startposition des Strahls und $\mathbf{d} = (d_x, d_y, d_z)$ der normierte Richtungsvektor ($\|\mathbf{d}\| = 1$).

1. **Voxel-Index der aktuellen Zelle**:
   $$\text{cell} = (\lfloor x_0 \rfloor, \lfloor y_0 \rfloor, \lfloor z_0 \rfloor)$$
2. **Schrittrichtung pro Achse**:
   $$\text{step}_k = \begin{cases} 1, & d_k > 0 \\ -1, & d_k < 0 \\ 0, & d_k = 0 \end{cases} \quad \text{für } k \in \{x, y, z\}$$
3. **Schrittweite $t_{\Delta}$ (Distanz in Strahlparametern $t$ für 1 komplette Voxelbreite)**:
   $$t_{\Delta, k} = \left| \frac{1}{d_k} \right|$$
4. **Initialer Abstand zur nächsten Voxel-Grenze $t_{\max}$**:
   $$t_{\max, k} = \begin{cases} \frac{\lfloor x_k \rfloor + 1 - x_k}{d_k}, & d_k > 0 \\ \frac{x_k - \lfloor x_k \rfloor}{|d_k|}, & d_k < 0 \\ \infty, & d_k = 0 \end{cases}$$
5. **Iteration**:
   In jedem Schritt bestimmt $\min(t_{\max, x}, t_{\max, y}, t_{\max, z})$ die Achse $k^*$, an der die nächste Voxel-Grenze gekreuzt wird:
   $$\text{cell}_{k^*} \leftarrow \text{cell}_{k^*} + \text{step}_{k^*}, \quad t_{\max, k^*} \leftarrow t_{\max, k^*} + t_{\Delta, k^*}$$

- **Terminierungskriterien**:
  - **Frei / Sky**: `cell` verlässt das Voxel-Gitter $\implies f(i) = 1$.
  - **Blockiert**: `grid.blocks_visibility(*cell)` ist wahr $\implies f(i) = 0$.
  - **Max Distance**: Zurückgelegte Distanz $t > t_{\text{max\_distance}} \implies f(i) = 0$.

### 3. Kleines Beispiel (4 × 4 × 4 Szene)
Wir betrachten ein Voxel-Gitter der Größe $4 \times 4 \times 4$ ($x, y, z \in \{0, 1, 2, 3\}$).
- **Hindernis**: Ein opaker Voxel liegt bei Koordinaten $(2, 1, 1)$.
- **Strahl-Startpunkt**: $\mathbf{p}_0 = (0.5, 0.5, 0.5)$
- **Richtungsvektor (unkorrigiert)**: $(2.0, 1.0, 1.0) \implies$ Normiert: $\mathbf{d} \approx (0.8165, 0.4082, 0.4082)$
- **Nudge**: Position wird leicht um $10^{-9} \mathbf{d}$ verschoben.
- **Initalisierung**:
  - $\text{cell} = [0, 0, 0]$
  - $\text{step} = [1, 1, 1]$
  - $t_{\Delta} = [1.2247, 2.4495, 2.4495]$
  - $t_{\max} = [(1.0 - 0.5)/0.8165, (1.0 - 0.5)/0.4082, (1.0 - 0.5)/0.4082] = [0.6124, 1.2247, 1.2247]$

**Verlauf des DDA-Traversierung**:

| Schritt | Aktuelle `cell` | $t_{\max, x}$ | $t_{\max, y}$ | $t_{\max, z}$ | Gekreuzte Achse ($\min$) | Status / Ereignis |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **0 (Start)** | `[0, 0, 0]` | 0.6124 | 1.2247 | 1.2247 | $x$ ($t=0.6124$) | Voxel (0,0,0) frei. Nächster Schritt $x$. |
| **1** | `[1, 0, 0]` | 1.8371 | 1.2247 | 1.2247 | $y$ & $z$ (Tied $t=1.2247$) | Voxel (1,0,0) frei. Nächster Schritt $y$ und $z$. |
| **2** | `[1, 1, 1]` | 1.8371 | 3.6742 | 3.6742 | $x$ ($t=1.8371$) | Voxel (1,1,1) frei. Nächster Schritt $x$. |
| **3** | `[2, 1, 1]` | 3.0618 | 3.6742 | 3.6742 | - | **Opaker Voxel getroffen!** $\implies f(i) = 0$. |

### 4. Umsetzung im Code
Der DDA-Raycaster ist in `quantum-service/src/qmr/raycast.py` implementiert:
- **Hauptfunktion**: `reaches_sky(grid, origin, direction, max_distance)` (Zeilen 12–58)
  - Zeile 28: $10^{-9}$ Origin Nudge gegen Floating-Point Boundary Edge Cases.
  - Zeilen 33–44: Berechnung von `step`, `t_delta`, `t_max`.
  - Zeilen 46–57: `while True`-Schleife zur Ausführung der DDA-Schritte und Trefferprüfung.
- **Tests**: `quantum-service/tests/test_raycast.py` (Zeilen 1–31) prüft leere Volumina, opake Blöcke und transparente Voxel.

### 5. Häufiges Missverständnis
*Missverständnis*: „Der DDA-Raycaster bewertet jeden Punkt im Raum in festen Schrittweiten $\Delta s = 0.1$.“  
*Korrektur*: Festschritt-Raymarching verfehlt leicht dünne Voxelgrenzen oder rechnet unnötig viele Punkte im leeren Raum. Der 3D-DDA berechnet analytisch exakt die Schnittpunkte mit den Voxel-Grenzflächen.

---

## 4. Exakte Auszählung (`exact`)

### 1. Intuition
Wenn die Anzahl der abzufragenden Richtungen $N$ klein ist (z.B. $N = 64$), kann der Computer einfach alle $N$ Richtungen nacheinander mit dem 3D-DDA-Raycaster prüfen und exakt summieren. Es entsteht kein Schätzfehler.

### 2. Mathematische Form
$$a_{\text{exact}} = \frac{1}{N} \sum_{i=0}^{N-1} f(i) = \frac{\text{Anzahl sichtbarer Richtungen}}{N}$$

- **Fehler**:
  $$\text{Absoluter Fehler } e = |a_{\text{exact}} - a| = 0$$
- **Ressourcenaufwand**:
  $$M = N \text{ Oracelabfragen / DDA-Auswertungen}$$

Für ein kleines Budget $M = 64$ benötigt die exakte Auszählung exakt $64$ DDA-Aufrufe. Da weder Monte Carlo noch Quanten-MLAE bei $M=64$ einen fehlerfreien Wert garantieren können, ist die exakte Auszählung für $N \le M$ allen stochastischen Verfahren strikt überlegen.

### 3. Umsetzung im Code
Das exakte Backend ist in `quantum-service/src/qmr/backends/exact.py` als `ExactBackend` implementiert (Zeilen 12–45).
- Zeile 20: Erzeugung der vollständigen Sichtbarkeitstabelle `table = visibility_table(request)`.
- Zeile 22: Berechnung von `estimate = sum(table) / len(table)`.
- Zeile 29: Protokollierung von `oracle_calls = len(table)`.

---

## 5. Klassisches Monte Carlo (`classical_monte_carlo`)

### 1. Intuition
Was tun wir, wenn $N$ sehr groß wäre ($N = 10^6$) und eine vollständige Auszählung zu teuer ist? Wir wählen rein zufällig $M$ Richtungen aus, prüfen deren Sichtbarkeit und verwenden deren relativen Anteil als Schätzwert für die gesamte Ambient Visibility.

### 2. Mathematische Form
Seien $I_1, I_2, \dots, I_M$ unabhängig und identisch verteilt (i.i.d.) gleichverteilte Zufallsvariablen aus der Indexmenge $\{0, 1, \dots, N-1\}$.  
Wir definieren die Stichproben-Zufallsvariablen:
$$X_j = f(I_j) \in \{0, 1\} \quad \text{für } j = 1, \dots, M$$

Der klassische Monte-Carlo-Schätzer lautet:
$$\hat{a}_{\text{MC}} = \frac{1}{M} \sum_{j=1}^{M} X_j$$

#### A. Herleitung des Erwartungswerts (Unverzerrtheit / Unbiasedness)
Da die Indizes gleichverteilt gewählt werden, gilt für das einzelne $X_j$:
$$\mathbb{E}[X_j] = P(X_j = 1) \cdot 1 + P(X_j = 0) \cdot 0 = \frac{1}{N} \sum_{i=0}^{N-1} f(i) = a$$

Aufgrund der Linearität des Erwartungswerts folgt:
$$\mathbb{E}[\hat{a}_{\text{MC}}] = \mathbb{E}\left[ \frac{1}{M} \sum_{j=1}^{M} X_j \right] = \frac{1}{M} \sum_{j=1}^{M} \mathbb{E}[X_j] = \frac{1}{M} \cdot M \cdot a = a$$
Der Monte-Carlo-Schätzer ist somit **erwartungstreu (unbiased)**. Der Bias ist exakt Null:
$$\text{Bias}(\hat{a}_{\text{MC}}) = \mathbb{E}[\hat{a}_{\text{MC}}] - a = 0$$

#### B. Herleitung der Varianz
Für eine Bernoulliverteilte Zufallsvariable $X_j \in \{0, 1\}$ mit $P(X_j=1) = a$ gilt:
$$\operatorname{Var}(X_j) = \mathbb{E}[X_j^2] - (\mathbb{E}[X_j])^2 = a - a^2 = a(1-a)$$

Da die Stichproben $X_1, \dots, X_M$ unabhängig gezogen werden (Sampling mit Zurücklegen), gilt für die Varianz der Summe:
$$\operatorname{Var}(\hat{a}_{\text{MC}}) = \operatorname{Var}\left( \frac{1}{M} \sum_{j=1}^{M} X_j \right) = \frac{1}{M^2} \sum_{j=1}^{M} \operatorname{Var}(X_j) = \frac{1}{M^2} \cdot M \cdot a(1-a) = \frac{a(1-a)}{M}$$

#### C. Herleitung des Root Mean Squared Error (RMSE)
Der mittlere quadratische Fehler (MSE) zerfällt allgemein in Varianz und Quadrat des Bias:
$$\text{MSE}(\hat{a}) = \mathbb{E}[(\hat{a} - a)^2] = \operatorname{Var}(\hat{a}) + (\text{Bias}(\hat{a}))^2$$

Da der Bias von Monte Carlo Null ist, entspricht der RMSE direkt der Standardabweichung:
$$\text{RMSE}(\hat{a}_{\text{MC}}) = \sqrt{\operatorname{Var}(\hat{a}_{\text{MC}})} = \sqrt{\frac{a(1-a)}{M}} = \frac{\sqrt{a(1-a)}}{\sqrt{M}}$$

Daraus folgt direkt die asymptotische Konvergenzgeschwindigkeit von Monte Carlo:
$$\text{RMSE}(\hat{a}_{\text{MC}}) = \mathcal{O}(M^{-1/2})$$

Um den Schätzfehler zu halbieren, muss das Stichprobenbudget $M$ **vervierfacht** werden.

### 3. Begriffsklärungen und Statistische Kennzahlen

| Begriff | Mathematische Definition | Bedeutung im Projekt |
| :--- | :--- | :--- |
| **Sample (Stichprobe)** | Einzug von $I_j \in \{0, \dots, N-1\}$ | Ein einzelner ausgewählter Richtungsindex. |
| **Oracle Call / Lookup** | Auswertung $f(I_j)$ | Das Nachschlagen des Sichtbarkeitsbits in der Tabelle. |
| **Seed** | Initialwert $s \in \mathbb{N}$ | Startzustand des PRNG (`random.Random(seed)`), um Läufe exakt zu reproduzieren. |
| **Absoluter Fehler** | $e = \|\hat{a} - a\|$ | Abweichung eines einzelnen Schätzwerts vom wahren Wert. |
| **Bias (Verzerrung)** | $\text{Bias} = \mathbb{E}[\hat{a}] - a$ | Systematische Über- oder Unterschätzung über viele Läufe. |
| **Varianz** | $\operatorname{Var}(\hat{a}) = \mathbb{E}[(\hat{a} - \mathbb{E}[\hat{a}])^2]$ | Mittlere quadratische Streuung um den eigenen Mittelwert. |
| **Standardabweichung ($\sigma$)** | $\sigma = \sqrt{\operatorname{Var}(\hat{a})}$ | Ausmaß der zufälligen Streuung der Schätzwerte. |
| **RMSE** | $\text{RMSE} = \sqrt{\mathbb{E}[(\hat{a} - a)^2]}$ | Gesamtabweichung inklusive Bias und Varianz. |

- **Warum mehrere Seeds notwendig sind**:
  Ein einzelner Stichprobenlauf mit z.B. $M=10$ liefert nur eine einzige Zahl $\hat{a}$. Um festzustellen, ob ein Verfahren erwartungstreu ist oder wie groß seine Varianz ist, müssen viele unabhängige Läufe mit unterschiedlichen Pseudo-Zufalls-Seeds durchgeführt werden.

### 4. Umsetzung im Code
Das Monte-Carlo-Backend ist in `quantum-service/src/qmr/backends/monte_carlo.py` als `ClassicalMonteCarloBackend` implementiert (Zeilen 38–87).
- Zeile 51: `samples = request.max_oracle_calls`.
- Zeile 52: `rng = random.Random(request.seed)`.
- Zeile 53: Ziehen von $M$ zufälligen Indizes mit Zurücklegen: `successes = sum(table[rng.randrange(len(table))] for _ in range(samples))`.
- Zeile 55: Berechnung von Wilson-Score-Konfidenzintervallen mittels `wilson_interval(successes, samples, level)` (Zeilen 15–35).

### 5. Häufiges Missverständnis
*Missverständnis*: „Wenn ich $M=100$ Monte-Carlo-Samples ziehe, ist mein relativer Fehler garantiert unter 1%.“  
*Korrektur*: Der Fehler von Monte Carlo verhält sich stochastisch. Bei $a=0,5$ und $M=100$ beträgt die Standardabweichung $\sigma = \sqrt{\frac{0.5 \times 0.5}{100}} = 0,05$ (also 5 absolute Prozentpunkte). Das $\mathcal{O}(M^{-1/2})$-Gesetz garantiert nur eine statistische Absenkung der Streubreite, keine strikte obere Schranke für jeden Einzellauf.
