"""
Planter box for two plants – procedural model for Blender 4.2 or newer.

Builds a detailed wooden planter box (corner posts, tongue-and-groove planks,
mitred top rim, divider, bottom slats, liner, soil, pebbles, screws, handles,
rubber feet and plant labels) into its own collection "Planter_Box".

In Blender:  Scripting workspace -> Open -> planter_box.py -> Run Script.
             The box is placed at the 3D cursor. Running the script again
             replaces the previous box; the rest of the scene is not touched.
Headless:    blender --background --python planter_box.py -- --save planter_box.blend
             (--save starts from an empty file and marks the collection as an
             asset, so the saved file can be used from the Asset Browser.)

All dimensions are in metres. The root empty "Planter_Box" sits on the floor
at the centre of the box; the empties "PlantSlot_1" and "PlantSlot_2" mark the
planting holes (parent your plants to them).
"""

import math
import random
import sys

import bpy  # first: bmesh and mathutils need it when bpy runs as a Python module
import bmesh
from mathutils import Matrix, Vector, noise

# --------------------------------------------------------------------------
# Parameters (metres)
# --------------------------------------------------------------------------
P = {
    "length": 1.00,         # outer length of the box body (X)
    "width": 0.50,          # outer width of the box body (Y)
    "clearance": 0.04,      # gap between the floor and the lowest plank
    "rows": 3,              # planks stacked per side
    "plank_h": 0.14,        # plank height
    "plank_t": 0.022,       # plank thickness
    "plank_gap": 0.004,     # shadow gap between stacked planks
    "post": 0.06,           # corner post cross-section
    "inset": 0.008,         # planks sit this far behind the post faces
    "rim_w": 0.08,          # width of the top rim boards
    "rim_t": 0.025,         # thickness of the top rim boards
    "rim_overhang": 0.015,  # rim overhang past the posts
    "soil_drop": 0.055,     # soil surface below the top of the rim
    "pebbles": 14,          # pebbles per bed
    "seed": 7,              # random seed (soil, pebbles, wood grain)
}

COLLECTION = "Planter_Box"

FOOT_H = 0.008       # rubber foot pads under the posts
LINER_GAP = 0.002    # liner distance from the wood
LINER_T = 0.0015     # liner thickness
EMBED = 0.015        # plank ends hidden inside the corner posts
SLAT_T = 0.018       # bottom slat thickness
CLEAT = 0.035        # cleats carrying the bottom slats
DIVIDER_T = 0.018    # divider board thickness
BATTEN_W = 0.06      # outer middle batten on the long sides
BATTEN_T = 0.018


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------
AXIS = {"X": 0, "Y": 1, "Z": 2}


def project_uv(face, uv_layer, grain, u_offset, center):
    """Planar UVs in metres. U follows the wood grain on long faces, V is
    measured from the centre line of the part (the wood shader places the
    tree's pith relative to it)."""
    n = face.normal
    dominant = max(range(3), key=lambda i: abs(n[i]))
    a, b = [i for i in range(3) if i != dominant]
    if AXIS[grain] == b:
        a, b = b, a
    for loop in face.loops:
        co = loop.vert.co
        loop[uv_layer].uv = (co[a] + u_offset, co[b] - center[b])


def finish_faces(bm, faces, grain, mat, rng):
    """Material index and UVs for a freshly built part. Every part gets its
    own random U offset so no two boards show the same grain."""
    uv_layer = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    verts = {v for f in faces for v in f.verts}
    center = sum((v.co for v in verts), Vector()) / max(1, len(verts))
    u_offset = rng.uniform(0.0, 40.0)
    for f in faces:
        f.material_index = mat
        f.normal_update()
        project_uv(f, uv_layer, grain, u_offset, center)
    return faces


def add_part(bm, verts, faces, grain, mat, rng, matrix=None):
    if matrix is not None:
        verts = [matrix @ Vector(v) for v in verts]
    bv = [bm.verts.new(v) for v in verts]
    new_faces = [bm.faces.new([bv[i] for i in f]) for f in faces]
    return finish_faces(bm, new_faces, grain, mat, rng)


def box(bm, lo, hi, grain, mat, rng, matrix=None):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))
    verts = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return add_part(bm, verts, faces, grain, mat, rng, matrix)


def prism(bm, pts, z0, z1, grain, mat, rng, matrix=None):
    """Extrude a counter-clockwise 2D outline from z0 to z1."""
    n = len(pts)
    verts = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return add_part(bm, verts, faces, grain, mat, rng, matrix)


def offset_outline(pts, d):
    """Offset a counter-clockwise outline inwards by d (mitred corners)."""
    out = []
    n = len(pts)
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e1 = (p1 - p0).normalized()
        e2 = (p2 - p1).normalized()
        n1 = Vector((-e1.y, e1.x))
        n2 = Vector((-e2.y, e2.x))
        out.append(p1 + (n1 + n2) * (d / (1.0 + n1.dot(n2))))
    return [(v.x, v.y) for v in out]


