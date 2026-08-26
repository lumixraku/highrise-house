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
import random
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
CLEAR_PANE_H = 3.75       # 75% clear glazing; upper quarter is solid wall
CLEAR_PANE_W = 1.50
MULLION_W = 0.11
MULLION_D = 0.14
GLASS_T = 0.025
FLOOR_T = 0.24
INTERIOR_SETBACK = 0.65
CURTAIN_SEED = 20260826
# Three discrete roller-curtain states: rolled up, half down, fully down.
CURTAIN_COVERAGES = (0.0, 0.5, 1.0)
CURTAIN_EDGE_INSET = 0.018
# Keep the curtain visibly behind the glazing in Material Preview as well as
# in the final render. 12 cm is still a close interior fit, but gives EEVEE
# enough depth separation to avoid sorting noise and Z-fighting.
CURTAIN_GAP = 0.12
CURTAIN_T = 0.01
CURTAIN_TOP_INSET = 0.0
CURTAIN_BOTTOM_INSET = 0.03
RADIAL_LIGHT_COUNT = 32
RADIAL_LIGHT_FILL = 0.42
RADIAL_LIGHT_CORE_GAP = 0.60
RADIAL_LIGHT_END_INSET = 1.00
# Make the ceiling fixtures legible through the facade at the saved overview
# scale while keeping the three radial segments and their gaps visible.
RADIAL_LIGHT_INNER_W = 0.34
RADIAL_LIGHT_OUTER_W = 1.00
RADIAL_LIGHT_T = 0.14
RADIAL_LIGHT_TOP_CLEARANCE = 0.18
RADIAL_LIGHT_SEGMENT_SPANS = ((0.03, 0.31), (0.36, 0.64), (0.69, 0.97))
RADIAL_LIGHT_ON_PROBABILITY = 0.72
RADIAL_DARK_SECTOR_WIDTH = 4
RADIAL_LIGHT_SEED = 20260823
# A 50 x 50 m office floor typically gives the service core roughly 12–16%
# of the gross plate. 18 x 18 m makes the centre read as a real high-rise core
# without consuming the deep perimeter office zone.
CORE_W = 18.0
CORE_D = 18.0
PILOTIS_RADIUS = 1.20
# Match the house's saved interactive look: EEVEE uses the shared 50/50
# reflection/transmission preview glass. Set this to CYCLES for a physical
# refracted render; the shared material keeps IOR/Fresnel at 1.52 there too.
RENDER_ENGINE = "BLENDER_EEVEE"
OFFICE_CYCLES_SAMPLES = 32
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
REFUGE_LEVELS = EQUIPMENT_LEVELS - set(range(PILOTIS_FLOORS, PILOTIS_FLOORS + 2)) - set(range(TOTAL_LEVELS - 2, TOTAL_LEVELS))
REFUGE_GRILLE_PITCH = 0.50
REFUGE_GRILLE_W = 0.08
REFUGE_GRILLE_LENGTH = 1.20

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
    for floor in sorted(OFFICE_LEVELS):
        bottom = floor * FLOOR_HEIGHT
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
                         floor * FLOOR_HEIGHT,
                         floor * FLOOR_HEIGHT + CLEAR_PANE_H)
    return mesh_object("Office_Mullions", vertices, faces, material)


def append_frosted_panel(vertices, faces, a, b, na, nb, z0, z1):
    """Append a thin privacy-film panel just inside a glass pane."""
    base = len(vertices)
    outside_a = a - na * (GLASS_T / 2 + CURTAIN_GAP)
    outside_b = b - nb * (GLASS_T / 2 + CURTAIN_GAP)
    inside_a = outside_a - na * CURTAIN_T
    inside_b = outside_b - nb * CURTAIN_T
    for z in (z0, z1):
        vertices.extend((outside_a + Vector((0, 0, z)),
                         outside_b + Vector((0, 0, z)),
                         inside_b + Vector((0, 0, z)),
                         inside_a + Vector((0, 0, z))))
    faces.extend([
        (base, base + 1, base + 5, base + 4),
        (base + 3, base + 7, base + 6, base + 2),
        (base, base + 4, base + 7, base + 3),
        (base + 1, base + 2, base + 6, base + 5),
        (base + 4, base + 5, base + 6, base + 7),
        (base + 3, base + 2, base + 1, base),
    ])


