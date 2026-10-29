# Mannequin für DayZ

Komplett neu aufgebaute Schaufensterpuppe in T-Pose auf einer Standplatte.

## Dateien

| Datei | Inhalt |
| --- | --- |
| `Mannequin.fbx` | Modell (ein Mesh, ein Material, Meter-Maßstab, 1,80 m hoch) |
| `Mannequin.blend` | Gleiches Modell als Blender-Datei mit fertigem Material |
| `Mannequin_BaseColor.png` | Farbe (Anthrazit, Platte schwarz), mit eingebackenem Ambient Occlusion |
| `Mannequin_Normal.png` | Normal Map (OpenGL-Format, Y+) |
| `Mannequin_Roughness.png` | Rauheit (Körper satiniert, Platte etwas glänzender) |
| `Mannequin_Metallic.png` | Metallic (komplett 0) |
| `Mannequin_AO.png` | Ambient Occlusion separat |
| `preview/` | Vorschaubilder |

## Kennzahlen

| | |
| --- | --- |
| Vertices (Blender / Object Builder) | **26.124** |
| Vertices inkl. UV-Nähten (Grafikkarte) | **27.526** |
| Dreiecke | 52.232 |
| Höhe | 1,80 m (Füße auf der Platte bei 3 cm) |
| Texturen | 2048 × 2048, ein Material, ein UV-Set |

Beide Vertex-Zahlen liegen unter 30.000.

## Was gemacht wurde

- Kopf, Gesicht und Körper komplett neu: anatomisch korrekter, runder Kopf mit Augen, Nase, Mund
  und Ohren; glatte Oberfläche ohne Knicke oder Löcher.
- Gleiche T-Pose, Größe und Fußstellung wie das Original, Standplatte übernommen (leicht gefast).
- Finger gerade und geschlossen wie bei einer Schaufensterpuppe.
- Kopf ist feiner unterteilt (runde Silhouette), der Rest nutzt ein sauberes Quad-Netz.
- Neue Texturen: satiniertes Anthrazit für die Puppe, mattschwarze Platte.

## Hinweise für DayZ

- Texturen mit **ImageToPAA** / **TexView 2** (DayZ Tools) nach `.paa` konvertieren.
  Übliche Namen: `mannequin_co.paa` (BaseColor), `mannequin_nohq.paa` (Normal),
  `mannequin_smdi.paa` (Specular/Gloss, aus Roughness ableiten: Gloss = 1 − Roughness).
- Die Normal Map ist fast flach (die Form steckt im Mesh). Falls Details in DayZ „falsch herum“
  beleuchtet wirken, den Grünkanal der Normal Map invertieren.
- Für Spielobjekte braucht DayZ zusätzlich LODs, Geometry- und View-Geometry-LODs (Object Builder).

## Lizenz der Ausgangsdaten

Körper, Kopf, Skelett und Gewichte stammen aus dem MakeHuman-Basismodell, das unter **CC0 1.0**
(gemeinfrei) veröffentlicht ist. Es gibt keine Einschränkungen, auch nicht für kommerzielle Mods.