def wall(bm, outer, inner, z0, z1, grain, mat, rng):
    """Thin closed wall between two matching outlines (outer and inner)."""
    n = len(outer)
    verts = ([(x, y, z0) for x, y in outer] + [(x, y, z1) for x, y in outer]
             + [(x, y, z0) for x, y in inner] + [(x, y, z1) for x, y in inner])
    o0, o1, i0, i1 = 0, n, 2 * n, 3 * n
    faces = []
    for a in range(n):
        b = (a + 1) % n
        faces.append((o0 + a, o0 + b, o1 + b, o1 + a))   # faces the wood
        faces.append((i0 + b, i0 + a, i1 + a, i1 + b))   # faces the soil
        faces.append((o1 + a, o1 + b, i1 + b, i1 + a))   # top edge
        faces.append((o0 + b, o0 + a, i0 + a, i0 + b))   # bottom edge
    return add_part(bm, verts, faces, grain, mat, rng)


def basis(normal, spin=0.0):
    """Rotation matrix whose Z axis points along normal."""
    z = Vector(normal).normalized()
    x = z.orthogonal().normalized()
    y = z.cross(x)
    rot = Matrix((x, y, z)).transposed().to_4x4()
    return rot @ Matrix.Rotation(spin, 4, "Z")


def screw(bm, location, normal, rng, mat_head=0, mat_recess=1):
    """Countersunk screw head with a cross recess, sitting on a surface."""
    m = Matrix.Translation(location) @ basis(normal, rng.uniform(0.0, math.pi))
    r, h, sides = 0.0042, 0.0009, 12
    rings = [(r, 0.0), (r, h * 0.45), (r * 0.82, h)]
    verts = []
    for rad, z in rings:
        for k in range(sides):
            a = 2.0 * math.pi * k / sides
            verts.append((rad * math.cos(a), rad * math.sin(a), z))
    faces = [tuple(reversed(range(sides)))]
    for ring in range(len(rings) - 1):
        s0, s1 = ring * sides, (ring + 1) * sides
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((s0 + k, s0 + k2, s1 + k2, s1 + k))
    faces.append(tuple(range((len(rings) - 1) * sides, len(rings) * sides)))
    add_part(bm, verts, faces, "X", mat_head, rng, m)
    for spin in (0.0, math.pi / 2):
        rm = m @ Matrix.Rotation(spin, 4, "Z")
        box(bm, (-0.0029, -0.00055, h - 0.0002), (0.0029, 0.00055, h + 0.00004),
            "X", mat_recess, rng, rm)


def tube(bm, path, radius, sides, mat, rng):
    """Sweep a circle along a polyline (parallel transport frames)."""
    path = [Vector(p) for p in path]
    rings, nrm = [], None
    for i, p in enumerate(path):
        if i == 0:
            t = path[1] - path[0]
        elif i == len(path) - 1:
            t = path[-1] - path[-2]
        else:
            t = (path[i + 1] - path[i]).normalized() + (path[i] - path[i - 1]).normalized()
        t.normalize()
        nrm = t.orthogonal() if nrm is None else nrm - t * nrm.dot(t)
        nrm.normalize()
        b = t.cross(nrm)
        rings.append([p + (nrm * math.cos(a) + b * math.sin(a)) * radius
                      for a in (2.0 * math.pi * k / sides for k in range(sides))])
    verts = [v for ring in rings for v in ring]
    faces = []
    for i in range(len(rings) - 1):
        s0, s1 = i * sides, (i + 1) * sides
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((s0 + k, s0 + k2, s1 + k2, s1 + k))
    faces.append(tuple(reversed(range(sides))))
    last = (len(rings) - 1) * sides
    faces.append(tuple(range(last, last + sides)))
    return add_part(bm, verts, faces, "X", mat, rng)


def mark_sharp(bm, angle_deg=35.0):
    """Smooth shading everywhere, sharp edges above the given angle."""
    limit = math.radians(angle_deg)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        if len(e.link_faces) != 2:
            e.smooth = False
        else:
            f1, f2 = e.link_faces
            e.smooth = f1.normal.angle(f2.normal, 0.0) < limit


# --------------------------------------------------------------------------
# Materials
# --------------------------------------------------------------------------
def srgb(r, g, b):
    """sRGB 0-255 to linear RGBA."""
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (lin(r), lin(g), lin(b), 1.0)


