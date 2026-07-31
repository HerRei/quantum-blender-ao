# Shader-Logik und Visualisierung

## 1. Einleitung und aktueller Integrationsstatus

Das Verzeichnis **`shaderpack`** enthält ein strukturiertes Iris- und OptiFine-kompatibles GLSL-Shaderpack-Gerüst (*Scaffold*). Das Ziel der Shader-Integration ist es, die vom Quanten-Service geschätzte diskrete Umgebungsverdeckung (*Ambient Visibility* $a \in [0, 1]$) optisch mit den Rendertargets von Minecraft zu verrechnen.

> Diese Komponente wurde nur statisch geprüft beziehungsweise kompiliert und noch nicht im laufenden Zielsystem validiert.

### 1.1 Aktueller Status: Pass-Through Gerüst
Das Shaderpack ist aktuell als **statisches Diagnose- und Pass-Through-Gerüst** implementiert. Es ist **nicht** dynamisch mit den Live-Schätzergebnissen der Fabric-Mod verbunden.

### 1.2 Technische Begründung der Schnittstellen-Einschränkung
In der offiziellen Iris-Shaderpack-Spezifikation werden benutzerdefinierte Uniforms über statische Ausdrucksbäume (*Expression Trees*) in `shaders.properties` definiert (`uniform.float.<name> = <expression>`). Diese Ausdrücke können nur aus vordefinierten Iris-Variablen (z. B. Tageszeit, Regenstärke), Operatoren und Literalen zusammengesetzt werden:
* **Entkopplung**: Iris stellt keine öffentliche, stabile Fabric-Java-API bereit, über die eine externe Java-Mod zur Laufzeit beliebige benutzerdefinierte `float`-Uniforms pro Frame in den Shader-Kontext injizieren kann.
* **Architekturelle Konsequenz**: Die Fabric-Mod besitzt null direkte Abhängigkeiten zu Iris. In `shaders.properties` (Zeile 8) ist eine Platzhalter-Uniform definiert:
  ```properties
  uniform.float.qmrReservedVisibility = smooth(9001, 1.0, 8.0, 8.0)
  ```
  Diese löst sich statisch auf den Festwert `1.0` auf (Keine-Operation / Pass-Through).

### 1.3 Manuelle Diagnoseregler
Um die mathematische Blending-Funktion dennoch visuell testen zu können, definiert `composite.fsh` (Zeilen 13–15) drei Präprozessor-Schalter bzw. Iris-Menüregler:
* `QMR_EXPERIMENTAL_LIGHTING`: 0 (Aus) oder 1 (An). Default: `0`.
* `QMR_MANUAL_VISIBILITY`: Manuelle Sichtbarkeit $0 \dots 100\%$. Default: `100`.
* `QMR_BLEND_PERCENT`: Mischungsintensität $0 \dots 100\%$. Default: `35`.

### 1.4 Statische Prüfung (`check-shaders.sh`)
Die Korrektheit des Shaderpacks wird im Repository automatisiert durch das Shell-Skript `scripts/check-shaders.sh` überprüft. Es verifiziert:
1. Vorhandensein der Kerndateien `composite.vsh` und `composite.fsh`.
2. Vorhandensein der GLSL-Versionsanweisung `#version 330 compatibility` in der ersten Zeile.
3. Balance geschweifter Klammern `{}`.
4. Gültigkeit und Existenz aller `#include`-Pfade.

---

## 2. Ziel-Visueller Effekt und Blending-Mathematik

### 2.1 Didaktische Aufbereitung der Verrechnungsformel

#### Intuition
Umgebungsverdeckung (*Ambient Visibility*) beschreibt, welcher Anteil des indirekten Himmelslichts einen Oberflächenpunkt erreicht. Ist ein Punkt vollständig zum Himmel hin geöffnet ($a=1.0$), erreicht ihn das volle Umgebungslicht (keine Abdunkelung). Steht der Punkt in einer Höhle oder Nische ($a \to 0$), wird das Umgebungslicht stark reduziert.

Die Shader-Logik multipliziert die ursprüngliche Textur- und Grundfarbe der Szene $C_{\text{base}}$ mit einem Abdunkelungsfaktor, der von der geschätzten Sichtbarkeit $a$ und einer eingestellten Mischungsintensität $\beta \in [0, 1]$ abhängt.

#### Mathematische Form
Die Verrechnungsformel lautet:
$$C_{\text{final}} = C_{\text{base}} \cdot \left( (1 - \beta) + \beta \cdot a \right)$$

In GLSL wird diese Linearkombination elegant über die integrierte Vektorfunktion `mix(1.0, a, blendAmount)` ausgedrückt:
$$C_{\text{final}} = C_{\text{base}} \cdot \text{mix}(1.0,\, a,\, \beta)$$

* Ist $\beta = 0.0$ (Schaltung aus), gilt $C_{\text{final}} = C_{\text{base}} \cdot 1.0 = C_{\text{base}}$.
* Ist $\beta = 1.0$ (Vollstärke) und $a = 0.4$, gilt $C_{\text{final}} = C_{\text{base}} \cdot 0.4$.
* Bei einem Standard-Blendwert $\beta = 0.35$ und $a = 0.0$ wird die Grundfarbe auf $(1 - 0.35) = 65\%$ ihrer Helligkeit abgedunkelt.

