"""
Preview renders of the planter box (Cycles).

blender --background --python render_preview.py -- --out previews
        [--only hero,top,detail] [--samples 128] [--percent 100]

Starts from an empty scene, builds the planter with planter_box.py, adds a
concrete floor, daylight and three cameras, and writes hero.jpg, top.jpg and
detail.jpg into the output folder.
"""

import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import planter_box  # noqa: E402


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def floor_material():
    mat = bpy.data.materials.new("Preview_Concrete")
    n = planter_box.Nodes(mat)
    tc = n.new("ShaderNodeTexCoord")
    co = tc.outputs["Object"]
    blotch = n.noise(co, 2.5, 6.0, 0.6).outputs["Fac"]
    grit = n.noise(co, 220.0, 2.0, 0.5).outputs["Fac"]
    value = n.math("MULTIPLY_ADD", blotch, 0.7, n.math("MULTIPLY", grit, 0.3))
    color = n.ramp(value, [(0.3, planter_box.srgb(128, 126, 120)),
                           (0.7, planter_box.srgb(170, 168, 162))])
    n.bsdf(color, n.math("MULTIPLY_ADD", blotch, 0.2, 0.7), height=grit,
           strength=0.15, distance=0.002)
    return mat


def setup_scene(samples=128, percent=100):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = percent
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 90
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"

    world = bpy.data.worlds.new("Preview_World")
    scene.world = world
    n = planter_box.Nodes(world)
    bg = n.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = planter_box.srgb(196, 210, 226)
    bg.inputs["Strength"].default_value = 0.9
    out = n.new("ShaderNodeOutputWorld")
    n.link(bg.outputs["Background"], out.inputs["Surface"])

    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 3.2
    sun.data.angle = math.radians(4.0)
    sun.data.color = (1.0, 0.95, 0.88)
    sun.rotation_euler = (math.radians(48), 0.0, math.radians(-38))
    scene.collection.objects.link(sun)

    fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", "AREA"))
    fill.data.energy = 120.0
    fill.data.size = 2.0
    fill.location = (1.8, -1.2, 1.6)
    look_at(fill, (0, 0, 0.3))
    scene.collection.objects.link(fill)

    bpy.ops.mesh.primitive_plane_add(size=8.0)
    floor = bpy.context.active_object
    floor.name = "Preview_Floor"
    floor.data.materials.append(floor_material())


def render(name, location, target, lens, out_dir):
    scene = bpy.context.scene
    cam = bpy.data.objects.get("Cam_" + name)
    if cam is None:
        cam = bpy.data.objects.new("Cam_" + name, bpy.data.cameras.new("Cam_" + name))
        scene.collection.objects.link(cam)
    cam.location = location
    cam.data.lens = lens
    look_at(cam, target)
    scene.camera = cam
    scene.render.filepath = os.path.join(out_dir, name + ".jpg")
    bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

    def arg(name, default):
        return argv[argv.index(name) + 1] if name in argv else default

    out_dir = os.path.abspath(arg("--out", "previews"))
    only = arg("--only", "hero,top,detail").split(",")
    os.makedirs(out_dir, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    setup_scene(int(arg("--samples", 128)), int(arg("--percent", 100)))
    planter_box.build()

    shots = {
        "hero": ((-1.25, -1.55, 1.05), (0.0, 0.0, 0.27), 50),
        "top": ((0.0, -0.62, 1.75), (0.0, 0.0, 0.42), 45),
        "detail": ((0.82, -0.62, 0.66), (0.42, -0.2, 0.40), 55),
    }
    for name, (loc, target, lens) in shots.items():
        if name in only:
            render(name, loc, target, lens, out_dir)


main()
