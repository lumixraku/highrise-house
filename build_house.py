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
  width of every facade, starting 0.75 m above its floor level.
* Directly above and below that window sits a 0.25 m ventilation louvre
  strip of the same length as the window.

Vertical band layout per floor, measured from the floor level:
    0.00 - 0.50  solid spandrel
    0.50 - 0.75  ventilation louvres
    0.75 - 2.25  window
    2.25 - 2.50  ventilation louvres
    2.50 - 4.00  solid spandrel
"""

import math
import os
import random
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

PILOTIS_FLOORS = 3     # of which these are open and raised
BLOCK_GROUPS = 2       # residential groups in the first/current tower
BLOCK_FLOORS = 17      # glazed residential floors in each group
REFUGE_FLOORS = 2      # fixed double-height refuge / sky-garden floors
FIXED_SOLID_BAND_FLOORS = 4  # 2 blank floors at the base + 2 at the top
TOTAL_FLOORS = (PILOTIS_FLOORS + BLOCK_GROUPS * BLOCK_FLOORS
                + (BLOCK_GROUPS - 1) * REFUGE_FLOORS
                + FIXED_SOLID_BAND_FLOORS)
TOWER_FLOORS = TOTAL_FLOORS - PILOTIS_FLOORS   # occupied floors above

TOWER_GAP = 18.0       # clear horizontal gap between the two building envelopes

WALL_T = 0.30     # facade wall thickness
SLAB_T = 0.22     # floor plate thickness

WIN_H = 1.50      # window height
VENT_H = 0.25     # ventilation strip height
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
WINDOWS_LONG = 18      # room windows across each long facade  (X)
WINDOWS_SHORT = 7       # room windows across each short facade (Y)
WINDOW_GAP = 0.12       # real vertical joint between adjacent room windows
PANE_GLASS_W = PANE_W - WINDOW_GAP

# The mullion is a cover cap centred on each pane joint: it sits proud of the
# glass line and overlaps the two panes it joins, so it costs NO facade length.
# That keeps the arithmetic clean — an opening is exactly N x PANE_W, so the
# footprint comes out on whole metres:
#   W = 18 x 4.00 + 2 x 2.00 = 76.00 m
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
# Each pair of groups is separated by one two-storey void. With three groups,
# this gives two refuge / sky-garden levels and keeps every residential group at
# the configured 17 floors.
#
# REFUGE_FLOORS floors have one continuous 8 m interior void with no intermediate
# slab. On the outside, only the lower 6 m is screened by the grille; a solid
# 2 m facade band above it closes the visible opening without changing the void.
SKY_GARDEN = True
REFUGE_GRILLE_TOP_BLANK_H = 2.0  # solid facade band above the 6 m grille
BALUSTRADE_H = 1.20        # open-edge guarding, per SCDF minimum 1.0 m
BALUSTRADE_T = 0.12

# A screen across the lower part of the void. The upper solid band holds the
# facade plane above the screen, while the lower openings remain naturally
# ventilated as a refuge floor must be.
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

COL_SIZE = 1.60       # continuous column footprint (sized for the tower load)
CORNER_COL_SIZE = 2.00  # exactly fills each retained 2 m corner facade margin
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
# plate, deliberately: it is the stricter of the two and the measured 360 m2
# clears it anyway, so keeping it means the cores cannot shrink on the strength
# of a smaller unit count.
#
# Splitting also fixes two things one core cannot:
#   * Egress. Worst-case travel to a central core was 42.5 m, marginal against
#     SCDF's ~30 m dead-end / ~45 m two-way. Twin cores bring it to 20 m.
#   * Stair remoteness. Two stairs in ONE shaft are not independent — a single
#     incident compromises both. The two core centres stay well separated.
#   * Lift zoning, which a 551-unit tower wants anyway: low zone in the west
#     core, high zone in the east, ~65 units per lift in each.
#
# Deliberately NOT an H-core: the spine that makes it an H would run a wall down
# the middle of the plate, forcing single-loaded corridors either side. H-cores
# suit office towers wanting deep lettable space; residential wants a continuous
# corridor loop.
# The core length is derived per tower from the long-face column grid below.
# Each tube spans a configured number of column bays; the column outer faces
# become the tube ends.
# These bootstrap values describe the reference tower until configure_tower()
# refreshes them for the active footprint.
CORE_COLUMN_BAYS = 2
COMPANION_CORE_COLUMN_BAYS = 3
CORE_W, CORE_D = 20.0, 9.0    # derived long length / fixed apartment-depth width
CORE_T = 0.28                 # core wall thickness
# The active tower derives CORE_OFFSET and CORE_W from its long-face column grid.
# The outermost core boundary stays one column line in from each end of the
# usable grid. Increasing the bay count therefore lengthens each tube inward,
# preserving the outboard stub while reducing the gap between the cores.
CORE_OFFSET = 18.0       # bootstrap value; refreshed by configure_tower()
CORE_XS = (-CORE_OFFSET, +CORE_OFFSET)

assert CORE_OFFSET + CORE_W / 2 <= W / 2 - PIER_LONG, \
    "core must stay clear of the corner pier zone"
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
TOP_Z = BASE_Z + TOWER_FLOORS * H    # roof level = 172.0
# The roof repeats the planted refuge-level language, but remains entirely open
# to the sky: its grille replaces the solid perimeter parapet and no canopy is
# added over the terrace. The lift/stair overruns remain the only roof volumes.
ROOF_GARDEN = True
ROOF_GARDEN_Z0 = TOP_Z + 0.22
# Match the refuge garden's full two-storey grille height, not the roof parapet.
ROOF_GARDEN_GRILLE_H = 2 * H

# --- refuge-level lateral trusses ------------------------------------------
# The taller companion tower gets a visible outrigger / belt-truss system at
# each double-height refuge level.  Members stay inside the facade line and
# use the same dark metal as the mullions so the structure reads as a deliberate
# architectural layer rather than a second concrete wall.
TRUSS_MEMBER = 0.38
TRUSS_FACADE_INSET = 0.55
TRUSS_CORE_FACE_OFFSET = 0.20
TRUSS_LEVEL_EDGE = 0.75
TRUSS_EDGE_INSET = 0.65
TRUSS_PLAN_MEMBER = 0.20       # hidden inside the refuge-level upper slab
# Top of the bulkhead upstand, which is the highest point on the building.
CORE_TOP_Z = TOP_Z + 0.22 + CORE_OVERRUN + 0.22 + CORE_ROOF_PARAPET

assert CORE_TOP_Z > TOP_Z + 0.22 + PARAPET_H, \
    "the core has to finish above the roof parapet, or it is not visible"

# Centre the refuge void in the GLAZED part of the tower, not in the tower as a
# whole, so it sits visually mid-way between the two blank bands rather than
# being pushed off-centre by them.
_glazed_first = SOLID_BASE_FLOORS
_glazed_last = TOWER_FLOORS - SOLID_TOP_FLOORS - 1
REFUGE_STARTS = [
    _glazed_first + (index + 1) * BLOCK_FLOORS + index * REFUGE_FLOORS
    for index in range(BLOCK_GROUPS - 1)
]
REFUGE_ENDS = [start + REFUGE_FLOORS - 1 for start in REFUGE_STARTS]
REFUGE_FLOOR_SET = (set().union(*[
    set(range(start, end + 1))
    for start, end in zip(REFUGE_STARTS, REFUGE_ENDS)
]) if SKY_GARDEN else set())
# Keep the first refuge aliases for the extra-view and verifier scripts.
REFUGE_START, REFUGE_END = REFUGE_STARTS[0], REFUGE_ENDS[0]
REFUGE_STOREYS = [PILOTIS_FLOORS + start + 1 for start in REFUGE_STARTS]
REFUGE_STOREY = REFUGE_STOREYS[0]
REFUGE_Z0S = [BASE_Z + start * H for start in REFUGE_STARTS]
REFUGE_Z1S = [z0 + REFUGE_FLOORS * H for z0 in REFUGE_Z0S]
REFUGE_Z0, REFUGE_Z1 = REFUGE_Z0S[0], REFUGE_Z1S[0]
REFUGE_GRILLE_Z0S = REFUGE_Z0S
REFUGE_GRILLE_Z1S = [z1 - REFUGE_GRILLE_TOP_BLANK_H for z1 in REFUGE_Z1S]
REFUGE_GRILLE_Z0, REFUGE_GRILLE_Z1 = REFUGE_GRILLE_Z0S[0], REFUGE_GRILLE_Z1S[0]
REFUGE_GRILLE_H = REFUGE_GRILLE_Z1 - REFUGE_GRILLE_Z0
REFUGE_START_BY_FLOOR = {start: index for index, start in enumerate(REFUGE_STARTS)}
REFUGE_END_BY_FLOOR = {end: index for index, end in enumerate(REFUGE_ENDS)}

assert abs(REFUGE_GRILLE_H - 6.0) < 1e-9 and REFUGE_GRILLE_Z0 == REFUGE_Z0, \
    "the refuge grille must start at the refuge floor and be 6 m high"
assert abs(REFUGE_Z1 - REFUGE_GRILLE_Z1 - REFUGE_GRILLE_TOP_BLANK_H) < 1e-9, \
    "the refuge grille must leave its configured top blank band"

assert not (REFUGE_FLOOR_SET & (set(range(SOLID_BASE_FLOORS))
            | set(range(TOWER_FLOORS - SOLID_TOP_FLOORS, TOWER_FLOORS)))), \
    "the refuge void must not overlap the blank bands"
assert SOLID_BASE_FLOORS + SOLID_TOP_FLOORS == FIXED_SOLID_BAND_FLOORS, \
    "the fixed solid-band floor count must match its two derived bands"
assert len(REFUGE_STARTS) == BLOCK_GROUPS - 1
assert all((start - (REFUGE_ENDS[index - 1] + 1 if index else _glazed_first)
            == BLOCK_FLOORS)
           for index, start in enumerate(REFUGE_STARTS)), \
    "each refuge must follow its configured residential group"
assert _glazed_last - REFUGE_ENDS[-1] == BLOCK_FLOORS, \
    "the final residential group must retain its configured floor count"
assert all((storey - (PILOTIS_FLOORS + _glazed_first + 1)) <= 21 + index * 20
           for index, storey in enumerate(REFUGE_STOREYS)), \
    "refuge floor spacing exceeds the configured interval"


def configure_tower(block_groups, windows_long, core_column_bays=CORE_COLUMN_BAYS):
    """Refresh the derived geometry for one tower variant."""
    global BLOCK_GROUPS, WINDOWS_LONG, CORE_COLUMN_BAYS
    global TOTAL_FLOORS, TOWER_FLOORS, OPEN_W, OPEN_D, W, D
    global PANE_GLASS_LONG, PANE_GLASS_SHORT
    global CORE_W, CORE_OFFSET, CORE_XS
    global BASE_Z, TOP_Z, ROOF_GARDEN_Z0, CORE_TOP_Z
    global _glazed_first, _glazed_last
    global REFUGE_STARTS, REFUGE_ENDS, REFUGE_FLOOR_SET
    global REFUGE_START, REFUGE_END, REFUGE_STOREYS, REFUGE_STOREY
    global REFUGE_Z0S, REFUGE_Z1S, REFUGE_Z0, REFUGE_Z1
    global REFUGE_GRILLE_Z0S, REFUGE_GRILLE_Z1S
    global REFUGE_GRILLE_Z0, REFUGE_GRILLE_Z1, REFUGE_GRILLE_H
    global REFUGE_START_BY_FLOOR, REFUGE_END_BY_FLOOR

    BLOCK_GROUPS = int(block_groups)
    WINDOWS_LONG = int(windows_long)
    CORE_COLUMN_BAYS = int(core_column_bays)
    if BLOCK_GROUPS < 2 or WINDOWS_LONG < 1:
        raise ValueError("each tower needs at least two groups and one long-face room")

    TOTAL_FLOORS = (PILOTIS_FLOORS + BLOCK_GROUPS * BLOCK_FLOORS
                    + (BLOCK_GROUPS - 1) * REFUGE_FLOORS
                    + FIXED_SOLID_BAND_FLOORS)
    TOWER_FLOORS = TOTAL_FLOORS - PILOTIS_FLOORS
    OPEN_W = opening_for(WINDOWS_LONG)
    OPEN_D = opening_for(WINDOWS_SHORT)
    W = OPEN_W + 2 * PIER_LONG
    D = OPEN_D + 2 * PIER_SHORT
    CORE_W, CORE_OFFSET, CORE_XS = core_layout(W)
    PANE_GLASS_LONG = PANE_GLASS_W
    PANE_GLASS_SHORT = PANE_GLASS_W

    if CORE_OFFSET + CORE_W / 2 > W / 2 - PIER_LONG:
        raise ValueError("tower is too narrow for the configured service cores")
    if CORE_W <= COL_SIZE:
        raise ValueError("core length must leave room for its defining columns")

    BASE_Z = PILOTIS_FLOORS * H
    TOP_Z = BASE_Z + TOWER_FLOORS * H
    ROOF_GARDEN_Z0 = TOP_Z + 0.22
    CORE_TOP_Z = TOP_Z + 0.22 + CORE_OVERRUN + 0.22 + CORE_ROOF_PARAPET

    _glazed_first = SOLID_BASE_FLOORS
    _glazed_last = TOWER_FLOORS - SOLID_TOP_FLOORS - 1
    REFUGE_STARTS = [
        _glazed_first + (index + 1) * BLOCK_FLOORS + index * REFUGE_FLOORS
        for index in range(BLOCK_GROUPS - 1)
    ]
    REFUGE_ENDS = [start + REFUGE_FLOORS - 1 for start in REFUGE_STARTS]
    REFUGE_FLOOR_SET = (set().union(*[
        set(range(start, end + 1))
        for start, end in zip(REFUGE_STARTS, REFUGE_ENDS)
    ]) if SKY_GARDEN else set())
    REFUGE_START, REFUGE_END = REFUGE_STARTS[0], REFUGE_ENDS[0]
    REFUGE_STOREYS = [PILOTIS_FLOORS + start + 1 for start in REFUGE_STARTS]
    REFUGE_STOREY = REFUGE_STOREYS[0]
    REFUGE_Z0S = [BASE_Z + start * H for start in REFUGE_STARTS]
    REFUGE_Z1S = [z0 + REFUGE_FLOORS * H for z0 in REFUGE_Z0S]
    REFUGE_Z0, REFUGE_Z1 = REFUGE_Z0S[0], REFUGE_Z1S[0]
    REFUGE_GRILLE_Z0S = REFUGE_Z0S
    REFUGE_GRILLE_Z1S = [z1 - REFUGE_GRILLE_TOP_BLANK_H for z1 in REFUGE_Z1S]
    REFUGE_GRILLE_Z0, REFUGE_GRILLE_Z1 = REFUGE_GRILLE_Z0S[0], REFUGE_GRILLE_Z1S[0]
    REFUGE_GRILLE_H = REFUGE_GRILLE_Z1 - REFUGE_GRILLE_Z0
    REFUGE_START_BY_FLOOR = {start: index for index, start in enumerate(REFUGE_STARTS)}
    REFUGE_END_BY_FLOOR = {end: index for index, end in enumerate(REFUGE_ENDS)}

    assert abs(REFUGE_GRILLE_H - 6.0) < 1e-9
    assert _glazed_last - REFUGE_ENDS[-1] == BLOCK_FLOORS


OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
SITE_WIDTH = 2 * W + TOWER_GAP
SITE_CENTER_X = (W + TOWER_GAP) / 2.0
SITE_DEPTH = D
SITE_TOP_Z = CORE_TOP_Z

# Band offsets inside one floor. The vent + glass + vent band starts 0.50 m
# above the floor; the taller remaining solid spandrel sits above it.
SPANDREL_LO_H = 0.50
VENT_LO_Z = SPANDREL_LO_H                       # 0.50
WIN_Z = VENT_LO_Z + VENT_H                      # 0.75
VENT_HI_Z = WIN_Z + WIN_H                       # 2.25
SPANDREL_HI_Z = VENT_HI_Z + VENT_H              # 2.50
SPANDREL_HI_H = H - SPANDREL_HI_Z               # 1.50

assert abs(SPANDREL_LO_H + VENT_H + WIN_H + VENT_H + SPANDREL_HI_H - H) < 1e-9

# Compact warm ceiling fixtures sit just inside the upper edge of each window
# bay. Their top remains below the opaque spandrel, so the glow reads as a room
# light through the glass rather than as a new facade band.
CEILING_LIGHT_W = 2.20
CEILING_LIGHT_D = 0.36
CEILING_LIGHT_H = 0.06
CEILING_LIGHT_TOP_GAP = 0.05
CEILING_LIGHT_Z = WIN_Z + WIN_H - CEILING_LIGHT_TOP_GAP - CEILING_LIGHT_H / 2.0
# A night-time residential facade should never have every room occupied and lit.
# Keep the pattern deterministic so rebuilding the same scheme does not change
# its appearance, while leaving enough adjacent windows on to read as homes.
CEILING_LIGHT_SEED = 20260823
CEILING_LIGHT_ON_RATIO = 0.36


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


def beam_between(name, start, end, width, mat):
    """Make a square structural member between two world-space points."""
    start, end = Vector(start), Vector(end)
    delta = end - start
    length = delta.length
    if length <= 1e-6:
        return None
    rotation = delta.to_track_quat("Z", "Y").to_euler()
    return box(name, (start + end) / 2.0,
               (width, width, length), mat, rot=rotation)


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


def core_layout(span, core_column_bays=None):
    """Derive the twin-core long dimension from the active column grid.

    Each core occupies ``core_column_bays`` long-face column bays. Its outer
    boundary remains one grid line in from each end, and its inner boundary
    moves inward as bays are added. The outside faces of the boundary columns
    become the tube ends, so those columns remain visible and structurally meet
    the core walls instead of stopping short.
    """
    grid = col_grid(span)
    bays = CORE_COLUMN_BAYS if core_column_bays is None else int(core_column_bays)
    if bays < 1:
        raise ValueError("core layout needs at least one column bay")
    west_lo_index = 1
    west_hi_index = west_lo_index + bays
    east_hi_index = len(grid) - 2
    east_lo_index = east_hi_index - bays
    if west_hi_index >= east_lo_index:
        raise ValueError("tower is too narrow for the configured core column bays")

    west_lo = grid[west_lo_index]
    west_hi = grid[west_hi_index]
    east_lo = grid[east_lo_index]
    east_hi = grid[east_hi_index]
    core_w = (west_hi - west_lo) + COL_SIZE
    west_center = (west_lo + west_hi) / 2.0
    east_center = (east_lo + east_hi) / 2.0
    if abs(west_center + east_center) > 1e-6:
        raise ValueError("column grid must stay symmetric around the tower centre")
    return core_w, abs(west_center), (-abs(west_center), abs(west_center))


def corner_columns():
    """Four 2 m columns that replace, rather than overlap, corner wall piers."""
    return [(sx * (W / 2 - CORNER_COL_SIZE / 2),
             sy * (D / 2 - CORNER_COL_SIZE / 2))
            for sx in (-1, 1) for sy in (-1, 1)]


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


def facade_ring(name, z0, height, thickness, mat):
    """Facade wall band terminating cleanly against the four corner columns."""
    zc = z0 + height / 2.0
    t = thickness
    return [
        box(f"{name}_S", (0.0, -(D / 2 - t / 2), zc),
            (W - 2 * CORNER_COL_SIZE, t, height), mat),
        box(f"{name}_N", (0.0, +(D / 2 - t / 2), zc),
            (W - 2 * CORNER_COL_SIZE, t, height), mat),
        box(f"{name}_W", (-(W / 2 - t / 2), 0.0, zc),
            (t, D - 2 * CORNER_COL_SIZE, height), mat),
        box(f"{name}_E", (+(W / 2 - t / 2), 0.0, zc),
            (t, D - 2 * CORNER_COL_SIZE, height), mat),
    ]


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


def lit_window_indices(floor_index, facade_index, window_count):
    """Fixed night-time occupancy: one small cluster plus scattered homes."""
    rng = random.Random(CEILING_LIGHT_SEED + floor_index * 101
                        + facade_index * 10007)
    target = round(window_count * CEILING_LIGHT_ON_RATIO)
    cluster_length = min(3, max(2, target // 2))
    start = rng.randrange(window_count - cluster_length + 1)
    lit = set(range(start, start + cluster_length))
    while len(lit) < target:
        isolated = [i for i in range(window_count) if i not in lit
                    and i - 1 not in lit and i + 1 not in lit]
        choices = isolated or [i for i in range(window_count) if i not in lit]
        lit.add(rng.choice(choices))
    return lit


def ceiling_lights(name, z0, floor_index, mat):
    """Warm ceiling panels in a deterministic mix of lit and unlit homes."""
    zc = z0 + CEILING_LIGHT_Z
    parts = []
    for facade_index, sx in enumerate((-1, 1)):
        for i in lit_window_indices(floor_index, facade_index, WINDOWS_SHORT):
            y = -OPEN_D / 2 + (i + 0.5) * PANE_PITCH
            x = sx * (W / 2 - INTERIOR_SETBACK + CEILING_LIGHT_D / 2)
            parts.append(box(f"{name}_ew_{i}_{sx}", (x, y, zc),
                             (CEILING_LIGHT_D, CEILING_LIGHT_W,
                              CEILING_LIGHT_H), mat))
    for facade_index, sy in enumerate((-1, 1), start=2):
        for i in lit_window_indices(floor_index, facade_index, WINDOWS_LONG):
            x = -OPEN_W / 2 + (i + 0.5) * PANE_PITCH
            y = sy * (D / 2 - INTERIOR_SETBACK + CEILING_LIGHT_D / 2)
            parts.append(box(f"{name}_ns_{i}_{sy}", (x, y, zc),
                             (CEILING_LIGHT_W, CEILING_LIGHT_D,
                              CEILING_LIGHT_H), mat))
    return parts


def corner_piers(name, z0, height, mat):
    """Corner support is provided by the continuous square corner columns."""
    return []


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


def grille(name, z0, height, mat, style=None, cell=None, full_corners=False):
    """Screen across the open refuge level.

    Holds the facade plane where the glazing stops, without closing the level in:
    every cell is a real opening, so the refuge floor still ventilates.

    The GRID pitch is PANE_W, so a cell sits directly over each window pane and
    the vertical lines carry through from the floor below to the floor above. Any
    other pitch makes the garden read as a separate object stuck into the tower.
    """
    parts = []
    style = style or GRILLE_STYLE
    cell = cell or GRILLE_CELL
    off = WALL_T / 2.0

    def divisions(axis_len, pitch):
        """Member centres across an opening, ends included."""
        n = max(1, int(round(axis_len / pitch)))
        step = axis_len / n
        return [-axis_len / 2 + i * step for i in range(n + 1)]

    if style == "FINS":
        # Vertical blades only, over the configured screen height.
        span_w = W if full_corners else OPEN_W
        span_d = D if full_corners else OPEN_D
        zc = z0 + height / 2.0
        for sy in (-1, 1):
            for i, x in enumerate(divisions(span_w, FIN_PITCH)):
                parts.append(box(
                    f"{name}_fin_ns_{i}_{sy}",
                    (x, sy * (D / 2 - off), zc),
                    (FIN_W, FIN_DEPTH, height), mat))
        for sx in (-1, 1):
            for i, y in enumerate(divisions(span_d, FIN_PITCH)):
                parts.append(box(
                    f"{name}_fin_ew_{i}_{sx}",
                    (sx * (W / 2 - off), y, zc),
                    (FIN_DEPTH, FIN_W, height), mat))
        return parts

    # GRID: verticals on the pane pitch, plus horizontals making square cells.
    zc = z0 + height / 2.0
    n_rows = max(1, int(round(height / cell)))
    row_pitch = height / n_rows

    for sy in (-1, 1):
        y = sy * (D / 2 - off)
        for i, x in enumerate(divisions(OPEN_W, cell)):
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
        for i, y in enumerate(divisions(OPEN_D, cell)):
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


def structural_trusses(name, mat):
    """Add refuge-level outrigger, belt, plan-X and perimeter Z trusses.

    The two refuge voids are the natural transfer levels: horizontal outriggers
    tie each core to the north/south perimeter, while the perimeter chords and
    alternating diagonals form a belt truss.  Matching single diagonals now
    continue around both long and short faces, while a second, horizontal
    X-braced diaphragm is embedded in the upper refuge slab.  The same levels
    get X-braces on each core's long wall, keeping the solid core tube as the
    fire-separated shaft while making its lateral role explicit in the model.
    """
    parts = []
    if not REFUGE_Z0S:
        return parts

    y_face = D / 2.0 - TRUSS_FACADE_INSET
    x_face = W / 2.0 - TRUSS_FACADE_INSET
    long_y0, long_y1 = -OPEN_W / 2.0, OPEN_W / 2.0
    short_y0 = -OPEN_D / 2.0 + TRUSS_EDGE_INSET
    short_y1 = OPEN_D / 2.0 - TRUSS_EDGE_INSET
    short_nodes = [
        short_y0,
        short_y0 + (short_y1 - short_y0) / 4.0,
        short_y0 + (short_y1 - short_y0) / 2.0,
        short_y0 + 3.0 * (short_y1 - short_y0) / 4.0,
        short_y1,
    ]
    long_bays = max(1, round(OPEN_W / COL_SPACING))
    long_nodes = [
        long_y0 + (long_y1 - long_y0) * index / long_bays
        for index in range(long_bays + 1)
    ]

    for level, (z0, z1) in enumerate(zip(REFUGE_Z0S, REFUGE_Z1S)):
        zl = z0 + TRUSS_LEVEL_EDGE
        zh = z1 - TRUSS_LEVEL_EDGE
        tag = f"{name}_{level}"

        # Long-face belt chords.  Their endpoints line up with the opening
        # edges, so the corner piers remain clear and the belt reads as a frame.
        for sy in (-1, 1):
            y = sy * y_face
            parts.append(beam_between(f"{tag}_LongLower_{sy}",
                                      (long_y0, y, zl), (long_y1, y, zl),
                                      TRUSS_MEMBER, mat))
            parts.append(beam_between(f"{tag}_LongUpper_{sy}",
                                      (long_y0, y, zh), (long_y1, y, zh),
                                      TRUSS_MEMBER, mat))
            # Keep the light single-diagonal language and continue it across
            # the front and rear elevations, closing the refuge truss ring.
            for bay, (xa, xb) in enumerate(zip(long_nodes, long_nodes[1:])):
                za, zb = ((zl, zh) if bay % 2 == 0 else (zh, zl))
                parts.append(beam_between(f"{tag}_LongZ_{sy}_{bay}",
                                          (xa, y, za), (xb, y, zb),
                                          TRUSS_MEMBER, mat))

        # Short-face belt chords with alternating diagonals.  Each bay is a
        # Z-shaped panel; reversing the slope at the next node gives the
        # intended zig-zag silhouette in the depth-side elevation.
        for sx in (-1, 1):
            x = sx * x_face
            parts.append(beam_between(f"{tag}_ShortLower_{sx}",
                                      (x, short_y0, zl), (x, short_y1, zl),
                                      TRUSS_MEMBER, mat))
            parts.append(beam_between(f"{tag}_ShortUpper_{sx}",
                                      (x, short_y0, zh), (x, short_y1, zh),
                                      TRUSS_MEMBER, mat))
            for bay, (ya, yb) in enumerate(zip(short_nodes, short_nodes[1:])):
                za, zb = ((zl, zh) if bay % 2 == 0 else (zh, zl))
                parts.append(beam_between(f"{tag}_ShortZ_{sx}_{bay}",
                                          (x, ya, za), (x, yb, zb),
                                          TRUSS_MEMBER, mat))

        # Plan X-bracing is hidden in the upper refuge floor slab.  It closes
        # the four diaphragm panels between the cores and the perimeter without
        # adding anything across ordinary residential window bands.
        plan_z = z1 - SLAB_T / 2.0
        x_west = CORE_XS[0] - CORE_W / 2.0 - TRUSS_CORE_FACE_OFFSET
        x_east = CORE_XS[1] + CORE_W / 2.0 + TRUSS_CORE_FACE_OFFSET
        for side, x_core, x_outer in (
                ("West", x_west, -x_face), ("East", x_east, x_face)):
            parts.append(beam_between(f"{tag}_PlanX_{side}_A",
                                      (x_core, short_y0, plan_z),
                                      (x_outer, short_y1, plan_z),
                                      TRUSS_PLAN_MEMBER, mat))
            parts.append(beam_between(f"{tag}_PlanX_{side}_B",
                                      (x_core, short_y1, plan_z),
                                      (x_outer, short_y0, plan_z),
                                      TRUSS_PLAN_MEMBER, mat))
        for side, y_core, y_outer in (
                ("South", -CORE_D / 2.0 - TRUSS_CORE_FACE_OFFSET,
                 -y_face),
                ("North", CORE_D / 2.0 + TRUSS_CORE_FACE_OFFSET,
                 y_face)):
            parts.append(beam_between(f"{tag}_PlanX_{side}_A",
                                      (long_y0, y_core, plan_z),
                                      (long_y1, y_outer, plan_z),
                                      TRUSS_PLAN_MEMBER, mat))
            parts.append(beam_between(f"{tag}_PlanX_{side}_B",
                                      (long_y1, y_core, plan_z),
                                      (long_y0, y_outer, plan_z),
                                      TRUSS_PLAN_MEMBER, mat))

        # Outriggers run from each core's north/south wall to the long-face
        # belt.  Two chords at different heights make the refuge void a real
        # truss depth rather than a single decorative line.
        for core, cx in enumerate(CORE_XS):
            for sy in (-1, 1):
                y_core = sy * (CORE_D / 2.0 + TRUSS_CORE_FACE_OFFSET)
                y_outer = sy * y_face
                for rail, z in (("Lower", zl), ("Upper", zh)):
                    parts.append(beam_between(
                        f"{tag}_Outrigger_{core}_{sy}_{rail}",
                        (cx, y_core, z), (cx, y_outer, z),
                        TRUSS_MEMBER, mat))

            # X-braces on both long faces of the core.  They sit just proud of
            # the wall face but remain within the core's plan plus the member
            # depth, so the shaft geometry itself is unchanged.
            x0 = cx - CORE_W / 2.0 + TRUSS_EDGE_INSET
            x1 = cx + CORE_W / 2.0 - TRUSS_EDGE_INSET
            for sy in (-1, 1):
                y = sy * (CORE_D / 2.0 + TRUSS_CORE_FACE_OFFSET)
                parts.append(beam_between(f"{tag}_CoreX_{core}_{sy}_A",
                                          (x0, y, zl), (x1, y, zh),
                                          TRUSS_MEMBER, mat))
                parts.append(beam_between(f"{tag}_CoreX_{core}_{sy}_B",
                                          (x0, y, zh), (x1, y, zl),
                                          TRUSS_MEMBER, mat))

    return [part for part in parts if part is not None]


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(reset=True, mats=None, add_trusses=False):
    if reset:
        reset_scene()

    if mats is None:
        mats = materials.build_all(engine=RENDER_ENGINE, wall_color=WALL_COLOR,
                                    glass_tint=GLASS_TINT)
    concrete = mats["concrete"]
    spandrel = mats["spandrel"]
    glass = mats["glass"]
    interior = mats["interior"]
    ceiling_light = mats["ceiling_light"]
    metal = mats["metal"]
    dark = mats["dark"]

    walls, glazing, frames, louvres, backs, slabs, structure = [], [], [], [], [], [], []
    trusses = []
    linings = []
    ceiling_lights_mesh = []
    plants, trunks, grilles = [], [], []
    foliage_mat = mats["foliage"]
    trunk_mat = mats["trunk"]

    # --- interior structural column grid --------------------------------
    structure += [box("GroundSlab", (0.0, 0.0, -0.15), (W + 14.0, D + 14.0, 0.30), concrete)]

    x_grid, y_grid = col_grid(W), col_grid(D)
    for i, x in enumerate(x_grid):
        for j, y in enumerate(y_grid):
            # Move only the four former grid-corner columns to the actual
            # building corners below; retain every other original grid column.
            if i in (0, len(x_grid) - 1) and j in (0, len(y_grid) - 1):
                continue
            # Keep the two column lines that define each core's ends. Only a
            # column whose full section is strictly inside a core is omitted;
            # boundary columns remain visible and touch the core walls.
            if any(abs(x - cx) + COL_SIZE / 2 < CORE_W / 2 - CORE_T
                   and abs(y) + COL_SIZE / 2 < CORE_D / 2 - CORE_T
                   for cx in CORE_XS):
                continue
            structure.append(box(
                f"Column_{i}_{j}", (x, y, CORE_TOP_Z / 2.0),
                (COL_SIZE, COL_SIZE, CORE_TOP_Z), concrete))

    for i, (x, y) in enumerate(corner_columns()):
        structure.append(box(
            f"CornerColumn_{i}", (x, y, CORE_TOP_Z / 2.0),
            (CORNER_COL_SIZE, CORNER_COL_SIZE, CORE_TOP_Z), spandrel))

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
    # Windowless floors: the transition floor above the pilotis and the blank
    # band at the top.
    blank_floors = set(range(SOLID_BASE_FLOORS)) | set(
        range(TOWER_FLOORS - SOLID_TOP_FLOORS, TOWER_FLOORS))

    for f in range(TOWER_FLOORS):
        z0 = BASE_Z + f * H
        tag = f"F{f + 1:02d}"

        if f in REFUGE_FLOOR_SET:
            # Refuge / sky garden: no glazing or intermediate slab, so the storeys
            # read as one double-height void. The upper two-metre facade band is
            # added below; corner piers still turn the building line.
            walls += corner_piers(f"{tag}_Pier", z0, H, spandrel)
            if f in REFUGE_START_BY_FLOOR:
                refuge_index = REFUGE_START_BY_FLOOR[f]
                walls += balustrade(f"{tag}_Balustrade", z0, spandrel)
                # Close the upper 2 m so the external opening and grille are both
                # exactly 6 m high, while the refuge void remains 8 m internally.
                walls += facade_ring(f"{tag}_TopBlank", REFUGE_GRILLE_Z1S[refuge_index],
                                     REFUGE_Z1S[refuge_index] - REFUGE_GRILLE_Z1S[refuge_index],
                                     WALL_T, spandrel)
                grilles += grille(f"SkyGarden_Grille_{refuge_index}",
                                  REFUGE_GRILLE_Z0S[refuge_index],
                                  REFUGE_GRILLE_Z1S[refuge_index] - REFUGE_GRILLE_Z0S[refuge_index],
                                  spandrel)
                g_struct, g_plant, g_trunk = sky_garden(
                    f"SkyGarden_{refuge_index}", z0, concrete,
                    foliage_mat, trunk_mat, metal)
                structure += g_struct
                plants += g_plant
                trunks += g_trunk
            if f in REFUGE_END_BY_FLOOR:
                # Slabs are added at the TOP of each floor, so skipping the refuge
                # storeys would leave the void with no ceiling and the floor above
                # with nothing under it.
                slabs.append(box(
                    f"{tag}_Slab", (0.0, 0.0, z0 + H - SLAB_T / 2.0),
                    (W - 2 * WALL_T, D - 2 * WALL_T, SLAB_T), concrete))
            continue

        if f in blank_floors:
            # Blank floor: solid wall the whole storey height, no openings.
            walls += facade_ring(f"{tag}_Blank", z0, H, WALL_T, spandrel)
            if not (SKY_GARDEN and f + 1 in REFUGE_START_BY_FLOOR):
                slabs.append(box(f"{tag}_Slab", (0.0, 0.0, z0 + H - SLAB_T / 2.0),
                                 (W - 2 * WALL_T, D - 2 * WALL_T, SLAB_T), concrete))
            continue

        walls += facade_ring(f"{tag}_SpandrelLo", z0, SPANDREL_LO_H, WALL_T, spandrel)
        walls += facade_ring(f"{tag}_SpandrelHi", z0 + SPANDREL_HI_Z,
                             SPANDREL_HI_H, WALL_T, spandrel)

        # Corner piers close the vent+window+vent zone at all four corners.
        walls += corner_piers(f"{tag}_Pier", z0 + VENT_LO_Z,
                              SPANDREL_HI_Z - VENT_LO_Z, spandrel)

        strip_lo = vent_strip(f"{tag}_VentLo", z0 + VENT_LO_Z, metal, dark)
        strip_hi = vent_strip(f"{tag}_VentHi", z0 + VENT_HI_Z, metal, dark)
        for o in strip_lo + strip_hi:
            (backs if "_back_" in o.name else louvres).append(o)

        glazing += glass_ring(f"{tag}_Glass", z0 + WIN_Z, WIN_H, glass)
        linings += interior_ring(f"{tag}_Interior", z0 + WIN_Z, WIN_H, interior)
        ceiling_lights_mesh += ceiling_lights(f"{tag}_CeilingLight", z0, f,
                                              ceiling_light)
        frames += mullions(f"{tag}_Mullion", z0 + WIN_Z, WIN_H, metal)

        # Floor plate for the level above, visible behind the glazing. Skipped
        # directly under the refuge level, where the thicker garden slab (which
        # shares the same top face) does the job instead.
        if not (SKY_GARDEN and f + 1 in REFUGE_START_BY_FLOOR):
            slabs.append(box(f"{tag}_Slab", (0.0, 0.0, z0 + H - SLAB_T / 2.0),
                             (W - 2 * WALL_T, D - 2 * WALL_T, SLAB_T), concrete))

    # --- roof garden ---------------------------------------------------
    structure.append(box("RoofSlab", (0.0, 0.0, TOP_Z + 0.11),
                         (W, D, 0.22), concrete))
    if ROOF_GARDEN:
        # Reuse the refuge level's slim, dense fins so the two sky gardens read
        # as one consistent facade language, while the roof stays uncovered.
        grilles += grille("RoofGarden_Grille", ROOF_GARDEN_Z0,
                          ROOF_GARDEN_GRILLE_H, spandrel, full_corners=True)
        g_struct, g_plant, g_trunk = sky_garden(
            "RoofGarden", ROOF_GARDEN_Z0, concrete, foliage_mat, trunk_mat, metal)
        structure += g_struct
        plants += g_plant
        trunks += g_trunk
    else:
        structure += ring("Parapet", ROOF_GARDEN_Z0, PARAPET_H, PARAPET_T, spandrel)

    # Lift motor rooms / stair bulkheads: the cores continuing above the roof.
    # Sized and placed by the cores themselves rather than by eye, so they sit
    # over the shafts they serve and move if the cores ever move.
    structure += cores("CoreOverrun", ROOF_GARDEN_Z0, CORE_OVERRUN, concrete)
    for k, cx in enumerate(CORE_XS):
        # Cap slab, then a low upstand around it.
        structure.append(box(
            f"CoreOverrunRoof_{k}",
            (cx, 0.0, ROOF_GARDEN_Z0 + CORE_OVERRUN + 0.11),
            (CORE_W, CORE_D, 0.22), concrete))
    structure += cores("CoreOverrunParapet",
                       ROOF_GARDEN_Z0 + CORE_OVERRUN + 0.22,
                       CORE_ROOF_PARAPET, spandrel)

    # The cores run UNBROKEN from the ground to the overrun above the roof. They
    # were previously built only at the pilotis and refuge levels, which left the
    # tower hollow between them — the lift shafts stopped and started again, and
    # the motor rooms on the roof would have sat on nothing. A shaft has to be
    # continuous to be a shaft.
    #
    # Within the refuge level they stay visible, which is what makes that void
    # read as a level you arrive at rather than a gap. With two of them the garden
    # reads as running BETWEEN two solid piers, which is a better reading than one
    # lump in the middle — the clear span between them remains the view.
    structure += cores("TowerCore", BASE_Z, TOP_Z - BASE_Z, concrete)

    if add_trusses:
        trusses += structural_trusses("RefugeTruss", metal)

    merged = {
        "Facade_Spandrels": join(walls, "Facade_Spandrels"),
        "Windows_Glass": join(glazing, "Windows_Glass"),
        "Interior_Lining": join(linings, "Interior_Lining"),
        "Ceiling_Lights": join(ceiling_lights_mesh, "Ceiling_Lights"),
        "Sky_Garden_Grille": join(grilles, "Sky_Garden_Grille"),
        "Sky_Garden_Planting": join(plants, "Sky_Garden_Planting"),
        "Sky_Garden_Trunks": join(trunks, "Sky_Garden_Trunks"),
        "Window_Mullions": join(frames, "Window_Mullions"),
        "Vent_Louvres": join(louvres, "Vent_Louvres"),
        "Vent_Shadowboxes": join(backs, "Vent_Shadowboxes"),
        "Floor_Plates": join(slabs, "Floor_Plates"),
        "Structure": join(structure, "Structure"),
        "Structural_Trusses": join(trusses, "Structural_Trusses"),
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

    # Frame the whole two-tower site: pull back proportionally to its envelope.
    reach = max(SITE_WIDTH, SITE_DEPTH, SITE_TOP_Z) * 1.35
    target = Vector((SITE_CENTER_X, 0.0, SITE_TOP_Z * 0.52))
    eye = Vector((SITE_CENTER_X + reach * 0.78, -reach * 1.05, SITE_TOP_Z * 0.72))
    cam.location = eye
    cam.rotation_euler = (target - eye).normalized().to_track_quat("-Z", "Y").to_euler()
    bpy.context.collection.objects.link(cam)
    scene.camera = cam


def report(objects, label="tower"):
    total_verts = sum(len(o.data.vertices) for o in objects.values() if o)
    print(f"\n=== high-rise house: {label} ===")
    print(f"tower footprint      : {W:.1f} x {D:.1f} m")
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
        print(f"refuge / sky gardens : {len(REFUGE_STARTS)} levels at storeys "
              f"{', '.join(map(str, REFUGE_STOREYS))}; each {REFUGE_FLOORS * H:.1f} m double height")
        print(f"garden screen        : {REFUGE_GRILLE_H:.1f} m opening + "
              f"{REFUGE_GRILLE_TOP_BLANK_H:.1f} m solid band above")
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
    print(f"residential groups    : {BLOCK_GROUPS} x {BLOCK_FLOORS} glazed floors per tower")
    print(f"pane pitch           : {PANE_PITCH:.2f} m (= pane width; mullions are "
          f"{MULLION_W:.2f} m caps over the joints)")
    print(f"clear internal depth : {D - 2 * WALL_T:.2f} m (inside face to inside face)")
    print(f"service cores        : 2 x {CORE_W:.2f} x {CORE_D:.2f} m at "
          f"x = {CORE_XS[0]:+.2f} / {CORE_XS[1]:+.2f}, "
          f"{2 * CORE_W * CORE_D:.0f} m2 total "
          f"({2 * CORE_W * CORE_D / (W * D) * 100:.1f}% of the plate)")
    print(f"core spacing         : {2 * CORE_OFFSET:.2f} m between centres, "
          f"{2 * (CORE_OFFSET - CORE_W / 2):.2f} m clear between them, "
          f"{W / 2 - (CORE_OFFSET + CORE_W / 2):.2f} m to each building end")
    print(f"core derivation      : {CORE_COLUMN_BAYS} long-face column bays "
          f"plus {COL_SIZE:.2f} m column faces")
    print(f"derivation           : W = {WINDOWS_LONG} x {PANE_W:.0f} + 2 x "
          f"{PIER_LONG:.0f} = {W:.0f} m,  D = {WINDOWS_SHORT} x {PANE_W:.0f} + 2 x "
          f"{PIER_SHORT:.0f} = {D:.0f} m")
    print(f"clear glass per pane : {PANE_W:.2f} m x {WIN_H:.2f} m (fixed module, "
          "same on all facades)")
    print(f"panes per floor total: {2 * (WINDOWS_LONG + WINDOWS_SHORT)} around the building")
    print("per-floor bands      : "
          f"{SPANDREL_LO_H:.2f} solid / {VENT_H:.2f} vent / {WIN_H:.2f} window / "
          f"{VENT_H:.2f} vent / {SPANDREL_HI_H:.2f} solid")
    print(f"window band          : {WIN_Z:.2f}\u2013{WIN_Z + WIN_H:.2f} m above each floor")
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
    diag = math.sqrt(SITE_WIDTH ** 2 + SITE_DEPTH ** 2 + SITE_TOP_Z ** 2)
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
                r3d.view_location = Vector((SITE_CENTER_X, 0.0, SITE_TOP_Z * 0.5))
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


def translate_objects(objects, x_offset):
    """Move one generated tower as a group without changing its local geometry."""
    for obj in objects.values():
        if obj is not None:
            obj.location.x += x_offset


def main():
    global SITE_WIDTH, SITE_CENTER_X, SITE_DEPTH, SITE_TOP_Z

    reset_scene()
    shared_mats = materials.build_all(engine=RENDER_ENGINE, wall_color=WALL_COLOR,
                                      glass_tint=GLASS_TINT)
    configure_tower(2, 18, core_column_bays=2)
    first_objects = build(reset=False, mats=shared_mats)
    first_w, first_d, first_top = W, D, CORE_TOP_Z
    report(first_objects, "existing tower (2 groups x 17 floors, 18 rooms)")

    configure_tower(3, 20, core_column_bays=COMPANION_CORE_COLUMN_BAYS)
    second_objects = build(reset=False, mats=shared_mats, add_trusses=True)
    second_w, second_d, second_top = W, D, CORE_TOP_Z
    second_center_x = first_w / 2.0 + TOWER_GAP + second_w / 2.0
    translate_objects(second_objects, second_center_x)

    SITE_WIDTH = first_w + TOWER_GAP + second_w
    SITE_CENTER_X = (TOWER_GAP + second_w) / 2.0
    SITE_DEPTH = max(first_d, second_d)
    SITE_TOP_Z = max(first_top, second_top)

    report(second_objects, "new adjacent tower (3 groups x 17 floors, 20 rooms)")
    print("=== two-tower site ===")
    print(f"clear gap            : {TOWER_GAP:.1f} m")
    print(f"overall envelope     : {SITE_WIDTH:.1f} x {SITE_DEPTH:.1f} m")
    print(f"site centre          : x = {SITE_CENTER_X:.1f} m")
    print(f"highest core top     : {SITE_TOP_Z:.2f} m")
    print("=====================\n")
    setup_render()
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