class Nodes:
    """Tiny wrapper to keep the node setups readable."""

    def __init__(self, mat):
        if mat.node_tree is None:  # Blender 4.x; 5.x always has a node tree
            mat.use_nodes = True
        self.tree = mat.node_tree
        self.tree.nodes.clear()
        self.x = 0

    def new(self, kind, **props):
        node = self.tree.nodes.new(kind)
        node.location = (self.x, 0)
        self.x += 220
        for key, value in props.items():
            setattr(node, key, value)
        return node

    def link(self, out, inp):
        self.tree.links.new(out, inp)

    def math(self, op, a, b=None, c=None):
        node = self.new("ShaderNodeMath", operation=op)
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                node.inputs[i].default_value = v
            else:
                self.link(v, node.inputs[i])
        return node.outputs[0]

    def scale(self, vec, s):
        node = self.new("ShaderNodeVectorMath", operation="MULTIPLY")
        self.link(vec, node.inputs[0])
        node.inputs[1].default_value = s
        return node.outputs[0]

    def noise(self, vec, scale, detail=2.0, rough=0.5, distortion=0.0):
        node = self.new("ShaderNodeTexNoise")
        self.link(vec, node.inputs["Vector"])
        node.inputs["Scale"].default_value = scale
        node.inputs["Detail"].default_value = detail
        node.inputs["Roughness"].default_value = rough
        node.inputs["Distortion"].default_value = distortion
        return node

    def voronoi(self, vec, scale, randomness=1.0):
        node = self.new("ShaderNodeTexVoronoi")
        self.link(vec, node.inputs["Vector"])
        node.inputs["Scale"].default_value = scale
        node.inputs["Randomness"].default_value = randomness
        return node

    def ramp(self, fac, stops):
        node = self.new("ShaderNodeValToRGB")
        self.link(fac, node.inputs["Fac"])
        elems = node.color_ramp.elements
        elems[0].position, elems[0].color = stops[0]
        elems[1].position, elems[1].color = stops[-1]
        for pos, col in stops[1:-1]:
            elems.new(pos).color = col
        return node.outputs["Color"]

    def bsdf(self, color, roughness, metallic=0.0, height=None, strength=0.2,
             distance=0.002):
        node = self.new("ShaderNodeBsdfPrincipled")
        for name, value in (("Base Color", color), ("Roughness", roughness),
                            ("Metallic", metallic)):
            if isinstance(value, (int, float, tuple)):
                node.inputs[name].default_value = value
            else:
                self.link(value, node.inputs[name])
        if height is not None:
            bump = self.new("ShaderNodeBump")
            bump.inputs["Strength"].default_value = strength
            bump.inputs["Distance"].default_value = distance
            self.link(height, bump.inputs["Height"])
            self.link(bump.outputs["Normal"], node.inputs["Normal"])
        out = self.new("ShaderNodeOutputMaterial")
        self.link(node.outputs["BSDF"], out.inputs["Surface"])
        return node

    def uv(self):
        node = self.new("ShaderNodeUVMap")
        node.uv_map = "UVMap"
        return node.outputs["UV"]


def get_material(name, viewport):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = viewport
    return mat


def wood_material():
    mat = get_material("Planter_Wood", srgb(170, 132, 92))
    n = Nodes(mat)
    uv = n.uv()
    sep = n.new("ShaderNodeSeparateXYZ")
    n.link(uv, sep.inputs["Vector"])
    u, v = sep.outputs["X"], sep.outputs["Y"]

    def along(scale, seed):
        """Slow noise along the board; U offsets make it random per board."""
        vec = n.new("ShaderNodeCombineXYZ")
        n.link(n.math("MULTIPLY", u, scale), vec.inputs["X"])
        vec.inputs["Y"].default_value = seed
        return n.noise(vec.outputs["Vector"], 1.0, 2.0, 0.5).outputs["Fac"]

    # growth rings: distance to the pith of the log the board was sawn from.
    # The pith wanders sideways and in depth, which draws the arches.
    pith_v = n.math("MULTIPLY_ADD", along(0.12, 3.7), 0.5, -0.25)
    depth = n.math("MAXIMUM", n.math("MULTIPLY_ADD", along(0.6, 11.3), 0.32, -0.1), 0.012)
    ring_vec = n.new("ShaderNodeCombineXYZ")
    n.link(n.math("MULTIPLY", u, 0.05), ring_vec.inputs["X"])
    n.link(n.math("SUBTRACT", v, pith_v), ring_vec.inputs["Y"])
    n.link(depth, ring_vec.inputs["Z"])
    wave = n.new("ShaderNodeTexWave", wave_type="RINGS", rings_direction="X",
                 wave_profile="SAW")
    n.link(ring_vec.outputs["Vector"], wave.inputs["Vector"])
    wave.inputs["Scale"].default_value = 50.0
    wave.inputs["Distortion"].default_value = 2.5
    wave.inputs["Detail"].default_value = 2.0
    wave.inputs["Detail Scale"].default_value = 1.0
    rings = n.math("POWER", wave.outputs["Fac"], 4.0)
    # fine fibres: noise stretched along the grain
    fibres = n.noise(n.scale(uv, (3.0, 260.0, 3.0)), 1.0, 6.0, 0.7).outputs["Fac"]
    # broad light/dark streaks
    streaks = n.noise(n.scale(uv, (0.8, 10.0, 0.8)), 1.0, 3.0, 0.5).outputs["Fac"]
    grain = n.math("MULTIPLY_ADD", rings, 0.5,
                   n.math("MULTIPLY_ADD", fibres, 0.25, n.math("MULTIPLY", streaks, 0.35)))
    color = n.ramp(grain, [(0.2, srgb(204, 160, 108)), (0.45, srgb(182, 134, 86)),
                           (0.75, srgb(146, 100, 60)), (1.0, srgb(118, 78, 44))])
    # per-board tint
    tint = along(0.02, 23.1)
    hsv = n.new("ShaderNodeHueSaturation")
    n.link(color, hsv.inputs["Color"])
    n.link(n.math("MULTIPLY_ADD", tint, 0.6, 0.7), hsv.inputs["Value"])
    n.link(n.math("MULTIPLY_ADD", tint, 0.4, 0.75), hsv.inputs["Saturation"])
    rough = n.math("MULTIPLY_ADD", grain, 0.25, 0.6)
    n.bsdf(hsv.outputs["Color"], rough, height=n.math("MULTIPLY_ADD", rings, 0.3, fibres),
           strength=0.04, distance=0.0008)
    return mat


