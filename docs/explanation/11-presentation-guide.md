# 11 - Präsentationsleitfaden für universitäre Vorträge

Dieser Leitfaden dient als Struktur- und Redeleitfaden für eine 15- bis 20-minütige akademische Präsentation des Projekts `quantum-minecraft-rendering`. Er gliedert den Vortrag in 13 Folien und liefert zu jeder Folie Kernaussagen, visuelle Darstellungen, mündliche Erklärungen sowie vorbereitete Antworten auf kritische Dozentenfragen.

---

## 1. Folien-für-Folien Leitfaden (13 Folien)

### Folie 1: Motivation & Kontext
- **Folientitel:** Quantenmechanische Beleuchtungsschätzung in Voxelwelten
- **Hauptaussage:** Kann Quanten-Amplitude-Estimation (QAE) in der Computergrafik zur Beschleunigung von Beleuchtungs- und Sichtbarkeitsberechnungen eingesetzt werden?
- **Geeignete Grafik:** Gegenüberstellung eines Minecraft-Screenshots mit einem Voxel-Gitter und einer Halbkugelsphäre.
- **Mündlicher Vortragstext:** „Guten Tag. In der Echtzeit-Computergrafik ist die Berechnung globaler Beleuchtung und Umgebungsverdeckung — der sogenannten Ambient Occlusion — eine der rechenintensivsten Aufgaben. Klassisch nutzen wir Monte-Carlo-Raytracing. In dieser Arbeit untersuchen wir am Beispiel einer Voxelwelt wie Minecraft, ob und unter welchen Bedingungen Quantenalgorithmen wie die Maximum-Likelihood Amplitude Estimation einen Vorteil bei der Schätzung diskreter Sichtbarkeiten bieten können.“
- **Typische Rückfrage:** „Verwenden Sie echte Quantenprozessoren für das Rendering?“
- **Antwort:** „Nein, die Quantenschaltungen werden auf klassischen CPUs mit Qiskit simuliert, um das theoretische Abfrage-Skalierungsverhalten exakt zu untersuchen.“

---

### Folie 2: Die Forschungsfrage
- **Folientitel:** Forschungsfrage & Modellgrenzen
- **Hauptaussage:** Erreicht finite-shot MLAE unter einem idealisierten Abfrage-Kostenmodell geringere Fehler als i.i.d. Monte Carlo?
- **Geeignete Grafik:** Textbox mit der formalen Forschungsfrage und Gegenüberstellung von $M_{\text{MLAE}}$ vs. $M_{\text{MC}}$.
- **Mündlicher Vortragstext:** „Unsere Forschungsfrage lautet streng: Kann Quanten-Amplitude-Estimation unter einem idealisierten Oracle-Kostenmodell bei gleicher Zahl logischer Abfragen genauer sein als klassisches Monte Carlo? Wichtig ist dabei die Abgrenzung: Wir messen primär die logische Abfragekomplexität $M$, trennen diese aber strikt von klassischen Simulatorlaufzeiten.“
- **Typische Rückfrage:** „Was verstehen Sie unter einem idealisierten Oracle-Kostenmodell?“
- **Antwort:** „Wir zählen die Anzahl der Aufrufe des reversiblen Sichtbarkeits-Oracles $U_f$, vernachlässigen aber vorerst die klassischen Kosten der Schaltungssynthese und der Zustandsevolution auf dem Simulator.“

---

### Folie 3: Klassisches Ambient Visibility Math
- **Folientitel:** Diskrete Ambient Visibility & 3D-DDA
- **Hauptaussage:** Sichtbarkeit $a$ ist der Mittelwert einer diskreten Trefferfunktion $f(i) \in \{0, 1\}$ über $N$ Richtungen.
- **Geeignete Grafik:** Formel $a = \frac{1}{N}\sum_{i=0}^{N-1} f(i)$ und Skizze eines 3D-DDA-Strahls durch ein Voxelgitter (`raycast.py:12-58`).
- **Mündlicher Vortragstext:** „Wir diskretisieren die Halbkugel über dem Abfragepunkt in $N=64$ Richtungen mittels eines Fibonacci-Gitters. Ein klassischer 3D-DDA-Raycaster prüft für jede Richtung $d_i$, ob der Strahl ungehindert in den Himmel austritt ($f(i)=1$) oder von einem Voxel blockiert wird ($f(i)=0$). Die exakte Sichtbarkeit $a$ ist der Anteil der freien Richtungen.“
- **Typische Rückfrage:** „Warum verwenden Sie keine kontinuierlichen Integrale oder komplexen BRDFs?“
- **Antwort:** „Das diskrete Modell isoliert das Kernproblem der Amplitudenschätzung ohne statistische Störfaktoren wie kontinuierliche Verteilungen oder Mehrfach-Bounces.“

