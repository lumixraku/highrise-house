"""Body-first procedural reconstruction of Abeno Harukas.

This pass intentionally models only the primary massing: three volumes of
different heights stand on the same ground plane and connect horizontally,
south to north (low, middle, high). Each volume is a different quadrilateral
in plan: the long connecting edges are slanted — they tilt along the
north-south axis instead of running straight east-west. The middle volume's
east side extends outward while its west side approaches the high volume.
Open two-storey truss bands sit just below the low/middle rooflines
(z 70-80 / 185-195 m) with no glazing, each running through the two
adjoining volumes. Chevron density follows face width (about 12 m per
group, seven groups on the long faces). Facade grids are schematic; core
and interior systems are deferred.
"""

import argparse
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from materials import make_glass, make_ground, make_metal, make_wall

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
# Three ground-standing volumes connected along Y. Plan corners are ordered
# SW, SE, NE, NW; adjacent volumes share their full connecting edge. The long
# connecting edges are slanted in plan — they tilt along the north-south axis
# instead of running straight east-west, so all three footprints are irregular
# quadrilaterals. The low/middle connecting edge (88 m) is the composition's
# widest line: both neighbouring volumes flare outward toward it, keeping
# every plan tilt within about 3 degrees. Flat roofs at 80/195/300 m.
MASSES = (
    ("Low", 80.0, ((-42.5, -40.0), (42.7, -40.0),
                   (44.0, -14.75), (-44.0, -10.25))),
    ("Middle", 195.0, ((-44.0, -10.25), (44.0, -14.75),
                       (42.3, 18.5), (-42.7, 14.5))),
    ("High", 300.0, ((-42.7, 14.5), (42.3, 18.5),
                     (41.8, 46.0), (-43.5, 46.0))),
)
# Union of the three plans. The low/middle connecting edge spans -44..+44
# (88 m), the widest line of the composition, shared by the low and middle
# volumes; the middle volume widens toward that low-side face. Depth 86 m.
OUTLINE = ((-42.5, -40.0), (42.7, -40.0), (44.0, -14.75), (42.3, 18.5),
           (41.8, 46.0), (-43.5, 46.0), (-42.7, 14.5), (-44.0, -10.25))
TRUSS_BAND_H = 10.0     # open truss zone, two 5 m facade storeys tall
TRUSS_SPACING = 12.0    # chevron spacing; the ~86 m front faces get 7 groups
TRUSS_INSET = 0.025     # truss stands inside the glass line (no glazing here)
BACKING_INSET = 0.06    # recessed dark back wall closing the open truss zone
TRUSS_POST_W = 0.45
TRUSS_DIAG_W = 0.35
TRUSS_CHORD_W = 0.40
SOURCES = {
    "source_height_m": 300.0,
    "source_floor_count": 60,
    "mass_layout": "Three volumes on one ground plane, connected south to north: low, middle, high.",
    "mass_heights_m": "80 / 195 / 300, flat roofs.",
    "plan_shape": "Three different quadrilaterals; long connecting edges tilt along the north-south axis, all within 3 degrees.",
    "truss_zones": "Open truss bands (two storeys, 10 m) just below the low/middle roofs at z 70-80 / 185-195 m, each running through the two adjoining volumes; ~12 m chevron spacing (7 groups on the long faces).",
    "model_scope": "Body-first massing pass; facade grids schematic; core and trusses deferred.",
}
COLLECTION = None


def collection(name):
    global COLLECTION
    COLLECTION = bpy.data.collections.new("Harukas_" + name)
    bpy.context.scene.collection.children.link(COLLECTION)
    return COLLECTION


def mesh_object(name, vertices, faces, material):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    COLLECTION.objects.link(obj)
    mesh.materials.append(material)
    return obj


def boxes(name, parts, material):
    vertices, faces = [], []
    for (x, y, z), (w, d, h) in parts:
        offset = len(vertices)
        vertices.extend((x + sx * w / 2, y + sy * d / 2, z + sz * h / 2)
                        for sx, sy, sz in ((-1, -1, -1), (1, -1, -1),
                                           (1, 1, -1), (-1, 1, -1),
                                           (-1, -1, 1), (1, -1, 1),
                                           (1, 1, 1), (-1, 1, 1)))
        faces.extend(tuple(offset + i for i in face) for face in BOX_FACES)
    return mesh_object(name, vertices, faces, material)


BOX_FACES = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))


def beam(name, start, end, width, material):
    start, end = Vector(start), Vector(end)
    obj = boxes(name, [((0, 0, 0), (width, width, (end - start).length))], material)
    obj.location = (start + end) / 2
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = (end - start).to_track_quat("Z", "Y")
    return obj