def soil_material():
    mat = get_material("Planter_Soil", srgb(52, 38, 28))
    n = Nodes(mat)
    uv = n.uv()
    clumps = n.voronoi(uv, 70.0).outputs["Distance"]
    large = n.noise(uv, 9.0, 4.0, 0.6).outputs["Fac"]
    fine = n.noise(uv, 160.0, 2.0, 0.5).outputs["Fac"]
    value = n.math("MULTIPLY_ADD", large, 0.55, n.math("MULTIPLY", fine, 0.3))
    value = n.math("SUBTRACT", value, n.math("MULTIPLY", clumps, 0.25))
    value = n.math("MINIMUM", n.math("MAXIMUM", value, 0.0), 0.84)
    # perlite specks, as in bagged potting soil
    specks = n.voronoi(uv, 140.0).outputs["Distance"]
    speck_mask = n.math("MULTIPLY", n.math("LESS_THAN", specks, 0.09),
                        n.math("GREATER_THAN", fine, 0.5))
    value = n.math("MAXIMUM", value, speck_mask)
    color = n.ramp(value, [(0.15, srgb(28, 19, 13)), (0.5, srgb(48, 34, 24)),
                           (0.84, srgb(82, 60, 42)), (0.92, srgb(226, 224, 216))])
    # "wet" vertex attribute: watered soil around the plants is darker and shinier
    wet = n.new("ShaderNodeAttribute", attribute_name="wet").outputs["Fac"]
    hsv = n.new("ShaderNodeHueSaturation")
    n.link(color, hsv.inputs["Color"])
    n.link(n.math("MULTIPLY_ADD", wet, -0.55, 1.0), hsv.inputs["Value"])
    height = n.math("MULTIPLY_ADD", clumps, 0.6, large)
    n.bsdf(hsv.outputs["Color"], n.math("MULTIPLY_ADD", wet, -0.15, 0.93), height=height,
           strength=0.45, distance=0.004)
    return mat


def liner_material():
    mat = get_material("Planter_Liner", srgb(18, 18, 18))
    n = Nodes(mat)
    uv = n.uv()
    weave = n.noise(uv, 90.0, 3.0, 0.5).outputs["Fac"]
    wrinkles = n.noise(uv, 6.0, 2.0, 0.5).outputs["Fac"]
    height = n.math("MULTIPLY_ADD", weave, 0.3, wrinkles)
    n.bsdf(srgb(16, 16, 17), n.math("MULTIPLY_ADD", weave, 0.15, 0.48),
           height=height, strength=0.25, distance=0.002)
    return mat


def stone_material():
    mat = get_material("Planter_Stone", srgb(128, 122, 112))
    n = Nodes(mat)
    uv = n.uv()
    large = n.noise(uv, 30.0, 4.0, 0.6).outputs["Fac"]
    grit = n.noise(uv, 600.0, 2.0, 0.5).outputs["Fac"]
    value = n.math("MULTIPLY_ADD", large, 0.7, n.math("MULTIPLY", grit, 0.3))
    color = n.ramp(value, [(0.3, srgb(70, 64, 58)), (0.55, srgb(112, 104, 94)),
                           (0.8, srgb(150, 140, 126))])
    n.bsdf(color, 0.72, height=n.math("ADD", large, grit), strength=0.3,
           distance=0.001)
    return mat


def metal_material():
    mat = get_material("Planter_Metal", srgb(170, 172, 175))
    n = Nodes(mat)
    uv = n.uv()
    # galvanised steel: visible zinc "spangle" cells
    spangle = n.voronoi(uv, 260.0).outputs["Color"]
    smudge = n.noise(uv, 40.0, 3.0, 0.5).outputs["Fac"]
    rough = n.math("MULTIPLY_ADD", spangle, 0.18,
                   n.math("MULTIPLY_ADD", smudge, 0.15, 0.2))
    n.bsdf(srgb(186, 188, 192), rough, metallic=1.0, height=smudge,
           strength=0.05, distance=0.001)
    return mat