---

### Folie 4: Klassisches Monte Carlo Sampling
- **Folientitel:** Klassische Referenz: i.i.d. Monte Carlo
- **Hauptaussage:** Klassisches Monte Carlo skaliert unverzerrt mit dem Gesetz der großen Zahlen: $\operatorname{RMSE} = O(M^{-1/2})$.
- **Geeignete Grafik:** Formeln für $\hat{a}_{\text{MC}} = \frac{1}{M}\sum X_j$ und $\operatorname{Var} = \frac{a(1-a)}{M}$ sowie ein Konfidenzintervall-Diagramm (Wilson Score, `monte_carlo.py:15-35`).
- **Mündlicher Vortragstext:** „Klassisches Monte Carlo wählt zufällig $M$ Richtungen aus der Tabelle aus. Es ist streng unverzerrt, hat aber die bekannte Konvergenzgrenze von $O(M^{-1/2})$. Um den Fehler zu halbieren, vervierfachen sich die notwendigen Stichproben.“
- **Typische Rückfrage:** „Ziehen Sie mit oder ohne Zurücklegen?“
- **Antwort:** „Wir ziehen i.i.d. mit Zurücklegen, da dies das Standard-Referenzmodell für klassische Unabhängigkeit darstellt.“

---

### Folie 5: Quanten-Zustandspräparation
- **Folientitel:** Zustandspräparation $A$ & Reversibles Oracle $U_f$
- **Hauptaussage:** Das Oracle $U_f$ codiert die Sichtbarkeitstabelle in die Phase/Amplitude eines Objective-Qubits.
- **Geeignete Grafik:** Quantenschaltkreis-Diagramm für $A = U_f (H^{\otimes n} \otimes I)$ und Formel $A|0\rangle = \sqrt{1-a}|\psi_0\rangle|0\rangle + \sqrt{a}|\psi_1\rangle|1\rangle$ (`cpu_quantum.py:141-171`).
- **Mündlicher Vortragstext:** „Im Quantenmodell präparieren wir eine uniforme Superposition über alle Richtungsindizes. Das reversible Oracle $U_f$ bildet den Zustand $|i\rangle|0\rangle$ auf $|i\rangle|f(i)\rangle$ ab. Die Wahrscheinlichkeit, das Objective-Qubit als $|1\rangle$ zu messen, entspricht exakt der Zielamplitude $a = \sin^2(\theta)$.“
- **Typische Rückfrage:** „Woher kennt das Quanten-Oracle die Sichtbarkeitstabelle?“
- **Antwort:** „In dieser Implementierung wird die Tabelle vorab klassisch berechnet und synthetisch als Mehrfach-Steuerungs-X-Gatter-Netzwerk in die Schaltung gebaut.“

---

### Folie 6: Grover-Amplifikation
- **Folientitel:** Grover-Rotation im 2D-Unterraum
- **Hauptaussage:** Der Grover-Operator $Q = -A S_0 A^{-1} S_{\text{good}}$ rotiert den Zustandsvektor um den Winkel $2\theta$.
- **Geeignete Grafik:** Geometrische 2D-Vektorrotation in der Ebene $\{|\psi_0\rangle|0\rangle, |\psi_1\rangle|1\rangle\}$ und Formel $p_k(a) = \sin^2((2k+1)\theta)$ (`cpu_quantum.py:182-200`).
- **Mündlicher Vortragstext:** „Durch Anwendung des Grover-Operators $Q$ verstärken wir die Amplitude des guten Zustands. Nach $k$ Iterationen beträgt die Messwahrscheinlichkeit für den Zustand 1 genau $\sin^2((2k+1)\theta)$. Je größer $k$, desto empfindlicher reagiert die Wahrscheinlichkeit auf kleine Abweichungen in $\theta$.“
- **Typische Rückfrage:** „Warum kann man $k$ nicht beliebig groß wählen?“
- **Antwort:** „Weil die Sinus-Funktion periodisch ist. Zu große $k$ führen zu Aliasing und Mehrdeutigkeiten bei der Rückberechnung von $a$.“

---

