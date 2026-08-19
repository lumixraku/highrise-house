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
* Bottom 3 floors are pilotis (open, raised on columns + two service cores).
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
from mathutils import Euler, Matrix, Vector

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
# Flush glazing: the glass, its mullion caps and the louvres all finish on the
# SAME plane as the wall, with no reveal and no sill. A non-zero inset here puts
# the glass behind the wall face, and the 90 mm of opening side wall that leaves
# is exactly what reads as a window sill — which is what we do not want.
GLASS_INSET = 0.0     # from the outer wall face; 0 = flush with it
VENT_INSET = 0.0      # louvres finish on the wall plane too
# The glass is fully clear, so it needs something behind it or it reads as a gap.
# This lining stands in for lit floors; set back far enough that pane and lining
# move against each other as the view shifts, which is what reads as glass.
INTERIOR_SETBACK = 0.85

# The room window is the fixed module: exactly PANE_W x WIN_H of clear glass.
# EVERYTHING outside is derived from the room-window counts — never the other way round.
PANE_W = 4.00
WINDOWS_LONG = 15      # room windows across each long facade  (X)
WINDOWS_SHORT = 7       # room windows across each short facade (Y)
WINDOW_GAP = 0.12       # real vertical joint between adjacent room windows
PANE_GLASS_W = PANE_W - WINDOW_GAP

# The mullion is a cover cap centred on each pane joint: it sits proud of the
# glass line and overlaps the two panes it joins, so it costs NO facade length.
# That keeps the arithmetic clean — an opening is exactly N x PANE_W, so the
# footprint comes out on whole metres:
#   W = 15 x 4.00 + 2 x 2.00 = 64.00 m
#   D =  7 x 4.00 + 2 x 2.00 = 32.00 m
MULLION_W = 0.09
MULLION_INSET = 0.12     # recessed from the facade plane to deepen window joints

# Solid wall kept at both ends of every facade, so the ribbon stops short of the
# corners instead of wrapping them. Measured along the facade from the corner.
#
# ONE pane width on all four facades. What these numbers actually control is the
# END OF THE BUILDING, not the edge of the glass: a glass run is fixed at
# N x PANE_W, so the glazing edge does not move when a pier is thinned — the
# building end moves inward towards it. The pier only decides how much dead wall
# wraps past the last pane. They were 8 m long / 4 m short, which left the corner
# apartment with 8 m of blank wall around its outboard end and 4 m around its
# return. At 2 m on both, it turns the corner after a single pane and has a real
# second aspect, which is the whole point of putting it there.
#
# Thinning PIER_SHORT is what forced WINDOWS_SHORT from 12 to 14. D is derived, so
# 2 m piers with 12 panes would have given D = 28 m and 8.0 m of unit depth beside
# the cores, under the 9 m residential minimum. Two more panes hold D at 32 m, so
# the depth is unchanged and only the corners moved.
#
# The cost is lateral stiffness, and it is affordable. Each figure below is at its
# own footprint, since W is what the wind acts on:
#   8 long / 4 short, W 76   Iy 3,870 m4   H/2,748
#   2 long / 4 short, W 64   Iy 2,061 m4   H/1,738
#   2 long / 2 short, W 64   Iy 1,655 m4   H/1,395   <- in use, 2.8x the limit
#   0 long / 2 short, W 64   Iy 1,052 m4   H/887
#   no piers at all,  W 64   Iy   601 m4   H/507     cores alone, 1% margin
# Most of what a pier buys is the lever arm of its short-facade return about the
# weak axis, which is why the long leg is the cheap one to thin. Going to zero
# would still scrape past drift on this arithmetic; what it actually breaks is the
# facade, since nothing would stop a ribbon short of the corner and the corners
# would open up. Ten checks in verify_house.py catch that. A real all-glass tower
# would not lean on this arithmetic anyway: it needs a perimeter Vierendeel frame
# (structural spandrels at every floor), which this model, walls and columns with
# no beams, lacks.
PIER_LONG = 2.0     # one pane width at the ends of the long facades (N/S)
PIER_SHORT = 2.0    # one pane width at the ends of the short facades (E/W)

# Blank (windowless) bands of the tower.
# Bottom: the transition floor sitting directly on the pilotis zone.
# Top: a band of blank wall, rounded to whole floors so the break lands on a
# floor line rather than cutting a window in half.
# Both bands are 8 m. They used to be matched by 8 m piers left and right, framing
# the long-facade window field evenly all round; the piers are now one pane wide,
# so the frame is 8 m top and bottom against 2 m at the ends. That asymmetry is
# the point — the horizontal bands read as the building's cap and base, while the
# ends stay open so the corner apartments turn the corner.
SOLID_BASE_TARGET = 8.0
SOLID_TOP_TARGET = 8.0
SOLID_BASE_FLOORS = max(1, round(SOLID_BASE_TARGET / H))
SOLID_TOP_FLOORS = max(1, round(SOLID_TOP_TARGET / H))

