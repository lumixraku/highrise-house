"""Build an editable, image-led approximation of MVRDV's The Stack proposal.

The competition entry has no as-built drawings. The massing follows the
orthographic elevation sheet in the MVRDV gallery: measured 321 px wide, 94 px
deep and 992 px tall against the published 356.8 m height, giving a slender
slab of about 115 x 34 m. The depth is deliberately widened to 40 m: the
drawing's 34 m slab is implausibly thin for a 298.8 m tower's gravity and wind
loads, and the client asked for a 40 m short side. The storey program sets the
height: 10 mall floors at 5 m, 22 office floors at 5 m and 32 apartment floors
at 4 m make a top plate at 288 m, with the glass running on to the 298.8 m top
over 64 floors. The four refuge plazas are two storeys each — a planted garden
deck with a chunky Abeno-style chevron belt truss spanning both storeys above it
— and both storeys wear a folded glass screen rather than an open slot.

The identity of the building is the public route up its middle: two service
cores run along the long axis and, between them, one continuous chain of
escalators climbs the full height from the ground hall to the planted roof,
stopping at four two-storey sky-garden plazas. The exterior is a vertical stack of
horizontal "neighbourhood" bands (glazed retail base around a crisscross
escalator atrium, a planted garden band, a diamond diagrid, planted sky gardens,
tall fins and the apartment band pierced by two offset voids), so the interior
reads as a vertical mall wrapped in a vertical forest rather than a
tower-and-podium.
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
WIDTH, DEPTH = 115.0, 40.0

# Program and storey heights. Retail/mall at the base, offices through the
# middle, apartments at the top; the brief sets 5 m for mall and offices and
# 4 m as the apartment minimum. The floor counts alone set every zone boundary
# and the total height, so changing a count moves the whole stack with it.
# The counts are the rentable storeys: each refuge is two storeys carved out of
# a zone (a planted garden deck and the chevron truss spanning both storeys
# above it), so removing its former open storey drops the stack by one storey
# per refuge.
MALL_H, OFFICE_H, APARTMENT_H = 5.0, 5.0, 4.0
MALL_FLOORS, OFFICE_FLOORS, APARTMENT_FLOORS = 10, 22, 32
LEVEL_BASE = MALL_FLOORS * MALL_H
LEVEL_APARTMENT = LEVEL_BASE + OFFICE_FLOORS * OFFICE_H
LEVEL_ROOF = LEVEL_APARTMENT + APARTMENT_FLOORS * APARTMENT_H
# The glazed crown runs on above the top plate; it is the one height that is not
# a storey count, so the deck sits two-and-a-bit apartment storeys below the top.
CROWN_H = 2.7 * APARTMENT_H
HEIGHT = LEVEL_ROOF + CROWN_H

# The fine vertical mullion module shared by the apartment band and the two
# apartment voids, so every frame line in the upper band lines up.
APARTMENT_MULLION_SPACING = 1.25

# The apartment band's vertical mullion grid; each void snaps to it. The bay is
# a whole number of mullion modules, so the void edges land on mullions and the
# windows beside each opening stay whole rather than being cut in half.
BAND_BAY = 12 * APARTMENT_MULLION_SPACING                    # 15.0 m

# The two service cores run along the long axis. Each core keeps its outer face
# where it is; only the two adjacent (inner) faces are thickened inward, stopped
# a clear margin back from the apartment voids so the public route keeps its
# full width.
CORE_VOID_CLEAR = 5.0
CORE_INNER = BAND_BAY + CORE_VOID_CLEAR
CORE_OUTER = 43.5
CORE_X = (CORE_INNER + CORE_OUTER) / 2
CORE_WIDTH = CORE_OUTER - CORE_INNER
CORE_DEPTH, CORE_Y = 16.0, 0.0
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

# The public route climbs a central shaft between the cores. The shaft runs from
# the top of the retail atrium to the roof, and every office and apartment plate
# is cut by it. In the office zone the route is a set of big crossing diagonals:
# its runs walk the shaft corners in star order, so two long ~30° flights cross
# each other over the void and the route reads lively and interwoven, like the
# lobby atria in the reference. Above the apartment line it reverts to a plain
# one-plane switchback, so the artistry belongs to the public lower shaft.
SPINE_HALF_X, SPINE_HALF_Y = 10.0, 6.0
SPINE_CROSS_X, SPINE_CROSS_Y = 8.0, 3.4   # crisscross rectangle half-extents

# The apartment band carries two offset voids — one against the west core, one
# against the east core — so the tower reads as one prism punctured by two
# openings, not as two towers joined by a bridge. Each is (x0, x1, z0, z1). The
# width is a whole number of mullion modules and the height a whole number of
# apartment storeys, so the opening edges land on the band grid and on floor
# lines. Both were enlarged to more than twice the original 15 x 20 m opening.
# Each opening is now half as wide as the span between the two core faces, so it
# runs from its core's inner face to the centreline; the escalator chain leaves
# the centreline and climbs the opposite half of the shaft to stay clear of it.
# Every vent is centred on a core X-brace bay, so the chunky brace reads in the
# middle of the opening. The lower vent is a free opening in the brick band — a
# few storeys of wall below it, the mid-apartment refuge above; the upper vent
# sits on that refuge's ceiling, as before.
VOID_MODULES = 14
VOID_W = VOID_MODULES * APARTMENT_MULLION_SPACING               # 17.5 m
VOID_LOW_FLOORS, VOID_HIGH_FLOORS = 12, 10
# The fourth refuge, in the middle of the apartment zone: two storeys sitting on
# the lower vent, whose ceiling carries the high void.
REFUGE_MID_OPEN = (LEVEL_APARTMENT + 15 * APARTMENT_H,
                   LEVEL_APARTMENT + 17 * APARTMENT_H)          # 220-228


def _brace_centre(index):
    """Centre height of core X-brace bay `index`."""
    return (2 * index + 1.5) * CORE_BRACE_BAND


def _void_span(index, floors):
    """A vent of `floors` storeys centred on brace bay `index`, snapped to the
    apartment floor lines so its edges land on the band grid."""
    centre = _brace_centre(index)
    z0 = LEVEL_APARTMENT + APARTMENT_H * round(
        (centre - floors * APARTMENT_H / 2 - LEVEL_APARTMENT) / APARTMENT_H)
    return z0, z0 + floors * APARTMENT_H


VOID_LOW_Z0, VOID_LOW_Z1 = _void_span(3, VOID_LOW_FLOORS)       # 172-220
VOID_HIGH_Z0 = REFUGE_MID_OPEN[1]                               # 228
VOID_HIGH_Z1 = VOID_HIGH_Z0 + VOID_HIGH_FLOORS * APARTMENT_H    # 268
VOIDS = (
    (-CORE_INNER, -CORE_INNER + VOID_W, VOID_LOW_Z0, VOID_LOW_Z1),
    (CORE_INNER - VOID_W, CORE_INNER, VOID_HIGH_Z0, VOID_HIGH_Z1),
)

# Abeno Harukas-style perimeter chevron trusses, used for the belt band of every
# refuge: complete upward chevrons with both feet on the lower chord, boundary
# posts and top/bottom chords, at a fixed ~12 m group spacing. The truss spans
# the refuge's full two storeys, so each face reads as one tall claw.
CHEVRON_SPACING = 12.0
CHEVRON_POST_W = 2.20           # chunky, like the Abeno reference
CHEVRON_DIAG_W = 1.20
CHEVRON_CHORD_W = 1.10
# The refuge skin is a vertical sawtooth in plan (a folding screen): its outer
# folds sit on the shared facade plane and its inner folds are drawn back, so
# nothing ever stands proud of the envelope. The truss is set behind the deepest
# fold so it never pierces the glass.
SCREEN_BAY = 3.0                # peak-to-peak spacing of the sawtooth
SCREEN_FOLD = 1.0               # how far the inner fold is drawn back
TRUSS_INSET = SCREEN_FOLD + 0.25

# The mall is a stack of retail floors around a central escalator atrium; the
# retail runs climb it as a rectangular helix, so the public route reads as a
# vertical street through the glazing.
MALL_VOID_X, MALL_VOID_Y = 30.0, 14.0

# The storey-by-storey escalator chains. The retail runs form a rectangular
# helix around the void — a run on each face of the ring, one storey per run at
# a real escalator pitch — so from above the route reads as a "回" that spirals
# up. Every run stays on the ring plate beside the opening, never across it, and
# the spine runs along the building's depth, weaving between the halves of the
# shaft so it stays clear of the two apartment vent voids.
FLIGHT_ANGLE = 30.0
MALL_HELIX_Y = MALL_VOID_Y + 2.4     # N/S lane, on the ring
MALL_HELIX_X = CORE_OUTER + 6.0      # E/W lane, clear of the cores

# The ground level is a single double-height hall: the first mall plate is
# lifted two storeys (10 m) so the base reads as a suspended floor rather than a
# 5 m ground storey, and the ground-to-first-floor trip is served by vertical
# lifts instead of a long escalator.
MALL_GROUND_STOREYS = 2
LEVEL_MALL_FIRST = MALL_GROUND_STOREYS * MALL_H

# Escalator entries from the ground hall up to the suspended first mall plate:
# each is a switchback of two one-storey flights at the real ~30-degree pitch
# (each run about 9 m, one storey's worth), placed in the end halls so the hall
# is reached from both sides without any run spanning the space.
ESCALATOR_ENTRIES = (
    ((46.0, -9.0), (0.0, 1.0)),
    ((50.0, 9.0), (0.0, -1.0)),
    ((-46.0, 9.0), (0.0, -1.0)),
    ((-50.0, -9.0), (0.0, 1.0)),
)

# The base curtain wall groups its frosted glass two storeys high, on the
# floor plates, running from the suspended first mall plate up to the band top
# (the mall plus the garden storeys it wraps); the lowest storeys are left as
# openwork, per the client direction.
BASE_GROUP_H = 2 * MALL_H

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

# The open refuge plates and the top roof are planted decks: a lawn inside a
# perimeter running track, with a scatter of trees.
GARDEN_MARGIN = 0.8
TRACK_W = 1.6
TRACK_INSET = 0.5
# Street lamps line the inner edge of every garden's running track: a slim
# dark pole with a warm glowing head every few metres.
LAMP_H = 3.0
LAMP_POLE_R = 0.06
LAMP_HEAD_R = 0.18
LAMP_SPACING = 9.0
LAMP_INSET = 0.3

# Refuge garden trees grow up through the truss toward the ceiling two storeys
# above the deck; each refuge caps its trees just under its own ceiling.
TREE_MAX_H = 8.5


def storey_levels():
    """Every floor level from the ground up, one entry per storey."""
    levels, z = [], 0.0
    for floors, height in ((MALL_FLOORS, MALL_H), (OFFICE_FLOORS, OFFICE_H),
                           (APARTMENT_FLOORS, APARTMENT_H)):
        for _ in range(floors):
            z += height
            levels.append(round(z, 3))
    return levels


# Every sky-garden plaza is now one two-storey volume: a planted garden deck at
# the bottom, with the chunky chevron belt truss spanning both storeys above it,
# and a folded glass screen wrapping the whole volume. The plate between the two
# storeys is dropped, so the garden opens straight up into the truss. The
# apartment zone carries a fourth refuge in the middle of its height, between the
# two voids.
#
# Office-zone band boundaries: the diagrid band carries the office storeys up to
# the office refuge — its diamond lattice is one band — and the fins run from
# that refuge up to the apartment one.
#
# Each refuge is two storeys tall; the deck is its bottom plate and the ceiling
# its top plate, both of which stay, so the truss and the garden read through the
# folded screen as one tall planted room.
REFUGE_MALL = (LEVEL_BASE - 2 * MALL_H, LEVEL_BASE)                      # 40-50
REFUGE_OFFICE = (LEVEL_BASE + 11 * OFFICE_H, LEVEL_BASE + 13 * OFFICE_H)  # 105-115
REFUGE_APARTMENT = (LEVEL_APARTMENT - 2 * OFFICE_H, LEVEL_APARTMENT)     # 150-160
REFUGE_APARTMENT_MID = REFUGE_MID_OPEN                                   # 208-216
REFUGES = (REFUGE_MALL, REFUGE_OFFICE, REFUGE_APARTMENT,
           REFUGE_APARTMENT_MID)
# One storey height per refuge, and two storeys per refuge.
REFUGE_HEIGHTS = (MALL_H, OFFICE_H, OFFICE_H, APARTMENT_H)
REFUGE_STOREY_H = tuple(2 * h for h in REFUGE_HEIGHTS)
REFUGE_OPEN_H = 0.0
# The garden deck sits on the bottom plate; the belt truss rises from it to the
# ceiling plate. From the bottom up: deck, truss, ceiling.
REFUGE_DECK_LEVELS = tuple(z0 for z0, _ in REFUGES)
REFUGE_CEILING_LEVELS = tuple(z1 for _, z1 in REFUGES)
REFUGE_FLOOR_LEVELS = REFUGE_DECK_LEVELS
# The deck and the ceiling keep their plate; the storey line between them is
# omitted, so the garden and the truss read as one two-storey volume.
REFUGE_DROP_LEVELS = tuple(z0 + h
                           for (z0, _), h in zip(REFUGES, REFUGE_HEIGHTS))
REFUGE_COMPONENT_SPANS = tuple(zip(REFUGE_DECK_LEVELS, REFUGE_CEILING_LEVELS))

# (z0, z1, band style) from the ground up, in the order read off the physical
# facade model: each block's own curtain-wall style, then the folded refuse
# screen, alternating up the stack.
BANDS = (
    (0.0, REFUGE_MALL[0], "base"),
    (REFUGE_MALL[0], REFUGE_MALL[1], "refuge"),
    (REFUGE_MALL[1], REFUGE_OFFICE[0], "garden"),
    (REFUGE_OFFICE[0], REFUGE_OFFICE[1], "refuge"),
    (REFUGE_OFFICE[1], REFUGE_APARTMENT[0], "fins"),
    (REFUGE_APARTMENT[0], REFUGE_APARTMENT[1], "refuge"),
    (REFUGE_APARTMENT[1], REFUGE_APARTMENT_MID[0], "brick"),
    (REFUGE_APARTMENT_MID[0], REFUGE_APARTMENT_MID[1], "refuge"),
    (REFUGE_APARTMENT_MID[1], HEIGHT, "brick"),
)

FACES = ("N", "S", "E", "W")
VIEW_NAMES = ("preview", "facade", "garden", "void", "base")


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


def slab_band(name, start, end, width, thick, mat):
    """A flat rectangular band from start to end: `width` across the run and
    `thick` normal to it (roughly vertical), so an escalator run, its
    balustrades and its landings all read as flat slabs rather than tubes."""
    start, end = Vector(start), Vector(end)
    delta = end - start
    horiz = Vector((delta.x, delta.y, 0.0))
    side = Vector((-horiz.y, horiz.x, 0.0))
    if side.length < 1e-6:
        side = Vector((0.0, 1.0, 0.0))
    side.normalize()
    normal = delta.cross(side)
    if normal.length < 1e-6:
        normal = Vector((0.0, 0.0, 1.0))
    normal.normalize()
    if normal.z < 0:
        normal = -normal
    axis = delta.normalized()
    hw, ht, hl = width / 2, thick / 2, delta.length / 2
    mid = (start + end) / 2
    verts = []
    for i in (-1, 1):
        for j in (-1, 1):
            for k in (-1, 1):
                verts.append(tuple(mid + axis * (hl * i) + side * (hw * j)
                                   + normal * (ht * k)))

    def idx(i, j, k):
        return ((i + 1) // 2) * 4 + ((j + 1) // 2) * 2 + ((k + 1) // 2)

    faces = (
        (idx(-1, -1, -1), idx(-1, -1, 1), idx(-1, 1, 1), idx(-1, 1, -1)),
        (idx(1, -1, -1), idx(1, 1, -1), idx(1, 1, 1), idx(1, -1, 1)),
        (idx(-1, -1, -1), idx(1, -1, -1), idx(1, -1, 1), idx(-1, -1, 1)),
        (idx(-1, 1, -1), idx(-1, 1, 1), idx(1, 1, 1), idx(1, 1, -1)),
        (idx(-1, -1, -1), idx(-1, 1, -1), idx(1, 1, -1), idx(1, -1, -1)),
        (idx(-1, -1, 1), idx(1, -1, 1), idx(1, 1, 1), idx(-1, 1, 1)),
    )
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.materials.append(mat)
    return _link(mesh, name)


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

# Each facade family sits on its own depth plane, so two members of different
# families that cross — the diagrid lattice over its glazing, mullions over
# transoms — never share a face plane. Coplanar, overlapping faces are exactly
# what z-fights, and a 2-6 cm step is far above the depth resolution at the
# 60-600 m review distances, so the offsets remove the flicker without reading
# as depth.
MULLION_OUT = FACADE
TRANSOM_OUT = FACADE - 0.06
GLASS_OUT = FACADE - 0.03
DIAGRID_OUT = FACADE - 0.04
FIN_OUT = FACADE
MULLION_D = FRAME_DEPTH
TRANSOM_D = 0.40
GLASS_D = 0.10
# Band-edge transoms sit a hair inside the shared storey line, so their caps do
# not land on the same plane as the mullions they meet.
SEAM = 0.02

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


def glass_span(face):
    """Half the u-range a band's glass runs: the building dimension, carried on
    past the corner exactly as the frame is, a little less. So the glass of two
    adjacent faces meets in the corner zone and closes it, while its end stays
    clear of the neighbouring face's own member planes (the transom, diagrid,
    glass and fin stand at 0.24, 0.26, 0.27 and 0.30 out), so no cap lands on
    another member's plane."""
    span = WIDTH if face in ("N", "S") else DEPTH
    return span / 2 + CORNER_EXT - 0.05