def flat_material(name, rgb, roughness, metallic=0.0):
    mat = get_material(name, srgb(*rgb))
    n = Nodes(mat)
    n.bsdf(srgb(*rgb), roughness, metallic=metallic)
    return mat


def build_materials():
    return {
        "wood": wood_material(),
        "soil": soil_material(),
        "liner": liner_material(),
        "stone": stone_material(),
        "metal": metal_material(),
        "recess": flat_material("Planter_Metal_Dark", (22, 22, 24), 0.6, 1.0),
        "rubber": flat_material("Planter_Rubber", (14, 14, 14), 0.85),
        "label": flat_material("Planter_Label", (232, 232, 226), 0.42),
    }


# --------------------------------------------------------------------------
# Planter parts
# --------------------------------------------------------------------------
class Dims:
    def __init__(self, p):
        self.L, self.W = p["length"], p["width"]
        self.t, self.post, self.inset = p["plank_t"], p["post"], p["inset"]
        self.ph, self.gap, self.rows = p["plank_h"], p["plank_gap"], p["rows"]
        self.clear = p["clearance"]
        self.z_top = self.clear + self.rows * self.ph + (self.rows - 1) * self.gap
        self.rim_w, self.rim_t, self.over = p["rim_w"], p["rim_t"], p["rim_overhang"]
        self.z_rim = self.z_top + self.rim_t
        # inner faces of the planks and of the corner posts
        self.xi = self.L / 2 - self.inset - self.t
        self.yi = self.W / 2 - self.inset - self.t
        self.xp = self.L / 2 - self.post
        self.yp = self.W / 2 - self.post
        self.z_slat = self.clear + CLEAT + SLAT_T  # top of the bottom slats
        self.z_soil = self.z_rim - p["soil_drop"]
        self.z_liner = self.z_top - 0.006
        self.z_divider = self.z_top - 0.008

    def interior(self):
        """Inside outline of the walls, notched around the corner posts."""
        xi, yi, xp, yp = self.xi, self.yi, self.xp, self.yp
        return [(-xp, -yi), (xp, -yi), (xp, -yp), (xi, -yp), (xi, yp), (xp, yp),
                (xp, yi), (-xp, yi), (-xp, yp), (-xi, yp), (-xi, -yp), (-xp, -yp)]

    def row(self, r):
        z0 = self.clear + r * (self.ph + self.gap)
        return z0, z0 + self.ph


def build_wood(bm, d, rng):
    L, W, t = d.L, d.W, d.t
    # corner posts
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(bm, (sx * d.xp, sy * d.yp, FOOT_H), (sx * L / 2, sy * W / 2, d.z_top),
                "Z", 0, rng)
    # tongue-and-groove planks; the tongue fills the shadow gap from behind
    tongue_t = t * 0.35
    for r in range(d.rows):
        z0, z1 = d.row(r)
        tongue = r < d.rows - 1
        for s in (-1, 1):
            yo, yin = s * (W / 2 - d.inset), s * (W / 2 - d.inset - t)
            x_end = d.xp + EMBED
            box(bm, (-x_end, yo, z0), (x_end, yin, z1), "X", 0, rng)
            if tongue:
                yc = (yo + yin) / 2
                box(bm, (-x_end + 0.01, yc - tongue_t / 2, z1 - 0.002),
                    (x_end - 0.01, yc + tongue_t / 2, z1 + d.gap + 0.008), "X", 0, rng)
            xo, xin = s * (L / 2 - d.inset), s * (L / 2 - d.inset - t)
            y_end = d.yp + EMBED
            box(bm, (xo, -y_end, z0), (xin, y_end, z1), "Y", 0, rng)
            if tongue:
                xc = (xo + xin) / 2
                box(bm, (xc - tongue_t / 2, -y_end + 0.01, z1 - 0.002),
                    (xc + tongue_t / 2, y_end - 0.01, z1 + d.gap + 0.008), "Y", 0, rng)
    # outer middle battens on the long sides
    for s in (-1, 1):
        y0 = s * (W / 2 - d.inset)
        box(bm, (-BATTEN_W / 2, y0, d.clear + 0.012),
            (BATTEN_W / 2, y0 + s * BATTEN_T, d.z_top), "Z", 0, rng)
    # mitred top rim with a hairline gap at the joints
    xo, yo = L / 2 + d.over, W / 2 + d.over
    xn, yn = xo - d.rim_w, yo - d.rim_w
    g = 0.0015
    for s in (-1, 1):
        long_pts = [(-xo + g, yo), (-xn + g, yn), (xn - g, yn), (xo - g, yo)]
        short_pts = [(xo, -yo + g), (xo, yo - g), (xn, yn - g), (xn, -yn + g)]
        if s < 0:
            long_pts = [(-x, -y) for x, y in long_pts]
            short_pts = [(-x, -y) for x, y in short_pts]
        prism(bm, long_pts, d.z_top, d.z_rim, "X", 0, rng)
        prism(bm, short_pts, d.z_top, d.z_rim, "Y", 0, rng)
    # cleats and bottom slats (gaps let water drain)
    for s in (-1, 1):
        box(bm, (-d.xp, s * d.yi, d.clear), (d.xp, s * (d.yi - 0.028), d.clear + CLEAT),
            "X", 0, rng)
    span = 2 * (d.xp - 0.005)
    count = max(2, int(span / 0.095))
    slat_w = 0.085
    step = (span - slat_w) / (count - 1)
    for i in range(count):
        x0 = -span / 2 + i * step
        box(bm, (x0, -d.yi + 0.001, d.clear + CLEAT), (x0 + slat_w, d.yi - 0.001, d.z_slat),
            "Y", 0, rng)
    # divider: three boards splitting the box into two beds
    y_div = d.yi - LINER_GAP - LINER_T
    h = (d.z_divider - d.z_slat - 2 * 0.003) / 3
    for i in range(3):
        z0 = d.z_slat + i * (h + 0.003)
        box(bm, (-DIVIDER_T / 2, -y_div, z0), (DIVIDER_T / 2, y_div, z0 + h), "Y", 0, rng)