def make_curtains(profile, cumulative, modules, pitch, material):
    """Add a randomly shuffled, exactly balanced three-state curtain pattern."""
    vertices, faces = [], []
    rng = random.Random(CURTAIN_SEED)
    total_windows = len(OFFICE_LEVELS) * modules
    per_state, remainder = divmod(total_windows, len(CURTAIN_COVERAGES))
    assert remainder == 0
    states = [coverage for coverage in CURTAIN_COVERAGES
              for _ in range(per_state)]
    rng.shuffle(states)
    state_counts = {coverage: 0 for coverage in CURTAIN_COVERAGES}
    visible_curtain_count = 0
    window_index = 0
    for floor in sorted(OFFICE_LEVELS):
        top = floor * FLOOR_HEIGHT + CLEAR_PANE_H - CURTAIN_TOP_INSET
        bottom = floor * FLOOR_HEIGHT + CURTAIN_BOTTOM_INSET
        for module in range(modules):
            s0 = module * pitch + MULLION_W / 2 + CURTAIN_EDGE_INSET
            s1 = (module + 1) * pitch - MULLION_W / 2 - CURTAIN_EDGE_INSET
            a, b = profile_at(profile, cumulative, s0), profile_at(profile, cumulative, s1)
            na, nb = profile_normal(a), profile_normal(b)
            coverage = states[window_index]
            state_counts[coverage] += 1
            if coverage > 0.0:
                z1 = top
                z0 = z1 - (top - bottom) * coverage
                append_frosted_panel(vertices, faces, a, b, na, nb, z0, z1)
                visible_curtain_count += 1
            window_index += 1
    obj = mesh_object("Office_Frosted_Curtains", vertices, faces, material)
    return obj, total_windows, visible_curtain_count, state_counts


def squircle_radius(angle, half=FOOTPRINT / 2.0,
                    exponent=SQUIRCLE_EXPONENT):
    """Return the perimeter radius along a ray from the tower centre."""
    c, s = abs(math.cos(angle)), abs(math.sin(angle))
    return half / (c ** exponent + s ** exponent) ** (1.0 / exponent)


def square_core_radius(angle):
    """Return the core boundary radius along a ray from the tower centre."""
    return min(CORE_W, CORE_D) / 2.0 / max(abs(math.cos(angle)),
                                           abs(math.sin(angle)))


def append_radial_panel(vertices, faces, corners, z0, z1):
    """Append a thin trapezoidal ceiling panel from four XY corners."""
    base = len(vertices)
    for z in (z0, z1):
        vertices.extend(Vector((point.x, point.y, z)) for point in corners)
    faces.extend([
        (base, base + 1, base + 2, base + 3),
        (base + 4, base + 7, base + 6, base + 5),
        (base, base + 4, base + 5, base + 1),
        (base + 1, base + 5, base + 6, base + 2),
        (base + 2, base + 6, base + 7, base + 3),
        (base + 3, base + 7, base + 4, base),
    ])