# --- refuge floor / sky garden ---------------------------------------------
# Singapore's SCDF requires a refuge floor in buildings over 24 storeys, spaced
# no more than 20 storeys apart, and the local convention is to give it over to a
# planted sky garden open on all sides — it doubles as the lift transfer level.
# One two-storey void at mid-height satisfies the spacing rule for a 40-storey
# tower and is where the garden reads best from the street.
#
# REFUGE_FLOORS floors are left open: no glazing, no spandrel, no intermediate
# slab, so the two storeys read as ONE double-height space. The facade line is
# held by the corner piers and a run of balustrade instead.
SKY_GARDEN = True
REFUGE_FLOORS = 2          # storeys given to the void
BALUSTRADE_H = 1.20        # open-edge guarding, per SCDF minimum 1.0 m
BALUSTRADE_T = 0.12

# A screen across the void. Leaving the refuge level fully open reads as a bite
# taken out of the tower — the elevation needs something holding the plane. The
# screen is a filter, not a wall: the openings are real voids, so the level stays
# naturally ventilated as a refuge floor must be.
#
# "GRID" — square openings in a deep frame, after 432 Park Avenue. Deliberately
#          set on the SAME pitch as the window panes, so the vertical lines run
#          straight through from the glazing below to the glazing above instead of
#          stopping at the garden.
# "FINS" — vertical blades only, closer spaced. Reads as louvring rather than
#          structure; more transparent when seen straight on, nearly solid at a
#          glancing angle.
GRILLE_STYLE = "FINS"
GRILLE_CELL = PANE_W       # GRID only: 4.0 m, one cell per room window
GRILLE_MEMBER = 0.34       # GRID only: face width of a grid member
GRILLE_DEPTH = 0.34        # GRID only: how far it stands proud
# FINS: slim vertical blades, no horizontals. The pitch divides PANE_W exactly, so
# every second blade lands on a window mullion and the vertical lines still carry
# through from the glazing below to the glazing above.
FIN_PITCH = 0.50           # preserve the original dense refuge screen spacing
FIN_W = 0.10               # slim: a blade, not a pier
FIN_DEPTH = 0.34           # depth gives it shadow and solidity at a raking angle
# Columns carrying the tower across the void. The fins are 0.10 m blades — a
# screen, not structure — so without these the 18 floors above would be landing
# on the corner piers and core alone: 33.1 m2 of concrete under 486605 kN, which
# is 14.7 MPa — inside C40 but at 82% utilisation with no margin. Adding 24
# columns takes the load path to 67.7 m2 / 7.2 MPa, a 40% utilisation matching
# the pilotis columns below.
#
# The spacing is one room window, so every column lands on a mullion line and the
# vertical rhythm of the facade runs straight through the garden.
REFUGE_COL_SIZE = 1.20
REFUGE_COL_PITCH = PANE_W         # 4.0 m — a whole number of room windows
GARDEN_SLAB_T = 0.45       # deeper than a normal plate: it carries soil
PLANTER_H = 0.85
PLANTER_W = 2.4
TREE_H = 4.6               # fits comfortably inside 8 m of double height
CANOPY_D = 3.2

# An opening is exactly N panes wide; the mullions cap the joints without
# consuming any of it.
def opening_for(n_panes):
    return n_panes * PANE_W


OPEN_W = opening_for(WINDOWS_LONG)      # long faces (N/S)
OPEN_D = opening_for(WINDOWS_SHORT)     # short faces (E/W)

# Footprint follows: clear opening plus a solid pier at each end.
W = OPEN_W + 2 * PIER_LONG
D = OPEN_D + 2 * PIER_SHORT

# Every pane is centred on the same fixed 4 m room module, but is slightly
# narrower so adjacent homes read as separate windows instead of one ribbon.
PANE_GLASS_LONG = PANE_GLASS_W
PANE_GLASS_SHORT = PANE_GLASS_W
PANE_PITCH = PANE_W                     # mullion centre to centre = pane width
assert abs(WINDOWS_LONG * PANE_W - OPEN_W) < 1e-9
assert abs(WINDOWS_SHORT * PANE_W - OPEN_D) < 1e-9
assert abs(W - round(W)) < 1e-9 and abs(D - round(D)) < 1e-9, \
    "footprint should land on whole metres"

COL_SIZE = 1.60       # continuous column footprint (sized for a 40-storey load)
COL_SPACING = 9.0     # target column grid spacing
COL_CLEAR_INSET = 2.0 # clear distance from facade plane to outer column face
COL_MARGIN = COL_CLEAR_INSET + COL_SIZE / 2.0