### Folie 7: Maximum Likelihood Amplitude Estimation (MLAE)
- **Folientitel:** Schätzung ohne Phasenabschätzung: MLAE
- **Hauptaussage:** MLAE nutzt ein optimales Likelihood-Modell über Schaltungen verschiedener Grover-Potenzen $k_j$.
- **Geeignete Grafik:** Formel der Log-Likelihood-Funktion $\ell(a) = \sum [h_j \ln p_{k_j}(a) + (s_j-h_j)\ln(1-p_{k_j}(a))]$ und Plot einer multimodalen Likelihood-Kurve mit Maximum (`cpu_quantum.py:289-304`).
- **Mündlicher Vortragstext:** „Statt eine aufwendige QPE mit vielen Zusatz-Qubits auszuführen, nutzt MLAE Schaltungen mit verschiedenen Grover-Potenzen $k \in \{0, 1, 2, 4, 8\}$. Aus den gemessenen Trefferzahlen bestimmen wir über ein klassisches Maximum-Likelihood-Verfahren den wahrscheinlichsten Wert für $a$.“
- **Typische Rückfrage:** „Wie werden Randfälle wie $a=0$ oder $a=1$ behandelt?“
- **Antwort:** „Über numerische Absicherungen mit $\epsilon$-Clipping im Likelihood-Evaluator (`audit_experiment.py:268-330`).“

---

### Folie 8: Software-Architektur
- **Folientitel:** Systemarchitektur & Entkopplung
- **Hauptaussage:** Entkopplung von Minecraft-Mod (Java 25) und Quantum-Service (Python 3.13 / FastAPI).
- **Geeignete Grafik:** Mermaid-Architekturdiagramm aus `00-overview.md` / `01-codebase-architecture.md`.
- **Mündlicher Vortragstext:** „Die Architektur besteht aus zwei Hauptkomponenten: Der Fabric-Mod in Java extrahiert die Voxelwelten asynchron. Der Python-Service empfängt JSON-Requests über eine FastAPI-REST-Schnittstelle und delegiert sie an ein austauschbares Backend (`exact`, `monte_carlo`, `cpu_quantum`).“
- **Typische Rückfrage:** „Blockiert die Quantensimulation das Spiel Minecraft?“
- **Antwort:** „Nein, alle HTTP-Requests und Netzwerk-Transporte laufen vollständig asynchron im Hintergrund.“

---

### Folie 9: Minecraft-Mod Demo & HUD
- **Folientitel:** Minecraft-Integration & Live-HUD
- **Hauptaussage:** Der Fabric-Mod visualisiert Sichtbarkeitswerte und Performanzmetrikencht im HUD.
- **Geeignete Grafik:** HUD-Screenshot-Mockup oder Texttabelle der HUD-Werte (`QuantumRenderingClient.java:192-216`).
- **Mündlicher Vortragstext:** „Über Tastenkürzel wie 'Q' oder 'G' kann der Spieler im Spiel das Rendering aktivieren und zwischen den Backends wechseln. Das HUD zeigt in Echtzeit den geglätteten Sichtbarkeitswert, Latenzen und die Zahl der Oracle-Aufrufe.“
- **Status-Hinweis:**
  > Diese Komponente wurde nur statisch geprüft beziehungsweise kompiliert und noch nicht im laufenden Zielsystem validiert. (Bezieht sich auf die Shader-Einbindung).

---

### Folie 10: Benchmark-Methodik
- **Folientitel:** Präregistriertes Audit-Versuchsdesign
- **Hauptaussage:** 256 Seeds pro Versuchszelle garantieren valide statistische Bootstrap-Konfidenzintervalle.
- **Geeignete Grafik:** Übersichtstabelle der Versuchszellen (7 Amplituden, 5 Budgets, 256 Seeds = 8.960 Einzelruns).
- **Mündlicher Vortragstext:** „Um wissenschaftliche Strenge zu garantieren, haben wir ein präregistriertes Audit mit 8.960 Einzellläufen durchgeführt. Wir untersuchen 7 exakte Zielamplituden über 5 Budget-Stufen und berechnen streng getrennt Bias, Varianz, Standardabweichung und RMSE.“
- **Typische Rückfrage:** „Warum haben Sie frühere Messergebnisse verworfen?“
- **Antwort:** „Frühere Messungen hatten unzulässiges Pooling über verschiedene Szenen und Richtungszahlen durchgeführt. Das Audit bereinigt diese Mängel vollständig.“

---