def build_liner(bm, d, rng):
    poly = d.interior()
    wall(bm, offset_outline(poly, LINER_GAP), offset_outline(poly, LINER_GAP + LINER_T),
         d.z_slat, d.z_liner, "X", 0, rng)


def bed_bounds(d, side):
    """x range, y range and post notch of one bed (side -1 left, +1 right)."""
    m = LINER_GAP + LINER_T
    x_out, x_in = side * (d.xi - m), side * DIVIDER_T / 2
    return (min(x_out, x_in), max(x_out, x_in)), (-(d.yi - m), d.yi - m), \
        (d.xp - m, d.yp - m)


def soil_height(d, x, y, cx, cy, seed):
    """Soil surface: loose noise, a planting hole and a watering ring."""
    p = Vector((x * 9.0 + seed, y * 9.0 + seed * 1.7, 0.3))
    h = noise.fractal(p, 0.6, 2.0, 4) * 0.004
    h += noise.noise(Vector((x * 40.0 + seed, y * 40.0, 1.1))) * 0.0012
    r = math.hypot(x - cx, y - cy)
    h -= 0.02 * math.exp(-((r - 0.075) / 0.032) ** 2)    # watering ring
    h += 0.008 * math.exp(-(r / 0.04) ** 2)              # root ball
    h -= 0.014 * math.exp(-(r / 0.018) ** 2)             # planting hole
    return d.z_soil + h


def soil_wetness(x, y, cx, cy, seed):
    """Freshly watered, darker soil around the planting hole (0..1)."""
    r = math.hypot(x - cx, y - cy)
    r *= 1.0 + 0.25 * noise.noise(Vector((x * 14.0, y * 14.0, seed)))
    return max(0.0, min(1.0, 1.4 - r / 0.1))


def axis_ticks(a, b, cuts, step):
    """Grid coordinates from a to b that include every cut position."""
    marks = sorted({a, b, *[c for c in cuts if a < c < b]})
    ticks = [marks[0]]
    for m0, m1 in zip(marks, marks[1:]):
        n = max(1, round((m1 - m0) / step))
        ticks += [m0 + (m1 - m0) * k / n for k in range(1, n + 1)]
    return ticks


def build_soil(bm, d, rng, seed):
    slots = []
    wet = bm.verts.layers.float.new("wet")
    for side in (-1, 1):
        (x0, x1), (y0, y1), (nx, ny) = bed_bounds(d, side)
        cx, cy = (x0 + x1) / 2, 0.0
        xs = axis_ticks(x0, x1, (-nx, nx), 0.012)
        ys = axis_ticks(y0, y1, (-ny, ny), 0.012)
        grid = {}

        def vert(i, j):
            if (i, j) not in grid:
                x, y = xs[i], ys[j]
                v = bm.verts.new((x, y, soil_height(d, x, y, cx, cy, seed)))
                v[wet] = soil_wetness(x, y, cx, cy, seed)
                grid[i, j] = v
            return grid[i, j]

        top = []
        for i in range(len(xs) - 1):
            for j in range(len(ys) - 1):
                mx, my = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
                if abs(mx) > nx and abs(my) > ny:
                    continue  # corner post
                top.append(bm.faces.new((vert(i, j), vert(i + 1, j),
                                         vert(i + 1, j + 1), vert(i, j + 1))))
        # close the bed: skirt down to the bottom slats plus a floor
        rim = list({e for f in top for e in f.edges if e.is_boundary})
        geom = bmesh.ops.extrude_edge_only(bm, edges=rim)["geom"]
        for v in geom:
            if isinstance(v, bmesh.types.BMVert):
                v.co.z = d.z_slat
        sides = [g for g in geom if isinstance(g, bmesh.types.BMFace)]
        bottom = [g for g in geom if isinstance(g, bmesh.types.BMEdge) and g.is_boundary]
        floor = bmesh.ops.holes_fill(bm, edges=bottom, sides=0)["faces"]
        faces = top + sides + floor
        bmesh.ops.recalc_face_normals(bm, faces=faces)
        finish_faces(bm, faces, "X", 0, rng)
        slots.append(((x0, x1), (y0, y1), (nx, ny), (cx, cy)))
    return slots


