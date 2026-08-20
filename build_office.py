"""Build a first-pass office tower mass with a Samsung-like squircle plan.

The footprint is a rounded square whose four sides bow very slightly outward.
This is intentionally a separate entrypoint from build_house.py: the office
profile is still under design and should not inherit residential assumptions.

Usage:
    blender --background --factory-startup --python build_office.py
    blender --background --factory-startup --python build_office.py --no-render
"""

import math
import os
import sys

import bpy
from mathutils import Euler, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import materials


# ---------------------------------------------------------------------------
# First-pass design parameters
# ---------------------------------------------------------------------------
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
OUTPUT_STEM = "office_tower"

FOOTPRINT = 50.0       # final bounding-box width and depth, metres
SQUIRCLE_EXPONENT = 2.7  # 2=circle; higher values approach a square
PROFILE_STEPS = 128
FLOOR_HEIGHT = 5.0
OFFICE_FLOORS_PER_GROUP = 8
OFFICE_GROUPS = 3
OFFICE_FLOORS = OFFICE_FLOORS_PER_GROUP * OFFICE_GROUPS
PILOTIS_FLOORS = 3
EQUIPMENT_FLOORS = OFFICE_GROUPS + 3
TOTAL_LEVELS = PILOTIS_FLOORS + OFFICE_FLOORS + EQUIPMENT_FLOORS
TOWER_HEIGHT = TOTAL_LEVELS * FLOOR_HEIGHT
CLEAR_PANE_H = 2.50
CLEAR_PANE_W = 1.50
MULLION_W = 0.11
MULLION_D = 0.14
GLASS_T = 0.025
FLOOR_T = 0.24
INTERIOR_SETBACK = 0.65
CORE_W = 14.0
CORE_D = 14.0
PILOTIS_RADIUS = 1.20
# Three groups of eight office floors sit above a two-level equipment podium, with
# a single equipment/refuge level between office groups and two more at the roof.
# Equipment levels count toward physical height, never toward office-floor count.
OFFICE_LEVELS = set()
EQUIPMENT_LEVELS = set()
EQUIPMENT_LEVELS.update(range(PILOTIS_FLOORS, PILOTIS_FLOORS + 2))
for group in range(OFFICE_GROUPS):
    group_start = PILOTIS_FLOORS + 2 + group * (OFFICE_FLOORS_PER_GROUP + 1)
    OFFICE_LEVELS.update(range(group_start, group_start + OFFICE_FLOORS_PER_GROUP))
    if group < OFFICE_GROUPS - 1:
        EQUIPMENT_LEVELS.add(group_start + OFFICE_FLOORS_PER_GROUP)
EQUIPMENT_LEVELS.update(range(TOTAL_LEVELS - 2, TOTAL_LEVELS))

RENDER = "--no-render" not in sys.argv[1:]


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def squircle_profile():
    """Return a continuous One UI-style superellipse, not straight sides plus arcs."""
    half = FOOTPRINT / 2.0
    power = 2.0 / SQUIRCLE_EXPONENT
    profile = []
    for i in range(PROFILE_STEPS):
        angle = 2.0 * math.pi * i / PROFILE_STEPS
        c = math.cos(angle)
        s = math.sin(angle)
        profile.append(
            (
                half * math.copysign(abs(c) ** power, c),
                half * math.copysign(abs(s) ** power, s),
            )
        )
    return profile


def profile_path(profile):
    cumulative = [0.0]
    for i, p0 in enumerate(profile):
        p1 = profile[(i + 1) % len(profile)]
        cumulative.append(cumulative[-1] + math.hypot(p1[0] - p0[0], p1[1] - p0[1]))
    return cumulative, cumulative[-1]