### Folie 11: Ergebnisse: Fehler & Skalierung
- **Folientitel:** Empirische Ergebnisse: Fehlerreduktion vs. Skalierung
- **Hauptaussage:** MLAE schlägt Monte Carlo bei $M=1015$ an allen Innenamplituden (Fehlerreduktion bis $3.46\times$), zeigt aber wegen $k_{\max}=8$ kein asymptotisches $O(M^{-1})$.
- **Geeignete Grafik:** Plot `rmse-vs-logical-oracle-calls.png` aus `experiments/audit-results/2026-07-31/plots/`.
- **Mündlicher Vortragstext:** „Hier sehen wir das Hauptergebnis: Bei einem Budget von $M=1015$ erzielt MLAE an allen 5 Innenamplituden einen deutlich kleineren RMSE als Monte Carlo. Allerdings skaliert die Kurve bei höheren Budgets nur noch mit $O(M^{-1/2})$, da der Grover-Schedule bei $k_{\max}=8$ saturiert und nur noch die Shot-Zahl erhöht wird.“
- **Typische Rückfrage:** „Warum liegt kein echter Quantenvorteil vor?“
- **Antwort:** „Weil die asymptotische Steigung $O(M^{-1})$ ein dynamisch wachsendes $k_{\max}$ erfordert hätte.“

---

### Folie 12: Ergebnisse: Laufzeiten & Grenzen
- **Folientitel:** Dominanz der exakten Auszählung & Laufzeiten
- **Hauptaussage:** Exakte Auszählung dominiert bei $N=64$ ($0.00025\text{ ms}$). Quantensimulation ist um Faktor $43.800\times$ langsamer als klassisches Monte Carlo.
- **Geeignete Grafik:** Plot `runtime-vs-logical-oracle-calls.png` und Laufzeit-Vergleichstabelle (`09-results-and-interpretation.md`).
- **Mündlicher Vortragstext:** „Bei Betrachtung der realen Wall-Clock-Zeiten zeigt sich: Für $N=64$ Richtungen ist die klassische exakte Auszählung in $0.00025\text{ ms}$ fertig und hat Fehler Null. Die Simulation der Quantenschaltung auf der CPU benötigt dagegen über 2 Sekunden — das ist $43.800$-mal langsamer als klassisches Monte Carlo.“
- **Typische Rückfrage:** „Würde eine GPU dieses Problem lösen?“
- **Antwort:** „Eine GPU verringert die Simulatordauer, ändert aber nichts daran, dass exakte Auszählung bei $N=64$ trivial bleibt.“

---

### Folie 13: Schlussfolgerung
- **Folientitel:** Fazit & Wissenschaftliche Kernaussage
- **Hauptaussage:** MLAE zeigt theoretischen Genauigkeitsgewinn unter idealisierten Oracle-Kosten, aber keinen praktischen Speed-up für Voxel-Visibility.
- **Geeignete Grafik:** Kasten mit dem zentralen Zitat aus `09-results-and-interpretation.md`.
- **Mündlicher Vortragstext:** „Wir schließen mit unserer Kernaussage: MLAE kann unter einem idealisierten Oracle-Kostenmodell bei ausgewählten Budgets und Amplituden weniger Schätzfehler als iid-Monte-Carlo aufweisen. Für die kleine diskrete Voxel-Visibility-Aufgabe dominieren jedoch exakte Auszählung, Oracle-Erzeugung und klassische Simulatorkosten. Es wurde kein praktischer Quantum Speed-up gezeigt. Ich danke für Ihre Aufmerksamkeit und freue mich auf Ihre Fragen.“

---

## 2. Antworten auf 11 kritische Dozentenfragen (Q&A)

### Frage 1: Warum verwenden Sie QAE und nicht einfach Grover Search?
**Antwort:** Grover-Suche sucht ein einzelnes Element in einem unsortierten Raum (Finden eines Good State). Wir wollen jedoch nicht ein bestimmtes Element finden, sondern das globale Verhältnis $a = \frac{\text{Anzahl Good States}}{N}$ exakt schätzen. Dafür ist Amplitude Estimation das mathematisch adäquate Verfahren.

### Frage 2: Warum zeigt Ihr Projekt keinen praktischen Quantum Speed-up?
**Antwort:** Drei Gründe: Erstens führen wir die Quantenschaltungen klassisch auf einer CPU aus ($O(2^n)$ Simulationsaufwand). Zweitens muss die Sichtbarkeitstabelle vorab klassisch berechnet werden. Drittens ist der Suchraum mit $N=64$ so klein, dass exakte klassische Auszählung in $0.25\ \mu\text{s}$ dominiert.