def prism(name, points, z0, z1, material):
    count = len(points)
    vertices = [(x, y, z) for z in (z0, z1) for x, y in points]
    faces = [tuple(range(count - 1, -1, -1)), tuple(range(count, 2 * count))]
    faces += [(index, (index + 1) % count,
               (index + 1) % count + count, index + count)
              for index in range(count)]
    return mesh_object(name, vertices, faces, material)


def edge_point(points, edge_index, fraction, z, inset=0.0):
    a = Vector((*points[edge_index], z))
    b = Vector((*points[(edge_index + 1) % 4], z))
    point = a.lerp(b, fraction)
    if inset:
        centre = Vector((sum(x for x, _ in points) / 4,
                         sum(y for _, y in points) / 4, z))
        point = point.lerp(centre, inset)
    return point


def inset_points(points, fraction):
    cx = sum(x for x, _ in points) / 4
    cy = sum(y for _, y in points) / 4
    return tuple((x + (cx - x) * fraction, y + (cy - y) * fraction)
                 for x, y in points)


def truss_face(name, points, edge, z0, z1, metal):
    """Complete upward chevrons with both ends on the lower chord, plus
    boundary posts and top/bottom chords. Group count follows the face width
    so the density matches the seven-group front faces."""
    a, b = points[edge], points[(edge + 1) % 4]
    width = math.hypot(b[0] - a[0], b[1] - a[1])
    groups = max(1, round(width / TRUSS_SPACING))
    for k in range(groups + 1):
        fraction = k / groups
        start = edge_point(points, edge, fraction, z0, TRUSS_INSET)
        end = edge_point(points, edge, fraction, z1, TRUSS_INSET)
        beam(f"{name}_TrussPost_{edge}_{k}", start, end, TRUSS_POST_W, metal)
    for k in range(groups):
        f0 = k / groups
        f1 = (k + 0.5) / groups
        f2 = (k + 1) / groups
        apex = edge_point(points, edge, f1, z1, TRUSS_INSET)
        beam(f"{name}_TrussDiag_{edge}_{k}_L",
             edge_point(points, edge, f0, z0, TRUSS_INSET), apex,
             TRUSS_DIAG_W, metal)
        beam(f"{name}_TrussDiag_{edge}_{k}_R",
             apex, edge_point(points, edge, f2, z0, TRUSS_INSET),
             TRUSS_DIAG_W, metal)
    beam(f"{name}_TrussChordBot_{edge}",
         edge_point(points, edge, 0.0, z0, TRUSS_INSET),
         edge_point(points, edge, 1.0, z0, TRUSS_INSET), TRUSS_CHORD_W, metal)
    beam(f"{name}_TrussChordTop_{edge}",
         edge_point(points, edge, 0.0, z1, TRUSS_INSET),
         edge_point(points, edge, 1.0, z1, TRUSS_INSET), TRUSS_CHORD_W, metal)


def facade_grid(name, points, z0, z1, metal):
    levels = [z0]
    step = 5.0
    level = math.ceil((z0 + 0.01) / step) * step
    while level < z1 - 0.01:
        levels.append(level)
        level += step
    levels.append(z1)

    for edge in range(4):
        for index in range(1, 10):
            fraction = index / 10
            start = edge_point(points, edge, fraction, z0, 0.002)
            end = edge_point(points, edge, fraction, z1, 0.002)
            beam(f"{name}_Mullion_{edge}_{index:02}", start, end, 0.12, metal)
        for level in levels[1:-1]:
            start = edge_point(points, edge, 0.0, level, 0.002)
            end = edge_point(points, edge, 1.0, level, 0.002)
            beam(f"{name}_Transom_{edge}_{int(level):03}", start, end, 0.10, metal)


def mass_bands(height):
    """Open truss bands sit just below every mass top below the crown and
    run through two volumes: both the mass ending there and every taller
    mass continuing past it carry the band at that height. No band at the
    ground level or at the 300 m crown."""
    crown = max(h for _, h, _ in MASSES)
    return sorted({(top - TRUSS_BAND_H, top)
                   for _, top, _ in MASSES
                   if top <= height and top < crown})


def glass_spans(height, bands):
    spans = []
    z = 0.0
    for z0, z1 in bands:
        if z0 > z:
            spans.append((z, z0))
        z = z1
    if z < height:
        spans.append((z, height))
    return spans