def profile_at(profile, cumulative, distance):
    distance %= cumulative[-1]
    for i in range(len(profile)):
        if cumulative[i + 1] >= distance:
            p0 = profile[i]
            p1 = profile[(i + 1) % len(profile)]
            t = (distance - cumulative[i]) / (cumulative[i + 1] - cumulative[i])
            return Vector((p0[0] + (p1[0] - p0[0]) * t,
                           p0[1] + (p1[1] - p0[1]) * t, 0.0))
    return Vector((profile[0][0], profile[0][1], 0.0))


def profile_normal(point):
    return Vector((point.x, point.y, 0.0)).normalized()


def mesh_object(name, vertices, faces, material, smooth=False):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    if smooth:
        for polygon in mesh.polygons:
            polygon.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def append_prism(vertices, faces, center, tangent, normal, width, depth, z0, z1):
    base = len(vertices)
    for z in (z0, z1):
        for side, front in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            vertices.append(center + tangent * (side * width / 2) + normal * (front * depth / 2) + Vector((0, 0, z)))
    faces.extend([
        (base, base + 1, base + 2, base + 3),
        (base + 4, base + 7, base + 6, base + 5),
        (base, base + 4, base + 5, base + 1),
        (base + 1, base + 5, base + 6, base + 2),
        (base + 2, base + 6, base + 7, base + 3),
        (base + 3, base + 7, base + 4, base),
    ])


def make_glass(profile, cumulative, perimeter, material):
    vertices, faces = [], []
    modules = max(1, round(perimeter / (CLEAR_PANE_W + MULLION_W)))
    pitch = perimeter / modules
    inset = (FLOOR_HEIGHT - CLEAR_PANE_H) / 2
    for floor in sorted(OFFICE_LEVELS):
        bottom = floor * FLOOR_HEIGHT + inset
        top = bottom + CLEAR_PANE_H
        for module in range(modules):
            s0 = module * pitch + MULLION_W / 2
            s1 = (module + 1) * pitch - MULLION_W / 2
            a, b = profile_at(profile, cumulative, s0), profile_at(profile, cumulative, s1)
            na, nb = profile_normal(a), profile_normal(b)
            base = len(vertices)
            for z in (bottom, top):
                vertices.extend((a + na * GLASS_T / 2 + Vector((0, 0, z)),
                                 b + nb * GLASS_T / 2 + Vector((0, 0, z)),
                                 b - nb * GLASS_T / 2 + Vector((0, 0, z)),
                                 a - na * GLASS_T / 2 + Vector((0, 0, z))))
            faces.extend([
                (base, base + 1, base + 5, base + 4),
                (base + 3, base + 7, base + 6, base + 2),
                (base, base + 4, base + 7, base + 3),
                (base + 1, base + 2, base + 6, base + 5),
                (base + 4, base + 5, base + 6, base + 7),
                (base + 3, base + 2, base + 1, base),
            ])
    return mesh_object("Office_Glass", vertices, faces, material), modules, pitch


def make_mullions(profile, cumulative, floors, modules, pitch, material):
    vertices, faces = [], []
    for floor in sorted(OFFICE_LEVELS):
        for module in range(modules):
            point = profile_at(profile, cumulative, module * pitch)
            normal = profile_normal(point)
            tangent = Vector((-normal.y, normal.x, 0.0))
            append_prism(vertices, faces, point + normal * GLASS_T / 2,
                         tangent, normal, MULLION_W, MULLION_D,
                         floor * FLOOR_HEIGHT, (floor + 1) * FLOOR_HEIGHT)
    return mesh_object("Office_Mullions", vertices, faces, material)


def make_floor_slabs(profile, material):
    vertices, faces = [], []
    n = len(profile)
    # Every storey has a complete structural plate, including the refuge levels.
    # The pilotis remains open below its first plate at level 3.
    for floor in range(PILOTIS_FLOORS, TOTAL_LEVELS + 1):
        z = floor * FLOOR_HEIGHT
        base = len(vertices)
        vertices.extend((x, y, z) for x, y in profile)
        vertices.extend((x, y, z - FLOOR_T) for x, y in profile)
        faces.extend((base + i, base + (i + 1) % n,
                      base + n + (i + 1) % n, base + n + i) for i in range(n))
        faces.append(tuple(base + i for i in range(n - 1, -1, -1)))
        faces.append(tuple(base + n + i for i in range(n)))
    return mesh_object("Office_Floor_Slabs", vertices, faces, material)