#### Kleines Beispiel
Angenommen, ein Voxel-Fragment besitzt die Grundfarbe $C_{\text{base}} = (0.8,\, 0.6,\, 0.4)$ (ein helles Braun).
Der Quantenservice ermittelt eine Sichtbarkeit von $a = 0.20$ (stark verdeckt). Die Blend-Intensität steht auf $\beta = 0.50$ (50%).

1. Berechnung des Sichtbarkeitsfaktors:
   $$\text{factor} = \text{mix}(1.0,\, 0.20,\, 0.50) = 1.0 \cdot (1 - 0.50) + 0.20 \cdot 0.50 = 0.50 + 0.10 = 0.60$$
2. Verrechnung mit der Grundfarbe:
   $$C_{\text{final}} = (0.8 \cdot 0.60,\, 0.6 \cdot 0.60,\, 0.4 \cdot 0.60) = (0.48,\, 0.36,\, 0.24)$$
Die Oberfläche wird gleichmäßig um 40% abgedunkelt, während der Farbton beibehalten wird.

#### Umsetzung im Code
Die GLSL-Funktion ist in `shaderpack/shaders/lib/qmr_visibility.glsl` (Zeilen 4–8) implementiert:
```glsl
vec3 qmrApplyAmbientVisibility(vec3 baseColor, float visibility, float blendAmount) {
    float boundedVisibility = clamp(visibility, 0.0, 1.0);
    float boundedBlend = clamp(blendAmount, 0.0, 1.0);
    return baseColor * mix(1.0, boundedVisibility, boundedBlend);
}
```

In `composite.fsh` (Zeilen 17–23) wird die Funktion im Fragment-Shader aufgerufen:
```glsl
void main() {
    color = texture(colortex0, texcoord);
    float enabled = float(QMR_EXPERIMENTAL_LIGHTING);
    float visibility = float(QMR_MANUAL_VISIBILITY) / 100.0;
    float blendAmount = enabled * float(QMR_BLEND_PERCENT) / 100.0;
    color.rgb = qmrApplyAmbientVisibility(color.rgb, visibility, blendAmount);
}
```

#### Häufiges Missverständnis
Ein häufiges Missverständnis von Informatikstudenten ist die Annahme, dass diese Formel ein vollständiges *Path Tracing* oder *Global Illumination (GI)* ersetzt. Ambient Visibility berücksichtigt **weder** Farbübertragungen zwischen Blöcken (*Color Bleeding*), **noch** mehrfache Lichtreflexionen (*Light Bounces*), richtenabhängige Lichtquellen oder Distanzabschwächungen. Es ist ein skalarer 1D-Geometrie-Verdeckungsfaktor für gerichtetes oder ungerichtetes Himmelslicht.

---

## 3. Sichtbarkeitseffekt-Tabelle

Die folgende Tabelle illustriert die Auswirkung verschiedener Sichtbarkeitswerte $a$ auf die relative Helligkeit der Grundfarbe bei voller Mischungsintensität ($\beta = 1.0$) und Standardmischung ($\beta = 0.35$).

| Sichtbarkeit $a$ | Geometrische Bedeutung | Helligkeit bei $\beta = 1.0$ | Helligkeit bei $\beta = 0.35$ | Optischer Eindruck |
| :---: | :--- | :---: | :---: | :--- |
| **1.00** | Völlig freier Himmel (z. B. flaches Feld) | 100.0% | 100.0% | Keine Abdunkelung, volle Tageshelligkeit |
| **0.75** | Leichte Verdeckung (z. B. neben einer Wand) | 75.0% | 91.25% | Weicher, subtiler Schatten an Kanten |
| **0.50** | Halboffene Szene (z. B. unter einem Baum) | 50.0% | 82.50% | Spürbare Einhüllung in Umgebungs-Schatten |
| **0.25** | Stark verdeckt (z. B. tief in einer Schlucht) | 25.0% | 73.75% | Deutlich abgedunkelte Oberflächen |
| **0.00** | Vollständig umschlossen (z. B. tiefe Höhle) | 0.0% | 65.0% | Maximale Abdunkelung auf Raumlicht-Niveau |

---

## 4. Datenfluss: HUD vs. Geplanter Shader

Es besteht ein wichtiger Unterschied zwischen dem aktuellen Live-Datenfluss im HUD und dem Datenfluss im Shader:

```text
[ Quantum Service Result ]
            │
            ▼ (asynchron über HTTP)
 [ LightingServiceClient ]
            │
            ▼
 [ LightingResultCache ] ──► [ VisibilitySmoother ] ──► [ In-Game HUD (Live Rendered) ]
                                      │
                                      └─── (Zukünftige Bridge) ──► [ GLSL Shader Uniform ]
                                                                          │
                                                                          ▼
                                                                [ composite.fsh ]
                                                            (Aktuell: Liest Regler)
```