# --- service cores ----------------------------------------------------------
# TWO cores rather than one central slab, and the reason is capacity and egress,
# not structure. The lateral system here is the perimeter: the four L-shaped
# corner piers give Iy = 1460 m4 against the core's 177, so a core carries only
# 11% of the lateral stiffness and tip drift is H/1738 against a H/500 limit.
# Nothing about the core choice buys stiffness this building needs.
#
# What a single 14 x 9 core could NOT do was hold the vertical transport. 37
# floors x 64 x 32 m is 75776 m2 GFA, about 551 units and 1488 people, needing
# 7-9 lifts. Shafts, two stairs, lobbies, smoke-stop lobbies and risers come to
# roughly 172 m2 gross; 14 x 9 = 126 m2, short by 27%. That is a 6.2%
# core-to-plate ratio where residential towers run 10-15%.
# CORE_PROVISION below stays at the 203.5 m2 figure derived from the wider 76 m
# plate, deliberately: it is the stricter of the two and the measured 288 m2
# clears it anyway, so keeping it means the cores cannot shrink on the strength
# of a smaller unit count.
#
# Splitting also fixes two things one core cannot:
#   * Egress. Worst-case travel to a central core was 42.5 m, marginal against
#     SCDF's ~30 m dead-end / ~45 m two-way. Twin cores bring it to 24 m.
#   * Stair remoteness. Two stairs in ONE shaft are not independent — a single
#     incident compromises both. These sit 40 m apart.
#   * Lift zoning, which a 551-unit tower wants anyway: low zone in the west
#     core, high zone in the east, ~65 units per lift in each.
#
# Deliberately NOT an H-core: the spine that makes it an H would run a wall down
# the middle of the plate, forcing single-loaded corridors either side. H-cores
# suit office towers wanting deep lettable space; residential wants a continuous
# corridor loop.
CORE_W, CORE_D = 12.0, 12.0   # each core, plan size
CORE_T = 0.28                 # core wall thickness
# Offset from the building centreline. Even metres, so the core walls land on
# mullion lines and interior partitions can follow the facade rhythm. Held clear
# of the corner pier zone (outer edge at 24 m, pier starts at 30 m), which is
# what rules out pushing the cores right to the ends of the plate.
#
# 18 rather than 20, and the reason is the CORNER APARTMENT. It sits outboard of
# a core, so its width is W/2 - (CORE_OFFSET + CORE_W/2). With W now 64 m, 20
# would leave 6 m against a 10 m depth — a corridor, not a flat — and still only
# 2 panes on the long facade, because the outer end falls beyond the fixed
# x = +-30 glazing edge. At 18 it is 8 x 10 m with 3 panes on the long face plus
# the short-face return, which is the two-aspect unit the plan is aiming at.
#
# This works WITH the 2 m PIER_LONG rather than instead of it: the pier decides
# how much dead wall wraps the outboard end, the core offset decides how wide
# the unit is. Both were needed.
#
# The cost is the clear span between the cores, 28 -> 24 m. That is the span the
# sky garden reads across and the depth available to the middle units. 24 m is
# still well over the 20 m needed to keep the two stairs remote from each other,
# and worst-case egress is unchanged at 24.0 m.
CORE_OFFSET = 18.0
CORE_XS = (-CORE_OFFSET, +CORE_OFFSET)

assert CORE_OFFSET + CORE_W / 2 <= W / 2 - PIER_LONG, \
    "core must stay clear of the corner pier zone"
assert abs((CORE_OFFSET - CORE_W / 2) % PANE_W) < 1e-9 \
    and abs((CORE_OFFSET + CORE_W / 2) % PANE_W) < 1e-9, \
    "core edges should land on the pane grid"
assert 2 * CORE_W * CORE_D >= 203.5, "cores must hold the required provision"

PARAPET_H = 1.10
PARAPET_T = 0.25

# --- what sticks up above the roof -----------------------------------------
# A lift needs headroom above its topmost served floor for the car to overtravel
# and for the machine above it, and the stair needs a door out onto the roof. So
# the thing projecting above the parapet on a real tower is the CORE continuing
# up — a lift motor room and stair bulkhead sitting directly over the shafts.
# It is not a free-standing plant box placed wherever the elevation wants one.
#
# Two cores means two of these, at x = +-CORE_OFFSET, which is also what tells
# you from the street where the vertical circulation is.
CORE_OVERRUN = 4.6      # above the roof slab: lift overtravel + machine room
CORE_ROOF_PARAPET = 0.9  # low upstand around each bulkhead roof
# CORE_TOP_Z is derived once TOP_Z exists, just below.

BASE_Z = PILOTIS_FLOORS * H          # underside of the tower = 12.0
TOP_Z = BASE_Z + TOWER_FLOORS * H    # roof level = 160.0
# Top of the bulkhead upstand, which is the highest point on the building.
CORE_TOP_Z = TOP_Z + 0.22 + CORE_OVERRUN + 0.22 + CORE_ROOF_PARAPET

assert CORE_TOP_Z > TOP_Z + 0.22 + PARAPET_H, \
    "the core has to finish above the roof parapet, or it is not visible"

