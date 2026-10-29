"""Werkzeugwand (Lochwand) 150 x 80 cm mit Haken – Generator für Blender.

Baut eine Lochwand mit Vierkantlochung 10 x 10 mm im 38-mm-Raster und steckt
Haken hinein, die nach vorne aus der Wand stehen. Jeder Haken bekommt ein Empty
als Markierung für einen Proxy. Danach werden .blend, FBX, OBJ und eine
Positionsliste (CSV) geschrieben.

Ausführen (Blender 4.2 oder neuer):
    blender --background --python generate_werkzeugwand.py
    blender --background --python generate_werkzeugwand.py -- --render

oder mit dem bpy-Modul aus PyPI:
    python generate_werkzeugwand.py [--render] [--out ORDNER]

Einheiten: 1 Blender-Einheit = 1 Meter.
Blender-Achsen: X = rechts, Z = oben, Vorderseite zeigt nach -Y (Frontansicht, Numpad 1).
Ursprung: Mitte der Rückseite, also dort, wo die Wand die Wandfläche berührt.
"""

import argparse
import csv
import math
import os
import sys

import bpy
from mathutils import Vector

# --------------------------------------------------------------------------
# Maße (Meter)
# --------------------------------------------------------------------------
BREITE = 1.50   # Breite der Wand
HOEHE = 0.80    # Höhe der Wand
TIEFE = 0.025   # Wandabstand: Vorderseite bis Wand (abgekanteter Rand)
BLECH = 0.002   # Blechstärke der Platte und des Rands
LOCH = 0.010    # Vierkantloch 10 x 10 mm
RASTER = 0.038  # Lochabstand 38 mm (Mitte zu Mitte)
SPALTEN = 37    # ungerade, damit ein Loch genau auf X = 0 liegt
REIHEN = 19     # ungerade, damit ein Loch genau auf Z = 0 liegt

DRAHT_R = 0.003     # Hakendraht Ø 6 mm
SEITEN = 8          # Kanten des Drahtquerschnitts (Polygonzahl)
ARM_Z = -0.026      # Höhe, an der der Arm an der Steckplatte sitzt (lokal)

# --------------------------------------------------------------------------
# Hakenbelegung: (Typ, Spalte, Reihe)
# Spalte 1..37 von links, Reihe 1..19 von oben. Ein Haken hängt im Loch
# (Spalte, Reihe) und steckt unten im Loch (Spalte, Reihe + 1). Der Doppelhaken
# belegt zusätzlich die Spalte rechts daneben.
# Typen: kurz, lang, doppel, bogen, ring
# --------------------------------------------------------------------------
HAKEN = [
    # obere Reihe: Kabel, Sägen, Hämmer
    ("bogen", 3, 2), ("bogen", 7, 2), ("lang", 12, 2), ("lang", 16, 2),
    ("doppel", 20, 2), ("doppel", 25, 2), ("lang", 30, 2), ("bogen", 35, 2),
    # mittlere Reihe: Schlüssel, Schraubendreher, Zangen
    ("kurz", 3, 8), ("kurz", 5, 8), ("kurz", 7, 8), ("kurz", 9, 8), ("kurz", 11, 8),
    ("ring", 15, 8), ("ring", 17, 8), ("ring", 19, 8), ("ring", 21, 8),
    ("doppel", 25, 8), ("kurz", 29, 8), ("kurz", 31, 8), ("lang", 35, 8),
    # untere Reihe
    ("lang", 4, 14), ("doppel", 8, 14), ("kurz", 13, 14), ("kurz", 15, 14),
    ("bogen", 20, 14), ("ring", 25, 14), ("ring", 27, 14), ("lang", 32, 14),
    ("kurz", 35, 14),
]

HAKEN_TYPEN = ("kurz", "lang", "doppel", "bogen", "ring")

FARBE_PLATTE = (0.125, 0.205, 0.305, 1.0)  # taubenblau lackiert (linear)
FARBE_HAKEN = (0.75, 0.76, 0.78, 1.0)     # verzinkt


def loch_x(spalte):
    return (spalte - (SPALTEN + 1) / 2) * RASTER


def loch_z(reihe):
    return ((REIHEN + 1) / 2 - reihe) * RASTER


