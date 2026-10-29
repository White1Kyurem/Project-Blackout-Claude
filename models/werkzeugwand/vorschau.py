"""Vorschaubilder für die Werkzeugwand (wird von generate_werkzeugwand.py --render aufgerufen).

Baut eine Betonwand, Licht und Kameras auf und rendert mit Cycles. Die Szene wird
nicht in die .blend gespeichert.
"""

import math
import os

import bpy
from mathutils import Vector

from generate_werkzeugwand import (BREITE, HOEHE, RASTER, REIHEN, SPALTEN, TIEFE, loch_x,
                                   loch_z)


def _schau_auf(obj, ziel):
    richtung = Vector(ziel) - obj.location
    obj.rotation_euler = richtung.to_track_quat('-Z', 'Y').to_euler()


def _kamera(col, name, ort, ziel, linse=50.0, ortho=None):
    cam = bpy.data.cameras.new(name)
    cam.lens = linse
    cam.clip_start = 0.01
    if ortho:
        cam.type = 'ORTHO'
        cam.ortho_scale = ortho
    obj = bpy.data.objects.new(name, cam)
    obj.location = ort
    col.objects.link(obj)
    _schau_auf(obj, ziel)
    return obj


def _licht(col, name, ort, ziel, staerke, groesse):
    licht = bpy.data.lights.new(name, 'AREA')
    licht.energy = staerke
    licht.size = groesse
    obj = bpy.data.objects.new(name, licht)
    obj.location = ort
    col.objects.link(obj)
    _schau_auf(obj, ziel)
    return obj


