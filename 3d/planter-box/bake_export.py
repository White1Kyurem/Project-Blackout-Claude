"""
Game-ready export of the planter box: one mesh, one material, baked textures.

blender --background --python bake_export.py -- --out export [--size 2048]

Builds the planter with planter_box.py, applies the modifiers, joins all
parts into one mesh, packs a second UV map without overlaps (hidden faces
get less space), bakes the procedural materials into base colour, roughness,
metallic, normal and ambient occlusion maps (Cycles) and writes
planter_box.glb, planter_box.fbx and planter_box.obj plus the textures.
The plant slot empties are exported as child nodes.
"""

import os
import sys

import bpy
import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import planter_box  # noqa: E402

NAME = "planter_box"
PASSES = [  # (suffix, principled input or bake type, colour space)
    ("basecolor", "Base Color", "sRGB"),
    ("roughness", "Roughness", "Non-Color"),
    ("metallic", "Metallic", "Non-Color"),
    ("normal", "NORMAL", "Non-Color"),
    ("ao", "AO", "Non-Color"),
]


def joined_mesh(root):
    """Copy every mesh part with its modifiers applied and join them."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    coll = bpy.data.collections.new("Planter_Export")
    bpy.context.scene.collection.children.link(coll)
    parts = []
    for child in root.children:
        if child.type != "MESH":
            continue
        mesh = bpy.data.meshes.new_from_object(child.evaluated_get(depsgraph))
        obj = bpy.data.objects.new(child.name + "_baked", mesh)
        obj.matrix_world = child.matrix_world
        coll.objects.link(obj)
        parts.append(obj)
    with bpy.context.temp_override(active_object=parts[0], object=parts[0],
                                   selected_objects=parts,
                                   selected_editable_objects=parts):
        bpy.ops.object.join()
    obj = parts[0]
    root.name = "Planter_Box_Source"  # free the name for the exported mesh
    obj.name = obj.data.name = "Planter_Box"
    return obj


def drop_hidden_soil(obj):
    """The soil skirt and floor sit behind the liner; skip them in the atlas."""
    soil = obj.data.materials.find("Planter_Soil")
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    hidden = [f for f in bm.faces if f.material_index == soil and f.normal.z < 0.3]
    bmesh.ops.delete(bm, geom=hidden, context="FACES")
    bm.to_mesh(obj.data)
    bm.free()


def texel_weight(obj, poly, d):
    """Atlas space per face: small for surfaces nobody gets to see."""
    mats = obj.data.materials
    name = mats[poly.material_index].name
    if name == "Planter_Liner":
        return 0.2
    n, c = poly.normal, poly.center
    if n.z < -0.5:
        return 0.3                       # undersides
    if name == "Planter_Wood" and abs(n.z) < 0.5 and c.z < d.z_top:
        inside = abs(c.x) <= d.xi + 1e-4 and abs(c.y) <= d.yi + 1e-4
        if inside and n.x * c.x + n.y * c.y < 0.0:  # facing the box centre
            return 0.25                  # behind the liner or under the soil
    if name.startswith("Planter_Metal") or name == "Planter_Rubber":
        return 1.5                       # small parts, keep them crisp
    return 1.0


def pack_uvs(obj):
    me = obj.data
    bake_uv = me.uv_layers.new(name="BakeUV", do_init=True)
    me.uv_layers.active = bake_uv
    d = planter_box.Dims(planter_box.P)
    for poly in me.polygons:
        w = texel_weight(obj, poly, d)
        for li in poly.loop_indices:
            bake_uv.data[li].uv *= w
    scene = bpy.context.scene
    scene.tool_settings.use_uv_select_sync = True
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    bake_uv = me.uv_layers["BakeUV"]  # edit mode reallocates the layer data
    # resulting resolution on the visible wood
    area_uv = area_3d = 0.0
    for poly in me.polygons:
        if texel_weight(obj, poly, d) == 1.0:
            uvs = [bake_uv.data[li].uv for li in poly.loop_indices]
            a = 0.0
            for i in range(1, len(uvs) - 1):
                e1, e2 = uvs[i] - uvs[0], uvs[i + 1] - uvs[0]
                a += abs(e1.x * e2.y - e1.y * e2.x) / 2
            area_uv += a
            area_3d += poly.area
    return (area_uv / area_3d) ** 0.5 if area_3d else 0.0


def bake(obj, size, out_dir):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8
    scene.render.bake.margin = 8
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Bake_World")
    scene.world.light_settings.distance = 0.12  # AO reach in metres
    images = {}
    for suffix, _, space in PASSES:
        img = bpy.data.images.new(f"{NAME}_{suffix}", size, size, alpha=False,
                                  float_buffer=False)
        img.colorspace_settings.name = space
        images[suffix] = img

    for suffix, socket, _ in PASSES:
        restore = []
        for mat in obj.data.materials:
            nodes, links = mat.node_tree.nodes, mat.node_tree.links
            target = nodes.new("ShaderNodeTexImage")
            target.image = images[suffix]
            nodes.active = target
            if socket in ("NORMAL", "AO"):
                continue
            # route the wanted input through an emission shader
            bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
            out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
            emit = nodes.new("ShaderNodeEmission")
            src = bsdf.inputs[socket]
            if src.is_linked:
                links.new(src.links[0].from_socket, emit.inputs["Color"])
            else:
                value = src.default_value
                emit.inputs["Color"].default_value = (
                    tuple(value) if hasattr(value, "__len__") else (value, value, value, 1.0))
            old = out.inputs["Surface"].links[0].from_socket
            links.new(emit.outputs["Emission"], out.inputs["Surface"])
            restore.append((mat, old, out, emit))
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        if socket == "NORMAL":
            bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", margin=8)
        elif socket == "AO":
            scene.cycles.samples = 128
            bpy.ops.object.bake(type="AO", margin=8)
            scene.cycles.samples = 8
        else:
            bpy.ops.object.bake(type="EMIT", margin=8)
        for mat, old, out, emit in restore:
            mat.node_tree.links.new(old, out.inputs["Surface"])
            mat.node_tree.nodes.remove(emit)
        for mat in obj.data.materials:
            for n in [n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE"]:
                mat.node_tree.nodes.remove(n)
        path = os.path.join(out_dir, "textures", f"{NAME}_{suffix}.png")
        images[suffix].filepath_raw = path
        images[suffix].file_format = "PNG"
        images[suffix].save()
        print("baked", path)
    return images


def gltf_output_group():
    """Node group the glTF exporter reads the occlusion map from."""
    group = bpy.data.node_groups.get("glTF Material Output")
    if group is None:
        group = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        group.interface.new_socket(name="Occlusion", in_out="INPUT",
                                   socket_type="NodeSocketFloat")
    return group


def baked_material(images):
    mat = bpy.data.materials.new("Planter_Box_Baked")
    n = planter_box.Nodes(mat)
    tex = {}
    for suffix in images:
        node = n.new("ShaderNodeTexImage")
        node.image = images[suffix]
        tex[suffix] = node.outputs["Color"]
    normal = n.new("ShaderNodeNormalMap")
    n.link(tex["normal"], normal.inputs["Color"])
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    n.link(tex["basecolor"], bsdf.inputs["Base Color"])
    n.link(tex["roughness"], bsdf.inputs["Roughness"])
    n.link(tex["metallic"], bsdf.inputs["Metallic"])
    n.link(normal.outputs["Normal"], bsdf.inputs["Normal"])
    out = n.new("ShaderNodeOutputMaterial")
    n.link(bsdf.outputs["BSDF"], out.inputs["Surface"])
    gltf = n.new("ShaderNodeGroup")
    gltf.node_tree = gltf_output_group()
    n.link(tex["ao"], gltf.inputs["Occlusion"])
    return mat


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_dir = os.path.abspath(argv[argv.index("--out") + 1] if "--out" in argv else "export")
    size = int(argv[argv.index("--size") + 1]) if "--size" in argv else 2048
    os.makedirs(os.path.join(out_dir, "textures"), exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    root = planter_box.build()
    obj = joined_mesh(root)
    drop_hidden_soil(obj)
    density = pack_uvs(obj)
    print(f"texel density on visible wood: {density * size:.0f} px/m")
    images = bake(obj, size, out_dir)

    # swap to the baked material and keep only the packed UV map
    me = obj.data
    me.materials.clear()
    me.materials.append(baked_material(images))
    for poly in me.polygons:
        poly.material_index = 0
    me.uv_layers.remove(me.uv_layers["UVMap"])
    me.uv_layers["BakeUV"].name = "UVMap"
    if "wet" in me.attributes:
        me.attributes.remove(me.attributes["wet"])

    # plant slots become children of the exported mesh
    export = [obj]
    for child in list(root.children):
        if child.type == "EMPTY":
            child.parent = obj
            export.append(child)
    bpy.ops.object.select_all(action="DESELECT")
    for o in export:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obj

    base = os.path.join(out_dir, NAME)
    bpy.ops.export_scene.gltf(filepath=base + ".glb", export_format="GLB",
                              use_selection=True, export_apply=True)
    bpy.ops.export_scene.fbx(filepath=base + ".fbx", use_selection=True,
                             object_types={"MESH", "EMPTY"}, path_mode="RELATIVE",
                             mesh_smooth_type="FACE", add_leaf_bones=False)
    bpy.ops.wm.obj_export(filepath=base + ".obj", export_selected_objects=True,
                          path_mode="RELATIVE", export_triangulated_mesh=False)

    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    print(f"exported {NAME}: {len(me.polygons)} faces, ~{tris} triangles")


main()