def make_interior(profile, material):
    scale = (FOOTPRINT / 2 - INTERIOR_SETBACK) / (FOOTPRINT / 2)
    n = len(profile)
    vertices, faces = [], []
    for group in range(OFFICE_GROUPS):
        first = PILOTIS_FLOORS + 2 + group * (OFFICE_FLOORS_PER_GROUP + 1)
        base = len(vertices)
        bottom = first * FLOOR_HEIGHT + 0.3
        top = (first + OFFICE_FLOORS_PER_GROUP) * FLOOR_HEIGHT - 0.3
        vertices.extend((x * scale, y * scale, bottom) for x, y in profile)
        vertices.extend((x * scale, y * scale, top) for x, y in profile)
        faces.extend((base + i, base + (i + 1) % n,
                      base + n + (i + 1) % n, base + n + i)
                     for i in range(n))
    return mesh_object("Office_Interior_Lining", vertices, faces, material, smooth=True)


def make_equipment_bands(profile, material):
    """Make the two equipment/refuge levels read as solid blank facade bands."""
    return [make_profile_solid(f"Office_Equipment_Refuge_{floor}", profile,
                               floor * FLOOR_HEIGHT,
                               (floor + 1) * FLOOR_HEIGHT, material)
            for floor in sorted(EQUIPMENT_LEVELS)]


def make_core(material):
    """Create one continuous solid service core for lifts, stairs, and risers."""
    bpy.ops.mesh.primitive_cube_add(location=(0.0, 0.0, TOWER_HEIGHT / 2.0))
    core = bpy.context.object
    core.name = "Office_Core"
    core.dimensions = (CORE_W, CORE_D, TOWER_HEIGHT)
    core.data.materials.append(material)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return core