def _betonwand(col):
    mat = bpy.data.materials.new("Vorschau_Beton")
    if mat.node_tree is None and hasattr(mat, "use_nodes"):
        mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.9
    rauschen = nodes.new("ShaderNodeTexNoise")
    rauschen.inputs["Scale"].default_value = 18.0
    rauschen.inputs["Detail"].default_value = 8.0
    rampe = nodes.new("ShaderNodeValToRGB")
    rampe.color_ramp.elements[0].color = (0.16, 0.16, 0.155, 1)
    rampe.color_ramp.elements[1].color = (0.30, 0.295, 0.285, 1)
    beule = nodes.new("ShaderNodeBump")
    beule.inputs["Strength"].default_value = 0.15
    links.new(rauschen.outputs["Fac"], rampe.inputs["Fac"])
    links.new(rampe.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(rauschen.outputs["Fac"], beule.inputs["Height"])
    links.new(beule.outputs["Normal"], bsdf.inputs["Normal"])

    me = bpy.data.meshes.new("Vorschau_Wand")
    g = 4.0
    me.from_pydata([(-g, 0.0005, -g), (g, 0.0005, -g), (g, 0.0005, g), (-g, 0.0005, g)], [],
                   [(0, 3, 2, 1)])
    me.materials.append(mat)
    obj = bpy.data.objects.new("Vorschau_Wand", me)
    col.objects.link(obj)
    return obj


def _text(col, mat, text, ort, groesse, ausrichtung='CENTER'):
    kurve = bpy.data.curves.new(f"Text_{text}", 'FONT')
    kurve.body = text
    kurve.size = groesse
    kurve.align_x = ausrichtung
    kurve.align_y = 'CENTER'
    kurve.materials.append(mat)
    obj = bpy.data.objects.new(f"Text_{text}", kurve)
    obj.location = ort
    obj.rotation_euler = (math.radians(90), 0, 0)
    col.objects.link(obj)
    return obj


def _leuchtfarbe(name, farbe):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None and hasattr(mat, "use_nodes"):
        mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.remove(nodes["Principled BSDF"])
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = farbe
    emission.inputs["Strength"].default_value = 1.0
    mat.node_tree.links.new(emission.outputs["Emission"], nodes["Material Output"].inputs["Surface"])
    return mat


def _render(szene, kamera, pfad, breite, hoehe):
    szene.camera = kamera
    szene.render.resolution_x = breite
    szene.render.resolution_y = hoehe
    szene.render.filepath = pfad
    bpy.ops.render.render(write_still=True)
    print(f"Gerendert: {pfad}")


def rendern(out, haken, samples, prozent=100):
    szene = bpy.context.scene
    szene.render.engine = 'CYCLES'
    szene.cycles.device = 'CPU'
    szene.cycles.samples = samples
    szene.render.resolution_percentage = prozent
    szene.cycles.use_denoising = True
    szene.render.image_settings.file_format = 'JPEG'
    szene.render.image_settings.quality = 90
    szene.view_settings.view_transform = 'AgX'

    welt = bpy.data.worlds.new("Vorschau_Welt")
    if welt.node_tree is None and hasattr(welt, "use_nodes"):
        welt.use_nodes = True
    hintergrund = welt.node_tree.nodes["Background"]
    hintergrund.inputs["Color"].default_value = (0.42, 0.44, 0.47, 1)
    hintergrund.inputs["Strength"].default_value = 0.25
    szene.world = welt

    col = bpy.data.collections.new("Vorschau")
    szene.collection.children.link(col)
    _betonwand(col)
    _licht(col, "Licht_Haupt", (-1.3, -1.6, 1.5), (0, 0, 0), 130, 1.4)
    _licht(col, "Licht_Fuell", (1.6, -1.8, 0.2), (0, 0, 0), 40, 2.0)

    ordner = os.path.join(out, "vorschau")
    os.makedirs(ordner, exist_ok=True)
    reihe_mitte = loch_z(8)

    kameras = [
        ("vorschau_gesamt.jpg", _kamera(col, "Kamera_Gesamt", (-1.05, -2.2, 0.42),
                                        (0.02, -0.03, -0.02), 45), 1920, 1200),
        ("vorschau_detail.jpg", _kamera(col, "Kamera_Detail", (-0.78, -0.52, reihe_mitte + 0.24),
                                        (-0.36, -0.05, reihe_mitte - 0.02), 50), 1920, 1200),
        ("vorschau_seite.jpg", _kamera(col, "Kamera_Seite", (1.22, -0.62, 0.22),
                                       (0.38, -0.06, 0.0), 40), 1920, 1200),
    ]
    for datei, kamera, b, h in kameras:
        _render(szene, kamera, os.path.join(ordner, datei), b, h)

    # Belegungsplan: Ansicht von vorne mit Spalten-, Reihen- und Hakennummern
    raster_mat = _leuchtfarbe("Vorschau_Text_Raster", (0.02, 0.03, 0.05, 1))
    haken_mat = _leuchtfarbe("Vorschau_Text_Haken", (0.30, 0.01, 0.60, 1))
    y_text = -TIEFE - 0.2
    for s in range(1, SPALTEN + 1):
        _text(col, raster_mat, str(s), (loch_x(s), y_text, loch_z(1) + 0.027), 0.014)
    for r in range(1, REIHEN + 1):
        _text(col, raster_mat, str(r), (loch_x(1) - 0.034, y_text, loch_z(r)), 0.014)
    for nr, obj in enumerate(haken, 1):
        breite = 2 if obj["haken_typ"] == "doppel" else 1
        x = obj.location.x + (breite - 1) * RASTER / 2
        _text(col, haken_mat, f"{nr:02d}", (x, y_text, obj.location.z - 1.5 * RASTER), 0.018)
    for obj in col.objects:
        if obj.type == 'LIGHT':
            obj.hide_render = True
    _licht(col, "Licht_Plan", (0, -2.5, 0.6), (0, 0, 0), 220, 3.0)
    plan = _kamera(col, "Kamera_Plan", (0, -3.0, 0), (0, 0, 0), ortho=BREITE * 1.04)
    _render(szene, plan, os.path.join(ordner, "belegungsplan.jpg"),
            2600, round(2600 * (HOEHE + 0.06) / (BREITE * 1.04)))