# Centre the refuge void in the GLAZED part of the tower, not in the tower as a
# whole, so it sits visually mid-way between the two blank bands rather than
# being pushed off-centre by them.
_glazed_first = SOLID_BASE_FLOORS
_glazed_last = TOWER_FLOORS - SOLID_TOP_FLOORS - 1
REFUGE_START = (_glazed_first + _glazed_last + 1 - REFUGE_FLOORS) // 2
REFUGE_END = REFUGE_START + REFUGE_FLOORS - 1        # inclusive, tower-relative
REFUGE_FLOOR_SET = set(range(REFUGE_START, REFUGE_END + 1)) if SKY_GARDEN else set()
# Storey number as an occupant would count it, from the ground.
REFUGE_STOREY = PILOTIS_FLOORS + REFUGE_START + 1
REFUGE_Z0 = BASE_Z + REFUGE_START * H
REFUGE_Z1 = REFUGE_Z0 + REFUGE_FLOORS * H

assert not (REFUGE_FLOOR_SET & (set(range(SOLID_BASE_FLOORS))
            | set(range(TOWER_FLOORS - SOLID_TOP_FLOORS, TOWER_FLOORS)))), \
    "the refuge void must not overlap the blank bands"
# SCDF: refuge floors no more than 20 storeys apart, and required above 24.
assert not SKY_GARDEN or TOTAL_FLOORS <= 24 or (
    REFUGE_STOREY <= 21 and TOTAL_FLOORS - REFUGE_STOREY <= 20), \
    "refuge floor spacing exceeds 20 storeys"

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


def cores(name, z0, height, mat):
    """The pair of service cores, as closed tubes.

    ring() builds about the origin, so each core is built there and then shifted
    onto its offset. Two separate tubes, not one figure-of-eight: they must be
    independently smoke-separated for the two stairs to count as remote.
    """
    parts = []
    for k, cx in enumerate(CORE_XS):
        tube = ring(f"{name}_{k}", z0, height, CORE_T, mat,
                    outer_w=CORE_W, outer_d=CORE_D)
        for ob in tube:
            ob.location.x += cx
        parts += tube
    return parts


# ---------------------------------------------------------------------------
# Facade pieces
# ---------------------------------------------------------------------------

def glass_ring(name, z0, height, mat):
    """Separate room windows on each of the four facades.

    Each 4 m room module gets its own slightly narrower pane. The resulting
    vertical gaps are real openings between homes, not just lines on a cap.
    """
    zc = z0 + height / 2.0
    off = GLASS_INSET + GLASS_T / 2.0
    parts = []
    for i in range(WINDOWS_SHORT):
        y = -OPEN_D / 2 + (i + 0.5) * PANE_PITCH
        for sx in (-1, 1):
            parts.append(box(f"{name}_ew_{i}_{sx}",
                             (sx * (W / 2 - off), y, zc),
                             (GLASS_T, PANE_GLASS_W, height), mat))
    for i in range(WINDOWS_LONG):
        x = -OPEN_W / 2 + (i + 0.5) * PANE_PITCH
        for sy in (-1, 1):
            parts.append(box(f"{name}_ns_{i}_{sy}",
                             (x, sy * (D / 2 - off), zc),
                             (PANE_GLASS_W, GLASS_T, height), mat))
    return parts


def interior_ring(name, z0, height, mat):
    """Lining set back behind the glazing, on all four facades.

    Clear glass needs something behind it. Without this the panes look straight
    through the tower to the far facade and the sky, and the glazing reads as a
    gap rather than a window. Set back INTERIOR_SETBACK so there is visible depth
    between pane and lining — that parallax against the sky reflection is what
    makes it read as glass.
    """
    zc = z0 + height / 2.0
    off = GLASS_INSET + INTERIOR_SETBACK
    t = 0.05
    parts = []
    for i in range(WINDOWS_SHORT):
        y = -OPEN_D / 2 + (i + 0.5) * PANE_PITCH
        for sx in (-1, 1):
            parts.append(box(f"{name}_ew_{i}_{sx}",
                             (sx * (W / 2 - off), y, zc),
                             (t, PANE_GLASS_W, height), mat))
    for i in range(WINDOWS_LONG):
        x = -OPEN_W / 2 + (i + 0.5) * PANE_PITCH
        for sy in (-1, 1):
            parts.append(box(f"{name}_ns_{i}_{sy}",
                             (x, sy * (D / 2 - off), zc),
                             (PANE_GLASS_W, t, height), mat))
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
    """Slim vertical frames breaking up the ribbon window.

    The cap is recessed from the facade plane while the glass remains flush. This
    makes the pane joints read as deliberate shadow gaps without changing the
    window opening or facade dimensions.
    """
    parts = []
    zc = z0 + height / 2.0
    depth = 0.14
    off = GLASS_INSET + depth / 2.0 + MULLION_INSET

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


