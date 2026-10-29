# Werkzeugwand (Lochwand) 150 × 80 cm

3D-Modell einer Werkzeug-Lochwand mit Haken, die nach vorne aus der Wand stehen. An jedem
Haken sitzt ein Empty als Markierung für einen Proxy (z. B. Werkzeug, das am Haken hängt).
Die Löcher sind echte Geometrie, also kann man überall weitere Haken einsetzen.

![Vorschau](vorschau/vorschau_gesamt.jpg)

| | |
| --- | --- |
| Größe | 150 cm breit × 80 cm hoch × 2,5 cm Wandabstand |
| Lochung | Vierkant 10 × 10 mm, Raster 38 mm, 37 Spalten × 19 Reihen = 703 Löcher |
| Blech | 2 mm, Rand rundum nach hinten abgekantet |
| Haken | 30 Stück, 5 Typen (siehe unten) |
| Polygone | Platte 15 880 Dreiecke, Haken 140–332 Dreiecke, alles zusammen 21 872 Dreiecke |
| Einheit | 1 Einheit = 1 Meter |

## Dateien

| Datei | Inhalt |
| --- | --- |
| `werkzeugwand.blend` | Blender-Szene: Platte, Haken, Proxy-Empties, Vorlagen und Kollisionsbox |
| `werkzeugwand.fbx` | Platte + alle Haken + Proxy-Empties |
| `werkzeugwand.obj` / `.mtl` | Platte + alle Haken (OBJ kennt keine Empties) |
| `einzelteile/lochwand_platte.*` | nur die Lochwand ohne Haken |
| `einzelteile/haken_<typ>.*` | jeder Hakentyp einzeln, Ursprung am Einsteckpunkt |
| `einzelteile/lochwand_kollision.*` | einfache Box (8 Punkte) für Geometry / View Geometry / Fire Geometry LOD |
| `proxy_positionen.csv` | Nummer, Typ, Loch und Koordinaten jedes Hakens und Proxys |
| `vorschau/belegungsplan.jpg` | Ansicht von vorne mit Spalten-, Reihen- und Hakennummern |
| `generate_werkzeugwand.py` | Skript, das alles oben erzeugt (Maße und Hakenbelegung stehen oben drin) |
| `vorschau.py` | rendert die Vorschaubilder |

## Achsen und Ursprung

Der Ursprung liegt in der Mitte der Rückseite, also auf der Wandfläche, an der die Lochwand hängt.

| | Blender | FBX / OBJ |
| --- | --- | --- |
| rechts | +X | +X |
| oben | +Z | +Y |
| vorne (aus der Wand heraus) | −Y | +Z |
| Vorderseite der Platte | Y = −0,025 | Z = +0,025 |

FBX und OBJ sind Y-up mit Vorderseite nach +Z, so wie das P3D-Koordinatensystem. Steht die Wand
nach dem Import verkehrt herum, einfach um 180° um die Hochachse drehen.

## Hakentypen

Alle Haken haben eine Steckplatte mit zwei Laschen: oben eingehängt (hinter dem Blech nach unten
abgekantet), unten eingesteckt im Loch darunter. Der Ursprung jedes Hakens ist die Mitte des
oberen Lochs auf der Vorderseite der Platte.

| Typ | Beschreibung | Ausladung | Proxy-Empty sitzt … |
| --- | --- | --- | --- |
| `kurz` | Einzelhaken, Spitze hochgebogen | 8,5 cm | oben auf dem Arm, bei 70 % der Länge |
| `lang` | Einzelhaken, Spitze hochgebogen | 16 cm | oben auf dem Arm, bei 70 % der Länge |
| `doppel` | zwei Arme im Abstand 38 mm, belegt 2 Spalten | 11 cm | mittig zwischen den Armen |
| `bogen` | J-Haken für Kabel und Schläuche | 9,5 cm | unten in der Biegung |
| `ring` | Ringhalter, innen Ø 2,9 cm (Schraubendreher, Spraydosen) | 7,7 cm | Ringmitte |

## Proxys setzen

- In Blender hängt an jedem Haken ein Empty `Proxy_<Nr>_<Typ>` (Kind des Hakens). Wird der Haken
  verschoben, wandert der Proxy mit. Die Empties sind auch in `werkzeugwand.fbx` enthalten.
- `proxy_positionen.csv` enthält dieselben Punkte als Zahlen: `proxy_blender_*` für Blender,
  `proxy_objfbx_*` für die exportierten FBX-/OBJ-Dateien (und damit für Object Builder). Welcher
  Haken welche Nummer hat, zeigt `vorschau/belegungsplan.jpg`.
- Die Hakenmeshes heißen `Haken_<Nr>_<Typ>`, das Material der Platte `Lochwand_Platte` und das
  der Haken `Lochwand_Haken`. Dort kommen die eigenen Texturen bzw. rvmats drauf.
- UVs: Box-Projektion, 1 UV-Einheit = 1 m, passend für kachelnde Metall-/Lacktexturen.

## Weitere Haken einsetzen

Lochpositionen (Spalte 1–37 von links, Reihe 1–19 von oben, Ursprung jeweils in der Lochmitte):

```
X        = (Spalte − 19) × 0,038
Höhe     = (10 − Reihe) × 0,038      (Blender Z, FBX/OBJ Y)
Vorne    = 0,025                     (Blender −Y, FBX/OBJ +Z)
```

Ein Haken auf Spalte/Reihe hängt im Loch (Spalte, Reihe) und steckt unten in (Spalte, Reihe + 1).

**Im Skript (empfohlen):** In `generate_werkzeugwand.py` die Liste `HAKEN` erweitern, z. B.
`("lang", 10, 5)`, und neu erzeugen. Das Skript prüft, dass kein Loch doppelt belegt ist und sich
keine Haken überschneiden, und schreibt CSV, Exporte und `.blend` neu.

**In Blender:** Einen Haken samt Proxy-Empty auswählen, mit `Alt+D` verknüpft duplizieren und um
ganze Löcher verschieben, z. B. `X` und `0.038*4` eintippen (4 Löcher nach rechts) oder `Z` und
`-0.038*6` (6 Reihen tiefer). Die Vorlagen aller Typen liegen in der ausgeblendeten Collection
`Haken_Vorlagen` am Ursprung. Das Viewport-Gitter ist auf 38 mm gestellt und Einrasten auf
„Gitter“, sodass ein Haken mit gedrückter `Strg`-Taste in der Vorderansicht auf Lochpositionen
springt.

**In Object Builder:** Die Haken aus `einzelteile/` als eigene P3D-Modelle anlegen und auf der Wand
als Proxys an den Lochpositionen oben platzieren.

## Neu erzeugen

Mit Blender (4.2 oder neuer):

```bash
blender --background --python generate_werkzeugwand.py
```

Mit Vorschaubildern (Cycles, dauert ein paar Minuten):

```bash
blender --background --python generate_werkzeugwand.py -- --render
```

Ohne installiertes Blender geht es auch mit dem `bpy`-Modul (`pip install bpy`, passend zur
Python-Version):

```bash
python generate_werkzeugwand.py --render
```

Größe, Raster, Blechstärke, Drahtstärke und Polygonzahl der Haken (`SEITEN`) stehen als
Konstanten oben im Skript. Bei anderer Größe `SPALTEN` und `REIHEN` ungerade lassen, damit die
Lochpositionen ganze Vielfache von 38 mm bleiben.