def build_mass(name, height, points, glass, metal, stone,
               backing, blockout):
    if blockout:
        body = prism(f"{name}_Body", points, 0.0, height, stone)
        body["tier"] = name
        body["height_m"] = height
        return body
    bands = mass_bands(height)
    # Truss zones carry no glazing: the glass body splits around each band,
    # and the recessed truss with a dark back wall sits inside it.
    body = None
    for index, (z0, z1) in enumerate(glass_spans(height, bands)):
        body = prism(f"{name}_Glass_{index}", points, z0, z1, glass)
        facade_grid(f"{name}_{index}", points, z0, z1, metal)
    for index, (z0, z1) in enumerate(bands):
        prism(f"{name}_Truss_Backing_{index}",
              inset_points(points, BACKING_INSET), z0, z1, backing)
        for edge in range(4):
            truss_face(f"{name}_{index}", points, edge, z0, z1, metal)
    body["tier"] = name
    body["height_m"] = height
    body["plan_shape"] = "quadrilateral"
    body["truss_bands"] = len(bands)
    return body


def ground(material):
    return prism("Ground_Tower_Footprint", OUTLINE, -0.6, 0.0, material)


def camera(name, location, target, ortho_scale=None, lens=45):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    COLLECTION.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    data.clip_end = 2000
    if ortho_scale is None:
        data.type = "PERSP"
        data.lens = lens
    else:
        data.type = "ORTHO"
        data.ortho_scale = ortho_scale
    return obj


def sun(name="Harukas_Sun"):
    data = bpy.data.lights.new(name, "SUN")
    data.energy = 4.0
    data.angle = math.radians(30.0)
    obj = bpy.data.objects.new(name, data)
    COLLECTION.objects.link(obj)
    obj.rotation_euler = (math.radians(55.0), 0.0, math.radians(35.0))
    return obj


def frame_viewport(location, target):
    """Set the saved 3D viewport to an exterior orbit matching the preview camera."""
    location, target = Vector(location), Vector(target)
    direction = target - location
    found = False
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            space = area.spaces.active
            region = space.region_3d
            if region is None:
                continue
            region.view_location = target
            region.view_rotation = direction.to_track_quat("-Z", "Y")
            region.view_distance = direction.length
            region.view_perspective = "PERSP"
            space.lens = 42
            space.clip_end = 5000
            found = True
    if not found:
        print("warning: no 3D viewport found to frame")


def setup_scene(args, ground_mat):
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    for key, value in SOURCES.items():
        scene[key] = value
    collection("Presentation")
    ground(ground_mat)
    sun()
    cameras = {
        "preview": camera("Harukas_Preview_Camera", (140, -285, 130), (0, 5, 135), lens=42),
        "plan": camera("Harukas_Plan_Camera", (0, 0, 550), (0, 0, 0), ortho_scale=120),
        "north": camera("Harukas_North_Camera", (0, 260, 145), (0, 0, 145), ortho_scale=350),
    }
    scene.camera = cameras["preview"]
    scene.render.resolution_x = args.resolution
    scene.render.resolution_y = round(args.resolution * 1.2)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.engine = "BLENDER_WORKBENCH" if args.blockout else "BLENDER_EEVEE"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.world = bpy.data.worlds.new("Harukas_World")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs[0].default_value = (0.28, 0.34, 0.44, 1.0)
    background.inputs[1].default_value = 1.0
    return cameras


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blockout", action="store_true")
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("--resolution", type=int, default=900)
    parser.add_argument("--views", nargs="+", default=["preview", "plan", "north"])
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])

    bpy.ops.wm.read_factory_settings(use_empty=True)
    glass = make_glass(name="Harukas_Body_Glass", engine="BLENDER_EEVEE", tint=(0.78, 0.92, 0.98))
    metal = make_metal(name="Harukas_Schematic_Mullions")
    stone = make_wall(name="Harukas_Blockout_Stone", color=(0.31, 0.37, 0.40))
    ground_mat = make_ground(name="Harukas_Ground")
    backing = make_wall(name="Harukas_Truss_Backing", color=(0.075, 0.085, 0.10))
    for name, height, points in MASSES:
        collection(name)
        build_mass(name, height, points, glass, metal, stone,
                   backing, args.blockout)
    cameras = setup_scene(args, ground_mat)
    frame_viewport(cameras["preview"].location, (0, 5, 135))
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "abeno_harukas.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    if not args.no_render:
        scene = bpy.context.scene
        for view in args.views:
            scene.camera = cameras[view]
            scene.render.filepath = os.path.join(OUT_DIR, f"abeno_harukas_{view}.png")
            bpy.ops.render.render(write_still=True)
    print(f"Built body-first Harukas model: {len(bpy.data.objects)} objects")
    print(f"Saved editable model: {path}")


if __name__ == "__main__":
    main()