def label_spot(cx, cy):
    """Where the plant label of a bed is stuck into the soil."""
    return cx + (0.11 if cx < 0 else -0.11), cy - 0.13


def build_pebbles(bm, d, rng, slots, seed, count):
    for (x0, x1), (y0, y1), (nx, ny), (cx, cy) in slots:
        placed = 0
        tries = 0
        while placed < count and tries < count * 50:
            tries += 1
            x = rng.uniform(x0 + 0.02, x1 - 0.02)
            y = rng.uniform(y0 + 0.02, y1 - 0.02)
            if math.hypot(x - cx, y - cy) < 0.115:
                continue
            if abs(x) > nx - 0.015 and abs(y) > ny - 0.015:
                continue
            lx, ly = label_spot(cx, cy)
            if math.hypot(x - lx, y - ly) < 0.03:
                continue
            size = rng.uniform(0.005, 0.012)
            scale = Vector((size * rng.uniform(1.0, 1.5), size, size * rng.uniform(0.5, 0.8)))
            z = soil_height(d, x, y, cx, cy, seed) + scale.z * 0.3
            m = (Matrix.Translation((x, y, z))
                 @ Matrix.Rotation(rng.uniform(0, math.tau), 4, "Z")
                 @ Matrix.Rotation(rng.uniform(-0.3, 0.3), 4, "X")
                 @ Matrix.Diagonal(scale.to_4d()))
            res = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0, matrix=m)
            verts = res["verts"]
            jitter = rng.uniform(0, 100)
            for v in verts:
                local = (v.co - Vector((x, y, z)))
                v.co += local * (noise.noise(local * 160.0 + Vector((jitter, 0, 0))) * 0.35)
            faces = list({f for v in verts for f in v.link_faces})
            finish_faces(bm, faces, "X", 0, rng)
            placed += 1


def build_hardware(bm, d, rng):
    """Galvanised screws and handles (material 0, screw recesses 1) and
    rubber feet (2)."""
    L, W = d.L, d.W
    up = Vector((0, 0, 1))
    # rubber feet under the posts
    pad = d.post * 0.42
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * (L / 2 - d.post / 2), sy * (W / 2 - d.post / 2)
            box(bm, (cx - pad, cy - pad, 0.0), (cx + pad, cy + pad, FOOT_H), "X", 2, rng)
    # rim screws: one per board over every post, one into each middle batten
    for sx in (-1, 1):
        for sy in (-1, 1):
            screw(bm, Vector((sx * (d.xp + 0.012), sy * (W / 2 - 0.016), d.z_rim)), up, rng)
            screw(bm, Vector((sx * (L / 2 - 0.016), sy * (d.yp + 0.012), d.z_rim)), up, rng)
    for s in (-1, 1):
        screw(bm, Vector((0.0, s * (W / 2 - d.inset + BATTEN_T / 2), d.z_rim)), up, rng)
    # two screws per plank through the middle battens
    for s in (-1, 1):
        y = s * (W / 2 - d.inset + BATTEN_T)
        for r in range(d.rows):
            z0, z1 = d.row(r)
            for dz in (-0.035, 0.035):
                screw(bm, Vector((0.0, y, (z0 + z1) / 2 + dz)), Vector((0, s, 0)), rng)
    # handles on the short sides
    span, depth, rc, plate_t = 0.13, 0.034, 0.012, 0.004
    z0, z1 = d.row(d.rows - 1)
    zh = (z0 + z1) / 2
    path2d = [(-span / 2, plate_t)]
    for k in range(7):
        a = math.pi - (math.pi / 2) * k / 6
        path2d.append((-span / 2 + rc + rc * math.cos(a), depth - rc + rc * math.sin(a)))
    for k in range(7):
        a = math.pi / 2 - (math.pi / 2) * k / 6
        path2d.append((span / 2 - rc + rc * math.cos(a), depth - rc + rc * math.sin(a)))
    path2d.append((span / 2, plate_t))
    for s in (-1, 1):
        rot = Matrix.Rotation(0.0 if s > 0 else math.pi, 4, "Z")
        face_x = L / 2 - d.inset
        path = [rot @ Vector((face_x + w, u, zh)) for u, w in path2d]
        tube(bm, path, 0.0055, 12, 0, rng)
        for u in (-span / 2, span / 2):
            lo = rot @ Vector((face_x, u - 0.015, zh - 0.022))
            hi = rot @ Vector((face_x + plate_t, u + 0.015, zh + 0.022))
            box(bm, lo, hi, "X", 0, rng)
            for dz in (-0.014, 0.014):
                p = rot @ Vector((face_x + plate_t, u, zh + dz))
                screw(bm, p, rot @ Vector((1, 0, 0)), rng)