# --------------------------------------------------------------------------
# Mesh-Aufbau
# --------------------------------------------------------------------------
class MeshBuilder:
    """Sammelt Flächen; gleiche Positionen innerhalb eines Teils teilen sich einen Vertex."""

    def __init__(self):
        self.verts = []
        self.faces = []
        self.uvs = []
        self.smooth = []
        self._index = {}

    def neues_teil(self):
        self._index = {}

    def _vertex(self, co):
        key = (round(co[0], 6), round(co[1], 6), round(co[2], 6))
        i = self._index.get(key)
        if i is None:
            i = len(self.verts)
            self._index[key] = i
            self.verts.append(key)
        return i

    def flaeche(self, pts, normale=None, uvs=None, smooth=False):
        pts = [Vector(p) for p in pts]
        if normale is not None:
            n = Vector((0.0, 0.0, 0.0))
            for a, b in zip(pts, pts[1:] + pts[:1]):
                n.x += (a.y - b.y) * (a.z + b.z)
                n.y += (a.z - b.z) * (a.x + b.x)
                n.z += (a.x - b.x) * (a.y + b.y)
            if n.dot(Vector(normale)) < 0:
                pts.reverse()
                if uvs is not None:
                    uvs = list(reversed(uvs))
        if uvs is None:
            uvs = [box_uv(p, normale or (0, -1, 0)) for p in pts]
        self.faces.append([self._vertex(p) for p in pts])
        self.uvs.append(uvs)
        self.smooth.append(smooth)

    def quader(self, x0, x1, y0, y1, z0, z1):
        self.neues_teil()
        c = [(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
        for idx, n in (((0, 1, 3, 2), (0, 0, -1)), ((4, 5, 7, 6), (0, 0, 1)),
                       ((0, 1, 5, 4), (0, -1, 0)), ((2, 3, 7, 6), (0, 1, 0)),
                       ((0, 2, 6, 4), (-1, 0, 0)), ((1, 3, 7, 5), (1, 0, 0))):
            self.flaeche([c[i] for i in idx], n)

    def rohr(self, pfad, radius, seiten=SEITEN, geschlossen=False, ref=(1, 0, 0)):
        """Rundes Rohr entlang eines Pfads (Parallel-Transport-Rahmen)."""
        self.neues_teil()
        pfad = [Vector(p) for p in pfad]
        if geschlossen:
            pfad = pfad + [pfad[0]]
        n_pkt = len(pfad)
        tangenten = []
        for i in range(n_pkt):
            if geschlossen and i in (0, n_pkt - 1):
                t = (pfad[1] - pfad[0]).normalized() + (pfad[-1] - pfad[-2]).normalized()
            elif i == 0:
                t = pfad[1] - pfad[0]
            elif i == n_pkt - 1:
                t = pfad[-1] - pfad[-2]
            else:
                t = (pfad[i + 1] - pfad[i]).normalized() + (pfad[i] - pfad[i - 1]).normalized()
            tangenten.append(t.normalized())
        ref = Vector(ref)
        normal = (ref - tangenten[0] * ref.dot(tangenten[0])).normalized()
        ringe, laenge = [], 0.0
        for i, (p, t) in enumerate(zip(pfad, tangenten)):
            if i:
                normal = (normal - t * normal.dot(t)).normalized()
                laenge += (p - pfad[i - 1]).length
            binormal = t.cross(normal)
            ring = [p + radius * (math.cos(2 * math.pi * k / seiten) * normal
                                  + math.sin(2 * math.pi * k / seiten) * binormal)
                    for k in range(seiten)]
            ringe.append((ring, laenge))
        umfang = 2 * math.pi * radius
        for i in range(n_pkt - 1):
            (r0, u0), (r1, u1) = ringe[i], ringe[i + 1]
            mitte = (pfad[i] + pfad[i + 1]) / 2
            for k in range(seiten):
                k2 = (k + 1) % seiten
                quad = [r0[k], r0[k2], r1[k2], r1[k]]
                aussen = sum(quad, Vector()) / 4 - mitte
                v0, v1 = umfang * k / seiten, umfang * (k + 1) / seiten
                self.flaeche(quad, aussen, [(u0, v0), (u0, v1), (u1, v1), (u1, v0)], smooth=True)
        if not geschlossen:
            for (ring, _), richtung in ((ringe[0], -tangenten[0]), (ringe[-1], tangenten[-1])):
                mitte = sum(ring, Vector()) / seiten
                uv = [(0.5 + (q - mitte).dot(richtung.orthogonal().normalized()),
                       0.5 + (q - mitte).dot(richtung.cross(richtung.orthogonal()).normalized()))
                      for q in ring]
                self.flaeche(ring, richtung, uv)

    def mesh(self, name, material):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.verts, [], self.faces)
        uv_layer = me.uv_layers.new(name="UVMap")
        loop_uvs = [c for face in self.uvs for uv in face for c in uv]
        uv_layer.data.foreach_set("uv", loop_uvs)
        me.polygons.foreach_set("use_smooth", self.smooth)
        # Kanten zwischen glatten und flachen Flächen hart machen
        kanten_smooth = {}
        for poly in me.polygons:
            for ek in poly.edge_keys:
                kanten_smooth.setdefault(ek, set()).add(poly.use_smooth)
        scharf = me.attributes.new("sharp_edge", 'BOOLEAN', 'EDGE')
        scharf.data.foreach_set("value", [len(kanten_smooth.get(e.key, ())) != 1 or
                                          not next(iter(kanten_smooth[e.key]))
                                          for e in me.edges])
        me.materials.append(material)
        me.validate(clean_customdata=False)
        me.update()
        return me


def box_uv(p, n):
    """Box-Projektion, 1 UV-Einheit = 1 m (für kachelnde Texturen)."""
    ax = max(range(3), key=lambda i: abs(n[i]))
    if ax == 0:
        return (p[1] + TIEFE, p[2] + HOEHE / 2)
    if ax == 1:
        return (p[0] + BREITE / 2, p[2] + HOEHE / 2)
    return (p[0] + BREITE / 2, p[1] + TIEFE)


def abrunden(punkte, radius, max_schritt=math.radians(22.5)):
    """Ersetzt die Ecken eines Polygonzugs durch Kreisbögen (Biegeradius)."""
    pts = [Vector(p) for p in punkte]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a = (pts[i] - pts[i - 1]).normalized()
        b = (pts[i + 1] - pts[i]).normalized()
        cos_t = max(-1.0, min(1.0, a.dot(b)))
        theta = math.acos(cos_t)
        if theta < 1e-4:
            out.append(pts[i])
            continue
        d = min(radius * math.tan(theta / 2),
                0.5 * (pts[i] - pts[i - 1]).length, 0.5 * (pts[i + 1] - pts[i]).length)
        r = d / math.tan(theta / 2)
        n = (b - a * cos_t).normalized()
        mittelpunkt = pts[i] - a * d + n * r
        schritte = max(2, math.ceil(theta / max_schritt))
        for k in range(schritte + 1):
            phi = theta * k / schritte
            out.append(mittelpunkt + r * (-n * math.cos(phi) + a * math.sin(phi)))
    out.append(pts[-1])
    return out


def baue_platte():
    """Lochblech mit umlaufend nach hinten abgekantetem Rand."""
    m = MeshBuilder()
    w2, h2 = BREITE / 2, HOEHE / 2
    yv, yh = -TIEFE, -TIEFE + BLECH  # Vorderseite, Rückseite des Blechs
    lx = [loch_x(s) for s in range(1, SPALTEN + 1)]
    lz = sorted(loch_z(r) for r in range(1, REIHEN + 1))

    def teilung(lo, hi, mitten):
        out = [lo]
        for c in mitten:
            out += [c - LOCH / 2, c + LOCH / 2]
        return out + [hi]

    xv, zv = teilung(-w2, w2, lx), teilung(-h2, h2, lz)
    xh, zh = teilung(-w2 + BLECH, w2 - BLECH, lx), teilung(-h2 + BLECH, h2 - BLECH, lz)

    # Vorder- und Rückseite des Blechs, Löcher ausgespart
    for a in range(len(xv) - 1):
        for c in range(len(zv) - 1):
            if a % 2 and c % 2:
                continue
            m.flaeche([(xv[a], yv, zv[c]), (xv[a + 1], yv, zv[c]),
                       (xv[a + 1], yv, zv[c + 1]), (xv[a], yv, zv[c + 1])], (0, -1, 0))
            m.flaeche([(xh[a], yh, zh[c]), (xh[a + 1], yh, zh[c]),
                       (xh[a + 1], yh, zh[c + 1]), (xh[a], yh, zh[c + 1])], (0, 1, 0))

    # Lochwände
    for x in lx:
        for z in lz:
            x0, x1, z0, z1 = x - LOCH / 2, x + LOCH / 2, z - LOCH / 2, z + LOCH / 2
            m.flaeche([(x0, yv, z0), (x1, yv, z0), (x1, yh, z0), (x0, yh, z0)], (0, 0, 1))
            m.flaeche([(x0, yv, z1), (x1, yv, z1), (x1, yh, z1), (x0, yh, z1)], (0, 0, -1))
            m.flaeche([(x0, yv, z0), (x0, yv, z1), (x0, yh, z1), (x0, yh, z0)], (1, 0, 0))
            m.flaeche([(x1, yv, z0), (x1, yv, z1), (x1, yh, z1), (x1, yh, z0)], (-1, 0, 0))

    # Abgekanteter Rand: außen, innen und Stirnseite an der Wand (Y = 0)
    for a in range(len(xv) - 1):
        for s, zo, zi in ((1, h2, zh[-1]), (-1, -h2, zh[0])):
            m.flaeche([(xv[a], yv, zo), (xv[a + 1], yv, zo), (xv[a + 1], 0, zo), (xv[a], 0, zo)],
                      (0, 0, s))
            m.flaeche([(xh[a], yh, zi), (xh[a + 1], yh, zi), (xh[a + 1], 0, zi), (xh[a], 0, zi)],
                      (0, 0, -s))
            m.flaeche([(xv[a], 0, zo), (xv[a + 1], 0, zo), (xh[a + 1], 0, zi), (xh[a], 0, zi)],
                      (0, 1, 0))
    for c in range(len(zv) - 1):
        for s, xo, xi in ((1, w2, xh[-1]), (-1, -w2, xh[0])):
            m.flaeche([(xo, yv, zv[c]), (xo, yv, zv[c + 1]), (xo, 0, zv[c + 1]), (xo, 0, zv[c])],
                      (s, 0, 0))
            m.flaeche([(xi, yh, zh[c]), (xi, yh, zh[c + 1]), (xi, 0, zh[c + 1]), (xi, 0, zh[c])],
                      (-s, 0, 0))
            m.flaeche([(xo, 0, zv[c]), (xo, 0, zv[c + 1]), (xi, 0, zh[c + 1]), (xi, 0, zh[c])],
                      (0, 1, 0))
    return m


def baue_haken(typ):
    """Haken im lokalen System: Ursprung = Mitte des oberen Lochs auf der Vorderseite.

    -Y zeigt aus der Wand heraus, das Blech liegt bei 0 <= y <= BLECH.
    Gibt den MeshBuilder und die lokale Proxy-Position zurück.
    """
    m = MeshBuilder()
    spalten = 2 if typ == "doppel" else 1
    for k in range(spalten):
        x = k * RASTER
        m.quader(x - 0.004, x + 0.004, -0.0005, BLECH + 0.003, -0.0048, -0.0033)   # obere Lasche
        m.quader(x - 0.004, x + 0.004, BLECH + 0.0015, BLECH + 0.003, -0.016, -0.0033)  # abgekantet
        m.quader(x - 0.004, x + 0.004, -0.0005, BLECH + 0.004,
                 -RASTER - 0.0048, -RASTER - 0.0033)  # untere Lasche
    m.quader(-0.008, (spalten - 1) * RASTER + 0.008, -0.0017, -0.0002, -RASTER - 0.009, 0.009)

    steigung = math.tan(math.radians(8))
    start = (0, -0.001, ARM_Z)
    if typ in ("kurz", "lang", "doppel"):
        laenge = {"kurz": 0.075, "lang": 0.150, "doppel": 0.100}[typ]
        ende_z = ARM_Z + laenge * steigung
        for k in range(spalten):
            x = k * RASTER
            m.rohr(abrunden([(x, start[1], start[2]), (x, -laenge, ende_z),
                             (x, -laenge - 0.007, ende_z + 0.014)], 0.006), DRAHT_R)
        anteil = 0.6 if typ == "doppel" else 0.7
        proxy = ((spalten - 1) * RASTER / 2, -anteil * laenge,
                 ARM_Z + anteil * laenge * steigung + DRAHT_R)
    elif typ == "bogen":
        m.rohr(abrunden([start, (0, -0.095, ARM_Z + 0.004), (0, -0.088, ARM_Z + 0.058)], 0.022),
               DRAHT_R)
        proxy = (0, -0.080, ARM_Z + DRAHT_R + 0.004)
    elif typ == "ring":
        r_ring, draht = 0.017, 0.0025
        m.rohr([start, (0, -0.041, ARM_Z)], DRAHT_R)
        mitte = Vector((0, -0.040 - r_ring, ARM_Z))
        kreis = [mitte + Vector((math.sin(a), math.cos(a), 0)) * r_ring
                 for a in (2 * math.pi * i / 16 for i in range(16))]
        m.rohr(kreis, draht, geschlossen=True, ref=(0, 0, 1))
        proxy = tuple(mitte)
    else:
        raise ValueError(f"Unbekannter Hakentyp: {typ}")
    return m, Vector(proxy)


def baue_kollision():
    m = MeshBuilder()
    m.quader(-BREITE / 2, BREITE / 2, -TIEFE, 0, -HOEHE / 2, HOEHE / 2)
    return m


# --------------------------------------------------------------------------
# Szene
# --------------------------------------------------------------------------
def material(name, farbe, metallic, rauheit):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = farbe
    mat.metallic = metallic
    mat.roughness = rauheit
    if mat.node_tree is None and hasattr(mat, "use_nodes"):
        mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = farbe
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = rauheit
    return mat


def collection(name, eltern=None):
    col = bpy.data.collections.new(name)
    (eltern or bpy.context.scene.collection).children.link(col)
    return col


def objekt(name, daten, col, ort=(0, 0, 0)):
    obj = bpy.data.objects.new(name, daten)
    obj.location = ort
    col.objects.link(obj)
    return obj


def layer_collection(name):
    return bpy.context.view_layer.layer_collection.children[name]


def pruefe_belegung():
    belegt = {}
    for nr, (typ, spalte, reihe) in enumerate(HAKEN, 1):
        if typ not in HAKEN_TYPEN:
            raise ValueError(f"Haken {nr}: unbekannter Typ {typ!r}")
        breite = 2 if typ == "doppel" else 1
        for s in range(spalte, spalte + breite):
            for r in (reihe, reihe + 1):
                if not (1 <= s <= SPALTEN and 1 <= r <= REIHEN):
                    raise ValueError(f"Haken {nr} ({typ}) liegt außerhalb des Lochrasters")
                if (s, r) in belegt:
                    raise ValueError(f"Haken {nr} und {belegt[(s, r)]} belegen beide "
                                     f"Loch Spalte {s}, Reihe {r}")
                belegt[(s, r)] = nr


def pruefe_abstaende(objekte):
    """Haken dürfen sich in der Ansicht von vorne nicht überschneiden."""
    boxen = []
    for obj in objekte:
        xs = [v.co.x + obj.location.x for v in obj.data.vertices]
        zs = [v.co.z + obj.location.z for v in obj.data.vertices]
        boxen.append((obj.name, min(xs), max(xs), min(zs), max(zs)))
    for i, a in enumerate(boxen):
        for b in boxen[i + 1:]:
            if a[1] < b[2] and b[1] < a[2] and a[3] < b[4] and b[3] < a[4]:
                raise ValueError(f"{a[0]} und {b[0]} überschneiden sich")


def baue_szene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    szene = bpy.context.scene
    szene.unit_settings.system = 'METRIC'
    szene.unit_settings.scale_length = 1.0
    szene.unit_settings.length_unit = 'CENTIMETERS'

    mat_platte = material("Lochwand_Platte", FARBE_PLATTE, 0.0, 0.45)
    mat_haken = material("Lochwand_Haken", FARBE_HAKEN, 1.0, 0.32)

    col_wand = collection("Werkzeugwand")
    col_vorlagen = collection("Haken_Vorlagen")
    col_hilfe = collection("Hilfsobjekte")

    platte = objekt("Lochwand_Platte", baue_platte().mesh("Lochwand_Platte", mat_platte), col_wand)

    meshes, proxies = {}, {}
    for typ in HAKEN_TYPEN:
        builder, proxy = baue_haken(typ)
        meshes[typ] = builder.mesh(f"Haken_{typ}", mat_haken)
        proxies[typ] = proxy
        vorlage = objekt(f"Vorlage_Haken_{typ}", meshes[typ], col_vorlagen)
        leer = objekt(f"Vorlage_Proxy_{typ}", None, col_vorlagen, proxy)
        leer.empty_display_type = 'ARROWS'
        leer.empty_display_size = 0.02
        leer.parent = vorlage

    pruefe_belegung()
    haken_objekte, zeilen = [], []
    for nr, (typ, spalte, reihe) in enumerate(HAKEN, 1):
        ort = Vector((loch_x(spalte), -TIEFE, loch_z(reihe)))
        obj = objekt(f"Haken_{nr:02d}_{typ}", meshes[typ], col_wand, ort)
        obj["haken_typ"] = typ
        obj["spalte"] = spalte
        obj["reihe"] = reihe
        leer = objekt(f"Proxy_{nr:02d}_{typ}", None, col_wand, proxies[typ])
        leer.empty_display_type = 'ARROWS'
        leer.empty_display_size = 0.03
        leer.parent = obj
        haken_objekte.append(obj)
        p = ort + proxies[typ]
        zeilen.append([nr, obj.name, leer.name, typ, spalte, reihe,
                       *(f"{c:.4f}" for c in ort), *(f"{c:.4f}" for c in p),
                       *(f"{c:.4f}" for c in (p.x, p.z, -p.y))])
    pruefe_abstaende(haken_objekte)

    kollision = objekt("Lochwand_Kollision", baue_kollision().mesh("Lochwand_Kollision", mat_platte),
                       col_hilfe)
    kollision.display_type = 'WIRE'
    kollision.hide_render = True
    col_hilfe.hide_render = True
    return platte, haken_objekte, kollision, zeilen


def waehle(objekte):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objekte:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objekte[0]


def exportiere(pfad, objekte, mit_empties=False):
    waehle(objekte)
    if pfad.endswith(".fbx"):
        bpy.ops.export_scene.fbx(
            filepath=pfad, use_selection=True,
            object_types={'MESH', 'EMPTY'} if mit_empties else {'MESH'},
            apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE',
            axis_forward='-Z', axis_up='Y', add_leaf_bones=False, bake_anim=False,
            use_custom_props=True)
    else:
        bpy.ops.wm.obj_export(
            filepath=pfad, export_selected_objects=True, forward_axis='NEGATIVE_Z', up_axis='Y',
            export_uv=True, export_normals=True, export_materials=True,
            export_smooth_groups=True, export_triangulated_mesh=False, path_mode='STRIP')


def dreiecke(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def viewport_raster():
    """Gitter im 3D-Viewport auf das Lochraster stellen, absolutes Einrasten aktivieren."""
    ts = bpy.context.scene.tool_settings
    ts.snap_elements_base = {'GRID'}
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.overlay.grid_scale = RASTER
                        space.overlay.grid_subdivisions = 1
                        space.clip_start = 0.001


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    parser.add_argument("--render", action="store_true", help="Vorschaubilder rendern")
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--prozent", type=int, default=100, help="Auflösung der Vorschau in %%")
    args = parser.parse_args(argv)
    out = os.path.abspath(args.out)
    teile = os.path.join(out, "einzelteile")
    os.makedirs(teile, exist_ok=True)

    platte, haken, kollision, zeilen = baue_szene()

    empties = [c for h in haken for c in h.children]
    for endung in ("fbx", "obj"):
        exportiere(os.path.join(out, f"werkzeugwand.{endung}"), [platte, *haken, *empties],
                   mit_empties=True)
        exportiere(os.path.join(teile, f"lochwand_platte.{endung}"), [platte])
        exportiere(os.path.join(teile, f"lochwand_kollision.{endung}"), [kollision])
        for typ in HAKEN_TYPEN:
            vorlage = bpy.data.objects[f"Vorlage_Haken_{typ}"]
            exportiere(os.path.join(teile, f"haken_{typ}.{endung}"), [vorlage, *vorlage.children],
                       mit_empties=True)

    with open(os.path.join(out, "proxy_positionen.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["nr", "haken", "proxy", "typ", "spalte", "reihe",
                    "haken_blender_x", "haken_blender_y", "haken_blender_z",
                    "proxy_blender_x", "proxy_blender_y", "proxy_blender_z",
                    "proxy_objfbx_x", "proxy_objfbx_y", "proxy_objfbx_z"])
        w.writerows(zeilen)

    layer_collection("Haken_Vorlagen").exclude = True
    layer_collection("Hilfsobjekte").hide_viewport = True
    viewport_raster()
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "werkzeugwand.blend"), compress=True)

    gesamt = dreiecke(platte) + sum(dreiecke(h) for h in haken)
    print(f"Lochwand: {dreiecke(platte)} Dreiecke, {len(haken)} Haken, gesamt {gesamt} Dreiecke")
    for typ in HAKEN_TYPEN:
        print(f"  Haken {typ}: {dreiecke(bpy.data.objects[f'Vorlage_Haken_{typ}'])} Dreiecke")

    if args.render:
        import vorschau
        vorschau.rendern(out, haken, args.samples, args.prozent)


if __name__ == "__main__":
    if "--" in sys.argv:  # blender --background --python generate_werkzeugwand.py -- ...
        argv = sys.argv[sys.argv.index("--") + 1:]
    elif os.path.abspath(sys.argv[0]) == os.path.abspath(__file__):  # python generate_werkzeugwand.py
        argv = sys.argv[1:]
    else:
        argv = []
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main(argv)
