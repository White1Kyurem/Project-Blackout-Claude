"""Kachelbare Texturen für die Werkzeugwand, prozedural mit numpy erzeugt.

Je Material entstehen in texturen/:
    <name>_co.png      Farbe (sRGB)                                   Blender + DayZ
    <name>_nohq.png    Normal Map im DirectX-Format (Grün invertiert)  DayZ
    <name>_smdi.png    R = 1, G = Glanzstärke, B = Glanzschärfe        DayZ
    <name>_normal.png  Normal Map im OpenGL-Format                     Blender
    <name>_rough.png   Rauheit                                        Blender
    <name>_metal.png   Metallisch                                     Blender
    <name>.rvmat       DayZ-Material (Super-Shader), Pfade anpassen

Lochwand_Platte: 1024 px = 1 m, Lochwand_Haken: 512 px = 25 cm.
"""

import os

import bpy
import numpy as np

# Pfad, unter dem die .paa-Dateien im DayZ-Mod liegen (für die .rvmat-Dateien)
DAYZ_PFAD = r"MeinMod\werkzeugwand\data"


def _rauschen(n, beta, rng, f_min=0.0, f_max=None):
    """Kachelbares 1/f-Rauschen (Mittelwert 0, Standardabweichung 1)."""
    f = np.hypot(np.fft.fftfreq(n)[:, None], np.fft.fftfreq(n)[None, :])
    f[0, 0] = 1.0
    amp = f ** (-beta / 2)
    amp[0, 0] = 0.0
    amp[f < f_min] = 0.0
    if f_max is not None:
        amp[f > f_max] = 0.0
    feld = np.fft.ifft2(amp * np.exp(2j * np.pi * rng.random((n, n)))).real
    return (feld - feld.mean()) / feld.std()