def face_point(face, u, z, out=0.0):
    (ox, oy), (ux, uy), (nx, ny), _, bias = face_geom(face)
    out += bias
    return (ox + ux * u + nx * out, oy + uy * u + ny * out, z)


def panel(name, face, u0, u1, z0, z1, outer, thick, mat, pad_u=0.0, pad_z=0.0,
          shift_z=0.0):
    """A rectangular panel whose outer face sits on the given plane: every
    visible element uses the shared facade plane, so nothing stands proud. The
    optional pads pull the panel's own edges in a little, so two families that
    meet at a shared edge or storey line do not land on the same cap plane; the
    optional shift slides the whole panel in z by a per-face amount, so two
    faces of the same band do not share a cap plane at a building corner."""
    (ox, oy), (ux, uy), (nx, ny), _, bias = face_geom(face)
    z0, z1 = z0 + shift_z + pad_z, z1 + shift_z - pad_z
    if abs(u1 - u0) > 2 * pad_u:
        u0, u1 = u0 + pad_u, u1 - pad_u
    out = outer - thick + bias
    uc = (u0 + u1) / 2
    cx = ox + ux * uc + nx * (out + thick / 2)
    cy = oy + uy * uc + ny * (out + thick / 2)
    u_len, z_len = abs(u1 - u0), abs(z1 - z0)
    dims = (u_len, thick, z_len) if face in ("N", "S") else (thick, u_len, z_len)
    return cube(name, (cx, cy, (z0 + z1) / 2), dims, mat)


