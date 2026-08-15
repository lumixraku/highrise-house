"""Procedural high-rise house generator for Blender.

Run headless:
    blender --background --factory-startup --python build_house.py

Outputs (into out/):
    highrise_house.blend   full scene
    highrise_house.glb     glTF export
    preview.png            EEVEE render

Design brief
------------
* Floor-to-floor height 4.0 m.
* Bottom 3 floors are pilotis (open, raised on columns + a service core).
* Above that sits the solid core of the building: 12 occupied floors.
* Every occupied floor carries a 1.5 m ribbon window spanning the full
  width of every facade, vertically centred in the floor.
* Directly above and below that window sits a 0.3 m ventilation louvre
  strip of the same length as the window.

Vertical band layout per floor, measured from the floor level:
    0.00 - 0.95  solid spandrel
    0.95 - 1.25  ventilation louvres
    1.25 - 2.75  window  (centre at 2.00 m = mid floor)
    2.75 - 3.05  ventilation louvres
    3.05 - 4.00  solid spandrel
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import materials     # noqa: E402  (needs the path set up first)

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

H = 4.0           # floor-to-floor height
# Footprint W (X) and D (Y) are DERIVED from the window module further down:
# the pane size is fixed, so the building widens to fit a whole number of panes.

# Look. CYCLES gives real refraction through the glass and is the reason it reads
# as glass rather than tinted plastic; BLENDER_EEVEE is much faster but fakes it.
RENDER_ENGINE = "CYCLES"
WALL_COLOR = materials.WARM_STONE     # or materials.COOL_STONE for pale grey
GLASS_TINT = materials.GLASS_GREEN
CYCLES_SAMPLES = 128

TOTAL_FLOORS = 40      # storeys counted from the ground
PILOTIS_FLOORS = 3     # of which these are open and raised
TOWER_FLOORS = TOTAL_FLOORS - PILOTIS_FLOORS   # occupied floors above

WALL_T = 0.30     # facade wall thickness
SLAB_T = 0.22     # floor plate thickness

WIN_H = 1.50      # window height
VENT_H = 0.30     # ventilation strip height
GLASS_T = 0.03
GLASS_INSET = 0.09    # from the outer wall face
VENT_INSET = 0.13     # louvres sit deeper than the glass

# The window pane is the fixed module: exactly PANE_W x WIN_H of clear glass.
# EVERYTHING outside is derived from the pane counts — never the other way round.
PANE_W = 2.00
WINDOWS_LONG = 30      # panes across each long facade  (X)
WINDOWS_SHORT = 12     # panes across each short facade (Y)

# The mullion is a cover cap centred on each pane joint: it sits proud of the
# glass line and overlaps the two panes it joins, so it costs NO facade length.
# That keeps the arithmetic clean — an opening is exactly N x PANE_W, so the
# footprint comes out on whole metres:
#   W = 30 x 2.00 + 2 x 8.00 = 76.00 m
#   D = 12 x 2.00 + 2 x 4.00 = 32.00 m
MULLION_W = 0.09

# Solid wall kept at both ends of every facade, so the ribbon stops short of the
# corners instead of wrapping them. Measured along the facade from the corner.
# The long (wide) facade uses 8 m, matching the blank bands above and below it,
# so its window is framed by an even 8 m margin all round. The short facade uses
# less, or it would end up mostly wall.
PIER_LONG = 8.0     # at the ends of the long facades (N/S)
PIER_SHORT = 4.0    # at the ends of the short facades (E/W)

# Blank (windowless) bands of the tower.
# Bottom: the transition floor sitting directly on the pilotis zone.
# Top: a band of blank wall, rounded to whole floors so the break lands on a
# floor line rather than cutting a window in half.
# Both bands are 8 m, so on the long facade the window field is framed by an
# even 8 m of blank wall on all four sides (8 m piers left and right).
SOLID_BASE_TARGET = 8.0
SOLID_TOP_TARGET = 8.0
SOLID_BASE_FLOORS = max(1, round(SOLID_BASE_TARGET / H))
SOLID_TOP_FLOORS = max(1, round(SOLID_TOP_TARGET / H))

# An opening is exactly N panes wide; the mullions cap the joints without
# consuming any of it.
def opening_for(n_panes):
    return n_panes * PANE_W


OPEN_W = opening_for(WINDOWS_LONG)      # long faces (N/S)
OPEN_D = opening_for(WINDOWS_SHORT)     # short faces (E/W)

# Footprint follows: clear opening plus a solid pier at each end.
W = OPEN_W + 2 * PIER_LONG
D = OPEN_D + 2 * PIER_SHORT

# Every pane is the same fixed module, so pitch is uniform on all four facades.
PANE_GLASS_LONG = PANE_W
PANE_GLASS_SHORT = PANE_W
PANE_PITCH = PANE_W                     # mullion centre to centre = pane width
assert abs(WINDOWS_LONG * PANE_W - OPEN_W) < 1e-9
assert abs(WINDOWS_SHORT * PANE_W - OPEN_D) < 1e-9
assert abs(W - round(W)) < 1e-9 and abs(D - round(D)) < 1e-9, \
    "footprint should land on whole metres"

COL_SIZE = 1.60       # pilotis column footprint (sized for a 40-storey load)
COL_SPACING = 9.0     # target column grid spacing
COL_MARGIN = 2.2      # inset of the outer column line from the facade
CORE_W, CORE_D = 14.0, 9.0   # service core inside the pilotis zone

PARAPET_H = 1.10
PARAPET_T = 0.25

BASE_Z = PILOTIS_FLOORS * H          # underside of the tower = 12.0
TOP_Z = BASE_Z + TOWER_FLOORS * H    # roof level = 60.0

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

# Band offsets inside one floor, derived so the window is vertically centred.
SPANDREL_H = (H - WIN_H - 2 * VENT_H) / 2.0     # 0.95
VENT_LO_Z = SPANDREL_H                          # 0.95
WIN_Z = VENT_LO_Z + VENT_H                      # 1.25
VENT_HI_Z = WIN_Z + WIN_H                       # 2.75
SPANDREL_HI_Z = VENT_HI_Z + VENT_H              # 3.05

assert abs(SPANDREL_H + VENT_H + WIN_H + VENT_H + SPANDREL_H - H) < 1e-9


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_material(name, base_color, roughness=0.6, metallic=0.0,
                  transmission=0.0, ior=1.45, emission=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = ior
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 1.0
    if transmission > 0.0:
        mat.blend_method = "BLEND"
        mat.use_backface_culling = False
    return mat


_BOX_VERTS = [
    (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
    (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5),
]
_BOX_FACES = [
    (0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
    (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
]


def box(name, center, dims, mat, rot=None):
    """Axis-aligned box (optionally rotated about its own centre)."""
    mesh = bpy.data.meshes.new(name)
    sx, sy, sz = dims
    verts = [(v[0] * sx, v[1] * sy, v[2] * sz) for v in _BOX_VERTS]
    mesh.from_pydata(verts, [], _BOX_FACES)
    mesh.validate()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = center
    if rot:
        obj.rotation_euler = rot
    obj.data.materials.append(mat)
    bpy.context.collection.objects.link(obj)
    return obj


def join(objects, name):
    """Join a list of objects into one; returns the merged object."""
    objects = [o for o in objects if o is not None]
    if not objects:
        return None
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1:
        bpy.ops.object.join()
    merged = bpy.context.view_layer.objects.active
    merged.name = name
    merged.data.name = name
    bpy.ops.object.select_all(action="DESELECT")
    return merged


def col_grid(span):
    """Evenly spaced column positions across `span`, inset by COL_MARGIN.

    Bays land as close to COL_SPACING as a whole number of bays allows, so the
    grid stays regular whatever the footprint.
    """
    usable = span - 2 * COL_MARGIN
    bays = max(1, round(usable / COL_SPACING))
    step = usable / bays
    start = -usable / 2
    return [start + i * step for i in range(bays + 1)]


def ring(name, z0, height, thickness, mat, outer_w=W, outer_d=D):
    """Closed rectangular band of wall, hugging the footprint edges."""
    zc = z0 + height / 2.0
    t = thickness
    parts = [
        box(f"{name}_S", (0.0, -(outer_d / 2 - t / 2), zc), (outer_w, t, height), mat),
        box(f"{name}_N", (0.0, +(outer_d / 2 - t / 2), zc), (outer_w, t, height), mat),
        box(f"{name}_W", (-(outer_w / 2 - t / 2), 0.0, zc), (t, outer_d - 2 * t, height), mat),
        box(f"{name}_E", (+(outer_w / 2 - t / 2), 0.0, zc), (t, outer_d - 2 * t, height), mat),
    ]
    return parts


# ---------------------------------------------------------------------------
# Facade pieces
# ---------------------------------------------------------------------------

def glass_ring(name, z0, height, mat):
    """Glazing band on each of the four facades.

    Each pane is centred on its facade and stops PIER_LONG (long faces) or
    PIER_SHORT (short faces) short of both corners, so the corners stay solid.
    """
    zc = z0 + height / 2.0
    off = GLASS_INSET + GLASS_T / 2.0
    parts = [
        box(f"{name}_W", (-(W / 2 - off), 0.0, zc), (GLASS_T, OPEN_D, height), mat),
        box(f"{name}_E", (+(W / 2 - off), 0.0, zc), (GLASS_T, OPEN_D, height), mat),
        box(f"{name}_S", (0.0, -(D / 2 - off), zc), (OPEN_W, GLASS_T, height), mat),
        box(f"{name}_N", (0.0, +(D / 2 - off), zc), (OPEN_W, GLASS_T, height), mat),
    ]
    return parts


def corner_piers(name, z0, height, mat):
    """L-shaped solid wall at each corner, filling the window and vent bands.

    Two runs per corner: one along the long facade, one along the short one,
    the second shortened by the wall thickness so they meet without overlapping.
    """
    zc = z0 + height / 2.0
    t = WALL_T
    parts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            # Leg along the long facade: PIER_LONG measured from the corner.
            parts.append(box(
                f"{name}_x_{sx}_{sy}",
                (sx * (W / 2 - PIER_LONG / 2.0), sy * (D / 2 - t / 2.0), zc),
                (PIER_LONG, t, height), mat))
            # Leg along the short facade: PIER_SHORT, less the thickness already
            # taken by the leg above, so the two meet without overlapping.
            parts.append(box(
                f"{name}_y_{sx}_{sy}",
                (sx * (W / 2 - t / 2.0),
                 sy * (D / 2 - t - (PIER_SHORT - t) / 2.0), zc),
                (t, PIER_SHORT - t, height), mat))
    return parts


def mullions(name, z0, height, mat):
    """Slim vertical frames breaking up the ribbon window."""
    parts = []
    zc = z0 + height / 2.0
    off = GLASS_INSET + GLASS_T / 2.0
    depth = 0.14

    # Cover caps centred on each pane joint, plus one at each end against the
    # pier. N panes therefore take N+1 caps, at exact multiples of the pane
    # width from the opening edge — they overlap the glass rather than
    # displacing it, so they cost no facade length.
    first_x = -OPEN_W / 2
    for i in range(WINDOWS_LONG + 1):
        x = first_x + i * PANE_PITCH
        for sy in (-1, 1):
            parts.append(box(
                f"{name}_ns_{i}_{sy}",
                (x, sy * (D / 2 - off), zc),
                (MULLION_W, depth, height), mat))

    first_y = -OPEN_D / 2
    for i in range(WINDOWS_SHORT + 1):
        y = first_y + i * PANE_PITCH
        for sx in (-1, 1):
            parts.append(box(
                f"{name}_ew_{i}_{sx}",
                (sx * (W / 2 - off), y, zc),
                (depth, MULLION_W, height), mat))
    return parts


def vent_strip(name, z0, louver_mat, back_mat):
    """Louvred ventilation band: dark backing panel plus tilted slats.

    Same length as the window: it wraps every facade.
    """
    parts = []
    n_slats = 3
    slat_t = 0.035
    slat_depth = 0.11
    tilt = math.radians(30.0)

    # Dark recessed backing so the opening does not read as a hole.
    back_off = VENT_INSET + 0.12
    zc = z0 + VENT_H / 2.0
    parts += [
        box(f"{name}_back_W", (-(W / 2 - back_off), 0.0, zc), (0.04, OPEN_D, VENT_H), back_mat),
        box(f"{name}_back_E", (+(W / 2 - back_off), 0.0, zc), (0.04, OPEN_D, VENT_H), back_mat),
        box(f"{name}_back_S", (0.0, -(D / 2 - back_off), zc), (OPEN_W, 0.04, VENT_H), back_mat),
        box(f"{name}_back_N", (0.0, +(D / 2 - back_off), zc), (OPEN_W, 0.04, VENT_H), back_mat),
    ]

    off = VENT_INSET + slat_depth / 2.0
    for k in range(n_slats):
        sz = z0 + VENT_H * (k + 0.5) / n_slats
        # N/S facades: slats run along X, tilt about X.
        for sy in (-1, 1):
            parts.append(box(
                f"{name}_slat_ns_{k}_{sy}",
                (0.0, sy * (D / 2 - off), sz),
                (OPEN_W, slat_depth, slat_t), louver_mat,
                rot=(sy * tilt, 0.0, 0.0)))
        # E/W facades: slats run along Y, tilt about Y.
        for sx in (-1, 1):
            parts.append(box(
                f"{name}_slat_ew_{k}_{sx}",
                (sx * (W / 2 - off), 0.0, sz),
                (slat_depth, OPEN_D, slat_t), louver_mat,
                rot=(0.0, -sx * tilt, 0.0)))
    return parts


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build():
    reset_scene()

    mats = materials.build_all(engine=RENDER_ENGINE, wall_color=WALL_COLOR,
                               glass_tint=GLASS_TINT)
    concrete = mats["concrete"]
    spandrel = mats["spandrel"]
    glass = mats["glass"]
    metal = mats["metal"]
    dark = mats["dark"]
    ground_mat = mats["ground"]

    walls, glazing, frames, louvres, backs, slabs, structure = [], [], [], [], [], [], []

    # --- pilotis: open, raised base ------------------------------------
    structure += [box("GroundSlab", (0.0, 0.0, -0.15), (W + 14.0, D + 14.0, 0.30), concrete)]

    for i, x in enumerate(col_grid(W)):
        for j, y in enumerate(col_grid(D)):
            # Skip columns that would land inside the service core walls.
            if abs(x) < CORE_W / 2 + COL_SIZE and abs(y) < CORE_D / 2 + COL_SIZE:
                continue
            structure.append(box(
                f"Column_{i}_{j}", (x, y, BASE_Z / 2.0),
                (COL_SIZE, COL_SIZE, BASE_Z), concrete))

    # Service core rising through the open floors (stairs / lifts).
    structure += ring("Core", 0.0, BASE_Z, 0.28, concrete, outer_w=CORE_W, outer_d=CORE_D)

    # Intermediate landings inside the core, one per open floor.
    for f in range(1, PILOTIS_FLOORS):
        structure.append(box(
            f"CoreLanding_{f}", (0.0, 0.0, f * H),
            (CORE_W - 0.56, CORE_D - 0.56, 0.18), concrete))

    # Underside slab of the tower, slightly oversized as a drip edge.
    structure.append(box("TowerSoffit", (0.0, 0.0, BASE_Z - SLAB_T / 2.0),
                         (W + 0.5, D + 0.5, SLAB_T), concrete))

    # --- tower: the solid core of the building -------------------------
    # Windowless floors: the transition floor above the pilotis, and a blank
    # band at the top.
    blank_floors = set(range(SOLID_BASE_FLOORS)) | set(
        range(TOWER_FLOORS - SOLID_TOP_FLOORS, TOWER_FLOORS))

    for f in range(TOWER_FLOORS):
        z0 = BASE_Z + f * H
        tag = f"F{f + 1:02d}"

        if f in blank_floors:
            # Blank floor: solid wall the whole storey height, no openings.
            walls += ring(f"{tag}_Blank", z0, H, WALL_T, spandrel)
            slabs.append(box(f"{tag}_Slab", (0.0, 0.0, z0 + H - SLAB_T / 2.0),
                             (W - 2 * WALL_T, D - 2 * WALL_T, SLAB_T), concrete))
            continue

        walls += ring(f"{tag}_SpandrelLo", z0, SPANDREL_H, WALL_T, spandrel)
        walls += ring(f"{tag}_SpandrelHi", z0 + SPANDREL_HI_Z, H - SPANDREL_HI_Z,
                      WALL_T, spandrel)

        # Corner piers close the vent+window+vent zone at all four corners.
        walls += corner_piers(f"{tag}_Pier", z0 + VENT_LO_Z,
                              SPANDREL_HI_Z - VENT_LO_Z, spandrel)

        strip_lo = vent_strip(f"{tag}_VentLo", z0 + VENT_LO_Z, metal, dark)
        strip_hi = vent_strip(f"{tag}_VentHi", z0 + VENT_HI_Z, metal, dark)
        for o in strip_lo + strip_hi:
            (backs if "_back_" in o.name else louvres).append(o)

        glazing += glass_ring(f"{tag}_Glass", z0 + WIN_Z, WIN_H, glass)
        frames += mullions(f"{tag}_Mullion", z0 + WIN_Z, WIN_H, metal)

        # Floor plate for the level above, visible behind the glazing.
        slabs.append(box(f"{tag}_Slab", (0.0, 0.0, z0 + H - SLAB_T / 2.0),
                         (W - 2 * WALL_T, D - 2 * WALL_T, SLAB_T), concrete))

    # --- roof ----------------------------------------------------------
    structure.append(box("RoofSlab", (0.0, 0.0, TOP_Z + 0.11),
                         (W, D, 0.22), concrete))
    structure += ring("Parapet", TOP_Z + 0.22, PARAPET_H, PARAPET_T, spandrel)
    structure.append(box("RoofPlant", (W * 0.12, 0.0, TOP_Z + 1.9),
                         (W * 0.30, D * 0.34, 3.4), concrete))

    ground = box("Ground", (0.0, 0.0, -0.32), (600.0, 600.0, 0.04), ground_mat)

    merged = {
        "Facade_Spandrels": join(walls, "Facade_Spandrels"),
        "Windows_Glass": join(glazing, "Windows_Glass"),
        "Window_Mullions": join(frames, "Window_Mullions"),
        "Vent_Louvres": join(louvres, "Vent_Louvres"),
        "Vent_Shadowboxes": join(backs, "Vent_Shadowboxes"),
        "Floor_Plates": join(slabs, "Floor_Plates"),
        "Structure": join(structure, "Structure"),
        "Ground": ground,
    }
    return merged


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = RENDER_ENGINE
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 960
    scene.render.film_transparent = False

    if RENDER_ENGINE == "CYCLES":
        scene.cycles.samples = CYCLES_SAMPLES
        scene.cycles.use_denoising = True
        # Glass needs enough bounces to pass through two faces and still pick up
        # the interior behind it; the default 4 transmission bounces clips panes
        # to black where they overlap.
        scene.cycles.max_bounces = 12
        scene.cycles.transmission_bounces = 12
        scene.cycles.transparent_max_bounces = 12
        scene.cycles.glossy_bounces = 6
        if hasattr(scene.cycles, "blur_glossy"):
            scene.cycles.blur_glossy = 1.0
    elif hasattr(scene, "eevee"):
        for attr, value in (("taa_render_samples", 128), ("use_gtao", True),
                            ("use_raytracing", True)):
            if hasattr(scene.eevee, attr):
                setattr(scene.eevee, attr, value)

    # Filmic-style view transform: raw sRGB blows out the sunlit walls and
    # flattens the glass highlights.
    if hasattr(scene, "view_settings"):
        try:
            scene.view_settings.view_transform = "AgX"
            scene.view_settings.look = "AgX - Punchy"
        except TypeError:
            pass

    scene.world = materials.make_sky_world()

    # The sun MUST light the faces the cameras look at. All views sit at +X/-Y,
    # so they see the south and east facades; the sun therefore has to come from
    # the south-east. With Z rotation -120 deg it came from the north-west and
    # every visible surface sat in shade, lit only by blue skylight — which
    # turned the warm walls cold and killed the glass highlights.
    sun_data = bpy.data.lights.new("Sun", type="SUN")
    sun_data.energy = 3.5
    sun_data.angle = math.radians(1.5)      # a tight disc = crisp glass glints
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.rotation_euler = (math.radians(materials.SUN_ELEV_DEG), 0.0,
                          math.radians(materials.SUN_AZIM_DEG))
    bpy.context.collection.objects.link(sun)

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 40.0
    cam = bpy.data.objects.new("Camera", cam_data)

    # Frame the whole building: pull back proportionally to its size so the
    # camera keeps working when the footprint or floor count changes.
    reach = max(W, D, TOP_Z) * 1.35
    target = Vector((0.0, 0.0, TOP_Z * 0.52))
    eye = Vector((reach * 0.78, -reach * 1.05, TOP_Z * 0.72))
    cam.location = eye
    cam.rotation_euler = (target - eye).normalized().to_track_quat("-Z", "Y").to_euler()
    bpy.context.collection.objects.link(cam)
    scene.camera = cam


def report(objects):
    total_verts = sum(len(o.data.vertices) for o in objects.values() if o)
    print("\n=== high-rise house ===")
    print(f"footprint            : {W:.1f} x {D:.1f} m")
    print(f"floor height         : {H:.1f} m")
    print(f"storeys              : {TOTAL_FLOORS} total")
    print(f"open pilotis floors  : {PILOTIS_FLOORS} (0.0 -> {BASE_Z:.1f} m)")
    print(f"occupied floors      : {TOWER_FLOORS} ({BASE_Z:.1f} -> {TOP_Z:.1f} m)")
    print(f"columns at pilotis   : {len(col_grid(W))} x {len(col_grid(D))} grid, "
          f"{COL_SIZE:.2f} m square")
    print(f"total height         : {TOP_Z + PARAPET_H + 0.22:.2f} m incl. parapet")
    print(f"blank base floor(s)  : {SOLID_BASE_FLOORS} "
          f"({BASE_Z:.1f} -> {BASE_Z + SOLID_BASE_FLOORS * H:.1f} m)")
    print(f"blank top band       : {SOLID_TOP_FLOORS} floors = "
          f"{SOLID_TOP_FLOORS * H:.1f} m "
          f"({TOP_Z - SOLID_TOP_FLOORS * H:.1f} -> {TOP_Z:.1f} m)")
    print(f"glazed floors        : {TOWER_FLOORS - SOLID_BASE_FLOORS - SOLID_TOP_FLOORS}")
    print(f"corner piers         : {PIER_LONG:.1f} m on long facades / "
          f"{PIER_SHORT:.1f} m on short facades")
    print(f"long-facade margins  : {PIER_LONG:.1f} m left/right, "
          f"{SOLID_BASE_FLOORS * H:.1f} m below, {SOLID_TOP_FLOORS * H:.1f} m above")
    print(f"clear window opening : {OPEN_W:.1f} m (long face) / {OPEN_D:.1f} m (short face)")
    print(f"panes per floor      : {WINDOWS_LONG} long face / {WINDOWS_SHORT} short face")
    print(f"pane pitch           : {PANE_PITCH:.2f} m (= pane width; mullions are "
          f"{MULLION_W:.2f} m caps over the joints)")
    print(f"clear internal depth : {D - 2 * WALL_T:.2f} m (inside face to inside face)")
    print(f"derivation           : W = {WINDOWS_LONG} x {PANE_W:.0f} + 2 x "
          f"{PIER_LONG:.0f} = {W:.0f} m,  D = {WINDOWS_SHORT} x {PANE_W:.0f} + 2 x "
          f"{PIER_SHORT:.0f} = {D:.0f} m")
    print(f"clear glass per pane : {PANE_W:.2f} m x {WIN_H:.2f} m (fixed module, "
          "same on all facades)")
    print(f"panes per floor total: {2 * (WINDOWS_LONG + WINDOWS_SHORT)} around the building")
    print("per-floor bands      : "
          f"{SPANDREL_H:.2f} solid / {VENT_H:.2f} vent / {WIN_H:.2f} window / "
          f"{VENT_H:.2f} vent / {SPANDREL_H:.2f} solid")
    print(f"window centre        : {WIN_Z + WIN_H / 2:.2f} m above each floor "
          f"(mid-floor = {H / 2:.2f} m)")
    print(f"objects / vertices   : {len([o for o in objects.values() if o])} / {total_verts}")
    print("=======================\n")


def main():
    objects = build()
    setup_render()
    report(objects)

    os.makedirs(OUT_DIR, exist_ok=True)
    blend_path = os.path.join(OUT_DIR, "highrise_house.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT_DIR, "highrise_house.glb"),
        export_format="GLB", use_selection=False)

    if "--no-render" not in sys.argv:
        bpy.context.scene.render.filepath = os.path.join(OUT_DIR, "preview.png")
        bpy.ops.render.render(write_still=True)

    print(f"saved -> {blend_path}")


if __name__ == "__main__":
    main()