def build_labels(bm, d, rng, slots):
    outline = [(0.0, 0.0), (0.008, 0.022), (0.008, 0.126), (0.006, 0.13),
               (-0.006, 0.13), (-0.008, 0.126), (-0.008, 0.022)]
    for _, _, _, (cx, cy) in slots:
        x, y = label_spot(cx, cy)
        m = (Matrix.Translation((x, y, d.z_soil - 0.045))
             @ Matrix.Rotation(rng.uniform(-0.35, 0.35), 4, "Z")
             @ Matrix.Rotation(math.radians(80), 4, "X"))
        prism(bm, outline, -0.0006, 0.0006, "Y", 0, rng, m)


# --------------------------------------------------------------------------
# Scene assembly
# --------------------------------------------------------------------------
def remove_collection(name):
    coll = bpy.data.collections.get(name)
    if coll is None:
        return
    for child in list(coll.children):
        remove_collection(child.name)
    for obj in list(coll.objects):
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if isinstance(data, bpy.types.Mesh) and data.users == 0:
            bpy.data.meshes.remove(data)
    bpy.data.collections.remove(coll)


def make_object(name, bm, materials, coll, parent, sharp_angle=35.0):
    mark_sharp(bm, sharp_angle)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for mat in materials:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    obj.parent = parent
    return obj


def add_bevel(obj, width, segments, angle=30.0):
    mod = obj.modifiers.new("Bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(angle)
    mod.use_clamp_overlap = True
    mod.harden_normals = True
    return mod


def build(params=None, location=None):
    p = dict(P, **(params or {}))
    d = Dims(p)
    rng = random.Random(p["seed"])
    seed = p["seed"] * 13.37
    mats = build_materials()

    remove_collection(COLLECTION)
    coll = bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(coll)

    root = bpy.data.objects.new(COLLECTION, None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.3
    coll.objects.link(root)
    if location is not None:
        root.location = location

    bm = bmesh.new()
    build_wood(bm, d, rng)
    wood = make_object("Planter_Wood", bm, [mats["wood"]], coll, root)
    add_bevel(wood, 0.002, 2)

    bm = bmesh.new()
    build_liner(bm, d, rng)
    make_object("Planter_Liner", bm, [mats["liner"]], coll, root)

    bm = bmesh.new()
    slots = build_soil(bm, d, rng, seed)
    make_object("Planter_Soil", bm, [mats["soil"]], coll, root, sharp_angle=60.0)

    bm = bmesh.new()
    build_pebbles(bm, d, rng, slots, seed, p["pebbles"])
    make_object("Planter_Pebbles", bm, [mats["stone"]], coll, root, sharp_angle=80.0)

    bm = bmesh.new()
    build_hardware(bm, d, rng)
    hardware = make_object("Planter_Hardware", bm,
                           [mats["metal"], mats["recess"], mats["rubber"]], coll, root)
    add_bevel(hardware, 0.0005, 1, angle=40.0)

    bm = bmesh.new()
    build_labels(bm, d, rng, slots)
    labels = make_object("Planter_Labels", bm, [mats["label"]], coll, root)
    add_bevel(labels, 0.0004, 1)

    for i, (_, _, _, (cx, cy)) in enumerate(slots, start=1):
        slot = bpy.data.objects.new(f"PlantSlot_{i}", None)
        slot.empty_display_type = "SINGLE_ARROW"
        slot.empty_display_size = 0.15
        slot.location = (cx, cy, soil_height(d, cx, cy, cx, cy, seed))
        coll.objects.link(slot)
        slot.parent = root

    root["outer_size_m"] = (d.L + 2 * d.over, d.W + 2 * d.over, d.z_rim)
    return root


def cli_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = {}
    for i, a in enumerate(argv):
        if a.startswith("--") and i + 1 < len(argv):
            args[a[2:]] = argv[i + 1]
    return args


def save_asset_file(path):
    """Write a clean .blend that only holds the planter."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build()
    coll = bpy.data.collections[COLLECTION]
    coll.asset_mark()
    coll.asset_data.description = "Wooden planter box for two plants, 1.03 x 0.53 x 0.49 m"
    for tag in ("planter", "greenhouse", "garden", "wood"):
        coll.asset_data.tags.new(tag, skip_if_exists=True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces[0].shading.type = "MATERIAL"
    bpy.ops.wm.save_as_mainfile(filepath=path)


if __name__ == "__main__":
    args = cli_args()
    if "save" in args:
        save_asset_file(bpy.path.abspath(args["save"]))
    else:
        build(location=bpy.context.scene.cursor.location.copy())