def _kratzer(n, anzahl, rng, laenge=(6, 45)):
    """Leicht gebogene, dünne Kratzer, die über den Rand hinweg weiterlaufen."""
    maske = np.zeros((n, n))
    for _ in range(anzahl):
        l = rng.uniform(*laenge)
        t = np.arange(0.0, l, 0.5)
        w = rng.uniform(0, np.pi) + rng.normal(0, 0.003) * t
        x = rng.uniform(0, n) + np.cumsum(np.cos(w)) * 0.5
        y = rng.uniform(0, n) + np.cumsum(np.sin(w)) * 0.5
        staerke = np.sqrt(np.sin(np.pi * t / l)) * rng.uniform(0.2, 0.7)
        ix, iy = np.floor(x).astype(int), np.floor(y).astype(int)
        fx, fy = x - ix, y - iy
        for dx, dy, g in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
                          (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            np.add.at(maske, ((iy + dy) % n, (ix + dx) % n), g * staerke)
    return np.clip(maske, 0.0, 1.0)


def _normal(hoehe, staerke):
    """Normal Map (OpenGL, Grün = +V) aus einer kachelbaren Höhenkarte."""
    dx = (np.roll(hoehe, -1, axis=1) - np.roll(hoehe, 1, axis=1)) / 2
    dy = (np.roll(hoehe, -1, axis=0) - np.roll(hoehe, 1, axis=0)) / 2
    n = np.stack([-dx * staerke, -dy * staerke, np.ones_like(hoehe)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def _speichern(pfad, bild, farbraum):
    """Speichert ein (H, W) oder (H, W, 3) Array mit Werten 0..1 als PNG.

    Zeile 0 ist wie bei Blender-Bildern die unterste Bildzeile.
    """
    bild = np.clip(bild, 0.0, 1.0)
    if bild.ndim == 2:
        bild = np.repeat(bild[..., None], 3, axis=-1)
    h, w = bild.shape[:2]
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = bild
    img = bpy.data.images.new(os.path.basename(pfad), w, h, alpha=False)
    img.colorspace_settings.name = farbraum
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = pfad
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def _lack(n, rng):
    """Taubenblau lackiertes Stahlblech mit Schmutz und Kratzern."""
    flecken = _rauschen(n, 3.2, rng, f_max=0.06)
    korn = _rauschen(n, 0.6, rng, f_min=0.15)
    orangenhaut = _rauschen(n, 2.0, rng, f_min=0.02, f_max=0.2)
    schmutz = np.clip((_rauschen(n, 3.2, rng, f_max=0.03) - 0.5) / 2.0, 0, 1) ** 1.5 * 0.35
    kratzer = _kratzer(n, 140, rng)

    farbe = np.array([0.37, 0.46, 0.55]) * (1 + 0.035 * flecken[..., None]) + 0.010 * korn[..., None]
    farbe = farbe * (1 - schmutz[..., None]) + np.array([0.33, 0.33, 0.31]) * schmutz[..., None]
    farbe = farbe * (1 - kratzer[..., None]) + np.array([0.52, 0.54, 0.55]) * kratzer[..., None]
    rauheit = np.clip(0.42 + 0.03 * korn + 0.30 * schmutz, 0, 1) * (1 - kratzer) + 0.30 * kratzer
    glanz = (0.25 * (1 - 0.6 * schmutz)) * (1 - kratzer) + 0.80 * kratzer
    hoehe = 0.35 * orangenhaut - 1.5 * kratzer
    return farbe, rauheit, kratzer, glanz, _normal(hoehe, 0.12)


def _zink(n, rng):
    """Verzinkter Stahldraht."""
    flecken = _rauschen(n, 3.0, rng, f_max=0.02)
    toenung = _rauschen(n, 3.5, rng, f_max=0.04)
    korn = _rauschen(n, 0.8, rng, f_min=0.1)

    farbe = (np.array([0.70, 0.71, 0.73]) * (1 + 0.04 * flecken[..., None])
             + 0.008 * korn[..., None] + 0.012 * toenung[..., None] * np.array([1.0, 0.4, -0.6]))
    rauheit = np.clip(0.30 + 0.05 * flecken + 0.015 * korn, 0, 1)
    glanz = np.clip(0.80 + 0.08 * flecken, 0, 1)
    return farbe, rauheit, np.ones((n, n)), glanz, _normal(0.3 * korn, 0.05)


def _rvmat(pfad, name, specular, power):
    stufe = """class Stage{nr}
{{
	texture="{textur}";
	uvSource="tex";
	class uvTransform
	{{
		aside[]={{1,0,0}};
		up[]={{0,1,0}};
		dir[]={{0,0,0}};
		pos[]={{0,0,0}};
	}};
}};
"""
    stufen = [
        (1, f"{DAYZ_PFAD}\\{name}_nohq.paa"),
        (2, "#(argb,8,8,3)color(0.5,0.5,0.5,0.5,DT)"),
        (3, "#(argb,8,8,3)color(0,0,0,0,MC)"),
        (4, "#(argb,8,8,3)color(1,1,1,1,AS)"),
        (5, f"{DAYZ_PFAD}\\{name}_smdi.paa"),
    ]
    s = specular
    text = (f"ambient[]={{1,1,1,1}};\ndiffuse[]={{1,1,1,1}};\nforcedDiffuse[]={{0,0,0,0}};\n"
            f"emmisive[]={{0,0,0,0}};\nspecular[]={{{s},{s},{s},1}};\nspecularPower={power};\n"
            f'PixelShaderID="Super";\nVertexShaderID="Super";\n')
    text += "".join(stufe.format(nr=nr, textur=t) for nr, t in stufen)
    text += ('class Stage6\n{\n\ttexture="#(ai,64,64,1)fresnel(1.5,1.22)";\n\tuvSource="none";\n};\n'
             'class Stage7\n{\n\ttexture="dz\\data\\data\\env_land_co.paa";\n'
             '\tuseWorldEnvMap="true";\n\tuvSource="none";\n};\n')
    with open(pfad, "w", newline="\r\n", encoding="utf-8") as f:
        f.write(text)


def erzeuge(ordner):
    """Schreibt alle Texturen und gibt {Material: {Kanal: Pfad}} zurück."""
    os.makedirs(ordner, exist_ok=True)
    rng = np.random.default_rng(1938)
    ergebnis = {}
    for name, funktion, n, specular, power in (("lochwand_platte", _lack, 1024, 0.4, 40),
                                               ("lochwand_haken", _zink, 512, 1.0, 90)):
        farbe, rauheit, metall, glanz, normal = funktion(n, rng)
        pfade = {k: os.path.join(ordner, f"{name}_{k}.png")
                 for k in ("co", "nohq", "smdi", "normal", "rough", "metal")}
        _speichern(pfade["co"], farbe, 'sRGB')
        _speichern(pfade["normal"], normal, 'Non-Color')
        _speichern(pfade["nohq"], normal * np.array([1, -1, 1]) + np.array([0, 1, 0]), 'Non-Color')
        _speichern(pfade["smdi"], np.stack([np.ones_like(glanz), glanz, 1 - rauheit], axis=-1),
                   'Non-Color')
        _speichern(pfade["rough"], rauheit, 'Non-Color')
        _speichern(pfade["metal"], metall, 'Non-Color')
        _rvmat(os.path.join(ordner, f"{name}.rvmat"), name, specular, power)
        ergebnis[name] = pfade
    return ergebnis
