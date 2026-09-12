"""Build an editable, image-led approximation of MVRDV's The Stack proposal.

The competition entry has no as-built drawings. The massing follows the
orthographic elevation sheet in the MVRDV gallery: measured 321 px wide, 94 px
deep and 992 px tall against the published 356.8 m height, giving a slender
slab of about 115 x 34 m. The depth is deliberately widened to 40 m: the
drawing's 34 m slab is implausibly thin for a 321.8 m tower's gravity and wind
loads, and the client asked for a 40 m short side. The storey program sets the
height: 14 mall floors at 5 m, 25 office floors at 5 m and 29 apartment floors
at 4 m make a top plate at 311 m, with the glass running on to the 321.8 m top
over 68 floors.

The identity of the building is its facade: the exterior is a vertical stack of
horizontal "neighbourhood" bands, each detailed differently (glazed retail base
with escalators, vertical shading fins, a diamond diagrid, planted sky gardens,
a louvre band with a diamond void, tall fins, and the masonry apartment band
pierced by one large apartment void, under the flat planted City Plaza roof).
This module builds that exterior first; the interior is intentionally
schematic.
"""

import argparse
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import materials


OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
BLEND_PATH = os.path.join(OUT_DIR, "the_stack.blend")

# Image-scaled envelope (see module docstring). The elevation sheet gives a
# front width of 321 px and a side width of 94 px against a 992 px = 356.8 m
# height, i.e. 115.5 x 33.8 m, so the width is 115 m; the depth is widened from
# that reading to 40 m for load plausibility (client direction).
WIDTH, DEPTH, HEIGHT = 115.0, 40.0, 321.8

# Program and storey heights. Retail/mall at the base, offices through the
# middle, apartments at the top; the brief sets 5 m for mall and offices and
# 4 m as the apartment minimum. 14 mall floors, 25 office floors and 29
# apartment floors make 68 floors and a top plate at 311 m; the glass runs on
# to the 321.8 m top, so the crown is a two-storey glazed volume under the deck.
MALL_H, OFFICE_H, APARTMENT_H = 5.0, 5.0, 4.0
MALL_FLOORS, OFFICE_FLOORS, APARTMENT_FLOORS = 14, 25, 29
LEVEL_BASE = MALL_FLOORS * MALL_H                            # 70 m
LEVEL_APARTMENT = LEVEL_BASE + OFFICE_FLOORS * OFFICE_H      # 195 m
LEVEL_ROOF = LEVEL_APARTMENT + APARTMENT_FLOORS * APARTMENT_H  # 311 m

# The apartment band's vertical mullion grid; the void snaps to it. The
# bay is two 7 m modules wide, so every window is a long strip rather than a
# single module.
BAND_BAY = 2 * WIDTH / round(WIDTH / 7.0)                    # 14.375 m

# One large void cut through the middle two bays of the upper apartment band,
# running the full depth. Each is (x centre, z centre, width, height); the
# opening edges land on the facade grid, and three apartment floors stay
# connected above and below the void.
VOID_KEEP_FLOORS = 3
VOID_BOTTOM = LEVEL_APARTMENT + VOID_KEEP_FLOORS * APARTMENT_H   # 207 m
VOID_TOP = LEVEL_ROOF - VOID_KEEP_FLOORS * APARTMENT_H           # 307 m
VOIDS = (
    (0.0, (VOID_BOTTOM + VOID_TOP) / 2, 2 * BAND_BAY,
     VOID_TOP - VOID_BOTTOM),
)

# The mall is a stack of retail floors around a central escalator atrium, so
# the long escalator still reads through the glazing.
MALL_VOID_X, MALL_VOID_Y = 30.0, 14.0

# The base curtain wall groups its frosted glass three storeys high, on the
# floor plates. Four groups cover the top twelve mall storeys; the lowest
# storeys are left as openwork, per the client direction.
BASE_GLASS_GROUPS = 4
BASE_GROUP_H = 3 * MALL_H                                    # 15 m

# Office and apartment ceiling lighting, following the house reference: a grid
# of small emissive panels on every storey ceiling, each independently lit
# daylight, lit warm, or switched off. The panels stay installed when off.
ROOM_LIGHT_W = 1.4
ROOM_LIGHT_H = 0.10
ROOM_LIGHT_PITCH = 3.5
ROOM_LIGHT_CLEAR = 0.6
ROOM_LIGHT_SEED = 20260823
ROOM_LIGHT_ON_RATIO = 0.5
# The house strength (100) clips both colours to white under AgX; this lower
# value keeps the cool-white / warm-white difference readable while still lit.
ROOM_LIGHT_STRENGTH = 8.0

# The mall ceilings are continuous luminous rings that follow each ring slab
# around the escalator atrium, all lit and bright rather than fragmented.
MALL_GLOW_CLEAR = 0.3


def storey_levels():
    """Every floor level from the ground up, one entry per storey."""
    levels, z = [], 0.0
    for floors, height in ((MALL_FLOORS, MALL_H), (OFFICE_FLOORS, OFFICE_H),
                           (APARTMENT_FLOORS, APARTMENT_H)):
        for _ in range(floors):
            z += height
            levels.append(round(z, 3))
    return levels


# Facade band boundaries (m), on the storey grid where they divide a zone.
LEVEL_RETAIL = 75.0
LEVEL_OFFICE_LOW = 95.0
LEVEL_OFFICE_HIGH = 135.0
LEVEL_HOTEL_HIGH = 175.0

# Fully open refuge storeys, one directly above the mall and one directly below
# the apartment block, each one office storey tall. They carry no facade at all,
# so the block above reads as lifted clear of the one below.
REFUGE_MALL = (LEVEL_BASE, LEVEL_BASE + OFFICE_H)                 # 70-75 m
REFUGE_APARTMENT = (LEVEL_APARTMENT - OFFICE_H, LEVEL_APARTMENT)  # 190-195 m