def make_ceiling_lights(on_material, off_material):
    """Place evenly spaced radial fan-shaped light bands on each office ceiling."""
    on_vertices, on_faces = [], []
    off_vertices, off_faces = [], []
    angular_pitch = 2.0 * math.pi / RADIAL_LIGHT_COUNT
    half_angle = angular_pitch * RADIAL_LIGHT_FILL / 2.0
    on_count = off_count = 0
    for floor in sorted(OFFICE_LEVELS):
        # The facade's upper quarter is now a solid spandrel, so place the
        # ceiling strips immediately below the glazed head. This keeps the
        # radial lights visible through the rolled-up clear windows instead of
        # hiding them behind the solid wall band above.
        z1 = (floor * FLOOR_HEIGHT + CLEAR_PANE_H
              - RADIAL_LIGHT_TOP_CLEARANCE)
        z0 = z1 - RADIAL_LIGHT_T
        rng = random.Random(RADIAL_LIGHT_SEED + floor * 1009)
        dark_start = rng.randrange(RADIAL_LIGHT_COUNT)
        for index in range(RADIAL_LIGHT_COUNT):
            angle = index * angular_pitch
            left = angle - half_angle
            right = angle + half_angle
            inner_left = Vector((math.cos(left), math.sin(left), 0.0)) * (
                square_core_radius(left) + RADIAL_LIGHT_CORE_GAP)
            inner_right = Vector((math.cos(right), math.sin(right), 0.0)) * (
                square_core_radius(right) + RADIAL_LIGHT_CORE_GAP)
            outer_left = Vector((math.cos(left), math.sin(left), 0.0)) * (
                squircle_radius(left) - RADIAL_LIGHT_END_INSET)
            outer_right = Vector((math.cos(right), math.sin(right), 0.0)) * (
                squircle_radius(right) - RADIAL_LIGHT_END_INSET)
            inner_mid = (inner_left + inner_right) / 2.0
            outer_mid = (outer_left + outer_right) / 2.0
            inner_scale = RADIAL_LIGHT_INNER_W / max(
                (inner_right - inner_left).length, 1e-6)
            outer_scale = RADIAL_LIGHT_OUTER_W / max(
                (outer_right - outer_left).length, 1e-6)
            inner_left = inner_mid + (inner_left - inner_mid) * inner_scale
            inner_right = inner_mid + (inner_right - inner_mid) * inner_scale
            outer_left = outer_mid + (outer_left - outer_mid) * outer_scale
            outer_right = outer_mid + (outer_right - outer_mid) * outer_scale
            dark_sector = ((index - dark_start) % RADIAL_LIGHT_COUNT
                           < RADIAL_DARK_SECTOR_WIDTH)
            for (t0, t1) in RADIAL_LIGHT_SEGMENT_SPANS:
                segment_on = (not dark_sector
                              and rng.random() < RADIAL_LIGHT_ON_PROBABILITY)
                segment_left_0 = inner_left + (outer_left - inner_left) * t0
                segment_right_0 = inner_right + (outer_right - inner_right) * t0
                segment_left_1 = inner_left + (outer_left - inner_left) * t1
                segment_right_1 = inner_right + (outer_right - inner_right) * t1
                target_vertices = on_vertices if segment_on else off_vertices
                target_faces = on_faces if segment_on else off_faces
                append_radial_panel(
                    target_vertices, target_faces,
                    (segment_left_0, segment_left_1,
                     segment_right_1, segment_right_0), z0, z1)
                if segment_on:
                    on_count += 1
                else:
                    off_count += 1
    on_obj = mesh_object("Office_Ceiling_Lights_On", on_vertices, on_faces,
                         on_material)
    off_obj = mesh_object("Office_Ceiling_Lights_Off", off_vertices, off_faces,
                          off_material)
    return on_obj, off_obj, on_count, off_count


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


def make_spandrel_bands(profile, material):
    """Close the upper quarter of every glazed office storey with solid wall."""
    return [make_profile_solid(
                f"Office_Spandrel_{floor}", profile,
                floor * FLOOR_HEIGHT + CLEAR_PANE_H,
                (floor + 1) * FLOOR_HEIGHT,
                material,
            ) for floor in sorted(OFFICE_LEVELS)]


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
    """Make the podium and roof equipment levels read as solid blank facade bands."""
    return [make_profile_solid(f"Office_Equipment_Refuge_{floor}", profile,
                               floor * FLOOR_HEIGHT,
                               (floor + 1) * FLOOR_HEIGHT, material)
            for floor in sorted(EQUIPMENT_LEVELS - REFUGE_LEVELS)]


def make_refuge_grilles(profile, cumulative, perimeter, material):
    """Use thin radial blades at the ventilated refuge levels."""
    vertices, faces = [], []
    count = max(1, round(perimeter / REFUGE_GRILLE_PITCH))
    pitch = perimeter / count
    for floor in sorted(REFUGE_LEVELS):
        for index in range(count):
            point = profile_at(profile, cumulative, index * pitch)
            normal = profile_normal(point)
            tangent = Vector((-normal.y, normal.x, 0.0))
            # The long axis points inward, like a clock tick aimed at the centre.
            append_prism(vertices, faces,
                         point - normal * (REFUGE_GRILLE_LENGTH / 2),
                         tangent, normal, REFUGE_GRILLE_W, REFUGE_GRILLE_LENGTH,
                         floor * FLOOR_HEIGHT, (floor + 1) * FLOOR_HEIGHT)
    return mesh_object("Office_Refuge_Grilles", vertices, faces, material)


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
    """Create the four continuous perimeter support columns.

    The lower three levels are the open pilotis zone; the columns continue
    through the occupied and equipment levels to carry the whole tower.
    """
    vertices, faces = [], []
    height = TOWER_HEIGHT
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
    bpy.ops.mesh.primitive_plane_add(size=FOOTPRINT, location=(0, 0, -0.05))
    ground = bpy.context.object
    ground.name = "Office_Ground"
    ground.data.materials.append(material)