def make_profile_solid(name, profile, z0, z1, material, cap=True):
    n = len(profile)
    vertices = [(x, y, z0) for x, y in profile]
    vertices += [(x, y, z1) for x, y in profile]
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    if cap:
        faces += [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    # Keep the roof and blank facade bands flat-shaded. Smoothing the top cap
    # into the curved wall creates an artificial grey gradient at the edge.
    return mesh_object(name, vertices, faces, material)


def make_pilotis(material):
    vertices, faces = [], []
    height = PILOTIS_FLOORS * FLOOR_HEIGHT
    segments = 24
    half = FOOTPRINT / 2.0
    corner_radius = half * (2.0 ** (-1.0 / SQUIRCLE_EXPONENT))
    support_offset = corner_radius * 0.75
    for x, y in ((-support_offset, -support_offset),
                 (-support_offset, support_offset),
                 (support_offset, -support_offset),
                 (support_offset, support_offset)):
            base = len(vertices)
            radius = PILOTIS_RADIUS
            for z in (0.0, height):
                for i in range(segments):
                    angle = 2.0 * math.pi * i / segments
                    vertices.append((x + radius * math.cos(angle),
                                     y + radius * math.sin(angle), z))
            faces.append(tuple(base + i for i in range(segments - 1, -1, -1)))
            faces.append(tuple(base + segments + i for i in range(segments)))
            for i in range(segments):
                j = (i + 1) % segments
                faces.append((base + i, base + j,
                              base + segments + j, base + segments + i))
    return mesh_object("Office_Pilotis", vertices, faces, material)


def add_ground(material):
    bpy.ops.mesh.primitive_plane_add(size=220, location=(0, 0, -0.05))
    ground = bpy.context.object
    ground.name = "Office_Ground"
    ground.data.materials.append(material)


def point_camera(camera, target):
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(OUT_DIR, "office_preview.png")
    scene.world = materials.make_sky_world(name="OfficeSky", strength=0.8)

    bpy.ops.object.light_add(type="SUN", location=(40, -40, 100))
    sun = bpy.context.object
    sun.name = "Office_Sun"
    sun.rotation_euler = (math.radians(32), math.radians(-28), math.radians(35))
    sun.data.energy = 3.0
    sun.data.angle = math.radians(12)

    # Pull back far enough to show the complete first-pass massing, including
    # the roof and the rounded plan turning into the visible side faces.
    bpy.ops.object.camera_add(location=(270, -320, 270))
    camera = bpy.context.object
    camera.name = "Office_Camera"
    camera.data.lens = 62
    point_camera(camera, Vector((0, 0, TOWER_HEIGHT * 0.38)))
    scene.camera = camera


def frame_viewport():
    """Save every Blender workspace with a distant, elevated tower view."""
    diagonal = math.sqrt(2 * FOOTPRINT**2 + TOWER_HEIGHT**2)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type != "VIEW_3D":
                    continue
                region = space.region_3d
                region.view_location = Vector((0.0, 0.0, TOWER_HEIGHT * 0.45))
                region.view_distance = diagonal * 2.2
                region.view_rotation = Euler(
                    (math.radians(58.0), 0.0, math.radians(38.0)), "XYZ"
                ).to_quaternion()
                region.view_perspective = "PERSP"
                space.clip_end = max(space.clip_end, diagonal * 8.0)


def main():
    reset_scene()
    glass = materials.make_glass(name="OfficeGlass", engine="CYCLES")
    metal = materials.make_metal(name="OfficeMullions")
    concrete = materials.make_concrete(name="OfficeConcrete")
    interior = materials.make_interior(name="OfficeInterior")
    ground = materials.make_ground(name="OfficeGround")
    profile = squircle_profile()
    cumulative, perimeter = profile_path(profile)
    floors = TOTAL_LEVELS
    tower, modules, pitch = make_glass(profile, cumulative, perimeter, glass)
    make_mullions(profile, cumulative, floors, modules, pitch, metal)
    make_floor_slabs(profile, concrete)
    make_interior(profile, interior)
    make_equipment_bands(profile, concrete)
    make_core(concrete)
    pilotis_top = PILOTIS_FLOORS * FLOOR_HEIGHT
    make_pilotis(concrete)
    make_profile_solid("Office_Roof", profile, TOWER_HEIGHT,
                       TOWER_HEIGHT + FLOOR_T, concrete)
    add_ground(ground)
    setup_render()
    frame_viewport()

    xs = [x for x, _ in profile]
    ys = [y for _, y in profile]
    assert abs((max(xs) - min(xs)) - FOOTPRINT) < 1e-4
    assert abs((max(ys) - min(ys)) - FOOTPRINT) < 1e-4
    assert TOWER_HEIGHT == TOTAL_LEVELS * FLOOR_HEIGHT
    assert len(OFFICE_LEVELS) == OFFICE_FLOORS
    assert len(EQUIPMENT_LEVELS) == EQUIPMENT_FLOORS
    assert not (OFFICE_LEVELS & EQUIPMENT_LEVELS)

    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, OUTPUT_STEM + ".blend"))
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = tower
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT_DIR, OUTPUT_STEM + ".glb"),
        export_format="GLB",
    )
    if RENDER:
        bpy.ops.render.render(write_still=True)
    print(f"Office tower: {FOOTPRINT:.1f} x {FOOTPRINT:.1f} x {TOWER_HEIGHT:.1f} m")
    print(f"Office floors: {OFFICE_FLOORS} in {OFFICE_GROUPS} groups of "
          f"{OFFICE_FLOORS_PER_GROUP}")
    print(f"Equipment/refuge levels: {sorted(EQUIPMENT_LEVELS)}")
    print(f"Physical levels: {TOTAL_LEVELS} at {FLOOR_HEIGHT:.1f} m floor-to-floor")
    print(f"Profile vertices: {len(profile)}")


if __name__ == "__main__":
    main()