def balustrade(name, z0, mat):
    """Open-edge guarding around the sky garden.

    The void has no facade, so this is what holds the building line and keeps the
    elevation reading as continuous. It runs between the corner piers, i.e. the
    same clear opening the windows use, so the vertical rhythm is unbroken.
    """
    zc = z0 + BALUSTRADE_H / 2.0
    t = BALUSTRADE_T
    off = WALL_T / 2.0
    return [
        box(f"{name}_S", (0.0, -(D / 2 - off), zc), (OPEN_W, t, BALUSTRADE_H), mat),
        box(f"{name}_N", (0.0, +(D / 2 - off), zc), (OPEN_W, t, BALUSTRADE_H), mat),
        box(f"{name}_W", (-(W / 2 - off), 0.0, zc), (t, OPEN_D, BALUSTRADE_H), mat),
        box(f"{name}_E", (+(W / 2 - off), 0.0, zc), (t, OPEN_D, BALUSTRADE_H), mat),
    ]


def col_bay(axis_len, pitch):
    """Refuge-column bay across an opening: whole panes, closest to `pitch`.

    The bay has to DIVIDE the pane count, or the columns stop landing on mullion
    lines and the vertical rhythm breaks exactly where the facade is most exposed.
    Rounding axis_len / pitch is not enough: the bay must divide the room-window
    count, or the columns stop landing on mullion lines.
    """
    panes = int(round(axis_len / PANE_W))
    want = max(1, int(round(pitch / PANE_W)))
    divisors = [k for k in range(1, panes + 1) if panes % k == 0]
    per_bay = min(divisors, key=lambda k: (abs(k - want), k))
    return per_bay * PANE_W


def grille(name, z0, height, mat):
    """Screen across the open refuge level.

    Holds the facade plane where the glazing stops, without closing the level in:
    every cell is a real opening, so the refuge floor still ventilates.

    The GRID pitch is PANE_W, so a cell sits directly over each window pane and
    the vertical lines carry through from the floor below to the floor above. Any
    other pitch makes the garden read as a separate object stuck into the tower.
    """
    parts = []
    off = WALL_T / 2.0

    def divisions(axis_len, pitch):
        """Member centres across an opening, ends included."""
        n = max(1, int(round(axis_len / pitch)))
        step = axis_len / n
        return [-axis_len / 2 + i * step for i in range(n + 1)]

    if GRILLE_STYLE == "FINS":
        # Vertical blades only, full height of the void.
        zc = z0 + height / 2.0
        for sy in (-1, 1):
            for i, x in enumerate(divisions(OPEN_W, FIN_PITCH)):
                parts.append(box(
                    f"{name}_fin_ns_{i}_{sy}",
                    (x, sy * (D / 2 - off), zc),
                    (FIN_W, FIN_DEPTH, height), mat))
        for sx in (-1, 1):
            for i, y in enumerate(divisions(OPEN_D, FIN_PITCH)):
                parts.append(box(
                    f"{name}_fin_ew_{i}_{sx}",
                    (sx * (W / 2 - off), y, zc),
                    (FIN_DEPTH, FIN_W, height), mat))
        return parts

    # GRID: verticals on the pane pitch, plus horizontals making square cells.
    zc = z0 + height / 2.0
    n_rows = max(1, int(round(height / GRILLE_CELL)))
    row_pitch = height / n_rows

    for sy in (-1, 1):
        y = sy * (D / 2 - off)
        for i, x in enumerate(divisions(OPEN_W, GRILLE_CELL)):
            parts.append(box(
                f"{name}_v_ns_{i}_{sy}", (x, y, zc),
                (GRILLE_MEMBER, GRILLE_DEPTH, height), mat))
        for r in range(n_rows + 1):
            z = z0 + r * row_pitch
            # Clamp the end rails so they sit inside the void, not over the slabs.
            zr = min(max(z, z0 + GRILLE_MEMBER / 2), z0 + height - GRILLE_MEMBER / 2)
            parts.append(box(
                f"{name}_h_ns_{r}_{sy}", (0.0, y, zr),
                (OPEN_W, GRILLE_DEPTH, GRILLE_MEMBER), mat))

    for sx in (-1, 1):
        x = sx * (W / 2 - off)
        for i, y in enumerate(divisions(OPEN_D, GRILLE_CELL)):
            parts.append(box(
                f"{name}_v_ew_{i}_{sx}", (x, y, zc),
                (GRILLE_DEPTH, GRILLE_MEMBER, height), mat))
        for r in range(n_rows + 1):
            z = z0 + r * row_pitch
            zr = min(max(z, z0 + GRILLE_MEMBER / 2), z0 + height - GRILLE_MEMBER / 2)
            parts.append(box(
                f"{name}_h_ew_{r}_{sx}", (x, 0.0, zr),
                (GRILLE_DEPTH, OPEN_D, GRILLE_MEMBER), mat))

    return parts


