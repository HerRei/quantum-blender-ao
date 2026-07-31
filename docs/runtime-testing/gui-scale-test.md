# GUI Skalierungs-Test

Das modifizierte HUD (`QuantumRenderingClient`) wurde unter verschiedenen UI-Skalierungen (`guiScale: 0` (Auto) und `guiScale: 3` (Large)) geprüft.

## Ergebnisse:
1. **Keine abgeschnittenen Zeilen**: Der Text rendert vollständig innerhalb des sichtbaren Bereichs, da die Skalierung nativ über `GuiGraphics` von Minecraft abgehandelt wird.
2. **Hintergrund**: Der nachträglich implementierte abgedunkelte Hintergrund (`guiGraphics.fill(...)`) skaliert korrekt mit den berechneten Textdimensionen mit und deckt die Texte zu jedem Zeitpunkt vollständig ab.
3. **Fehlermeldungen**: Lange Stacktraces bei Connection Errors (wie `java.net.ConnectException` oder JSON Parse Errors) werden, sofern zu lang für das HUD, ordnungsgemäß durch die Breiten-Limitierung des Minecraft Font-Renderers umgebrochen bzw. gekürzt.
4. **Lesbarkeit**: Die Backend-Spezifikation, Status, Servicezeit und Roundtrip bleiben auch auf Skalierung 3 sauber getrennt und gut lesbar.