def folded_panel(name, face, u0, o0, u1, o1, z0, z1, thick, mat):
    """One leaf of a folded (sawtooth) screen: a thin box whose outer face runs
    from the face-local plan point (u0, o0) to (u1, o1), its thickness drawn back
    along the face normal. The fold depth is free, so the outer folds can sit
    exactly on the shared facade plane and the inner folds be drawn back — the
    screen reads as a vertical folding fan and never stands proud of the
    envelope."""
    (ox, oy), (ux, uy), (nx, ny), _, bias = face_geom(face)
    n = Vector((nx, ny, 0.0)).normalized()
    o0, o1 = o0 + bias, o1 + bias
    p0 = Vector((ox + ux * u0 + nx * o0, oy + uy * u0 + ny * o0, 0.0))
    p1 = Vector((ox + ux * u1 + nx * o1, oy + uy * u1 + ny * o1, 0.0))
    axis = p1 - p0
    length = axis.length
    if length < 1e-6:
        return None
    axis.normalize()
    up = Vector((0.0, 0.0, 1.0))
    mid = (p0 + p1) / 2 - n * (thick / 2)
    mid.z = (z0 + z1) / 2
    hl, hw, ht = length / 2, (z1 - z0) / 2, thick / 2
    verts = []
    for i in (-1, 1):
        for j in (-1, 1):
            for k in (-1, 1):
                verts.append(tuple(mid + axis * (hl * i) + up * (hw * j)
                                   + n * (ht * k)))

    def idx(i, j, k):
        return ((i + 1) // 2) * 4 + ((j + 1) // 2) * 2 + ((k + 1) // 2)

    faces = (
        (idx(-1, -1, -1), idx(-1, -1, 1), idx(-1, 1, 1), idx(-1, 1, -1)),
        (idx(1, -1, -1), idx(1, 1, -1), idx(1, 1, 1), idx(1, -1, 1)),
        (idx(-1, -1, -1), idx(1, -1, -1), idx(1, -1, 1), idx(-1, -1, 1)),
        (idx(-1, 1, -1), idx(-1, 1, 1), idx(1, 1, 1), idx(1, 1, -1)),
        (idx(-1, -1, -1), idx(-1, 1, -1), idx(1, 1, -1), idx(1, -1, -1)),
        (idx(-1, -1, 1), idx(1, -1, 1), idx(1, 1, 1), idx(-1, 1, 1)),
    )
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.materials.append(mat)
    return _link(mesh, name)


def face_pad(face, base=0.0, step=0.008):
    """The per-face part of a pad: N, S, E and W each step a little further, so
    two bands of the same family meeting at a building corner do not share a cap
    plane either."""
    return base + FACES.index(face) * step


def bar_span(zc, z0, z1, w, pad):
    """A frame bar centred on zc with blade width w, clipped to [z0, z1] and
    pulled off an edge by pad when it lands on the band boundary, so a boundary
    bar and the mullions it meets do not share a cap plane."""
    if zc <= z0 + 1e-6:
        return z0 + pad, z0 + pad + w
    if zc >= z1 - 1e-6:
        return z1 - pad - w, z1 - pad
    return zc - w / 2, zc + w / 2


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
    """(u0, u1, z0, z1) openings cut by the two apartment voids. Each void runs
    through the depth, so only the long N/S faces are pierced."""
    if face not in ("N", "S"):
        return []
    return list(VOIDS)


def x_panel(name, x, normal, u0, u1, z0, z1, thick, mat):
    """A panel on a vertical X-facing plane: its finished face sits at x, its
    thickness runs away from the void along -normal, and u is measured in y, so
    the void side walls can carry the same curtain wall as the exterior."""
    cube(name, (x - normal * thick / 2, (u0 + u1) / 2, (z0 + z1) / 2),
         (thick, abs(u1 - u0), abs(z1 - z0)), mat)


def void_curtain_wall(mats):
    """Dress both X faces of each apartment void in the same curtain wall as the
    exterior apartment band — dark vision glass over a light spandrel on the
    shared 1.25 m mullion module, with white mullions and transoms. The outer
    face keeps the recess clad as before; the inner (shaft-side) face closes the
    shaft off from the open void, and the void's width leaves the public
    escalator's lane clear of it, so the route always climbs indoors. The linings
    sit inside the opening, clear of the core face beyond the void."""
    levels_all = storey_levels()
    for x0, x1, z0, z1 in VOIDS:
        cw0 = z0
        hy = DEPTH / 2
        # Both X side walls of the recess: the outer face keeps the cladding it
        # has always had, the inner face is the lining that closes the shaft.
        for inner, s in ((x0, 1.0), (x1, -1.0)):
            def line(name, d, thick, u0, u1, za, zb, mat,
                     inner=inner, s=s):
                x_panel(name, inner + s * d, -s, u0, u1, za, zb, thick, mat)

            nu = max(1, round(DEPTH / APARTMENT_MULLION_SPACING))
            du = DEPTH / nu
            for m in range(nu + 1):
                u = -DEPTH / 2 + m * du
                line("Stack_Void_CW_Mullion", 0.06, MULLION_D,
                     u - FRAME_BLADE_W / 2, u + FRAME_BLADE_W / 2,
                     cw0 + 0.01, z1 - 0.01, mats["apartment_frame"])
            zs = [cw0] + [z for z in levels_all if cw0 < z < z1] + [z1]
            for a, b in zip(zs, zs[1:]):
                split = a + (b - a) * APARTMENT_SPLIT
                line("Stack_Void_CW_Spandrel", 0.31, GLASS_D,
                     -hy + 0.03, hy - 0.03, a, split, mats["spandrel"])
                line("Stack_Void_CW_Glass", 0.31, GLASS_D,
                     -hy + 0.03, hy - 0.03, split, b, mats["glass_dark"])
            cuts = sorted({round(z, 3) for z in zs}
                          | {round(a + (b - a) * APARTMENT_SPLIT, 3)
                             for a, b in zip(zs, zs[1:])})
            for zc in cuts:
                za, zb = bar_span(zc, cw0, z1, FRAME_BLADE_W, SEAM)
                line("Stack_Void_CW_Transom", 0.04, TRANSOM_D,
                     -hy + 0.015, hy - 0.015, za, zb,
                     mats["apartment_frame"])


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
    the masonry backing is built as pieces rather than one pierced panel. Holes
    are clipped to the rectangle first, so a hole beyond the band's own z-range
    cannot add a spurious slice."""
    clipped = []
    for p, q, c, d in holes:
        c2, d2 = max(c, z0), min(d, z1)
        if c2 < d2:
            clipped.append((p, q, c2, d2))
    if not clipped:
        return [(u0, u1, z0, z1)]
    zs = sorted({z0, z1} | {c for _, _, c, _ in clipped}
                | {d for _, _, _, d in clipped})
    out = []
    for a, b in zip(zs, zs[1:]):
        zc = (a + b) / 2
        band = [(p, q) for p, q, c, d in clipped if c < zc < d]
        for p, q in u_intervals(u0, u1, band):
            out.append((p, q, a, b))
    return out


# ---------------------------------------------------------------------------
# The band builders
# ---------------------------------------------------------------------------

def band_base(face, z0, z1, mats):
    """Frosted glass curtain wall over the base hall, framed like the apartment
    band: white blade mullions of the same section, with the glass grouped two
    storeys high and aligned to the floor plates. The glazing runs from the
    suspended first mall plate up to the band top, which is the top of the
    garden it carries; the lowest storeys are left as openwork. The glass is
    translucent, so the hall and the garden behind it read as a lit volume
    rather than a hole. Extending z1 adds whole two-storey groups, so the same
    style wraps the mall garden without changing the mall glazing below."""
    length = face_geom(face)[3]
    glazed_bottom = LEVEL_MALL_FIRST
    groups = max(1, int(round((z1 - glazed_bottom) / BASE_GROUP_H)))
    # White blade mullions on the base module, running the full height so the
    # unglazed lowest storeys read as openwork.
    n = max(1, round(length / 4.2))
    step = length / n
    for i in range(n + 1):
        u = -length / 2 + i * step
        panel(f"{face}_Base_Mullion", face, u - FRAME_BLADE_W / 2,
              u + FRAME_BLADE_W / 2, z0, z1, MULLION_OUT, MULLION_D,
              mats["apartment_frame"], pad_z=face_pad(face, 0.006))
    # A transom on every glazed group line, on the floor plates.
    for k in range(groups + 1):
        zb = glazed_bottom + k * BASE_GROUP_H
        if zb > z1 + 0.01:
            break
        a, b = bar_span(zb, z0, z1, FRAME_BLADE_W, SEAM)
        panel(f"{face}_Base_Transom", face, -length / 2, length / 2, a, b,
              TRANSOM_OUT, TRANSOM_D, mats["apartment_frame"],
              pad_u=face_pad(face, 0.012, 0.004),
              pad_z=face_pad(face, 0.012, 0.004))
    # Frosted glass, one two-storey panel per group.
    # Frosted glass, one two-storey panel per group. The glass stops on the
    # building dimension, not the corner-extended length, so two faces' glass
    # never overlaps in the corner zone.
    for k in range(groups):
        za = glazed_bottom + k * BASE_GROUP_H
        panel(f"{face}_Base_Glass", face, -glass_span(face), glass_span(face), za,
              min(za + BASE_GROUP_H, z1), GLASS_OUT, GLASS_D,
              mats["glass_frost"], shift_z=face_pad(face, 0.0, 0.006))


def base_interior(mats):
    """The transparent base hall seen through its glass: a white stair block at
    the foot, with the ground-to-first-floor trip served by the six perimeter
    escalator runs rather than a long diagonal across the atrium opening."""
    cube("Stack_Base_Stair", (-8, 0, 4.5), (20, 16, 9), mats["slab"])


_ESCALATOR_SEQ = [0]


def base_escalator(name, start, end, mats):
    """One escalator run, read as a flat inclined band rather than a tube: a
    thin belt deck on two side balustrades with handrails, and a horizontal
    landing at each end so the run visibly meets the floor it serves. Shared by
    the hall escalators, the retail-atrium helix and the spine chain, so
    every run in the building is the same component. Each run's balustrades are
    nudged a hair inboard by a per-run step, so two flights meeting at a landing
    never share a side-face plane."""
    seq = _ESCALATOR_SEQ[0]
    _ESCALATOR_SEQ[0] += 1
    trim = (seq % 24) * 0.002
    lstep = (seq % 9) * 0.01
    start, end = Vector(start), Vector(end)
    delta = end - start
    horiz = Vector((delta.x, delta.y, 0.0))
    side = Vector((-horiz.y, horiz.x, 0.0))
    if side.length < 1e-6:
        side = Vector((0.0, 1.0, 0.0))
    side.normalize()
    normal = delta.cross(side)
    normal.normalize()
    if normal.z < 0:
        normal = -normal
    half_w, deck_t, rail_h = 1.7, 0.30, 1.10
    slab_band(f"{name}_Belt", start, end, 2 * (half_w - trim - 0.02), deck_t,
              mats["core"])
    for s in (-1, 1):
        edge = side * (s * (half_w - 0.12 - trim))
        base = edge + normal * (deck_t / 2 + rail_h / 2)
        slab_band(f"{name}_Balustrade", start + base, end + base, 0.24, rail_h,
                  mats["frame"])
        top = edge + normal * (deck_t / 2 + rail_h + 0.06)
        slab_band(f"{name}_Handrail", start + top, end + top, 0.20, 0.12,
                  mats["core"])
    for tag, point, step in (("Bottom", start, -1.0), ("Top", end, 1.0)):
        far = Vector(point) + side * 0.0 + horiz.normalized() * (
            (1.4 + lstep) * step)
        # A run that starts between the cores must not bury its landing in the
        # concrete, so clamp the extension to the core-free central zone.
        if abs(point.x) <= CORE_INNER + 0.01:
            limit = CORE_INNER - 0.1
            far.x = max(-limit, min(limit, far.x))
        # Pull the landing's storey-line cap back by the same per-run step, so
        # the two flights that meet at a turn do not share a cap plane.
        p0 = Vector(point) + horiz.normalized() * trim
        lw = 2 * half_w - (0.02 if tag == "Bottom" else 0.005)
        slab_band(f"{name}_Landing_{tag}", p0, far, lw, 0.14,
                  mats["frame"])


def base_escalators(mats):
    """Escalator entries from the ground hall up to the suspended first mall
    plate. Each entry is a switchback of two one-storey flights at the real
    ~30-degree pitch, so every run is about one storey long and nothing spans
    the hall."""
    run = MALL_H / math.tan(math.radians(FLIGHT_ANGLE))
    step = 2 * 1.7 + 0.6
    for index, (start, (dx, dy)) in enumerate(ESCALATOR_ENTRIES):
        p0 = Vector((start[0], start[1], 0.5))
        d = Vector((dx, dy, 0.0)).normalized()
        side = Vector((-d.y, d.x, 0.0))
        if side.x * start[0] < 0.0:
            side = -side
        p1 = p0 + d * run + Vector((0.0, 0.0, MALL_H))
        base_escalator(f"Stack_Base_Escalator_Up_{index}_A", p0, p1, mats)
        p2 = p1 + side * step
        p3 = p2 - d * run + Vector((0.0, 0.0, MALL_H))
        base_escalator(f"Stack_Base_Escalator_Up_{index}_B", p2, p3, mats)


def mall_escalators(mats):
    """The retail atrium climbs as one rectangular helix: a run hugs each face
    of the ring, each rising one storey at a real ~30-degree escalator pitch, and
    the four runs of a loop carry the route round and up, so from above it reads
    as a "回" spiralling to the mall top. Every run stays on the ring plate
    beside the opening, never across it, so the route is always inside the room
    rather than over the draughty void."""
    levels = [z for z in storey_levels()
              if LEVEL_MALL_FIRST <= z <= REFUGE_MALL[0]
              and z not in REFUGE_DROP_LEVELS]
    half = MALL_H / math.tan(math.radians(FLIGHT_ANGLE)) / 2.0
    legs = (
        ((-half, -MALL_HELIX_Y), (half, -MALL_HELIX_Y)),
        ((MALL_HELIX_X, -half), (MALL_HELIX_X, half)),
        ((half, MALL_HELIX_Y), (-half, MALL_HELIX_Y)),
        ((-MALL_HELIX_X, half), (-MALL_HELIX_X, -half)),
    )
    for i in range(len(levels) - 1):
        z0, z1 = levels[i], levels[i + 1]
        (x0, y0), (x1, y1) = legs[i % 4]
        base_escalator(f"Stack_Mall_Escalator_{i}",
                       (x0, y0, z0), (x1, y1, z1), mats)


def spine_route(levels):
    """Landing (x, y) for every storey level. In the public lower shaft — the
    office zone — the route walks the shaft corners in star order: two long
    diagonals cross over the centre, interleaved with runs along the two long
    edges, all at a real escalator's ~30° pitch. Above the apartment line it
    settles into a plain one-plane switchback along the depth."""
    a, b = SPINE_CROSS_X, SPINE_CROSS_Y
    cross = ((-a, -b), (0.0, 0.0), (a, b), (0.0, b),
             (-a, b), (0.0, 0.0), (a, -b), (0.0, -b))
    split = sum(1 for z in levels if z < LEVEL_APARTMENT)
    # Phase the star so its last landing before the apartment line is a corner:
    # the transition run then drops into the switchback as a full ~8 m diagonal
    # rather than a short, over-steep hop off the centre.
    offset = (1 - split) % len(cross)
    route = []
    for i in range(len(levels)):
        if i < split:
            route.append(cross[(i + offset) % len(cross)])
        else:
            route.append((0.0, -b if (i - split) % 2 == 0 else b))
    return route


def spine_escalators(mats):
    """The public route above the retail base: one escalator run per storey. In
    the office zone it is a long crossed-diagonal composition — the flights walk
    the shaft corners in star order, so two ~30° diagonals cross in the middle of
    the shaft and the run along each long edge interlocks with them. Above the
    apartment line it is a plain one-plane switchback along the depth, so the
    artistry reads only in the public lower shaft."""
    levels = [z for z in storey_levels() if z >= LEVEL_BASE]
    route = spine_route(levels)
    for i in range(len(levels) - 1):
        z0, z1 = levels[i], levels[i + 1]
        x0, y0 = route[i]
        x1, y1 = route[i + 1]
        base_escalator(f"Stack_Spine_Escalator_{i}",
                       (x0, y0, z0), (x1, y1, z1), mats)


def room_light_state(floor_index, i, j):
    """Independent on/off state and colour temperature of one room panel."""
    rng = random.Random(ROOM_LIGHT_SEED + floor_index * 101
                        + i * 10007 + j * 1000003)
    if rng.random() >= ROOM_LIGHT_ON_RATIO:
        return "off"
    return rng.choice(("daylight", "warm"))


def is_refuge(zc):
    """True for a storey inside one of the open refuge bands. Storey levels are
    storey tops, so the refuge storey's top sits on the band's upper edge."""
    return any(z0 < zc <= z1 for z0, z1 in REFUGES)


def room_ceiling_lights(mats):
    """A grid of panel lights on the ceiling of every office and apartment
    storey, following the house reference. Panels are clipped around the cores,
    the central public shaft and the two apartment voids, and merged into one
    object per light state. The open refuge storeys take no ceiling lights:
    their open-air gardens are lit by the track lamps instead."""
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
        if zc <= LEVEL_BASE or is_refuge(zc):
            continue
        # A dropped refuge plate is no ceiling: the storey below it is part of
        # the open refuge, so it takes no panel grid (no floating fixtures).
        if zc in REFUGE_DROP_LEVELS:
            continue
        z = zc - 0.15 - ROOM_LIGHT_H / 2
        for i, px in enumerate(xs):
            for j, py in enumerate(ys):
                in_core = (abs(px) - half < CORE_X + CORE_WIDTH / 2
                           and abs(py) - half < CORE_DEPTH / 2)
                # The central public shaft is open air between the cores, so no
                # panel sits over it either.
                in_shaft = (abs(px) < SPINE_HALF_X + half
                            and abs(py) < SPINE_HALF_Y + half)
                # A storey whose ceiling faces an apartment void takes no lights
                # in the opening; the void is open air the full depth, and its
                # top plate is the ceiling of an open storey too.
                in_void = any(
                    x0 - half < px < x1 + half and z0 <= zc <= z1
                    for x0, x1, z0, z1 in VOIDS)
                if in_core or in_shaft or in_void:
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
        if zc >= LEVEL_BASE:
            break
        if zc < LEVEL_MALL_FIRST:
            continue
        if zc in REFUGE_DROP_LEVELS:
            continue
        z = zc - 0.15 - ROOM_LIGHT_H / 2
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
    panel(f"{face}_Diagrid_Glass", face, -glass_span(face), glass_span(face), z0, z1,
          GLASS_OUT, 0.12, mats["glass_cool"],
          shift_z=face_pad(face, 0.0, 0.006))
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
            beamf(f"{face}_Diagrid", face, u0, zm, um, zb, m, mats["frame"],
                  DIAGRID_OUT)
            beamf(f"{face}_Diagrid", face, um, zb, u1, zm, m, mats["frame"],
                  DIAGRID_OUT)
            beamf(f"{face}_Diagrid", face, u1, zm, um, za, m, mats["frame"],
                  DIAGRID_OUT)
            beamf(f"{face}_Diagrid", face, um, za, u0, zm, m, mats["frame"],
                  DIAGRID_OUT)


def band_garden(face, z0, z1, mats):
    """D-zone office band: the same diamond diagrid lattice as the band above —
    the cross pattern runs on through the zone rather than a fork-column
    colonnade — with a sparse, recessed planting at its base so the band still
    reads as a garden. The band carries the whole office zone up to the refuge,
    so the lattice and its glazing are one continuous surface with no seam."""
    band_diagrid(face, z0, z1, mats)
    length = face_geom(face)[3]
    rng = random.Random(4200 + FACES.index(face))
    m = max(1, round(length / 16))
    for i in range(m):
        u = -length / 2 + (i + 0.5) * length / m
        h = rng.uniform(2.5, min(8.0, (z1 - z0) * 0.4))
        beam(f"{face}_Garden_Trunk", face_point(face, u, z0, -1.6),
             face_point(face, u, z0 + 1.2 + h, -1.6), 0.16, mats["trunk"])
        sphere(f"{face}_Garden_Canopy",
               face_point(face, u, z0 + 2.0 + h, -1.6),
               rng.uniform(1.1, 1.8), mats["foliage"])


def band_fins(face, z0, z1, mats):
    """Tall vertical fins, flat in the shared facade plane."""
    length = face_geom(face)[3]
    panel(f"{face}_Fins_Glass", face, -glass_span(face), glass_span(face), z0, z1,
          GLASS_OUT, 0.12, mats["glass_cool"],
          shift_z=face_pad(face, 0.0, 0.006))
    n = max(2, round(length / 1.1))
    for i in range(n + 1):
        u = -length / 2 + i * length / n
        panel(f"{face}_Fin", face, u - 0.09, u + 0.09, z0, z1,
              FIN_OUT, MULLION_D, mats["fin"], pad_z=face_pad(face, 0.022))



# Upper apartment band: a fine vertical-strip curtain wall after the Abeno
# Harukas reference. Narrow panes on the shared mullion module, a transom at
# every floor and at each storey's lower-quarter vision/spandrel split, over a
# dark glass skin so the band reads as vertical strips rather than long
# horizontal bands. Every frame line is a thin blade with real depth, matching
# the fins band, rather than a flat line on the facade plane.
APARTMENT_SPLIT = 0.25


def window_wall(face, u0, u1, z0, z1, mats, prefix, holes=()):
    """One run of the apartment-band curtain wall: narrow vertical panes on the
    shared mullion module, dark vision glass over a light blue spandrel in each
    storey's lower quarter, a transom at every floor line and spandrel split,
    and fine vertical mullions through all floors."""
    # A hole may belong to a void that lies above or below this band, so clip
    # every hole to the band's own height first; otherwise the mullion skip
    # would run a pane a whole storey past the band top and leave a stray frame
    # standing in the open refuge above it.
    holes = [(a, b, max(c, z0), min(d, z1)) for a, b, c, d in holes
             if max(c, z0) < min(d, z1)]
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
    for a, b, c, d in rects_outside(u0, u1, z0, z1, holes):
        zs = [c] + [z for z in cuts if c < z < d] + [d]
        for zc0, zc1 in zip(zs, zs[1:]):
            mid = (zc0 + zc1) / 2
            if any(s0 <= mid <= s1 for s0, s1 in spandrel_spans):
                panel(f"{face}_{prefix}_Spandrel", face, a, b, zc0, zc1,
                      GLASS_OUT, GLASS_D, mats["spandrel"],
                      shift_z=face_pad(face, 0.0, 0.006))
            else:
                panel(f"{face}_{prefix}_Glass", face, a, b, zc0, zc1,
                      GLASS_OUT, GLASS_D, mats["glass_dark"],
                      shift_z=face_pad(face, 0.0, 0.006))
    nu = max(1, round((u1 - u0) / APARTMENT_MULLION_SPACING))
    du = (u1 - u0) / nu
    # Fine vertical mullions on the pane module, unbroken through all floors.
    for m in range(nu + 1):
        u = u0 + m * du
        skip = sorted((c, d) for a, b, c, d in holes if a < u < b)
        for za, zb in u_intervals(z0, z1, skip):
            panel(f"{face}_{prefix}_Mullion", face, u - FRAME_BLADE_W / 2,
                  u + FRAME_BLADE_W / 2, za, zb, MULLION_OUT, MULLION_D,
                  mats["apartment_frame"], pad_z=face_pad(face, 0.006))
    # A transom at every floor line and at each storey's lower-quarter
    # vision/spandrel split. The bars are cut where the void opening is, its
    # bottom edge included, so each tower half closes its own frame ring rather
    # than sharing one bar across the slot. Only the void's head stays unbroken,
    # where the two halves meet again above the opening.
    for zb in cuts:
        cut = [(a, b) for a, b, c, d in holes if c <= zb < d]
        for a, b in u_intervals(u0, u1, cut):
            za, zc = bar_span(zb, z0, z1, FRAME_BLADE_W, SEAM)
            panel(f"{face}_{prefix}_Transom", face, a, b, za, zc,
                  TRANSOM_OUT, TRANSOM_D, mats["apartment_frame"],
                  pad_u=face_pad(face, 0.012, 0.004),
                  pad_z=face_pad(face, 0.012, 0.004))


def band_brick(face, z0, z1, mats, holes=()):
    """Upper apartment band: one run of the shared curtain-wall component over
    the whole face, cut around the two apartment voids."""
    # The facade ends exactly on its last mullion, so the grid and the skin are
    # laid on the building dimension, not the corner-extended face length.
    span = WIDTH if face in ("N", "S") else DEPTH
    window_wall(face, -span / 2, span / 2, z0, z1, mats, "Brick", holes)


# The two apartment voids are open notches cut between each core and the public
# shaft: their outer edge is the core's concrete face and their inner edge opens
# straight into the shaft, so no lining wall is built. The core's X-braces read
# on the exposed face inside each void, and the escalator chain passes through.


def chevron_face(face, u0, u1, z0, z1, mats, prefix, outer, corner_start=False):
    """Abeno Harukas-style perimeter chevrons: complete upward chevrons with both
    feet on the lower chord and the apex on the upper chord, one boundary post
    per group, and a top and bottom chord. Group count follows the span at the
    fixed ~12 m spacing, so it changes with the face width. The first post is
    skipped when the band wraps a corner, where the previous face's last post
    already stands."""
    width = u1 - u0
    groups = max(1, int(width / CHEVRON_SPACING + 0.5))
    step = width / groups
    post_r, diag_r, chord_r = (CHEVRON_POST_W / 2, CHEVRON_DIAG_W / 2,
                               CHEVRON_CHORD_W / 2)

    def member(name, ua, za, ub, zb, radius):
        off = outer - radius
        start = face_point(face, ua, za, off)
        end = face_point(face, ub, zb, off)
        beam(f"{face}_{prefix}_{name}", start, end, radius, mats["steel"])

    # Round tubes, as in the Abeno band trusses: flat members all share the
    # facade plane and their coincident faces z-fight where they overlap at a
    # joint, which round sections avoid.
    # Post end caps are pulled a little off the storey lines, so they never share
    # a plane with the brick glass, mullions and transoms at the floor above and
    # below (which would z-fight); the depth-side posts are pulled a little more
    # than the front/back ones so the two posts that meet at a corner also do not
    # share a cap plane.
    inset = 0.10 if face in ("E", "W") else 0.05
    pz0, pz1 = z0 + inset, z1 - inset
    for k in range(0 if corner_start else 1, groups + 1):
        # Keep the boundary posts inside the face end: a round post overhangs
        # its centre by post_r, so an end post left on the building corner would
        # stick out past the envelope. Pull the two end posts in by their own
        # radius; the interior posts are unaffected (the step is far wider).
        u = min(u0 + k * step, u1 - post_r)
        u = max(u, u0 + post_r)
        member("Post", u, pz0, u, pz1, post_r)
    for k in range(groups):
        f0 = u0 + k * step
        f1 = f0 + step / 2
        f2 = f0 + step
        # Pull the two outer feet in by their own radius too: the round cap at a
        # foot left on the face end overhangs the corner just like a post does.
        a = max(f0, u0 + diag_r) if k == 0 else f0
        b = min(f2, u1 - diag_r) if k == groups - 1 else f2
        member("Diag", a, z0, f1, z1, diag_r)
        member("Diag", f1, z1, b, z0, diag_r)
    for z in (z0, z1):
        member("Chord", u0, z, u1, z, chord_r)


def refuge_belt_trusses(mats):
    """An Abeno Harukas-style chevron belt truss spanning each refuge's full two
    storeys, its feet on the garden deck and its apex on the ceiling, so each
    face reads as one chunky claw. Wrapped on all four faces and recessed behind
    the folded glass screen, so the truss reads through the screen rather than
    standing in front of it."""
    for deck, top in zip(REFUGE_DECK_LEVELS, REFUGE_CEILING_LEVELS):
        for face in FACES:
            span = WIDTH if face in ("N", "S") else DEPTH
            chevron_face(face, -span / 2, span / 2, deck, top, mats,
                         f"Refuge_Belt_{int(deck)}", FACADE - TRUSS_INSET)


def sky_garden(name, z, mats, plates, trees, tree_max_h=TREE_MAX_H):
    """A planted deck on an open plate: a lawn inside a perimeter running track,
    with a scatter of trees, so the refuge storeys and the roof all read as
    gardens. `plates` are the (x0, x1, y0, y1) floor areas of the deck."""
    hx = WIDTH / 2 + FACADE - GLASS_BACK - GLASS_T - GARDEN_MARGIN
    hy = DEPTH / 2 + FACADE - GLASS_BACK - GLASS_T - GARDEN_MARGIN
    for x0, x1, y0, y1 in plates:
        cube(f"{name}_Lawn", ((x0 + x1) / 2, (y0 + y1) / 2, z),
             (x1 - x0, y1 - y0, 0.10), mats["lawn"])
    tx, ty = hx - TRACK_INSET, hy - TRACK_INSET
    for side, (px, py, dx, dy) in {
            "N": (0, ty - TRACK_W / 2, 2 * tx, TRACK_W),
            "S": (0, -(ty - TRACK_W / 2), 2 * tx, TRACK_W),
            "E": (tx - TRACK_W / 2, 0, TRACK_W, 2 * (ty - TRACK_W)),
            "W": (-(tx - TRACK_W / 2), 0, TRACK_W, 2 * (ty - TRACK_W)),
    }.items():
        cube(f"{name}_Track_{side}", (px, py, z + 0.06), (dx, dy, 0.10),
             mats["track"])
    # Street lamps along the inner edge of the running track, centred in each
    # spacing segment so the corner lamps of two sides never double up. The
    # track ring hugs the outer deck edge, so every lamp stands on a plate.
    lamp_x = tx - TRACK_W - LAMP_INSET
    lamp_y = ty - TRACK_W - LAMP_INSET
    for half, fixed, along_x in ((tx, lamp_y, True), (tx, -lamp_y, True),
                                 (ty, lamp_x, False), (ty, -lamp_x, False)):
        n = max(1, int(2 * half / LAMP_SPACING))
        for i in range(n):
            u = -half + (i + 0.5) * 2 * half / n
            px, py = (u, fixed) if along_x else (fixed, u)
            beam(f"{name}_Lamp_Post", (px, py, z - 0.1),
                 (px, py, z + LAMP_H), LAMP_POLE_R, mats["dark"])
            sphere(f"{name}_Lamp_Head", (px, py, z + LAMP_H), LAMP_HEAD_R,
                   mats["glow"])
    rng = random.Random(7100 + int(z))
    placed = 0
    for _ in range(trees * 8):
        if placed >= trees:
            break
        px = rng.uniform(-hx + 3, hx - 3)
        py = rng.uniform(-hy + 3, hy - 3)
        if abs(px) < CORE_X + CORE_WIDTH / 2 + 1 and abs(py) < CORE_DEPTH / 2 + 1:
            continue
        if abs(px) < SPINE_HALF_X + 1.5 and abs(py) < SPINE_HALF_Y + 1.5:
            continue
        if not any(x0 < px < x1 and y0 < py < y1 for x0, x1, y0, y1 in plates):
            continue
        # A tall tree: it grows up through the truss toward the ceiling two
        # storeys above, stopping under that refuge's own ceiling.
        height = rng.uniform(min(6.0, tree_max_h), tree_max_h)
        r = rng.uniform(1.4, 1.8)
        trunk_top = z + height - 1.7 * r
        beam(f"{name}_Trunk", (px, py, z - 0.25), (px, py, trunk_top),
             0.14 + height * 0.012, mats["trunk"])
        sphere(f"{name}_Canopy", (px, py, trunk_top + r * 0.6), r,
               mats["foliage"])
        placed += 1


def refuge_gardens(mats):
    """The three refuge decks are planted sky gardens, the same deck as the
    roof: a lawn, a running track and a dense grove of trees, so the stack reads
    as a vertical forest. The lowest garden is the mall's last ring plate around
    the atrium; the mid-office and upper decks are full plates."""
    hx = WIDTH / 2 + FACADE - GLASS_BACK - GLASS_T - GARDEN_MARGIN
    hy = DEPTH / 2 + FACADE - GLASS_BACK - GLASS_T - GARDEN_MARGIN
    vx, vy = MALL_VOID_X + 0.02, MALL_VOID_Y + 0.02
    mall_ring = ((vx, hx, -hy, hy), (-hx, -vx, -hy, hy),
                 (-vx, vx, vy, hy), (-vx, vx, -hy, -vy))
    caps = tuple(h - 1.5 for h in REFUGE_STOREY_H)
    sky_garden("Stack_Refuge_Mall_Garden", REFUGE_DECK_LEVELS[0] + 0.14, mats,
               mall_ring, trees=12, tree_max_h=caps[0])
    sky_garden("Stack_Refuge_Office_Garden", REFUGE_DECK_LEVELS[1] + 0.14, mats,
               ((-hx, hx, -hy, hy),), trees=14, tree_max_h=caps[1])
    sky_garden("Stack_Refuge_Apartment_Garden", REFUGE_DECK_LEVELS[2] + 0.14,
               mats, ((-hx, hx, -hy, hy),), trees=16, tree_max_h=caps[2])
    sky_garden("Stack_Refuge_Apartment_Mid_Garden", REFUGE_DECK_LEVELS[3] + 0.14,
               mats, ((-hx, hx, -hy, hy),), trees=16, tree_max_h=caps[3])


def band_roof(mats):
    """The top plate is the planted City Plaza roof, inside the glazed crown:
    the same deck as the refuges, so the building is crowned by a garden."""
    hx = WIDTH / 2 + FACADE - GLASS_BACK - GLASS_T - GARDEN_MARGIN
    hy = DEPTH / 2 + FACADE - GLASS_BACK - GLASS_T - GARDEN_MARGIN
    sky_garden("Stack_Roof", LEVEL_ROOF + 0.14, mats, ((-hx, hx, -hy, hy),),
               trees=14)


def band_refuge(face, z0, z1, mats, holes=()):
    """The folded screen that wraps every refuge. A vertical sawtooth runs the
    full two-storey volume: its outer folds sit on the shared facade plane and
    its inner folds are drawn back by SCREEN_FOLD, so the skin reads as a
    folding screen and nothing stands proud of the envelope. Thin white posts
    run up every fold, framing the glass like a screen; the chunky chevron truss
    stands behind the deepest fold and reads through."""
    span = WIDTH if face in ("N", "S") else DEPTH
    teeth = max(1, round(span / SCREEN_BAY))
    du = span / teeth
    peak, valley = FACADE, FACADE - SCREEN_FOLD
    for k in range(teeth):
        u0 = -span / 2 + k * du
        u1 = u0 + du / 2
        u2 = u0 + du
        folded_panel(f"{face}_Refuge_Screen", face, u0, peak, u1, valley,
                     z0, z1, GLASS_T, mats["glass_cool"])
        folded_panel(f"{face}_Refuge_Screen", face, u1, valley, u2, peak,
                     z0, z1, GLASS_T, mats["glass_cool"])
    # A post on every fold, pulled a hair inside its own leaf so the two never
    # share a cap plane and no post protrudes past the envelope.
    for k in range(teeth + 1):
        u = -span / 2 + k * du
        outer = peak if k % 2 == 0 else valley
        panel(f"{face}_Refuge_Screen_Post", face, u - FRAME_BLADE_W / 2,
              u + FRAME_BLADE_W / 2, z0 + 0.02, z1 - 0.02, outer - 0.05,
              MULLION_D, mats["apartment_frame"],
              pad_z=face_pad(face, 0.006))


BAND_BUILDERS = {
    "base": band_base,
    "refuge": band_refuge,
    "garden": band_garden,
    "fins": band_fins,
    "brick": band_brick,
}


# ---------------------------------------------------------------------------
# Interior (the public route and its gardens) and site
# ---------------------------------------------------------------------------

# The chunky perimeter columns the outriggers engage: their plane and section
# are shared by the full ring (see perimeter_columns). The outriggers now run
# from each core's edges to the ring's single mid-depth column on the short
# faces, at the open refuge levels, so the frame shares the overturning.
OUTRIGGER_COL_W = 2.4
OUTRIGGER_COL_X = WIDTH / 2 - 3.0
OUTRIGGER_COL_Y = CORE_DEPTH / 2
OUTRIGGER_LEVELS = REFUGE_FLOOR_LEVELS

# A full perimeter ring of the same big-frame steel columns, carried evenly
# around the building just inside the curtain wall and set back behind the glass
# like the outriggers. The long faces divide into equal bays but skip any bay
# that falls inside an apartment void and skip their end (corner) bays, since on
# the wide face those ends are the short-face columns seen edge-on; the short
# faces carry two columns only, at the quarter and three-quarter points of the
# depth, so the middle half of the short face is column-free — and those two
# columns are also where the outriggers land.
RING_COL_W = OUTRIGGER_COL_W
RING_COL_INSET = WIDTH / 2 - OUTRIGGER_COL_X        # same plane as the outriggers
RING_LONG_BAYS = 7
RING_SHORT_Y = DEPTH / 4                            # 1/4 and 3/4 of the short face


def core_bracing(mats):
    """Giant spatial X-braces between the two service cores: four diagonals per
    bay, each running from a corner of one core's face to the diagonally
    opposite corner of the other, so the bracing uses the cores' full depth and
    reads as an X in plan, in elevation and from the side alike. The ends run
    CORE_BRACE_W into each core, so the members meet the concrete in a solid
    connection rather than only touching the inner corner. The members are
    diagonals only — they need no floor plate — so the escalator chain climbs
    the public shaft between them, weaving past the X rather than being
    displaced by it."""
    x = CORE_INNER + CORE_BRACE_W
    y = CORE_DEPTH / 2 - CORE_BRACE_W
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


def perimeter_columns(mats):
    """A ring of chunky steel columns just inside the curtain wall, set back
    behind the glass like the outriggers. The long faces carry equal bays but no
    end columns — on the wide face the ends are the short-face columns seen
    edge-on — and skip any bay inside an apartment void; each short face carries
    two columns, at the quarter and three-quarter points."""
    hx = WIDTH / 2 - RING_COL_INSET
    hy = DEPTH / 2 - RING_COL_INSET
    bay = 2 * hx / RING_LONG_BAYS
    half = RING_COL_W / 2

    def in_void(x):
        return any(x0 - half < x < x1 + half for x0, x1, _, _ in VOIDS)

    points = [(-hx + k * bay, sy * hy)
              for sy in (-1, 1) for k in range(1, RING_LONG_BAYS)
              if not in_void(-hx + k * bay)]
    points += [(sx * hx, sy * RING_SHORT_Y)
               for sx in (-1, 1) for sy in (-1, 1)]
    for x, y in points:
        cube("Stack_Perimeter_Column", (x, y, LEVEL_ROOF / 2),
             (RING_COL_W, RING_COL_W, LEVEL_ROOF), mats["steel"])


def midspan_columns(mats):
    """One chunky column at the exact middle of each long face, between the two
    cores and on the long-face column line, full height from the ground to the
    top: it breaks the long span between the cores."""
    y = DEPTH / 2 - RING_COL_INSET
    for sy in (-1, 1):
        cube("Stack_Midspan_Column", (0.0, sy * y, LEVEL_ROOF / 2),
             (RING_COL_W, RING_COL_W, LEVEL_ROOF), mats["steel"])


def outrigger_trusses(mats):
    """Horizontal trusses at the refuge levels tying each core to the ring's
    short-face column, so the columns share the overturning: a top and bottom
    chord with an X of diagonals between them, one truss off each core edge and
    side. Each runs slightly diagonally in plan, from the core's edge out to the
    column at the quarter point of the short face."""
    x0 = CORE_X + CORE_WIDTH / 2        # core outer face
    x1 = OUTRIGGER_COL_X                # ring column centre
    for level in OUTRIGGER_LEVELS:
        truss_h = APARTMENT_H if level >= LEVEL_APARTMENT else OFFICE_H
        for sx in (-1, 1):
            for sy in (-1, 1):
                ax, ay = sx * x0, sy * OUTRIGGER_COL_Y
                bx, by = sx * x1, sy * RING_SHORT_Y
                brace("Stack_Outrigger_Chord", (ax, ay, level),
                      (bx, by, level), 0.8, 0.8, mats["steel"])
                brace("Stack_Outrigger_Chord", (ax, ay, level + truss_h),
                      (bx, by, level + truss_h), 0.8, 0.8, mats["steel"])
                brace("Stack_Outrigger_Diag", (ax, ay, level),
                      (bx, by, level + truss_h), 0.5, 0.5, mats["steel"])
                brace("Stack_Outrigger_Diag", (ax, ay, level + truss_h),
                      (bx, by, level), 0.5, 0.5, mats["steel"])


def merge_intervals(intervals):
    """Merge overlapping (a, b) spans into a sorted, disjoint list."""
    out = []
    for a, b in sorted(intervals):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def plate_with_holes(name, x0, x1, y0, y1, z, holes, mat, thick=0.28):
    """Build one floor plate as the big rectangle minus rectangular holes. The
    plate is cut into x-strips, and each strip into the y-intervals left by the
    holes covering it, so the public shaft and the two apartment voids stay
    open."""
    xs = sorted({x0, x1} | {a for a, _, _, _ in holes}
                | {b for _, b, _, _ in holes})
    for a, b in zip(xs, xs[1:]):
        xc = (a + b) / 2
        spans = merge_intervals([(c, d) for hx0, hx1, c, d in holes
                                 if hx0 + 1e-6 < xc < hx1 - 1e-6])
        for c, d in u_intervals(y0, y1, spans):
            cube(name, ((a + b) / 2, (c + d) / 2, z), (b - a, d - c, thick),
                 mat)


def add_interior(mats):
    """Two service cores on the long axis, braced on their inner faces, and one
    plate per storey. The public shaft between the cores and the two apartment
    voids are cut out of every plate above the mall, so the escalator chain has
    a continuous vertical street to climb."""
    for side in (-1, 1):
        cube("Stack_Core_West" if side < 0 else "Stack_Core_East",
             (side * CORE_X, CORE_Y, HEIGHT / 2),
             (CORE_WIDTH + 0.02, CORE_DEPTH, HEIGHT), mats["core"])
    core_bracing(mats)
    slab_half = WIDTH / 2 + FACADE - GLASS_BACK - GLASS_T
    slab_half_y = DEPTH / 2 + FACADE - GLASS_BACK - GLASS_T

    def plate_holes(zc):
        holes = [(-SPINE_HALF_X, SPINE_HALF_X, -SPINE_HALF_Y, SPINE_HALF_Y)]
        for x0, x1, z0, z1 in VOIDS:
            if z0 - 1e-6 <= zc < z1 - 1e-6:
                holes.append((x0, x1, -slab_half_y, slab_half_y))
        return holes

    # Mall floors ring a central atrium so the escalators read through the
    # glazing. The ground level carries no plate: the first retail floor is
    # suspended two storeys up, leaving a double-height hall below it. The mall
    # garden deck is the refuge's bottom plate, so the mall rings stop at it.
    for zc in storey_levels():
        if zc > REFUGE_MALL[0]:
            break
        if zc < LEVEL_MALL_FIRST:
            continue
        if zc in REFUGE_DROP_LEVELS:
            continue
        for sx in (-1, 1):
            cube("Stack_Mall_Slab",
                 (sx * (MALL_VOID_X + slab_half) / 2, 0, zc),
                 (slab_half - MALL_VOID_X, 2 * slab_half_y, 0.28),
                 mats["slab"])
        for sy in (-1, 1):
            cube("Stack_Mall_Slab",
                 (0, sy * (MALL_VOID_Y + slab_half_y) / 2, zc),
                 (2 * MALL_VOID_X, slab_half_y - MALL_VOID_Y, 0.28),
                 mats["slab"])
    # Office and apartment plates, cut around the public shaft and the two
    # apartment voids. The storey line inside each refuge is dropped, so its
    # garden deck and its truss read as one two-storey volume.
    for zc in storey_levels():
        if zc < REFUGE_MALL[1]:
            continue
        if zc in REFUGE_DROP_LEVELS:
            continue
        plate_with_holes("Stack_Floor_Slab", -slab_half, slab_half,
                         -slab_half_y, slab_half_y, zc, plate_holes(zc),
                         mats["slab"])


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
    nt = world.node_tree
    background = nt.nodes["Background"]
    # Match the Material Preview studio lighting the model is reviewed in: the
    # bundled interior.exr HDRI lights the scene and reflects in the glass,
    # while camera rays keep a clean, soft sky-blue backdrop.
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(os.path.join(
        bpy.utils.system_resource("DATAFILES"), "studiolights", "world",
        "interior.exr"))
    background.inputs["Strength"].default_value = 1.0
    nt.links.new(env.outputs["Color"], background.inputs["Color"])
    sky = nt.nodes.new("ShaderNodeBackground")
    sky.inputs["Color"].default_value = (0.55, 0.66, 0.78, 1)
    sky.inputs["Strength"].default_value = 1.0
    light_path = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(light_path.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(background.outputs[0], mix.inputs[1])
    nt.links.new(sky.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes["World Output"].inputs["Surface"])
    bpy.ops.object.light_add(type="SUN", location=(180, -220, 380))
    sun = bpy.context.object
    sun.data.energy = 4.5
    sun.data.angle = math.radians(6.0)
    sun.rotation_euler = (math.radians(52), math.radians(-18),
                          math.radians(-32))

    camera_data = []
    for name, loc, target, lens in (
            ("preview", (340, -560, 200), (0, 0, 165), 55),
            ("facade", (150, -230, 240), (0, 0, 240), 90),
            ("garden", (70, -120, 125), (0, 0, 120), 45),
            ("void", (30, -260, 205), (0, 0, 199), 55),
            ("base", (190, -250, 80), (0, 0, 30), 55)):
        bpy.ops.object.camera_add(location=loc)
        cam = bpy.context.object
        cam.name = f"Stack_Camera_{name}"
        # A generous near plane keeps depth precision high across the 600 m
        # view distance, so thin facade offsets do not z-fight.
        cam.data.clip_start, cam.data.clip_end = 5.0, 3000.0
        cam.data.lens = lens
        cam.rotation_euler = (Vector(target) - cam.location).to_track_quat(
            "-Z", "Y").to_euler()
        camera_data.append((name, cam))

    scene = bpy.context.scene
    scene.camera = camera_data[0][1]
    # Save the 3D viewport framed on the whole building (matching the preview
    # camera) so opening the .blend does not start inside the tower.
    frame_viewport((340, -560, 200), (0, 0, 165), lens=55)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 900, 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene["reference_url"] = "https://mvrdv.com/projects/340/the-stack"
    scene["published_height_m"] = 356.8
    scene["model_height_m"] = HEIGHT
    scene["crown_height_m"] = CROWN_H
    scene["published_levels"] = 77
    scene["floor_count"] = MALL_FLOORS + OFFICE_FLOORS + APARTMENT_FLOORS
    scene["refuge_open_height_m"] = REFUGE_OPEN_H
    scene["mall_floors"] = MALL_FLOORS
    scene["mall_ground_height_m"] = LEVEL_MALL_FIRST
    scene["base_escalators"] = len(ESCALATOR_ENTRIES)
    scene["escalator_helix"] = "true"
    scene["mall_escalator_pitch_deg"] = FLIGHT_ANGLE
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
    scene["refuges"] = len(REFUGES)
    scene["refuge_layers"] = "garden,truss"
    scene["refuge_levels_m"] = ", ".join(
        f"{z0:g}-{z1:g}" for z0, z1 in REFUGE_COMPONENT_SPANS)
    scene["refuge_open_levels_m"] = ""
    scene["refuge_open_heights_m"] = ""
    scene["refuge_screen_m"] = f"fold {SCREEN_FOLD:g}, bay {SCREEN_BAY:g}"
    scene["depth_override_m"] = DEPTH
    scene["depth_override_note"] = (
        "Elevation sheet reads 34 m; depth widened to 40 m for load "
        "plausibility (client direction).")
    scene["voids"] = len(VOIDS)
    scene["void_width_m"] = VOID_W
    scene["void_heights_m"] = (f"{VOID_LOW_FLOORS * APARTMENT_H:g},"
                               f"{VOID_HIGH_FLOORS * APARTMENT_H:g}")
    scene["void_area_m2"] = VOID_W * (VOID_LOW_FLOORS
                                      + VOID_HIGH_FLOORS) * APARTMENT_H
    scene["void_centre_on_brace"] = "true"
    scene["void_x_spans_m"] = ";".join(
        f"{x0:g}-{x1:g}" for x0, x1, _, _ in VOIDS)
    scene["void_z_spans_m"] = ";".join(
        f"{z0:g}-{z1:g}" for _, _, z0, z1 in VOIDS)
    scene["spine_shaft_m"] = f"{2 * SPINE_HALF_X:g}x{2 * SPINE_HALF_Y:g}"
    scene["public_route_runs"] = (
        sum(1 for z in storey_levels()
            if LEVEL_MALL_FIRST <= z <= REFUGE_MALL[0]
            and z not in REFUGE_DROP_LEVELS) - 1
        + sum(1 for z in storey_levels() if z >= REFUGE_MALL[1]) - 1)
    scene["structural_scheme"] = (
        "Two service cores on the long axis, X-braced on their inner faces, "
        "with one public escalator shaft and four two-storey planted refuge "
        "gardens, each under a chevron belt truss and wrapped in a folded "
        "glass screen.")
    scene["core_bracing"] = CORE_BRACE_COUNT
    scene["perimeter_columns"] = 2 * (RING_LONG_BAYS + 1) + 2
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
        "frame": materials.make_metal("Stack_Frame", color=(0.95, 0.95, 0.94)),
        "fin": materials.make_metal("Stack_Fin", color=(0.95, 0.95, 0.94)),
        "dark": materials.make_dark("Stack_Dark_Panel", color=(0.06, 0.06, 0.07)),
        "brick": materials.make_wall("Stack_Masonry", color=(0.55, 0.44, 0.34)),
        "spandrel": materials.make_wall("Stack_Spandrel_Blue",
                                        color=(0.70, 0.79, 0.86)),
        "apartment_frame": materials.make_wall("Stack_Apartment_Frame",
                                               color=(0.95, 0.95, 0.94)),
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
        "lawn": materials.make_wall("Stack_Lawn", color=(0.16, 0.36, 0.14)),
        "track": materials.make_wall("Stack_Track", color=(0.46, 0.14, 0.11)),
    }


def build(args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = build_materials()
    ground(mats)
    add_interior(mats)
    perimeter_columns(mats)
    midspan_columns(mats)
    outrigger_trusses(mats)
    base_interior(mats)
    base_escalators(mats)
    mall_escalators(mats)
    spine_escalators(mats)
    mall_ceiling_lights(mats)
    room_ceiling_lights(mats)
    for z0, z1, band in BANDS:
        for face in FACES:
            builder = BAND_BUILDERS[band]
            if builder is band_brick:
                builder(face, z0, z1, mats, holes=void_holes(face))
            else:
                builder(face, z0, z1, mats)
    void_curtain_wall(mats)
    refuge_belt_trusses(mats)
    refuge_gardens(mats)
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