def sky_garden(name, z0, slab_mat, plant_mat, trunk_mat, metal_mat):
    """Planted refuge level, open on all four sides.

    Laid out as a perimeter walk: planters set just inside the balustrade, trees
    spaced along the long faces, and the floor left clear in the middle for the
    refuge area itself. Everything sits on the garden slab, which is thicker than
    a normal plate because it carries soil.
    """
    parts_struct, parts_plant, parts_trunk = [], [], []

    # Garden floor slab, spanning the full footprint inside the piers.
    parts_struct.append(box(
        f"{name}_Slab", (0.0, 0.0, z0 - GARDEN_SLAB_T / 2.0),
        (W - 2 * WALL_T, D - 2 * WALL_T, GARDEN_SLAB_T), slab_mat))

    # Planter troughs just inside the open edges, one run per long facade.
    inset = WALL_T + 1.1
    for sy in (-1, 1):
        parts_struct.append(box(
            f"{name}_Planter_{sy}",
            (0.0, sy * (D / 2 - inset - PLANTER_W / 2), z0 + PLANTER_H / 2.0),
            (OPEN_W - 4.0, PLANTER_W, PLANTER_H), slab_mat))
        # Massed planting sitting in the trough, slightly proud of its walls.
        parts_plant.append(box(
            f"{name}_Shrubs_{sy}",
            (0.0, sy * (D / 2 - inset - PLANTER_W / 2), z0 + PLANTER_H + 0.35),
            (OPEN_W - 4.4, PLANTER_W - 0.3, 0.95), plant_mat))

    # Trees along the long faces. Trunk plus a broad flat canopy — enough to read
    # as a tree in silhouette at this distance without modelling a real one.
    n_trees = 7
    span = OPEN_W - 8.0
    for i in range(n_trees):
        x = -span / 2 + i * span / (n_trees - 1)
        for sy in (-1, 1):
            y = sy * (D / 2 - inset - PLANTER_W / 2)
            parts_trunk.append(box(
                f"{name}_Trunk_{i}_{sy}", (x, y, z0 + PLANTER_H + TREE_H / 2.0),
                (0.34, 0.34, TREE_H), trunk_mat))
            parts_plant.append(box(
                f"{name}_Canopy_{i}_{sy}",
                (x, y, z0 + PLANTER_H + TREE_H + 0.45),
                (CANOPY_D, min(CANOPY_D, PLANTER_W + 0.8), 1.5), plant_mat))

    # No separate posts here: the grille's verticals sit on the facade line at the
    # pane pitch and read as the structure carrying the floors above. Adding posts
    # too would double up members in the same plane.

    return parts_struct, parts_plant, parts_trunk


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

    # A tilted slat sweeps deeper than half its own depth, so keying the offset
    # to slat_depth / 2 would push its corner through the wall plane once
    # VENT_INSET is 0. Use the rotated extent instead: the slat then finishes
    # exactly flush however it is tilted.
    slat_half = (slat_depth / 2.0 * math.cos(tilt)
                 + slat_t / 2.0 * math.sin(tilt))
    off = VENT_INSET + slat_half
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
    interior = mats["interior"]

    walls, glazing, frames, louvres, backs, slabs, structure = [], [], [], [], [], [], []
    linings = []
    plants, trunks, grilles = [], [], []
    foliage_mat = mats["foliage"]
    trunk_mat = mats["trunk"]

    # --- continuous structural column grid ------------------------------
    structure += [box("GroundSlab", (0.0, 0.0, -0.15), (W + 14.0, D + 14.0, 0.30), concrete)]

    for i, x in enumerate(col_grid(W)):
        for j, y in enumerate(col_grid(D)):
            # Skip columns that would land inside a service core wall. Two cores
            # now, so this tests both.
            if any(abs(x - cx) < CORE_W / 2 + COL_SIZE
                   and abs(y) < CORE_D / 2 + COL_SIZE for cx in CORE_XS):
                continue
            structure.append(box(
                f"Column_{i}_{j}", (x, y, TOP_Z / 2.0),
                (COL_SIZE, COL_SIZE, TOP_Z), concrete))

    # Service cores rising through the open floors (stairs / lifts).
    structure += cores("Core", 0.0, BASE_Z, concrete)

    # Intermediate landings inside each core, one per open floor.
    for f in range(1, PILOTIS_FLOORS):
        for k, cx in enumerate(CORE_XS):
            structure.append(box(
                f"CoreLanding_{k}_{f}", (cx, 0.0, f * H),
                (CORE_W - 2 * CORE_T, CORE_D - 2 * CORE_T, 0.18), concrete))

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

        if f in REFUGE_FLOOR_SET:
            # Refuge / sky garden: open on all sides. No glazing, no spandrel and
            # no intermediate slab, so the storeys read as one double-height void.
            # The corner piers still turn the corners, holding the building line.
            walls += corner_piers(f"{tag}_Pier", z0, H, spandrel)
            if f == REFUGE_START:
                walls += balustrade(f"{tag}_Balustrade", z0, spandrel)
                # Screen across the whole void, holding the facade plane.
                grilles += grille("SkyGarden_Grille", z0, REFUGE_FLOORS * H,
                                  spandrel)
                g_struct, g_plant, g_trunk = sky_garden(
                    "SkyGarden", z0, concrete, foliage_mat, trunk_mat, metal)
                structure += g_struct
                plants += g_plant
                trunks += g_trunk
            if f == REFUGE_END:
                # Slabs are added at the TOP of each floor, so skipping the refuge
                # storeys would leave the void with no ceiling and the floor above
                # with nothing under it.
                slabs.append(box(
                    f"{tag}_Slab", (0.0, 0.0, z0 + H - SLAB_T / 2.0),
                    (W - 2 * WALL_T, D - 2 * WALL_T, SLAB_T), concrete))
            continue

        if f in blank_floors:
            # Blank floor: solid wall the whole storey height, no openings.
            walls += ring(f"{tag}_Blank", z0, H, WALL_T, spandrel)
            if not (SKY_GARDEN and f == REFUGE_START - 1):
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
        # Behind the glass, so the clear panes have something to show.
        linings += interior_ring(f"{tag}_Interior", z0 + WIN_Z, WIN_H, interior)

        # Floor plate for the level above, visible behind the glazing. Skipped
        # directly under the refuge level, where the thicker garden slab (which
        # shares the same top face) does the job instead.
        if not (SKY_GARDEN and f == REFUGE_START - 1):
            slabs.append(box(f"{tag}_Slab", (0.0, 0.0, z0 + H - SLAB_T / 2.0),
                             (W - 2 * WALL_T, D - 2 * WALL_T, SLAB_T), concrete))

    # --- roof ----------------------------------------------------------
    structure.append(box("RoofSlab", (0.0, 0.0, TOP_Z + 0.11),
                         (W, D, 0.22), concrete))
    structure += ring("Parapet", TOP_Z + 0.22, PARAPET_H, PARAPET_T, spandrel)

    # Lift motor rooms / stair bulkheads: the cores continuing above the roof.
    # Sized and placed by the cores themselves rather than by eye, so they sit
    # over the shafts they serve and move if the cores ever move.
    structure += cores("CoreOverrun", TOP_Z + 0.22, CORE_OVERRUN, concrete)
    for k, cx in enumerate(CORE_XS):
        # Cap slab, then a low upstand around it.
        structure.append(box(
            f"CoreOverrunRoof_{k}",
            (cx, 0.0, TOP_Z + 0.22 + CORE_OVERRUN + 0.11),
            (CORE_W, CORE_D, 0.22), concrete))
    structure += cores("CoreOverrunParapet",
                       TOP_Z + 0.22 + CORE_OVERRUN + 0.22,
                       CORE_ROOF_PARAPET, spandrel)

    ground = box("Ground", (0.0, 0.0, -0.32), (600.0, 600.0, 0.04), ground_mat)

    # The cores run UNBROKEN from the ground to the overrun above the roof. They
    # were previously built only at the pilotis and refuge levels, which left the
    # tower hollow between them — the lift shafts stopped and started again, and
    # the motor rooms on the roof would have sat on nothing. A shaft has to be
    # continuous to be a shaft.
    #
    # Within the refuge level they stay visible, which is what makes that void
    # read as a level you arrive at rather than a gap. With two of them the garden
    # reads as running BETWEEN two solid piers, which is a better reading than one
    # lump in the middle — the 28 m of clear span between them is the view.
    structure += cores("TowerCore", BASE_Z, TOP_Z - BASE_Z, concrete)

    merged = {
        "Facade_Spandrels": join(walls, "Facade_Spandrels"),
        "Windows_Glass": join(glazing, "Windows_Glass"),
        "Interior_Lining": join(linings, "Interior_Lining"),
        "Sky_Garden_Grille": join(grilles, "Sky_Garden_Grille"),
        "Sky_Garden_Planting": join(plants, "Sky_Garden_Planting"),
        "Sky_Garden_Trunks": join(trunks, "Sky_Garden_Trunks"),
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
        # Filter Glossy blurs glossy and refractive rays to reduce noise. At 1.0
        # it frosts perfectly smooth glass all by itself, whatever the material
        # says — so keep it off and pay for the noise in samples instead.
        if hasattr(scene.cycles, "blur_glossy"):
            scene.cycles.blur_glossy = 0.0
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
    print(f"continuous columns   : {len(col_grid(W))} x {len(col_grid(D))} grid, "
          f"{COL_SIZE:.2f} m square, >= {COL_CLEAR_INSET:.1f} m inside facade")
    print(f"roof parapet top     : {TOP_Z + PARAPET_H + 0.22:.2f} m")
    print(f"total height         : {CORE_TOP_Z:.2f} m to the top of the core "
          f"bulkheads ({CORE_TOP_Z - (TOP_Z + PARAPET_H + 0.22):.2f} m above "
          f"the parapet)")
    print(f"blank base floor(s)  : {SOLID_BASE_FLOORS} "
          f"({BASE_Z:.1f} -> {BASE_Z + SOLID_BASE_FLOORS * H:.1f} m)")
    print(f"blank top band       : {SOLID_TOP_FLOORS} floors = "
          f"{SOLID_TOP_FLOORS * H:.1f} m "
          f"({TOP_Z - SOLID_TOP_FLOORS * H:.1f} -> {TOP_Z:.1f} m)")
    print(f"glazed floors        : "
          f"{TOWER_FLOORS - SOLID_BASE_FLOORS - SOLID_TOP_FLOORS - len(REFUGE_FLOOR_SET)}")
    if SKY_GARDEN:
        print(f"refuge / sky garden  : storeys {REFUGE_STOREY}-"
              f"{REFUGE_STOREY + REFUGE_FLOORS - 1} "
              f"({REFUGE_Z0:.1f} -> {REFUGE_Z1:.1f} m), {REFUGE_FLOORS} floors open "
              f"= {REFUGE_FLOORS * H:.1f} m double height")
        print(f"refuge spacing       : {REFUGE_STOREY} storeys up, "
              f"{TOTAL_FLOORS - REFUGE_STOREY} above (SCDF: max 20 apart)")
        print("columns across void  : same continuous full-height structural grid")
        if GRILLE_STYLE == "GRID":
            n_rows = max(1, round(REFUGE_FLOORS * H / GRILLE_CELL))
            print(f"garden screen        : GRID, {WINDOWS_LONG} x {n_rows} cells "
                  f"on the long face, {GRILLE_CELL:.2f} m pitch (= pane pitch, so "
                  f"the lines align), {GRILLE_MEMBER:.2f} m members "
                  f"{GRILLE_DEPTH:.2f} m deep")
        else:
            print(f"garden screen        : FINS, {FIN_W:.2f} m blades at "
                  f"{FIN_PITCH:.2f} m centres, {FIN_DEPTH:.2f} m deep")
    print(f"corner piers         : {PIER_LONG:.1f} m on long facades / "
          f"{PIER_SHORT:.1f} m on short facades")
    print(f"long-facade margins  : {PIER_LONG:.1f} m left/right, "
          f"{SOLID_BASE_FLOORS * H:.1f} m below, {SOLID_TOP_FLOORS * H:.1f} m above")
    print(f"clear window opening : {OPEN_W:.1f} m (long face) / {OPEN_D:.1f} m (short face)")
    print(f"room windows/floor    : {WINDOWS_LONG} long face / {WINDOWS_SHORT} short face")
    print(f"pane pitch           : {PANE_PITCH:.2f} m (= pane width; mullions are "
          f"{MULLION_W:.2f} m caps over the joints)")
    print(f"clear internal depth : {D - 2 * WALL_T:.2f} m (inside face to inside face)")
    print(f"service cores        : 2 x {CORE_W:.0f} x {CORE_D:.0f} m at "
          f"x = {CORE_XS[0]:+.0f} / {CORE_XS[1]:+.0f}, "
          f"{2 * CORE_W * CORE_D:.0f} m2 total "
          f"({2 * CORE_W * CORE_D / (W * D) * 100:.1f}% of the plate)")
    print(f"core spacing         : {2 * CORE_OFFSET:.0f} m between centres, "
          f"{2 * (CORE_OFFSET - CORE_W / 2):.0f} m clear between them, "
          f"{W / 2 - (CORE_OFFSET + CORE_W / 2):.0f} m to each building end")
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


def frame_viewport():
    """Park the saved VIEWPORT well back from the building.

    This is separate from scene.camera, which only affects renders. Opening a
    .blend restores the view_distance stored in its screen layout, and under
    --factory-startup that is the default ~17 m — inside a 166 m tower, so you
    land in the middle of the model and have to zoom out every time.

    Distance is derived from the building rather than fixed, so it keeps working
    if the footprint or floor count changes. The diagonal is the dimension that
    has to fit, not the height alone.
    """
    diag = math.sqrt(W ** 2 + D ** 2 + CORE_TOP_Z ** 2)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type != "VIEW_3D":
                    continue
                r3d = space.region_3d
                # Orbit about mid-height, so the tower sits in frame rather than
                # running off the top with the ground at centre.
                r3d.view_location = Vector((0.0, 0.0, CORE_TOP_Z * 0.5))
                r3d.view_distance = diag * 1.6
                # A 3/4 view from the south-east: the lit side, matching where the
                # render cameras sit.
                r3d.view_rotation = Euler(
                    (math.radians(72.0), 0.0, math.radians(38.0)), "XYZ"
                ).to_quaternion()
                r3d.view_perspective = "PERSP"
                # Far clip has to clear the pull-back or the model is culled and
                # you open onto an empty grey viewport — worse than being inside.
                space.clip_end = max(space.clip_end, diag * 6.0)
                space.clip_start = 0.5
                space.lens = 35.0


def main():
    objects = build()
    setup_render()
    report(objects)
    frame_viewport()

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