# (z0, z1, band style) from the ground up, in the order read off the physical
# facade model: base, refuge, trees, diagrid, the vertical-fin office block,
# the louvre band with the eye, refuge, then the masonry band that runs to the
# flat top.
BANDS = (
    (0.0, LEVEL_BASE, "base"),
    (REFUGE_MALL[0], REFUGE_MALL[1], "refuge"),
    (LEVEL_RETAIL, LEVEL_OFFICE_LOW, "garden"),
    (LEVEL_OFFICE_LOW, LEVEL_OFFICE_HIGH, "diagrid"),
    (LEVEL_OFFICE_HIGH, LEVEL_HOTEL_HIGH, "fins"),
    (LEVEL_HOTEL_HIGH, REFUGE_APARTMENT[0], "louver"),
    (REFUGE_APARTMENT[0], REFUGE_APARTMENT[1], "refuge"),
    (LEVEL_APARTMENT, HEIGHT, "brick"),
)

FACES = ("N", "S", "E", "W")
VIEW_NAMES = ("preview",)


# ---------------------------------------------------------------------------
# Geometry helpers (data-level, so thousands of facade elements stay fast)
# ---------------------------------------------------------------------------

_CUBE_VERTS = ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
               (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1))
_CUBE_FACES = ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
               (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0))


def _link(mesh, name):
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def cube(name, loc, dims, mat, bevel=0.0):
    mesh = bpy.data.meshes.new(name)
    hx, hy, hz = dims[0] / 2, dims[1] / 2, dims[2] / 2
    verts = [(vx * hx, vy * hy, vz * hz) for vx, vy, vz in _CUBE_VERTS]
    mesh.from_pydata(verts, [], _CUBE_FACES)
    mesh.update()
    mesh.materials.append(mat)
    obj = _link(mesh, name)
    obj.location = loc
    if bevel:
        mod = obj.modifiers.new("Soft architectural edges", "BEVEL")
        mod.width, mod.segments = bevel, 2
    return obj


def merged_boxes(name, items, mat):
    """One mesh holding many boxes, so a dense field of light panels stays a
    single object instead of thousands. Each item is (location, dimensions)."""
    verts, faces = [], []
    for loc, dims in items:
        base = len(verts)
        hx, hy, hz = dims[0] / 2, dims[1] / 2, dims[2] / 2
        verts.extend((loc[0] + vx * hx, loc[1] + vy * hy, loc[2] + vz * hz)
                     for vx, vy, vz in _CUBE_VERTS)
        faces.extend(tuple(base + i for i in face) for face in _CUBE_FACES)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.materials.append(mat)
    return _link(mesh, name)


def beam(name, start, end, radius, mat):
    start, end = Vector(start), Vector(end)
    delta = end - start
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8,
                          radius1=radius, radius2=radius, depth=delta.length)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(mat)
    obj = _link(mesh, name)
    obj.location = (start + end) / 2
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = delta.to_track_quat("Z", "Y")
    return obj


def brace(name, start, end, width, depth, mat):
    """A rectangular steel member from start to end: width runs in the brace
    plane, depth across it, so the X reads as flat structural members."""
    start, end = Vector(start), Vector(end)
    delta = end - start
    mesh = bpy.data.meshes.new(name)
    verts = [(vx * width / 2, vy * depth / 2, vz * delta.length / 2)
             for vx, vy, vz in _CUBE_VERTS]
    mesh.from_pydata(verts, [], _CUBE_FACES)
    mesh.update()
    mesh.materials.append(mat)
    obj = _link(mesh, name)
    obj.location = (start + end) / 2
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = delta.to_track_quat("Z", "Y")
    return obj


def sphere(name, loc, radius, mat):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=radius)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(mat)
    obj = _link(mesh, name)
    obj.location = loc
    return obj


# ---------------------------------------------------------------------------
# Facade frame: local (u, normal) coordinates on each of the four faces
# ---------------------------------------------------------------------------

# One exterior plane shared by every band: glass, frame, louvre, lattice, fin
# and garden-tree outer faces are all coplanar, so nothing stands proud of the
# facade. The glass is set back a hair so the opaque frame still reads in front
# of it without the two surfaces z-fighting.
FACADE = 0.30
GLASS_BACK = 0.01
GLASS_T = 0.12

# Every frame member shares one section, matching the diagrid's square depth, so
# no band reads deeper than another.
FRAME_DEPTH = 0.44
FRAME_BLADE_W = 0.18

# Every face runs a little past the building corner so the bands of two adjacent
# faces overlap and read as one continuous sharp corner. The few centimetres
# kept back keep the overlapping faces from ever landing exactly coplanar.
CORNER_EXT = FACADE - 0.03


def face_geom(face):
    """Return (origin(x,y), u_dir, normal, face_length, outward_bias)."""
    if face == "N":
        return ((0.0, DEPTH / 2), (1.0, 0.0), (0.0, 1.0),
                WIDTH + 2 * CORNER_EXT, 0.0)
    if face == "S":
        return ((0.0, -DEPTH / 2), (1.0, 0.0), (0.0, -1.0),
                WIDTH + 2 * CORNER_EXT, 0.0)
    if face == "E":
        return ((WIDTH / 2, 0.0), (0.0, 1.0), (1.0, 0.0),
                DEPTH + 2 * CORNER_EXT, 0.0)
    return ((-WIDTH / 2, 0.0), (0.0, 1.0), (-1.0, 0.0),
            DEPTH + 2 * CORNER_EXT, 0.0)