### Frage 3: Warum wird die Visibility-Tabelle klassisch erstellt, anstatt Raycasting reversibel in der Quantenschaltung auszuführen?
**Antwort:** Reversibles 3D-DDA-Raycasting auf einer QPU würde Tausende von Ancilla-Qubits und extrem tiefe Quantenschaltungen für Voxel-Speicherzugriffe erfordern. Um das Grundprinzip von QAE verlässlich zu untersuchen, wurde das Raycasting als klassischer Vorbereitungsschritt getrennt.

### Frage 4: Wo genau liegt das verwendete Oracle-Modell?
**Antwort:** Das Oracle ist das synthetisierte Schaltungselement $U_f$, das in `cpu_quantum.py` (Zeilen 141–161) gebaut wird. Es bildet $|i\rangle|0\rangle \to |i\rangle|f(i)\rangle$ ab. Unser Abfrage-Kostenmodell $M = s \cdot \sum (2k+1)$ zählt exakt die logischen Aufrufe dieses Operators.

### Frage 5: Warum ist die exakte Auszählung schneller als klassisches Monte Carlo und Quanten-Simulation?
**Antwort:** Bei $N=64$ Richtungen müssen nur 64 Speicherstellen addiert werden. Das dauert $250\text{ ns}$. Monte Carlo benötigt Zufallszahlengenerierung und Stichprobenverwaltung. MLAE erzeugt zusätzlich Gatter-Matrizen und führt komplexe Likelihood-Optimierungen aus.

### Frage 6: Was bedeutet der Faktor $(2k+1)$ in der Kostenformel?
**Antwort:** Der Grover-Operator lautet $Q = -A S_0 A^{-1} S_{\text{good}}$. Ein Block $Q$ enthält somit eine Vorwärts-Präparation $A$ und eine inverse Präparation $A^{-1}$, die jeweils ein Oracle $U_f$ enthalten (insgesamt 2 Oracle-Aufrufe pro $Q$). Die Schaltung $Q^k A$ enthält daher $2k + 1$ Aufrufe von $U_f$.

### Frage 7: Warum entsteht Aliasing bei MLAE?
**Antwort:** Die Erfolgswahrscheinlichkeit $p_k(a) = \sin^2((2k+1)\theta)$ ist periodisch. Verschiedene Amplituden $a$ können für ein festes $k$ dieselbe Wahrscheinlichkeit $p_k(a)$ erzeugen. Erst durch die Kombination verschiedener Potenzen $k \in \{0, 1, 2, 4, 8\}$ werden diese Mehrdeutigkeiten in der Likelihood-Funktion aufgelöst.

### Frage 8: Warum ist eine zweite GPU wissenschaftlich nicht notwendig?
**Antwort:** Der wissenschaftliche Kern untersucht das mathematische Fehler- und Abfrageverhalten $M$ vs. RMSE. Eine zweite GPU verändert lediglich die Simulatordauer auf klassischer Hardware, beeinflusst aber weder die logische Abfragekomplexität $M$ noch die mathematische Präzision der Quantenschaltungen.

### Frage 9: Was würde der Einsatz einer echten QPU an den Ergebnissen verändern?
**Antwort:** Auf einer echten QPU würde der Simulations-Overhead entfallen. Allerdings stünde man vor der Herausforderung, dass physische Dekohärenz und Gatter-Rauschen (Gate Noise) die feingliedrigen Grover-Phasen zerstören würden. Zudem bliebe der Engpass der klassischen Oracle-Synthese bestehen.

### Frage 10: Warum ist Minecraft mehr als nur eine Dekoration in diesem Projekt?
**Antwort:** Minecraft liefert hochvariable, komplexe 3D-Voxelstrukturen aus einer realen Anwendungsumgebung. Es dient als praxisnahe Datenquelle für Beleuchtungsprobleme und belegt die funktionale Entkopplung zwischen Grafikanwendung und Quanten-Service.

### Frage 11: Was ist der größte „Threat to Validity“ in Ihrer Studie?
**Antwort:** Der größte Threat to Validity ist die Begrenzung des Richtungsregisters auf $N=64$ sowie die Saturierung des Grover-Schedules bei $k_{\max}=8$. Dadurch konnte das theoretische $O(M^{-1})$-Skalierungsverhalten für große Budgets nicht asymptotisch demonstriert werden.