1. **HUD-Datenfluss (Aktiv & Live)**:
   Das Schätzergebnis des Quantum-Service wird vom Java-Mod-Client empfangen, im `LightingResultCache` gespeichert, durch den `VisibilitySmoother` geglättet und direkt im Minecraft-GUI-Overlay (`renderHud`) auf den Bildschirm gezeichnet.
2. **Shader-Datenfluss (Statisches Gerüst)**:
   Der Fragment-Shader `composite.fsh` liest aktuell die manuellen Präprozessor-Regler (`QMR_MANUAL_VISIBILITY`). Er ist noch nicht an die dynamische Mod-Pipeline angebunden, weil Iris keine dynamische Uniform-Injektion unterstützt.

---

## 5. Zeitliche exponentielle Glättung (Temporal Smoothing)

### 5.1 Didaktische Aufbereitung der Glättungsformel

#### Intuition
Da die Schätzung der Sichtbarkeit über das Netzwerk und den Quantensimulator asynchron erfolgt (z. B. alle 5 Ticks bzw. 250 ms), würde eine direkte, schlagartige Übernahme des geschätzten Werts $a$ zu störendem Bildflackern (*Screen Flickering*) bei Spielerbewegungen führen. Der `VisibilitySmoother` berechnet daher eine zeitlich kontinuierliche Übergangsfunktion zwischen Frames.

#### Mathematische Form
Gegeben sei der bisherige geglättete Wert $v_{t-1}$ und der neu eingetroffene diskrete Schätzwert $\hat{a}$. Bei einer zeitlichen Bildrate mit Bilddauer $\Delta t$ und einer festgelegten Halbwerts-/Zeitkonstante $\tau$ lautet der Glättungsfaktor $\alpha$:
$$\alpha = 1.0 - e^{-\frac{\Delta t}{\tau}}$$

Der neue geglättete Wert $v_t$ berechnet sich iterativ gemäß:
$$v_t = (1 - \alpha) \cdot v_{t-1} + \alpha \cdot \hat{a} = v_{t-1} + \alpha \cdot (\hat{a} - v_{t-1})$$

#### Kleines Beispiel
Es sei $\tau = 0.25$ Sekunden ($250\,\text{ms}$).
Der bisherige Glättungswert sei $v_{t-1} = 1.0$. Plötzlich trifft ein neuer Schätzwert $\hat{a} = 0.0$ ein.
Nach einem Frame-Intervall von $\Delta t = 0.01667$ Sekunden ($60\,\text{FPS}$):
$$\alpha = 1.0 - e^{-\frac{0.01667}{0.25}} = 1.0 - e^{-0.06668} \approx 1.0 - 0.9355 = 0.0645$$

Neuer geglätteter Wert für den ersten Frame:
$$v_t = 1.0 + 0.0645 \cdot (0.0 - 1.0) = 1.0 - 0.0645 = 0.9355$$
Der Wert fällt weich von $1.0$ über $0.9355 \to 0.875 \to \dots$ innerhalb von ca. 250 ms auf $0.0$ ab.

#### Umsetzung im Code
Die Logik ist in `minecraft-mod/src/main/java/ch/unibas/qmr/state/VisibilitySmoother.java` (Zeilen 4–36) implementiert:
```java
public double update(double target, long currentTimeNanos) {
    if (lastTimeNanos == 0) {
        lastTimeNanos = currentTimeNanos;
        currentValue = target;
        return target;
    }
    double deltaSeconds = (currentTimeNanos - lastTimeNanos) / 1.0e9;
    lastTimeNanos = currentTimeNanos;
    double alpha = 1.0 - Math.exp(-deltaSeconds / halfLifeSeconds);
    currentValue += alpha * (target - currentValue);
    return currentValue;
}
```

#### Häufiges Missverständnis
Die Glättung verändert nicht die mathematische Genauigkeit des Quanten-Schätzers, sondern dient ausschließlich der visuellen Bildstabilisierung im Grafik-Client.

---

## 6. Rationale des Gerüst-Ansatzes

Warum wird im Repository ein Shaderpack-Gerüst eingecheckt, obwohl Iris aktuell keine dynamische Uniform-Injektion aus Java-Mods unterstützt?

1. **Standardisierung des GLSL-Pipelines**: Das Gerüst definiert bereits die vollständige Struktur (Vertex-Shader, Fragment-Shader, Render-Passes) nach dem Iris/OptiFine-Standard.
2. **Syntaktische Entkopplung**: Über `scripts/check-shaders.sh` wird sichergestellt, dass GLSL 330 compatibility Code valide bleibt und keine Syntaxfehler enthält.
3. **Zukunftssicherheit**: Sobald Iris eine stabile API oder ein Versioned-Bridge-Schnittstellenmodell für benutzerdefinierte Java-Mod-Uniforms bereitstellt, muss lediglich die Uniform-Deklaration in `shaders.properties` angepasst werden. Die Blending-Logik `qmrApplyAmbientVisibility` ist bereits fertiggestellt und verifiziert.