def point_camera(camera, target):
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = RENDER_ENGINE
    if RENDER_ENGINE == "CYCLES":
        scene.cycles.samples = OFFICE_CYCLES_SAMPLES
        scene.cycles.use_denoising = True
        scene.cycles.max_bounces = 12
        scene.cycles.transmission_bounces = 12
        scene.cycles.transparent_max_bounces = 12
        scene.cycles.glossy_bounces = 6
    elif hasattr(scene, "eevee"):
        for attr, value in (("taa_render_samples", 128),
                            ("use_gtao", True),
                            # The reflection branch must see scene geometry,
                            # not only the world sky, just like house glass.
                            ("use_raytracing", True)):
            if hasattr(scene.eevee, attr):
                setattr(scene.eevee, attr, value)
    if hasattr(scene.cycles, "blur_glossy"):
        scene.cycles.blur_glossy = 0.0
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
    bpy.ops.object.camera_add(location=(225, -270, 225))
    camera = bpy.context.object
    camera.name = "Office_Camera"
    camera.data.lens = 62
    point_camera(camera, Vector((0, 0, TOWER_HEIGHT * 0.42)))
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
                region.view_distance = diagonal * 1.55
                region.view_rotation = Euler(
                    (math.radians(58.0), 0.0, math.radians(38.0)), "XYZ"
                ).to_quaternion()
                region.view_perspective = "PERSP"
                space.clip_end = max(space.clip_end, diagonal * 8.0)


def main():
    reset_scene()
    glass = materials.make_glass(name="OfficeGlass", engine=RENDER_ENGINE)
    frosted_curtain = materials.make_frosted_glass_film(
        name="OfficeFrostedCurtain"
    )
    metal = materials.make_metal(name="OfficeMullions")
    concrete = materials.make_concrete(name="OfficeConcrete")
    spandrel = materials.make_wall(
        name="OfficeSpandrel", color=materials.COOL_STONE
    )
    ceiling_light = materials.make_ceiling_light(name="OfficeCeilingLight")
    ceiling_light_off = materials.make_ceiling_light(
        name="OfficeCeilingLight_Off", color=(0.018, 0.014, 0.010), strength=0.0
    )
    ground = materials.make_ground(name="OfficeGround")
    profile = squircle_profile()
    cumulative, perimeter = profile_path(profile)
    floors = TOTAL_LEVELS
    tower, modules, pitch = make_glass(profile, cumulative, perimeter, glass)
    _, total_windows, visible_curtain_count, curtain_state_counts = make_curtains(
        profile, cumulative, modules, pitch, frosted_curtain
    )
    make_mullions(profile, cumulative, floors, modules, pitch, metal)
    _, _, light_on_count, light_off_count = make_ceiling_lights(
        ceiling_light, ceiling_light_off
    )
    make_floor_slabs(profile, concrete)
    make_spandrel_bands(profile, spandrel)
    make_equipment_bands(profile, concrete)
    make_refuge_grilles(profile, cumulative, perimeter, metal)
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
    assert abs(CLEAR_PANE_H / FLOOR_HEIGHT - 0.75) < 1e-6
    assert len(OFFICE_LEVELS) == OFFICE_FLOORS
    assert len(EQUIPMENT_LEVELS) == EQUIPMENT_FLOORS
    assert not (OFFICE_LEVELS & EQUIPMENT_LEVELS)
    total_light_segments = (OFFICE_FLOORS * RADIAL_LIGHT_COUNT
                            * len(RADIAL_LIGHT_SEGMENT_SPANS))
    assert light_on_count + light_off_count == total_light_segments
    assert light_off_count > 0
    assert total_windows == OFFICE_FLOORS * modules
    assert sum(curtain_state_counts.values()) == total_windows
    assert all(count == total_windows // len(CURTAIN_COVERAGES)
               for count in curtain_state_counts.values())
    assert visible_curtain_count == total_windows - curtain_state_counts[0.0]

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
    print(f"Ceiling lights: {RADIAL_LIGHT_COUNT} radial fan strips per office "
          f"floor, 3 segments each ({total_light_segments} total segments)")
    print(f"Light states: {light_on_count} on / {light_off_count} off; "
          f"dark sectors are {RADIAL_DARK_SECTOR_WIDTH} strips wide")
    print(f"Curtain states: rolled up {curtain_state_counts[0.0]}, "
          f"half down {curtain_state_counts[0.5]}, "
          f"fully down {curtain_state_counts[1.0]} "
          f"({visible_curtain_count} visible panels / {total_windows} windows)")


if __name__ == "__main__":
    main()