def face_point(face, u, z, out=0.0):
    (ox, oy), (ux, uy), (nx, ny), _, bias = face_geom(face)
    out += bias
    return (ox + ux * u + nx * out, oy + uy * u + ny * out, z)


def panel(name, face, u0, u1, z0, z1, outer, thick, mat):
    """A rectangular panel whose outer face sits on the given plane: every
    visible element uses the shared facade plane, so nothing stands proud."""
    (ox, oy), (ux, uy), (nx, ny), _, bias = face_geom(face)
    out = outer - thick + bias
    uc = (u0 + u1) / 2
    cx = ox + ux * uc + nx * (out + thick / 2)
    cy = oy + uy * uc + ny * (out + thick / 2)
    u_len, z_len = abs(u1 - u0), abs(z1 - z0)
    dims = (u_len, thick, z_len) if face in ("N", "S") else (thick, u_len, z_len)
    return cube(name, (cx, cy, (z0 + z1) / 2), dims, mat)


def beamf(name, face, u0, z0, u1, z1, radius, mat, outer=FACADE):
    """A facade member with a square section (never a round tube) whose outer
    face lies on the given plane and whose depth runs along the face normal, so
    the frame stays flat and flush with the glass."""
    (ox, oy), (ux, uy), (nx, ny), _, bias = face_geom(face)
    side = 2 * radius
    normal = Vector((nx, ny, 0.0)).normalized()
    start = Vector(face_point(face, u0, z0, outer - side / 2))
    end = Vector(face_point(face, u1, z1, outer - side / 2))
    delta = end - start
    length = delta.length
    if length < 1e-6:
        return None
    z_axis = delta / length
    x_axis = normal.cross(z_axis).normalized()
    y_axis = z_axis.cross(x_axis).normalized()
    mesh = bpy.data.meshes.new(name)
    verts = [(vx * side / 2, vy * side / 2, vz * length / 2)
             for vx, vy, vz in _CUBE_VERTS]
    mesh.from_pydata(verts, [], _CUBE_FACES)
    mesh.update()
    mesh.materials.append(mat)
    obj = _link(mesh, name)
    obj.matrix_world = Matrix.Translation((start + end) / 2) @ Matrix((
        (x_axis.x, y_axis.x, z_axis.x, 0.0),
        (x_axis.y, y_axis.y, z_axis.y, 0.0),
        (x_axis.z, y_axis.z, z_axis.z, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    ))
    return obj


# ---------------------------------------------------------------------------
# Through-hole footprints in face-local (u, z) space
# ---------------------------------------------------------------------------

def void_holes(face):
    """(u0, u1, z0, z1) openings cut by the apartment void. The void runs
    through the depth, so only the long N/S faces are pierced."""
    if face not in ("N", "S"):
        return []
    return [(x - w / 2, x + w / 2, z - h / 2, z + h / 2)
            for x, z, w, h in VOIDS]


def u_intervals(u0, u1, holes):
    """The complementary u-intervals of [u0, u1] outside a set of (a, b)
    spans, used to cut horizontal members around the tunnel openings."""
    cur, out = u0, []
    for a, b in sorted(holes):
        if a > cur:
            out.append((cur, a))
        cur = max(cur, b)
    if cur < u1:
        out.append((cur, u1))
    return out


def rects_outside(u0, u1, z0, z1, holes):
    """Split a rectangle around non-overlapping holes (guillotine on z), so
    the masonry backing is built as pieces rather than one pierced panel."""
    if not holes:
        return [(u0, u1, z0, z1)]
    zs = sorted({z0, z1} | {c for _, _, c, _ in holes} | {d for _, _, _, d in holes})
    out = []
    for a, b in zip(zs, zs[1:]):
        zc = (a + b) / 2
        band = [(p, q) for p, q, c, d in holes if c < zc < d]
        for p, q in u_intervals(u0, u1, band):
            out.append((p, q, a, b))
    return out


# ---------------------------------------------------------------------------
# The band builders
# ---------------------------------------------------------------------------

def band_base(face, z0, z1, mats):
    """Frosted glass curtain wall over the base hall, framed like the apartment
    band: white blade mullions of the same section, with the glass grouped three
    storeys high and aligned to the floor plates. Four groups cover the top
    twelve mall storeys; the lowest storeys are left as openwork. The glass is
    translucent, so the hall reads as a lit volume rather than a hole."""
    length = face_geom(face)[3]
    glazed_bottom = z1 - BASE_GLASS_GROUPS * BASE_GROUP_H        # 10 m
    # White blade mullions on the base module, running the full height so the
    # unglazed lowest storeys read as openwork.
    n = max(1, round(length / 4.2))
    step = length / n
    for i in range(n + 1):
        u = -length / 2 + i * step
        panel(f"{face}_Base_Mullion", face, u - FRAME_BLADE_W / 2,
              u + FRAME_BLADE_W / 2, z0, z1, FACADE, FRAME_DEPTH,
              mats["apartment_frame"])
    # A transom on every glazed group line, on the floor plates.
    for k in range(BASE_GLASS_GROUPS + 1):
        zb = glazed_bottom + k * BASE_GROUP_H
        panel(f"{face}_Base_Transom", face, -length / 2, length / 2,
              zb - FRAME_BLADE_W / 2, zb + FRAME_BLADE_W / 2, FACADE,
              FRAME_DEPTH, mats["apartment_frame"])
    # Frosted glass, one three-storey panel per group.
    for k in range(BASE_GLASS_GROUPS):
        za = glazed_bottom + k * BASE_GROUP_H
        panel(f"{face}_Base_Glass", face, -length / 2, length / 2, za,
              za + BASE_GROUP_H, FACADE - GLASS_BACK, 0.10,
              mats["glass_frost"])


def base_interior(mats):
    """The transparent base hall seen through its glass: one very long
    escalator climbs the full length, a return flight crosses it, and a white
    stair block sits at the foot, all lit warmly from within."""
    # One very long escalator climbing the whole hall: two close side beams
    # with handrails and a run of short treads across them.
    for dy in (-1.7, 1.7):
        beam("Stack_Base_Escalator", (-28, dy, 3), (28, dy, 64), 1.5,
             mats["core"])
        beam("Stack_Base_Escalator_Rail", (-28, dy, 5.6), (28, dy, 66.6),
             0.26, mats["frame"])
    for k in range(1, 26):
        t = k / 26
        beam("Stack_Base_Tread", (-28 + t * 56, -1.7, 3 + t * 61),
             (-28 + t * 56, 1.7, 3 + t * 61), 0.2, mats["core"])
    # A shorter return flight crossing it, with its own landings.
    beam("Stack_Base_Escalator", (-24, 0, 8), (24, 0, 40), 1.6, mats["core"])
    for x in (-24.0, 24.0):
        cube("Stack_Base_Landing", (x, 0, 8), (8, 20, 1.2), mats["slab"])
    cube("Stack_Base_Stair", (-12, 0, 4.5), (28, 18, 9), mats["slab"])


def room_light_state(floor_index, i, j):
    """Independent on/off state and colour temperature of one room panel."""
    rng = random.Random(ROOM_LIGHT_SEED + floor_index * 101
                        + i * 10007 + j * 1000003)
    if rng.random() >= ROOM_LIGHT_ON_RATIO:
        return "off"
    return rng.choice(("daylight", "warm"))


def room_ceiling_lights(mats):
    """A grid of panel lights on the ceiling of every office and apartment
    storey, following the house reference. Panels are clipped around the cores
    and the apartment void and merged into one object per light state."""
    slab_half = WIDTH / 2 + FACADE - GLASS_BACK - GLASS_T
    slab_half_y = DEPTH / 2 + FACADE - GLASS_BACK - GLASS_T
    half = ROOM_LIGHT_W / 2
    xs, x = [], -slab_half + ROOM_LIGHT_CLEAR + half
    while x <= slab_half - ROOM_LIGHT_CLEAR - half:
        xs.append(x)
        x += ROOM_LIGHT_PITCH
    ys, y = [], -slab_half_y + ROOM_LIGHT_CLEAR + half
    while y <= slab_half_y - ROOM_LIGHT_CLEAR - half:
        ys.append(y)
        y += ROOM_LIGHT_PITCH
    boxes = {"daylight": [], "warm": [], "off": []}
    for floor_index, zc in enumerate(storey_levels(), start=1):
        if zc <= LEVEL_BASE:
            continue
        z = zc - 0.14 - ROOM_LIGHT_H / 2
        for i, px in enumerate(xs):
            for j, py in enumerate(ys):
                in_core = (abs(px) - half < CORE_X + CORE_WIDTH / 2
                           and abs(py) - half < CORE_DEPTH / 2)
                in_void = any(abs(px - vx) < vw / 2 + half
                              and abs(zc - vz) < vh / 2
                              for vx, vz, vw, vh in VOIDS)
                if in_core or in_void:
                    continue
                state = room_light_state(floor_index, i, j)
                boxes[state].append(((px, py, z),
                                     (ROOM_LIGHT_W, ROOM_LIGHT_W,
                                      ROOM_LIGHT_H)))
    for state, items in boxes.items():
        if items:
            merged_boxes(f"Stack_Room_Lights_{state.capitalize()}", items,
                         mats[f"light_{state}"])


def mall_ceiling_lights(mats):
    """A continuous luminous ceiling ring on every mall storey, following the
    ring slab around the atrium: one bright, fully lit object per floor."""
    slab_half = WIDTH / 2 + FACADE - GLASS_BACK - GLASS_T
    slab_half_y = DEPTH / 2 + FACADE - GLASS_BACK - GLASS_T
    inner, inner_y = slab_half - MALL_GLOW_CLEAR, slab_half_y - MALL_GLOW_CLEAR
    depth = 2 * inner_y
    items = []
    for zc in storey_levels():
        if zc > LEVEL_BASE:
            break
        z = zc - 0.14 - ROOM_LIGHT_H / 2
        for sx in (-1, 1):
            items.append(((sx * (MALL_VOID_X + inner) / 2, 0, z),
                          (inner - MALL_VOID_X, depth, ROOM_LIGHT_H)))
        for sy in (-1, 1):
            items.append(((0, sy * (MALL_VOID_Y + inner_y) / 2, z),
                          (2 * MALL_VOID_X, inner_y - MALL_VOID_Y,
                           ROOM_LIGHT_H)))
    merged_boxes("Stack_Mall_Ceiling_Lights", items, mats["glow"])


def band_diagrid(face, z0, z1, mats):
    """Diamond diagrid lattice over glazing, one diamond row per storey so the
    diamond crossings land on the floor plates. The horizontal pitch matches the
    storey height to keep the diamonds square."""
    length = face_geom(face)[3]
    panel(f"{face}_Diagrid_Glass", face, -length / 2, length / 2, z0, z1,
          FACADE - GLASS_BACK, 0.12, mats["glass_cool"])
    nz = max(1, sum(1 for z in storey_levels() if z0 < z <= z1))
    dz = (z1 - z0) / nz
    nu = max(1, round(length / dz))
    du = length / nu
    m = FRAME_DEPTH / 2
    for i in range(nu):
        for j in range(nz):
            u0 = -length / 2 + i * du
            u1 = u0 + du
            za = z0 + j * dz
            zb = za + dz
            um, zm = (u0 + u1) / 2, (za + zb) / 2
            beamf(f"{face}_Diagrid", face, u0, zm, um, zb, m, mats["frame"])
            beamf(f"{face}_Diagrid", face, um, zb, u1, zm, m, mats["frame"])
            beamf(f"{face}_Diagrid", face, u1, zm, um, za, m, mats["frame"])
            beamf(f"{face}_Diagrid", face, um, za, u0, zm, m, mats["frame"])


def arc_beam(name, face, p0, p1, ctrl, radius, mat, outer, steps=4):
    """A curved member: a chain of short beams along a quadratic Bezier from
    p0 to p1 bent through ctrl, so branches fork in smooth candelabra arcs
    rather than straight angles."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * ctrl[0] + t * t * p1[0]
        z = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * ctrl[1] + t * t * p1[1]
        pts.append((u, z))
    for a, b in zip(pts, pts[1:]):
        beamf(name, face, a[0], a[1], b[0], b[1], radius, mat, outer)


def forest_tree(face, u, base, top, width, depth, rng, mat, outer):
    """One stylised metal tree drawn like a railway switch diagram: a single
    thick trunk rises, forks, and every resulting line runs all the way to the
    top of the band, so no branch stops in mid-air. The forks are smooth arcs,
    like the arms of an old candelabra."""
    trunk_top = base + (top - base) * rng.uniform(0.30, 0.42)
    beamf(f"{face}_Garden_Tree", face, u, base, u, trunk_top, 0.40, mat, outer)
    n = 2 ** depth
    xs = [u + (i - (n - 1) / 2) * width / max(1, n - 1)
          + rng.uniform(-0.25, 0.25) for i in range(n)]
    z = top
    for level in range(depth):
        z_next = trunk_top + (top - trunk_top) * (1 - (level + 1) / depth)
        parents = [(xs[j] + xs[j + 1]) / 2 for j in range(0, len(xs), 2)]
        radius = 0.18 + 0.22 * (level + 1) / depth
        for j, px in enumerate(parents):
            for child in (xs[2 * j], xs[2 * j + 1]):
                ctrl = ((child + px) / 2 + (child - px) * 0.25,
                        (z + z_next) / 2 + (z - z_next) * 0.18)
                arc_beam(f"{face}_Garden_Tree", face, (child, z), (px, z_next),
                         ctrl, radius, mat, outer, steps=3)
        xs, z = parents, z_next


def band_garden(face, z0, z1, mats):
    """Sky garden: a white-steel line-drawing woodland fixed to the exterior
    skin, over a little recessed planting behind the glass, per the facade
    model photo."""
    length = face_geom(face)[3]
    panel(f"{face}_Garden_Glass", face, -length / 2, length / 2, z0, z1,
          FACADE - GLASS_BACK, 0.12, mats["glass_cool"])
    rng = random.Random(4200 + FACES.index(face))
    n = max(3, round(length / 5.5))
    step = length / n
    for i in range(n):
        u = -length / 2 + (i + 0.5) * step + rng.uniform(-0.6, 0.6)
        forest_tree(face, u, z0 + 0.5, z1 - 0.15,
                    step * rng.uniform(0.72, 1.0), rng.randint(2, 3),
                    rng, mats["fin"], FACADE)
    # A sparse, recessed planting so the glazing still reads as a garden.
    m = max(1, n // 3)
    for i in range(m):
        u = -length / 2 + (i + 0.5) * length / m
        h = rng.uniform(2.5, (z1 - z0) * 0.5)
        beam(f"{face}_Garden_Trunk", face_point(face, u, z0, -1.6),
             face_point(face, u, z0 + 1.2 + h, -1.6), 0.16, mats["trunk"])
        sphere(f"{face}_Garden_Canopy",
               face_point(face, u, z0 + 2.0 + h, -1.6),
               rng.uniform(1.1, 1.8), mats["foliage"])


def band_louver(face, z0, z1, mats):
    """Horizontal louvres with the central inverted-triangle eye."""
    length = face_geom(face)[3]
    panel(f"{face}_Louver_Glass", face, -length / 2, length / 2, z0, z1,
          FACADE - GLASS_BACK, 0.12, mats["glass_cool"])
    z = z0 + 1.0
    while z < z1:
        beamf(f"{face}_Louver", face, -length / 2, z, length / 2, z, 0.16,
              mats["louver"])
        z += 1.6
    # Inverted triangle ("the eye") on the two wide faces only: its base spans
    # the clear width between the two service cores and its apex points down,
    # with the same top and bottom margins the diamond eye used to keep.
    if face in ("N", "S"):
        inset = (z1 - z0) * 0.2
        ztop, zbot = z1 - inset, z0 + inset
        du = CORE_SPAN / 2
        beamf(f"{face}_Eye", face, -du, ztop, du, ztop, 0.3, mats["frame"])
        beamf(f"{face}_Eye", face, -du, ztop, 0, zbot, 0.3, mats["frame"])
        beamf(f"{face}_Eye", face, du, ztop, 0, zbot, 0.3, mats["frame"])


def band_fins(face, z0, z1, mats):
    """Tall vertical fins, flat in the shared facade plane."""
    length = face_geom(face)[3]
    panel(f"{face}_Fins_Glass", face, -length / 2, length / 2, z0, z1,
          FACADE - GLASS_BACK, 0.12, mats["glass_cool"])
    n = max(2, round(length / 1.1))
    for i in range(n + 1):
        u = -length / 2 + i * length / n
        panel(f"{face}_Fin", face, u - 0.09, u + 0.09, z0, z1, FACADE,
              FRAME_DEPTH, mats["fin"])


# Upper apartment band: a fine vertical-strip curtain wall after the Abeno
# Harukas reference. Narrow panes on a 1.25 m module, a transom at every floor
# and at each storey's lower-quarter vision/spandrel split, over a dark glass
# skin so the band reads as vertical strips rather than long horizontal bands.
# Every frame line is a thin blade with real depth, matching the fins band,
# rather than a flat line on the facade plane.
APARTMENT_MULLION_SPACING = 1.25
APARTMENT_SPLIT = 0.25
APARTMENT_BLADE_D = FRAME_DEPTH


def band_brick(face, z0, z1, mats, holes=()):
    """Upper apartment band as a fine vertical-strip curtain wall, per the
    Abeno Harukas reference: narrow vertical panes on a 1.25 m module, a
    transom at every floor and at the lower-quarter vision/spandrel split. The
    upper three quarters are dark vision glass and the lower quarter a light
    blue spandrel panel. The grid is cut around the apartment void."""
    length = face_geom(face)[3]
    levels = [z0] + [z for z in storey_levels() if z0 < z <= z1]
    if levels[-1] < z1:
        levels.append(z1)
    spans = list(zip(levels, levels[1:]))
    spandrel_spans = [(a, a + (b - a) * APARTMENT_SPLIT) for a, b in spans]
    cuts = sorted({round(z, 3) for z in levels}
                  | {round(s, 3) for _, s in spandrel_spans})
    # Curtain-wall skin, split at every floor and spandrel line: dark vision
    # glass above, a light blue spandrel panel in the lower quarter. No solid
    # masonry backing.
    for a, b, c, d in rects_outside(-length / 2, length / 2, z0, z1, holes):
        zs = [c] + [z for z in cuts if c < z < d] + [d]
        for zc0, zc1 in zip(zs, zs[1:]):
            mid = (zc0 + zc1) / 2
            if any(s0 <= mid <= s1 for s0, s1 in spandrel_spans):
                panel(f"{face}_Brick_Spandrel", face, a, b, zc0, zc1,
                      FACADE - GLASS_BACK, 0.10, mats["spandrel"])
            else:
                panel(f"{face}_Brick_Glass", face, a, b, zc0, zc1,
                      FACADE - GLASS_BACK, 0.10, mats["glass_dark"])
    mullion_w, transom_w = FRAME_BLADE_W, FRAME_BLADE_W
    nu = max(1, round(length / APARTMENT_MULLION_SPACING))
    du = length / nu
    # Fine vertical mullions on the pane module, unbroken through all floors.
    for m in range(nu + 1):
        u = -length / 2 + m * du
        skip = sorted((c, d) for a, b, c, d in holes if a < u < b)
        for za, zb in u_intervals(z0, z1, skip):
            panel(f"{face}_Brick_Mullion", face, u - mullion_w / 2,
                  u + mullion_w / 2, za, zb, FACADE, APARTMENT_BLADE_D,
                  mats["apartment_frame"])
    # A transom at every floor line and at each storey's lower-quarter
    # vision/spandrel split. Only the opening's interior is cut, so the bars run
    # unbroken across the void's head and sill, matching the plates behind them.
    for zb in cuts:
        cut = [(a, b) for a, b, c, d in holes if c < zb < d]
        for a, b in u_intervals(-length / 2, length / 2, cut):
            panel(f"{face}_Brick_Transom", face, a, b,
                  max(zb - transom_w / 2, z0), min(zb + transom_w / 2, z1),
                  FACADE, APARTMENT_BLADE_D, mats["apartment_frame"])


def void_linings(mats):
    """Concrete side walls for the apartment void, running the full depth and
    standing a little proud of the facade so no lining face is coplanar with it.
    The head and sill are the floor plates themselves, so each level keeps a
    single slab rather than a slab plus a separate lining."""
    for index, (x, z, w, h) in enumerate(VOIDS):
        depth = DEPTH + 2 * (FACADE + 0.05)
        cube(f"Stack_Void_{index}_Wall_W", (x - w / 2, 0, z),
             (0.4, depth, h), mats["slab"])
        cube(f"Stack_Void_{index}_Wall_E", (x + w / 2, 0, z),
             (0.4, depth, h), mats["slab"])


def band_roof(mats):
    """A planted roof garden standing on the highest floor plate, inside the
    glazed crown. The glass runs on two storeys above that plate, so the top of
    the building is the open glass edge and the trees sit within a ring of glass
    rather than under a ceiling, per the reference."""
    base = LEVEL_ROOF + 0.14
    rng = random.Random(5200)
    for _ in range(14):
        tx = rng.uniform(-(WIDTH - 20) / 2, (WIDTH - 20) / 2)
        ty = rng.uniform(-(DEPTH - 12) / 2, (DEPTH - 12) / 2)
        beam("Stack_Roof_Trunk", (tx, ty, base),
             (tx, ty, base + 2.4), 0.16, mats["trunk"])
        sphere("Stack_Roof_Canopy", (tx, ty, base + 2.8),
               rng.uniform(1.1, 1.7), mats["foliage"])


def band_refuge(face, z0, z1, mats, holes=()):
    """A fully open refuge storey: no facade at all, so the floor plates and the
    cores read straight through and the block above appears lifted off the block
    below. The plates themselves come from the storey program."""


BAND_BUILDERS = {
    "base": band_base,
    "refuge": band_refuge,
    "diagrid": band_diagrid,
    "garden": band_garden,
    "louver": band_louver,
    "fins": band_fins,
    "brick": band_brick,
}


# ---------------------------------------------------------------------------
# Interior (schematic for now) and site
# ---------------------------------------------------------------------------

CORE_X, CORE_WIDTH, CORE_DEPTH, CORE_Y = 33.5, 20.0, 20.0, 0.0
CORE_SPAN = 2 * (CORE_X - CORE_WIDTH / 2)          # 47 m clear between cores
CORE_BRACE_W, CORE_BRACE_D = 3.0, 3.0              # chunky square steel members

# Every X is identical and its height equals the gap to the next X, including
# the gaps at the very bottom and top, so the points where the braces meet the
# cores are evenly spaced down the core: five braces and six gaps make eleven
# equal bands from the ground to the roof.
CORE_BRACE_COUNT = 5
CORE_BRACE_BAND = LEVEL_ROOF / (2 * CORE_BRACE_COUNT + 1)
CORE_BRACE_H = CORE_BRACE_BAND
CORE_BRACE_BAYS = tuple(
    (round((2 * i + 1) * CORE_BRACE_BAND, 3),
     round((2 * i + 2) * CORE_BRACE_BAND, 3))
    for i in range(CORE_BRACE_COUNT))


def core_bracing(mats):
    """Giant spatial X-braces between the two service cores: four diagonals per
    bay, each running from a corner of one core's face to the diagonally
    opposite corner of the other, so the bracing uses the cores' full depth and
    reads as an X in plan, in elevation and from the side alike."""
    x, y = CORE_SPAN / 2, CORE_DEPTH / 2
    pairs = (
        ("A", (-x, -y), (x, y)),
        ("B", (-x, y), (x, -y)),
        ("C", (x, -y), (-x, y)),
        ("D", (x, y), (-x, -y)),
    )
    for index, (z0, z1) in enumerate(CORE_BRACE_BAYS):
        for tag, (sx, sy), (ex, ey) in pairs:
            brace(f"Stack_Core_Brace_{index}_{tag}",
                  (sx, CORE_Y + sy, z0), (ex, CORE_Y + ey, z1),
                  CORE_BRACE_W, CORE_BRACE_D, mats["steel"])


def add_interior(mats):
    """Two service cores on the long axis and one slab per storey. Kept
    deliberately simple: the exterior is the review focus."""
    for side in (-1, 1):
        cube("Stack_Core_West" if side < 0 else "Stack_Core_East",
             (side * CORE_X, CORE_Y, HEIGHT / 2),
             (CORE_WIDTH, CORE_DEPTH, HEIGHT), mats["core"])
    for index, z in enumerate((LEVEL_BASE, LEVEL_OFFICE_LOW,
                               LEVEL_OFFICE_HIGH, LEVEL_HOTEL_HIGH,
                               LEVEL_APARTMENT, LEVEL_ROOF)):
        cube(f"Stack_Core_Transfer_{index}", (0, CORE_Y, z),
             (2 * (CORE_X + CORE_WIDTH / 2), 16, 1.0), mats["steel"])
    core_bracing(mats)
    # One plate per storey. The mall is a full-height glazed atrium, so its
    # levels carry no plates; slabs run from the first office floor to the top
    # and are split around the apartment void so it stays clear. The plates run
    # right out to the glass line so the slab and the facade stay connected.
    slab_half = WIDTH / 2 + FACADE - GLASS_BACK - GLASS_T
    slab_half_y = DEPTH / 2 + FACADE - GLASS_BACK - GLASS_T
    slab_depth = 2 * slab_half_y
    # Mall floors ring a central atrium, so the escalator still reads through
    # the glazing and every retail level is legible.
    for zc in storey_levels():
        if zc > LEVEL_BASE:
            break
        for sx in (-1, 1):
            cube("Stack_Mall_Slab",
                 (sx * (MALL_VOID_X + slab_half) / 2, 0, zc),
                 (slab_half - MALL_VOID_X, slab_depth, 0.28), mats["slab"])
        for sy in (-1, 1):
            cube("Stack_Mall_Slab",
                 (0, sy * (MALL_VOID_Y + slab_half_y) / 2, zc),
                 (2 * MALL_VOID_X, slab_half_y - MALL_VOID_Y, 0.28),
                 mats["slab"])
    # Office and apartment plates, split around the apartment void.
    for zc in storey_levels():
        if zc <= LEVEL_BASE:
            continue
        cut = [(x - w / 2, x + w / 2) for x, z, w, h in VOIDS
               if abs(zc - z) < h / 2]
        for a, b in u_intervals(-slab_half, slab_half, cut):
            cube("Stack_Floor_Slab", ((a + b) / 2, 0, zc),
                 (b - a, slab_depth, 0.28), mats["slab"])


def ground(mats):
    return cube("Ground_Site", (0, 0, -0.45), (WIDTH + 24, DEPTH + 24, 0.8),
                mats["ground"])


# ---------------------------------------------------------------------------
# Scene, cameras, lights
# ---------------------------------------------------------------------------

def frame_viewport(location, target, lens=55):
    """Point the saved 3D viewport at the whole building, matching the preview
    camera, so the file opens on an exterior orbit rather than inside the
    tower."""
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
            space.lens = lens
            space.clip_start = 5.0
            space.clip_end = 6000
            found = True
    if not found:
        print("warning: no 3D viewport found to frame")


def setup_scene(args, mats):
    world = bpy.data.worlds.new("The_Stack_World")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        0.30, 0.42, 0.58, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.7
    bpy.ops.object.light_add(type="SUN", location=(180, -220, 380))
    sun = bpy.context.object
    sun.data.energy = 4.5
    sun.data.angle = math.radians(6.0)
    sun.rotation_euler = (math.radians(52), math.radians(-18),
                          math.radians(-32))

    camera_data = []
    for name, loc, target in (
            ("preview", (340, -560, 210), (0, 0, 175)),):
        bpy.ops.object.camera_add(location=loc)
        cam = bpy.context.object
        cam.name = f"Stack_Camera_{name}"
        # A generous near plane keeps depth precision high across the 600 m
        # view distance, so thin facade offsets do not z-fight.
        cam.data.clip_start, cam.data.clip_end = 5.0, 3000.0
        cam.data.lens = 55
        cam.rotation_euler = (Vector(target) - cam.location).to_track_quat(
            "-Z", "Y").to_euler()
        camera_data.append((name, cam))

    scene = bpy.context.scene
    scene.camera = camera_data[0][1]
    # Save the 3D viewport framed on the whole building (matching the preview
    # camera) so opening the .blend does not start inside the tower.
    frame_viewport((340, -560, 210), (0, 0, 175), lens=55)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 900, 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene["reference_url"] = "https://mvrdv.com/projects/340/the-stack"
    scene["published_height_m"] = 356.8
    scene["model_height_m"] = HEIGHT
    scene["published_levels"] = 77
    scene["floor_count"] = MALL_FLOORS + OFFICE_FLOORS + APARTMENT_FLOORS
    scene["mall_floors"] = MALL_FLOORS
    scene["office_floors"] = OFFICE_FLOORS
    scene["apartment_floors"] = APARTMENT_FLOORS
    scene["storey_heights_m"] = (f"mall {MALL_H}, office {OFFICE_H}, "
                                 f"apartment {APARTMENT_H}")
    scene["estimated_width_m"] = WIDTH
    scene["estimated_depth_m"] = DEPTH
    scene["elevation_width_pixels"] = 321
    scene["elevation_depth_pixels"] = 94
    scene["elevation_height_pixels"] = 992
    scene["facade_bands"] = ",".join(band for _, _, band in BANDS)
    scene["refuge_floors"] = 2
    scene["refuge_levels_m"] = (f"{REFUGE_MALL[0]}-{REFUGE_MALL[1]}, "
                                f"{REFUGE_APARTMENT[0]}-{REFUGE_APARTMENT[1]}")
    scene["depth_override_m"] = DEPTH
    scene["depth_override_note"] = (
        "Elevation sheet reads 34 m; depth widened to 40 m for load "
        "plausibility (client direction).")
    scene["voids"] = len(VOIDS)
    scene["structural_scheme"] = ("Two service cores along the long axis, tied "
                                  "by transfer frames and X-braced between.")
    scene["core_bracing"] = CORE_BRACE_COUNT
    scene["approximation_note"] = (
        "Competition proposal; dimensions and facade bands inferred from MVRDV "
        "elevation, section and model imagery.")
    return dict(camera_data)


def build_materials():
    return {
        "glass_cool": materials.make_glass(
            "Stack_Glass_Cool", engine="BLENDER_EEVEE", tint=(0.34, 0.58, 0.66)),
        "glass_frost": materials.make_frosted_glass(
            "Stack_Glass_Frost", tint=(0.60, 0.65, 0.68), alpha=0.5),
        "glass_dark": materials.make_glass(
            "Stack_Glass_Dark", engine="BLENDER_EEVEE", tint=(0.20, 0.18, 0.16)),
        "frame": materials.make_metal("Stack_Frame", color=(0.62, 0.66, 0.68)),
        "fin": materials.make_metal("Stack_Fin", color=(0.72, 0.76, 0.78)),
        "louver": materials.make_metal("Stack_Louver", color=(0.50, 0.54, 0.56)),
        "dark": materials.make_dark("Stack_Dark_Panel", color=(0.06, 0.06, 0.07)),
        "brick": materials.make_wall("Stack_Masonry", color=(0.55, 0.44, 0.34)),
        "spandrel": materials.make_wall("Stack_Spandrel_Blue",
                                        color=(0.70, 0.79, 0.86)),
        "apartment_frame": materials.make_wall("Stack_Apartment_Frame",
                                               color=(0.92, 0.92, 0.90)),
        "slab": materials.make_concrete("Stack_Slabs", color=(0.36, 0.38, 0.39)),
        "core": materials.make_concrete("Stack_Core", color=(0.20, 0.23, 0.25)),
        "steel": materials.make_metal("Stack_Core_Steel", color=(0.65, 0.68, 0.66)),
        "ground": materials.make_ground("Stack_Ground", color=(0.13, 0.14, 0.13)),
        "light_daylight": materials.make_ceiling_light(
            "Stack_Light_Daylight", materials.CEILING_LIGHT_DAYLIGHT,
            ROOM_LIGHT_STRENGTH),
        "light_warm": materials.make_ceiling_light(
            "Stack_Light_Warm", materials.CEILING_LIGHT_WARM,
            ROOM_LIGHT_STRENGTH),
        "light_off": materials.make_ceiling_light(
            "Stack_Light_Off", (0.055, 0.045, 0.035), 0.0),
        "glow": materials.make_ceiling_light(
            "Stack_Mall_Glow", color=(1.0, 0.72, 0.38), strength=16.0),
        "trunk": materials.make_trunk("Stack_Trunk"),
        "foliage": materials.make_foliage("Stack_Foliage", color=(0.09, 0.30, 0.11)),
    }


def build(args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = build_materials()
    ground(mats)
    add_interior(mats)
    base_interior(mats)
    mall_ceiling_lights(mats)
    room_ceiling_lights(mats)
    for z0, z1, band in BANDS:
        for face in FACES:
            builder = BAND_BUILDERS[band]
            if builder is band_brick:
                builder(face, z0, z1, mats, holes=void_holes(face))
            else:
                builder(face, z0, z1, mats)
    void_linings(mats)
    band_roof(mats)
    cameras = setup_scene(args, mats)
    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    if not args.no_render:
        for view in args.views:
            bpy.context.scene.camera = cameras[view]
            bpy.context.scene.render.filepath = os.path.join(
                OUT_DIR, f"the_stack_{view}.png")
            bpy.ops.render.render(write_still=True)
    print(f"Built The Stack proposal: {len(bpy.data.objects)} objects")
    print(f"Saved editable model: {BLEND_PATH}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("--views", nargs="+", default=list(VIEW_NAMES))
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    build(args)


if __name__ == "__main__":
    main()
