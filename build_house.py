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
* Bottom 7 floors are a continuous podium base: two open pilotis floors, three
  glazed floors, and two open upper floors, with the tower cores continuing through it.
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
from mathutils.geometry import tessellate_polygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import materials     # noqa: E402  (needs the path set up first)

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

H = 4.0           # floor-to-floor height
# Footprint W (X) and D (Y) are DERIVED from the window module further down:
# the pane size is fixed, so the building widens to fit a whole number of panes.

# Look. EEVEE keeps the default interactive; its alpha-blended glazing shows the
# room fixtures without ray-traced refraction. Switch to CYCLES only for a slow,
# physically refracted final render.
RENDER_ENGINE = "BLENDER_EEVEE"
WALL_COLOR = materials.WARM_STONE     # or materials.COOL_STONE for pale grey
GLASS_TINT = materials.GLASS_CLEAR
CYCLES_SAMPLES = 128

PILOTIS_FLOORS = 7     # of which these are open and raised
BLOCK_GROUPS = 2       # residential groups in the first/current tower
BLOCK_FLOORS = 17      # glazed residential floors in each group
REFUGE_FLOORS = 2      # fixed double-height refuge / sky-garden floors
FIXED_SOLID_BAND_FLOORS = 4  # 2 blank floors at the base + 2 at the top
TOTAL_FLOORS = (PILOTIS_FLOORS + BLOCK_GROUPS * BLOCK_FLOORS
                + (BLOCK_GROUPS - 1) * REFUGE_FLOORS
                + FIXED_SOLID_BAND_FLOORS)
TOWER_FLOORS = TOTAL_FLOORS - PILOTIS_FLOORS   # occupied floors above

TOWER_GAP = 30.0       # target clear distance inside the open-book arrangement
# The two towers form an open book in plan. Their inner short ends face the
# central gap; the two outward page directions subtend 150 degrees.
BOOK_OPEN_ANGLE = 150.0
# The end clearance is measured along each page before the oblique corners are
# accounted for. At 150 degrees it produces a little over 30 m of true corner-
# to-corner clearance between the two rectangular envelopes.
BOOK_EDGE_CLEARANCE = 42.0
BOOK_FIRST_OUTWARD_DEG = 180.0

# Two fully open pilotis floors support three occupied podium floors.  Every
# occupied floor is one continuous plate: its two lateral connection edges are
# cubic Bezier curves, not overlapping capsule outlines.
PODIUM_TOTAL_FLOORS = 5
PODIUM_PILOTIS_FLOORS = 2
PODIUM_OCCUPIED_FLOORS = PODIUM_TOTAL_FLOORS - PODIUM_PILOTIS_FLOORS
PODIUM_PILOTIS_H = H
PODIUM_H = 6.0
PODIUM_PILOTIS_CEILING_Z = PODIUM_PILOTIS_FLOORS * PODIUM_PILOTIS_H
PODIUM_TOP_Z = (PODIUM_PILOTIS_CEILING_Z
                + PODIUM_OCCUPIED_FLOORS * PODIUM_H)
PODIUM_TO_TOWER_BASE = PILOTIS_FLOORS * H - PODIUM_TOTAL_FLOORS * H
PODIUM_DEPTH = 66.0
PODIUM_BOTTOM_DEPTH = 80.0
PODIUM_LENGTH_MARGIN = 20.0
PODIUM_BOTTOM_LENGTH_MARGIN = 12.0
PODIUM_CORRIDOR_DEPTH = 3.0
# The occupied podium levels carry a deep perimeter balcony.  Keep the
# undercroft/canopy offset above unchanged; only these gallery decks double.
PODIUM_BALCONY_DEPTH = 6.0
PODIUM_GRID_PITCH = 3.00
PODIUM_CORRIDOR_RAIL_H = 1.20
PODIUM_PILOTIS_COLUMN_SIZE = 1.20
PODIUM_PILOTIS_COLUMN_PITCH = 12.0
# A generous diamond lattice sits on the OUTSIDE of the curtain wall.  The
# visible glass height is divided into exactly two diamond cells per storey,
# so the pattern reads as an elegant large-scale facade rather than a fine mesh.
PODIUM_DIAMOND_ROWS = 3
PODIUM_DIAMOND_MEMBER = 0.32
PODIUM_DIAMOND_STANDOFF = 0.08
# The public podium ceilings use many small exposed globes.  Three-metre pitch
# is dense enough to read as a galaxy from outside without becoming a luminous
# ceiling panel; every fixture is on, with a sparse warm-white accent.
PODIUM_CEILING_LIGHT_PITCH = 3.00
PODIUM_CEILING_LIGHT_RADIUS = 0.14
PODIUM_CEILING_LIGHT_EDGE_CLEARANCE = 1.20
# Use the full upper and lower edges of each inward round end as the two link
# faces.  One cubic connects the two upper edges and one connects the two lower
# edges, leaving a broad, continuously filled floor plate between them.
PODIUM_BEZIER_ATTACH_ANGLE = math.pi / 2.0

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
# The room window is the fixed module: exactly PANE_W x WIN_H of clear glass.
# EVERYTHING outside is derived from the room-window counts — never the other way round.
PANE_W = 4.00
WINDOWS_LONG = 18      # room windows across each long facade  (X)
WINDOWS_SHORT = 9       # room windows across each short facade (Y)
WINDOW_GAP = 0.03       # real vertical joint between adjacent room windows
PANE_GLASS_W = PANE_W - WINDOW_GAP
# The two end panes lose only the inward half-gap: their outside edges align
# with the opening and the full-width ventilation band.
END_PANE_GLASS_W = PANE_W - WINDOW_GAP / 2.0

# The mullion is a cover cap centred on each pane joint: it sits on the glass
# line and overlaps the two panes it joins, so it costs NO facade length.
# That keeps the arithmetic clean — an opening is exactly N x PANE_W, so the
# footprint comes out on whole metres:
#   W = 18 x 4.00 + 2 x 2.00 = 76.00 m
#   D =  9 x 4.00 + 2 x 2.00 = 40.00 m
MULLION_W = 0.09
MULLION_INSET = 0.0      # flush with the facade/glass plane to cover the joints

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
# D is derived from the short-face pane count. The current nine-pane depth gives
# 40 m overall. The cores are thickened to 11 m, leaving 14.5 m of clear unit
# depth on either side.
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
# screen, not structure — so the outer perimeter columns and the two cores remain
# the gravity load path through the refuge levels. Interior apartment columns are
# deliberately not used: the open residential plate is part of the architectural
# brief, and the cores remain continuous through the tower.
#
# The outer ring keeps the residential plate open; the facade fins remain a
# separate pane-aligned screen rather than additional structural columns.
REFUGE_COL_SIZE = 1.20
REFUGE_COL_PITCH = PANE_W         # 4.0 m — a whole number of room windows
GARDEN_SLAB_T = 0.45       # deeper than a normal plate: it carries soil
PLANTER_H = 0.85
PLANTER_W = 2.4
# Enclosed refuge trees stay safely below their 8 m void. Trees on the open
# tower and podium roofs use a broad, foliage-led 8 m waterdrop profile: green
# begins low and keeps tapering toward one high tip rather than forming a spindle.
TREE_TRUNK_H = 2.35
TREE_CANOPY_RADIUS = 1.65
TREE_CANOPY_H = 3.15
TREE_CROWN_OVERLAP = 0.28
TALL_TREE_TOTAL_H = 8.0
TALL_TREE_CANOPY_H = 6.40
TALL_TREE_CANOPY_RADIUS = 2.20
TALL_TREE_TRUNK_H = TALL_TREE_TOTAL_H - TALL_TREE_CANOPY_H + TREE_CROWN_OVERLAP
# The open podium roof is a real sky garden: individual planted islands leave
# generous walking room instead of reading as continuous, crowded hedge rows.
PODIUM_GARDEN_ISLAND_RADIUS = 4.0
PODIUM_GARDEN_SOIL_RADIUS = 3.50
PODIUM_GARDEN_ISLANDS_PER_SIDE = 5
PODIUM_GARDEN_ISLAND_Y = 25.0
TALL_ROOF_TREES_PER_FACE = 11

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

COL_SIZE = 1.60       # outer-perimeter column footprint (sized for the tower load)
CORNER_COL_SIZE = 2.00  # exactly fills each retained 2 m corner facade margin
COL_SPACING = 9.0     # target column grid spacing
COL_CLEAR_INSET = 2.0 # clear distance from facade plane to outer column face
COL_MARGIN = COL_CLEAR_INSET + COL_SIZE / 2.0
# The last open storey above the podium is recast as a facade-aligned arcade.
# Its piers bridge the original inset column line to the exterior plane, while
# each half-round arch spans precisely between the inner faces of its piers.
PILOTIS_ARCADE_PIER_DEPTH = COL_CLEAR_INSET + COL_SIZE
PILOTIS_ARCADE_SEGMENTS = 16
# Small recessed fixtures in the arcade soffits. They are deliberately kept
# separate from the arcade mesh so the fixtures can be replaced locally without
# touching the arches themselves. These are emissive mesh globes only, matching
# the existing podium ceiling lights; no extra Blender light objects are added.
PILOTIS_ARCADE_LIGHT_RADIUS = 0.18

# --- service cores ----------------------------------------------------------
# TWO cores rather than one central slab, and the reason is capacity and egress,
# not structure. The lateral system here is the perimeter: the four L-shaped
# corner piers give Iy = 1460 m4 against the core's 177, so a core carries only
# 11% of the lateral stiffness and tip drift is H/1738 against a H/500 limit.
# Nothing about the core choice buys stiffness this building needs.
#
# What a single 14 x 11 core could NOT do was hold the vertical transport. 37
# floors x 76 x 40 m is 112480 m2 GFA, about 818 units and 2209 people, needing
# 7-9 lifts. Shafts, two stairs, lobbies, smoke-stop lobbies and risers come to
# roughly 172 m2 gross; 14 x 11 = 154 m2, short by 24%. That is a 5.1%
# core-to-plate ratio where residential towers run 10-15%.
# CORE_PROVISION below stays at the 203.5 m2 figure derived from the wider 76 m
# plate, deliberately: it is the stricter of the two and the measured 422 m2
# clears it anyway, so keeping it means the cores cannot shrink on the strength
# of a smaller unit count.
#
# Splitting also fixes two things one core cannot:
#   * Egress. Worst-case travel to a central core was 42.5 m, marginal against
#     SCDF's ~30 m dead-end / ~45 m two-way. Twin cores bring it to 20 m.
#   * Stair remoteness. Two stairs in ONE shaft are not independent — a single
#     incident compromises both. The two core centres stay well separated.
#   * Lift zoning, which an 818-unit tower wants anyway: low zone in the west
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
CORE_W, CORE_D = 20.0, 11.0   # derived long length / thickened apartment-depth width
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

BASE_Z = PODIUM_TOP_Z + PODIUM_TO_TOWER_BASE  # underside of the tower
TOP_Z = BASE_Z + TOWER_FLOORS * H    # roof level
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
# use the same pale exterior finish so the structure reads as part of the facade
# rather than a dark metal overlay.
TRUSS_MEMBER = 0.38
TRUSS_FACADE_INSET = 0.55
TRUSS_CORE_FACE_OFFSET = 0.20
TRUSS_LEVEL_EDGE = 0.75
TRUSS_EDGE_INSET = 0.65
TRUSS_PLAN_MEMBER = 0.20       # hidden inside the refuge-level upper slab
TRUSS_CLAW_GROUPS = 3           # three two-triangle groups on each short facade
TRUSS_TRIANGLES_PER_CLAW = 2
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
        raise ValueError("core length must leave room for the structural module")

    BASE_Z = PODIUM_TOP_Z + PODIUM_TO_TOWER_BASE
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
SITE_CENTER_X = 0.0
SITE_CENTER_Y = 0.0
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

# House ceiling lighting is seven independent rectangular rings of square
# panels: one outside the perimeter-column line, one centred on that structural
# line, and five on the room side of it. The panels stay installed when switched
# off; each fixture keeps a deterministic random lit/warm/off state.
CEILING_LIGHT_W = 1.20
CEILING_LIGHT_D = 1.20
CEILING_LIGHT_INTERIOR_RING_COUNT = 5
CEILING_LIGHT_RING_COUNT = CEILING_LIGHT_INTERIOR_RING_COUNT + 2
# Setbacks are measured inward from the glass plane. The outer target is kept
# outside the column line; the five inner rings span the complete clear zone
# between the perimeter columns and the service cores.
CEILING_LIGHT_OUTER_TARGET = 0.45
CEILING_LIGHT_COLUMN_CLEAR = 0.20
CEILING_LIGHT_CORE_CLEAR = 0.20
# The two inner rings use one corner panel per corner. Remove the two nearest
# bay-axis panels at each end of every side so those corner panels have clear
# space and no two 1.20 m fixtures overlap.
CEILING_LIGHT_CORNER_AXIS_COUNT = 2
CEILING_LIGHT_H = 0.06
CEILING_LIGHT_Z = H - SLAB_T - CEILING_LIGHT_H / 2.0
# Every fixture independently has this chance of being lit. Keep the seeded
# pattern stable between rebuilds, while letting rooms have zero, one, or two
# lights on like a real inhabited building.
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


def spheres_mesh(name, centers, radius, mat, segments=10, latitudes=5):
    """Create many low-poly, genuinely round light globes in one mesh."""
    if not centers:
        return None
    vertices, faces = [], []
    for center in centers:
        base = len(vertices)
        x, y, z = center
        vertices.append((x, y, z + radius))
        for latitude in range(1, latitudes):
            theta = math.pi * latitude / latitudes
            ring_z = z + radius * math.cos(theta)
            ring_r = radius * math.sin(theta)
            for segment in range(segments):
                phi = 2.0 * math.pi * segment / segments
                vertices.append((x + ring_r * math.cos(phi),
                                 y + ring_r * math.sin(phi), ring_z))
        bottom = len(vertices)
        vertices.append((x, y, z - radius))
        first_ring = base + 1
        last_ring = first_ring + (latitudes - 2) * segments
        for segment in range(segments):
            nxt = (segment + 1) % segments
            faces.append((base, first_ring + nxt, first_ring + segment))
            faces.append((bottom, last_ring + segment, last_ring + nxt))
        for latitude in range(latitudes - 2):
            lower = first_ring + latitude * segments
            upper = lower + segments
            for segment in range(segments):
                nxt = (segment + 1) % segments
                faces.append((lower + segment, lower + nxt,
                              upper + nxt, upper + segment))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.validate()
    obj = bpy.data.objects.new(name, mesh)
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


def tapered_cylinder(name, center, radius_bottom, radius_top, height, mat,
                     vertices=12):
    """Create one smooth tapered round element, such as a tree trunk."""
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices, radius1=radius_bottom, radius2=radius_top,
        depth=height, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    obj.data.materials.append(mat)
    return obj


def waterdrop_canopy(name, center, radius, height, mat, segments=16):
    """Create a broad-bottomed, continuously tapering waterdrop tree crown."""
    # The lower crown is already wide, like a dense painted tree mass. From its
    # broadest point it only narrows towards the tip, so it cannot read as the
    # old symmetric spindle.
    profile = (
        (0.72, -0.50), (0.93, -0.43), (1.00, -0.29), (0.96, -0.12),
        (0.84, 0.06), (0.66, 0.23), (0.43, 0.38), (0.18, 0.47),
    )
    verts = [(0.0, 0.0, -height / 2.0)]
    ring_starts = []
    for radius_factor, z_factor in profile:
        ring_starts.append(len(verts))
        for segment in range(segments):
            angle = 2.0 * math.pi * segment / segments
            verts.append((radius * radius_factor * math.cos(angle),
                          radius * radius_factor * math.sin(angle),
                          height * z_factor))
    top_index = len(verts)
    verts.append((0.0, 0.0, height / 2.0))

    faces = []
    for segment in range(segments):
        next_segment = (segment + 1) % segments
        faces.append((0, ring_starts[0] + next_segment,
                      ring_starts[0] + segment))
    for ring_start, next_start in zip(ring_starts, ring_starts[1:]):
        for segment in range(segments):
            next_segment = (segment + 1) % segments
            faces.append((ring_start + segment, ring_start + next_segment,
                          next_start + next_segment, next_start + segment))
    for segment in range(segments):
        next_segment = (segment + 1) % segments
        faces.append((ring_starts[-1] + segment,
                      ring_starts[-1] + next_segment, top_index))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = center
    obj.data.materials.append(mat)
    bpy.context.collection.objects.link(obj)
    return obj


def planted_tree(name, center, soil_z, foliage_mat, trunk_mat, scale=1.0,
                 tall=False):
    """Build one reusable curved tree: tapered trunk below a waterdrop crown."""
    x, y = center
    trunk_h = (TALL_TREE_TRUNK_H if tall else TREE_TRUNK_H) * scale
    canopy_h = (TALL_TREE_CANOPY_H if tall else TREE_CANOPY_H) * scale
    canopy_radius = (TALL_TREE_CANOPY_RADIUS if tall else TREE_CANOPY_RADIUS) * scale
    trunk = tapered_cylinder(
        f"{name}_Trunk", (x, y, soil_z + trunk_h / 2.0),
        0.20 * scale, 0.12 * scale, trunk_h, trunk_mat)
    canopy = waterdrop_canopy(
        f"{name}_WaterdropCanopy",
        (x, y, soil_z + trunk_h + canopy_h / 2.0 - TREE_CROWN_OVERLAP * scale),
        canopy_radius, canopy_h, foliage_mat)
    return canopy, trunk


def podium_point(spec, local_x, local_y):
    """Transform a local point on one podium lobe into the overall plan."""
    centre, _, _, rotation = spec
    angle = math.radians(rotation)
    axis = Vector((math.cos(angle), math.sin(angle)))
    normal = Vector((-axis.y, axis.x))
    return Vector(centre) + axis * local_x + normal * local_y


def podium_roof_garden(podium_specs, deck_z, mats):
    """Turn the highest podium deck into a spacious planted sky garden."""
    planters, foliage, trunks = [], [], []
    concrete, foliage_mat, trunk_mat = (mats["concrete"], mats["foliage"],
                                        mats["trunk"])
    for lobe_index, spec in enumerate(podium_specs):
        # Place five separate green islands along each outer side of a wing.
        # The two bands sit beyond the 40 m tower depth, leaving the centre of
        # the roof clear and distributing trees across the whole sky garden.
        _, lobe_width, _, _ = spec
        island_margin = PODIUM_GARDEN_ISLAND_RADIUS + 6.0
        island_span = lobe_width - 2.0 * island_margin
        island_xs = [(-island_span / 2.0
                      + index * island_span
                      / (PODIUM_GARDEN_ISLANDS_PER_SIDE - 1))
                     for index in range(PODIUM_GARDEN_ISLANDS_PER_SIDE)]
        for side in (-1, 1):
            local_y = side * PODIUM_GARDEN_ISLAND_Y
            for island_index, local_x in enumerate(island_xs):
                position = podium_point(spec, local_x, local_y)
                island_name = f"PodiumRoof_Lobe{lobe_index}_Island_{side}_{island_index}"
                planter = tapered_cylinder(
                    f"{island_name}_Planter",
                    (position.x, position.y, deck_z + PLANTER_H / 2.0),
                    PODIUM_GARDEN_ISLAND_RADIUS, PODIUM_GARDEN_ISLAND_RADIUS,
                    PLANTER_H, concrete, vertices=32)
                planting = tapered_cylinder(
                    f"{island_name}_Lawn",
                    (position.x, position.y, deck_z + PLANTER_H + 0.10),
                    PODIUM_GARDEN_SOIL_RADIUS, PODIUM_GARDEN_SOIL_RADIUS,
                    0.20, foliage_mat, vertices=32)
                canopy, trunk = planted_tree(
                    f"{island_name}_Tree", position,
                    deck_z + PLANTER_H + 0.20, foliage_mat, trunk_mat,
                    tall=True)
                planters.append(planter)
                foliage.extend((planting, canopy))
                trunks.append(trunk)
    return planters, foliage, trunks


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

    Each core occupies ``core_column_bays`` long-face module bays. Its outer
    boundary remains one grid line in from each end, and its inner boundary
    moves inward as bays are added. The module grid determines the core size;
    the structural columns themselves are kept only at the outer perimeter.
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

    Interior 4 m room modules get slightly narrower panes, leaving real joints
    between homes. The first and last pane on every facade reach the opening
    edges, aligned with the full-width ventilation band.
    """
    zc = z0 + height / 2.0
    off = GLASS_INSET + GLASS_T / 2.0
    parts = []
    for i in range(WINDOWS_SHORT):
        pane_w = (END_PANE_GLASS_W
                  if i in (0, WINDOWS_SHORT - 1) else PANE_GLASS_W)
        if i == 0:
            y = -OPEN_D / 2 + pane_w / 2.0
        elif i == WINDOWS_SHORT - 1:
            y = OPEN_D / 2 - pane_w / 2.0
        else:
            y = -OPEN_D / 2 + (i + 0.5) * PANE_PITCH
        for sx in (-1, 1):
            parts.append(box(f"{name}_ew_{i}_{sx}",
                             (sx * (W / 2 - off), y, zc),
                             (GLASS_T, pane_w, height), mat))
    for i in range(WINDOWS_LONG):
        pane_w = (END_PANE_GLASS_W
                  if i in (0, WINDOWS_LONG - 1) else PANE_GLASS_W)
        if i == 0:
            x = -OPEN_W / 2 + pane_w / 2.0
        elif i == WINDOWS_LONG - 1:
            x = OPEN_W / 2 - pane_w / 2.0
        else:
            x = -OPEN_W / 2 + (i + 0.5) * PANE_PITCH
        for sy in (-1, 1):
            parts.append(box(f"{name}_ns_{i}_{sy}",
                             (x, sy * (D / 2 - off), zc),
                             (pane_w, GLASS_T, height), mat))
    return parts


def ceiling_light_rng(floor_index, facade_index, room_index, fixture_index):
    """Stable random stream for one installed room fixture."""
    return random.Random(CEILING_LIGHT_SEED + floor_index * 101
                         + facade_index * 10007 + room_index * 1000003
                         + fixture_index * 100000007)


def ceiling_light_ring_setbacks():
    """Return the exterior plus evenly spaced interior fixture-ring setbacks."""
    # For a side at half-span ``edge``, the outer ring must stay between the
    # facade and the outer face of the perimeter columns. The inner rings must
    # start beyond the column's inner face and end before the nearest core face.
    def outer_limit(span):
        column = col_grid(span)[-1]
        return (span / 2 - GLASS_T - CEILING_LIGHT_D - column
                - COL_SIZE / 2 - CEILING_LIGHT_COLUMN_CLEAR)

    def column_inner_limit(span):
        column = col_grid(span)[-1]
        return (span / 2 - GLASS_T - column + COL_SIZE / 2
                + CEILING_LIGHT_COLUMN_CLEAR)

    outer = min(CEILING_LIGHT_OUTER_TARGET,
                outer_limit(W), outer_limit(D))
    inner_start = max(column_inner_limit(W), column_inner_limit(D))
    inner_end = min(
        D / 2 - GLASS_T - CEILING_LIGHT_D - CORE_D / 2
        - CEILING_LIGHT_CORE_CLEAR,
        W / 2 - GLASS_T - CEILING_LIGHT_D
        - max(abs(cx) + CORE_W / 2 for cx in CORE_XS)
        - CEILING_LIGHT_CORE_CLEAR,
    )
    interior_span = inner_end - inner_start
    required_span = ((CEILING_LIGHT_INTERIOR_RING_COUNT - 1)
                     * CEILING_LIGHT_D)
    if outer <= 0.0 or interior_span < required_span:
        raise ValueError("ceiling-light rings do not fit between structure")
    # Use the full clear interval for the interior rings.  The previous
    # ``count + 1`` interpolation packed five 1.20 m fixtures into 5.80 m
    # with only 0.97 m between centres, so neighbouring rings overlapped.
    # Putting the first and last rings on the two structural limits gives the
    # available space back to the layout (1.45 m centre-to-centre here).
    return (outer,) + tuple(
        inner_start + interior_span * ring_index
        / (CEILING_LIGHT_INTERIOR_RING_COUNT - 1)
        for ring_index in range(CEILING_LIGHT_INTERIOR_RING_COUNT))


def ceiling_light_axis_positions(span):
    """Return two evenly spaced fixture axes inside every structural bay."""
    grid = col_grid(span)
    return [lo + (hi - lo) / 3.0 for lo, hi in zip(grid, grid[1:])] + [
        lo + 2.0 * (hi - lo) / 3.0 for lo, hi in zip(grid, grid[1:])]


def ceiling_light_overlaps_column(center, dims):
    """Return whether a ceiling panel intersects any perimeter support."""
    x, y = center[:2]
    half_w, half_d = dims[0] / 2.0, dims[1] / 2.0
    x_grid, y_grid = col_grid(W), col_grid(D)
    for i, column_x in enumerate(x_grid):
        for j, column_y in enumerate(y_grid):
            if i not in (0, len(x_grid) - 1) and j not in (0, len(y_grid) - 1):
                continue
            is_corner = i in (0, len(x_grid) - 1) and j in (0, len(y_grid) - 1)
            column_size = CORNER_COL_SIZE if is_corner else COL_SIZE
            half_column = column_size / 2.0
            if (abs(x - column_x) < half_w + half_column
                    and abs(y - column_y) < half_d + half_column):
                return True
    return False


def add_ceiling_light(parts, name, center, dims, floor_index, facade_index,
                      room_index, ring_index, mats):
    """Install one panel unless a load-bearing perimeter column occupies it."""
    if ceiling_light_overlaps_column(center, dims):
        return
    parts.append(box(
        name, center, dims,
        mats[ceiling_light_state(floor_index, facade_index, room_index,
                                 ring_index)]))


def ceiling_light_state(floor_index, facade_index, room_index, fixture_index):
    """Return the independent on/off state and colour temperature of a panel."""
    rng = ceiling_light_rng(floor_index, facade_index, room_index,
                            fixture_index)
    if rng.random() >= CEILING_LIGHT_ON_RATIO:
        return "off"
    return rng.choice(("daylight", "warm"))


def ceiling_lights(name, z0, floor_index, mats):
    """Seven panel-light rings, including one that follows the column line."""
    zc = z0 + CEILING_LIGHT_Z
    parts = []
    ring_setbacks = ceiling_light_ring_setbacks()
    for facade_index, sx in enumerate((-1, 1)):
        for ring_index, setback in enumerate(ring_setbacks):
            x = sx * (W / 2 - GLASS_T - setback - CEILING_LIGHT_D / 2)
            axes = ceiling_light_axis_positions(D)
            if ring_index:
                # Leave the two bay-axis positions nearest each corner to the
                # single corner lamp. This keeps the 1.20 m panels separate.
                axes = sorted(axes)[CEILING_LIGHT_CORNER_AXIS_COUNT:
                                   -CEILING_LIGHT_CORNER_AXIS_COUNT]
            for axis_index, y in enumerate(axes):
                add_ceiling_light(
                    parts, f"{name}_ew_{ring_index}_{sx}_{axis_index}",
                    (x, y, zc),
                    (CEILING_LIGHT_D, CEILING_LIGHT_W, CEILING_LIGHT_H),
                    floor_index, facade_index, axis_index, ring_index, mats)
    for facade_index, sy in enumerate((-1, 1), start=2):
        for ring_index, setback in enumerate(ring_setbacks):
            y = sy * (D / 2 - GLASS_T - setback - CEILING_LIGHT_D / 2)
            axes = ceiling_light_axis_positions(W)
            if ring_index:
                axes = sorted(axes)[CEILING_LIGHT_CORNER_AXIS_COUNT:
                                   -CEILING_LIGHT_CORNER_AXIS_COUNT]
            for axis_index, x in enumerate(axes):
                add_ceiling_light(
                    parts, f"{name}_ns_{ring_index}_{sy}_{axis_index}",
                    (x, y, zc),
                    (CEILING_LIGHT_W, CEILING_LIGHT_D, CEILING_LIGHT_H),
                    floor_index, facade_index, axis_index, ring_index, mats)
    # Inner rings continue around the four corners with one panel per corner.
    # The outer ring has no corner panel because the larger corner column occupies
    # that position on the facade side.
    for ring_index, setback in enumerate(ring_setbacks[1:], start=1):
        inset = W / 2 - GLASS_T - setback - CEILING_LIGHT_D / 2
        corner_depth = D / 2 - GLASS_T - setback - CEILING_LIGHT_D / 2
        for corner_index, (sx, sy) in enumerate(
                ((-1, -1), (-1, 1), (1, -1), (1, 1))):
            add_ceiling_light(
                parts, f"{name}_corner_{ring_index}_{corner_index}",
                (sx * inset, sy * corner_depth, zc),
                (CEILING_LIGHT_W, CEILING_LIGHT_D, CEILING_LIGHT_H),
                floor_index, 4, corner_index, ring_index, mats)

    # The new ring follows the perimeter support line. Panels sit in the clear
    # portion of every structural bay; the overlap test above makes the rule
    # explicit, so a fixture is never generated where a column occupies it.
    column_ring_index = CEILING_LIGHT_RING_COUNT - 1
    for facade_index, sx in enumerate((-1, 1)):
        x = sx * col_grid(W)[-1]
        for axis_index, y in enumerate(ceiling_light_axis_positions(D)):
            add_ceiling_light(
                parts, f"{name}_ew_column_{sx}_{axis_index}", (x, y, zc),
                (CEILING_LIGHT_D, CEILING_LIGHT_W, CEILING_LIGHT_H),
                floor_index, facade_index, axis_index, column_ring_index, mats)
    for facade_index, sy in enumerate((-1, 1), start=2):
        y = sy * col_grid(D)[-1]
        for axis_index, x in enumerate(ceiling_light_axis_positions(W)):
            add_ceiling_light(
                parts, f"{name}_ns_column_{sy}_{axis_index}", (x, y, zc),
                (CEILING_LIGHT_W, CEILING_LIGHT_D, CEILING_LIGHT_H),
                floor_index, facade_index, axis_index, column_ring_index, mats)
    return parts


def corner_piers(name, z0, height, mat):
    """Corner support is provided by the continuous square corner columns."""
    return []


def mullions(name, z0, height, mat):
    """Slim vertical frames breaking up the ribbon window.

    The cap is flush with the facade/glass plane, so it closes the real joint
    between adjacent panes without changing the window opening or facade
    dimensions.
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


def sky_garden(name, z0, slab_mat, plant_mat, trunk_mat, metal_mat,
               tall_trees=False):
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

    # Trees along the long faces use the shared curved waterdrop silhouette.
    n_trees = TALL_ROOF_TREES_PER_FACE if tall_trees else 7
    span = OPEN_W - 8.0
    for i in range(n_trees):
        x = -span / 2 + i * span / (n_trees - 1)
        for sy in (-1, 1):
            y = sy * (D / 2 - inset - PLANTER_W / 2)
            canopy, trunk = planted_tree(
                f"{name}_Tree_{i}_{sy}", (x, y), z0 + PLANTER_H,
                plant_mat, trunk_mat, scale=1.0 if tall_trees else 0.82,
                tall=tall_trees)
            parts_plant.append(canopy)
            parts_trunk.append(trunk)

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
    short_claw_groups = TRUSS_CLAW_GROUPS
    short_perimeter_bays = short_claw_groups * TRUSS_TRIANGLES_PER_CLAW
    # Keep the same claw silhouette on the wider elevations without letting a
    # single diagonal grow into a visually implausible 12 m span. The long-face
    # group count follows the long/short opening ratio, rounded to whole claws.
    long_claw_groups = max(short_claw_groups,
                           round(OPEN_W / OPEN_D * short_claw_groups))
    long_perimeter_bays = long_claw_groups * TRUSS_TRIANGLES_PER_CLAW
    short_nodes = [
        short_y0 + (short_y1 - short_y0) * index / short_perimeter_bays
        for index in range(short_perimeter_bays + 1)
    ]
    long_nodes = [
        long_y0 + (long_y1 - long_y0) * index / long_perimeter_bays
        for index in range(long_perimeter_bays + 1)
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
            # One upright separates every pair of triangles, giving the
            # requested three-claw / chicken-foot silhouette.
            for claw in range(1, long_claw_groups):
                node = claw * TRUSS_TRIANGLES_PER_CLAW
                x = long_nodes[node]
                parts.append(beam_between(f"{tag}_LongUpright_{sy}_{claw}",
                                          (x, y, zl), (x, y, zh),
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
            for claw in range(1, short_claw_groups):
                node = claw * TRUSS_TRIANGLES_PER_CLAW
                y = short_nodes[node]
                parts.append(beam_between(f"{tag}_ShortUpright_{sx}_{claw}",
                                          (x, y, zl), (x, y, zh),
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


def semicircular_arch(name, start, end, outward, spring_z, top_z, mat):
    """Fill the solid spandrel above one half-round arcade opening."""
    axis = (end - start).normalized()
    centre = (start + end) / 2.0
    outer_radius = (end - start).length / 2.0
    front_offset = outward * (PILOTIS_ARCADE_PIER_DEPTH / 2.0)
    back_offset = -front_offset
    vertices = []
    for index in range(PILOTIS_ARCADE_SEGMENTS + 1):
        theta = math.pi * index / PILOTIS_ARCADE_SEGMENTS
        direction = axis * math.cos(theta)
        outer = centre + direction * outer_radius
        vertices.extend((
            (outer.x + front_offset.x, outer.y + front_offset.y,
             top_z),
            (outer.x + back_offset.x, outer.y + back_offset.y,
             top_z),
            (outer.x + front_offset.x, outer.y + front_offset.y,
             spring_z + outer_radius * math.sin(theta)),
            (outer.x + back_offset.x, outer.y + back_offset.y,
             spring_z + outer_radius * math.sin(theta)),
        ))
    faces = []
    for index in range(PILOTIS_ARCADE_SEGMENTS):
        base, nxt = 4 * index, 4 * (index + 1)
        faces.extend((
            (base, nxt, nxt + 2, base + 2),
            (base + 1, base + 3, nxt + 3, nxt + 1),
            (base, base + 1, nxt + 1, nxt),
            (base + 2, nxt + 2, nxt + 3, base + 3),
        ))
    faces.extend(((0, 2, 3, 1),
                  (4 * PILOTIS_ARCADE_SEGMENTS,
                   4 * PILOTIS_ARCADE_SEGMENTS + 3,
                   4 * PILOTIS_ARCADE_SEGMENTS + 2,
                   4 * PILOTIS_ARCADE_SEGMENTS + 1)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.validate()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    bpy.context.collection.objects.link(obj)
    return obj


def pilotis_arcades(mat):
    """Wrap the open storey over the podium in triumphal-arch-like arcades."""
    parts = []
    arcade_z0 = PODIUM_TOP_Z
    arcade_z1 = BASE_Z + H

    def side(name, positions, face_coordinate, along_x, side_sign):
        outward = Vector((0.0, side_sign)) if along_x else Vector((side_sign, 0.0))
        for index, (coordinate, pier_width) in enumerate(positions):
            if along_x:
                centre = (coordinate,
                          face_coordinate - side_sign * PILOTIS_ARCADE_PIER_DEPTH / 2.0)
                dimensions = (pier_width, PILOTIS_ARCADE_PIER_DEPTH,
                              arcade_z1 - arcade_z0)
            else:
                centre = (face_coordinate - side_sign * PILOTIS_ARCADE_PIER_DEPTH / 2.0,
                          coordinate)
                dimensions = (PILOTIS_ARCADE_PIER_DEPTH, pier_width,
                              arcade_z1 - arcade_z0)
            parts.append(box(f"{name}_Pier_{index}",
                             (centre[0], centre[1], (arcade_z0 + arcade_z1) / 2.0),
                             dimensions, mat))
        for index, ((first, _), (second, _)) in enumerate(zip(positions,
                                                                 positions[1:])):
            arch_plane = (face_coordinate
                          - side_sign * PILOTIS_ARCADE_PIER_DEPTH / 2.0)
            start_coordinate = first + COL_SIZE / 2.0
            end_coordinate = second - COL_SIZE / 2.0
            start = (Vector((start_coordinate, arch_plane)) if along_x
                     else Vector((arch_plane, start_coordinate)))
            end = (Vector((end_coordinate, arch_plane)) if along_x
                   else Vector((arch_plane, end_coordinate)))
            outer_radius = (end - start).length / 2.0
            parts.append(semicircular_arch(f"{name}_Arch_{index}", start, end,
                                            outward, arcade_z1 - outer_radius - 0.40,
                                            arcade_z1, mat))

    # These centres match the real corner and perimeter support locations. The
    # thicker facade piers now extend each recessed support out to the tower skin.
    long_positions = [(x, COL_SIZE) for x in col_grid(W)]
    short_positions = [(y, COL_SIZE) for y in col_grid(D)]
    side("PilotisArcade_S", long_positions, -D / 2.0, True, -1.0)
    side("PilotisArcade_N", long_positions, D / 2.0, True, 1.0)
    side("PilotisArcade_W", short_positions, -W / 2.0, False, -1.0)
    side("PilotisArcade_E", short_positions, W / 2.0, False, 1.0)
    return join(parts, "Pilotis_Arcades")


def pilotis_arcade_lights(mats):
    """Add small recessed emissive globes beneath each arcade arch.

    The fixtures are a separate mesh/object from ``Pilotis_Arcades`` so this
    detail can be regenerated locally without rebuilding any facade geometry.
    Three globes follow each half-round soffit, using the same emissive podium
    materials as the other circular ceiling lights.
    """
    cool, warm = [], []
    arcade_z0 = PODIUM_TOP_Z
    arcade_z1 = BASE_Z + H
    opening_index = 0

    def side(positions, face_coordinate, along_x, side_sign):
        nonlocal opening_index
        outward = Vector((0.0, side_sign)) if along_x else Vector((side_sign, 0.0))
        arch_plane = (face_coordinate
                      - side_sign * PILOTIS_ARCADE_PIER_DEPTH / 2.0)
        soffit_inset = outward * (PILOTIS_ARCADE_PIER_DEPTH * 0.28)
        for (first, _), (second, _) in zip(positions, positions[1:]):
            start_coordinate = first + COL_SIZE / 2.0
            end_coordinate = second - COL_SIZE / 2.0
            start = (Vector((start_coordinate, arch_plane)) if along_x
                     else Vector((arch_plane, start_coordinate)))
            end = (Vector((end_coordinate, arch_plane)) if along_x
                   else Vector((arch_plane, end_coordinate)))
            axis = (end - start).normalized()
            radius = (end - start).length / 2.0
            centre = (start + end) / 2.0
            spring_z = arcade_z1 - radius - 0.40
            # A globe is tucked into the curved underside, leaving only its
            # lower half visible.  Alternating temperatures adds a restrained
            # warm accent without changing the existing ceiling-light field.
            for fixture_index, theta in enumerate(
                    (math.pi * 0.25, math.pi * 0.50, math.pi * 0.75)):
                along = axis * (radius * math.cos(theta))
                soffit_z = spring_z + radius * math.sin(theta)
                point = centre + along - soffit_inset
                point3 = Vector((point.x, point.y,
                                 soffit_z - PILOTIS_ARCADE_LIGHT_RADIUS * 0.55))
                (warm if (opening_index + fixture_index) % 7 == 0 else cool).append(
                    tuple(point3))
            opening_index += 1

    long_positions = [(x, COL_SIZE) for x in col_grid(W)]
    short_positions = [(y, COL_SIZE) for y in col_grid(D)]
    side(long_positions, -D / 2.0, True, -1.0)
    side(long_positions, D / 2.0, True, 1.0)
    side(short_positions, -W / 2.0, False, -1.0)
    side(short_positions, W / 2.0, False, 1.0)

    bulbs = [
        spheres_mesh("Pilotis_Arcade_LightCool", cool,
                     PILOTIS_ARCADE_LIGHT_RADIUS,
                     mats["podium_ceiling_light_cool"]),
        spheres_mesh("Pilotis_Arcade_LightWarm", warm,
                     PILOTIS_ARCADE_LIGHT_RADIUS,
                     mats["podium_ceiling_light_warm"]),
    ]
    bulbs_mesh = join(bulbs, "Pilotis_Arcade_Lights")
    return bulbs_mesh


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(reset=True, mats=None, add_trusses=False,
          truss_object_name="Structural_Trusses"):
    if reset:
        reset_scene()

    if mats is None:
        mats = materials.build_all(engine=RENDER_ENGINE, wall_color=WALL_COLOR,
                                    glass_tint=GLASS_TINT)
    concrete = mats["concrete"]
    spandrel = mats["spandrel"]
    glass = mats["glass"]
    ceiling_light_mats = {
        "daylight": mats["ceiling_light_daylight"],
        "warm": mats["ceiling_light_warm"],
        "off": mats["ceiling_light_off"],
    }
    metal = mats["metal"]
    dark = mats["dark"]

    walls, glazing, frames, louvres, backs, slabs, structure = [], [], [], [], [], [], []
    trusses = []
    ceiling_lights_mesh = []
    plants, trunks, grilles = [], [], []
    foliage_mat = mats["foliage"]
    trunk_mat = mats["trunk"]

    # --- tower perimeter columns -----------------------------------------
    # These are the apartment towers' original load-bearing perimeter columns.
    # The podium wraps around them; it does not replace or truncate them.
    tower_column_z0 = 0.0
    tower_column_height = CORE_TOP_Z
    structure += [box("GroundSlab", (0.0, 0.0, -0.15), (W + 14.0, D + 14.0, 0.30), concrete)]

    x_grid, y_grid = col_grid(W), col_grid(D)
    for i, x in enumerate(x_grid):
        for j, y in enumerate(y_grid):
            # Keep only the outermost grid layer. The four grid-corner positions
            # are replaced by the larger corner columns below, so no duplicate
            # supports are left at the corners.
            if i not in (0, len(x_grid) - 1) and j not in (0, len(y_grid) - 1):
                continue
            if i in (0, len(x_grid) - 1) and j in (0, len(y_grid) - 1):
                continue
            structure.append(box(
                f"Column_{i}_{j}",
                (x, y, tower_column_z0 + tower_column_height / 2.0),
                (COL_SIZE, COL_SIZE, tower_column_height), concrete))

    for i, (x, y) in enumerate(corner_columns()):
        structure.append(box(
            f"CornerColumn_{i}",
            (x, y, tower_column_z0 + tower_column_height / 2.0),
            (CORNER_COL_SIZE, CORNER_COL_SIZE, tower_column_height), spandrel))

    pilotis_arcade = pilotis_arcades(spandrel)
    pilotis_arcade_lamp = pilotis_arcade_lights(mats)

    # Service cores rising through the open floors (stairs / lifts).
    structure += cores("Core", 0.0, BASE_Z, concrete)

    # Intermediate landings inside each core, one per open floor.
    for f in range(1, PILOTIS_FLOORS):
        for k, cx in enumerate(CORE_XS):
            structure.append(box(
                f"CoreLanding_{k}_{f}", (cx, 0.0, f * H),
                (CORE_W - 2 * CORE_T, CORE_D - 2 * CORE_T, 0.18), concrete))

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
            if f == 0:
                # The elevated triumphal arcade occupies this band, so it
                # supplies the facade rather than a continuous blank wall.
                slabs.append(box(f"{tag}_Slab", (0.0, 0.0, z0 + H - SLAB_T / 2.0),
                                 (W - 2 * WALL_T, D - 2 * WALL_T, SLAB_T), concrete))
                continue
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
        ceiling_lights_mesh += ceiling_lights(f"{tag}_CeilingLight", z0, f,
                                              ceiling_light_mats)
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
            "RoofGarden", ROOF_GARDEN_Z0, concrete, foliage_mat, trunk_mat, metal,
            tall_trees=True)
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
        # Match the exterior exactly; mullions and louvres keep their dark metal.
        trusses += structural_trusses("RefugeTruss", spandrel)

    merged = {
        "Facade_Spandrels": join(walls, "Facade_Spandrels"),
        "Windows_Glass": join(glazing, "Windows_Glass"),
        "Ceiling_Lights": join(ceiling_lights_mesh, "Ceiling_Lights"),
        "Sky_Garden_Grille": join(grilles, "Sky_Garden_Grille"),
        "Sky_Garden_Planting": join(plants, "Sky_Garden_Planting"),
        "Sky_Garden_Trunks": join(trunks, "Sky_Garden_Trunks"),
        "Window_Mullions": join(frames, "Window_Mullions"),
        "Vent_Louvres": join(louvres, "Vent_Louvres"),
        "Vent_Shadowboxes": join(backs, "Vent_Shadowboxes"),
        "Floor_Plates": join(slabs, "Floor_Plates"),
        "Structure": join(structure, "Structure"),
        "Pilotis_Arcades": pilotis_arcade,
        "Pilotis_Arcade_Lights": pilotis_arcade_lamp,
        truss_object_name: join(trusses, truss_object_name),
    }
    return merged


def rounded_rectangle_path(center, width, depth, rotation_deg, radius, pitch):
    """Return a faceted, constant-radius rounded-rectangle perimeter.

    The path is counter-clockwise in plan.  Its four straight runs retain the
    requested overall width/depth while each corner is a true quarter-circle
    approximation, so the podium reads as one rounded rectangle rather than a
    box with four separate corner posts.
    """
    radius = min(float(radius), width / 2.0, depth / 2.0)
    if radius <= 0.0:
        raise ValueError("rounded podium corners need a positive radius")
    arc_segments = max(2, round(math.pi * radius / (2.0 * pitch)))
    local_points, local_tangents = [], []

    def add_point(point, tangent):
        if local_points and math.hypot(point[0] - local_points[-1][0],
                                      point[1] - local_points[-1][1]) < 1e-8:
            return
        # The final quarter arc returns to the first point. Keep the path
        # closed by the caller's modulo indexing, rather than creating a
        # zero-length last panel at the seam.
        if len(local_points) >= 3 and math.hypot(
                point[0] - local_points[0][0],
                point[1] - local_points[0][1]) < 1e-8:
            return
        local_points.append(point)
        local_tangents.append(Vector(tangent).normalized())

    def add_line(start, end):
        segment = Vector((end[0] - start[0], end[1] - start[1]))
        direction = segment.normalized()
        steps = max(1, round(segment.length / pitch))
        for index in range(steps + 1):
            point = Vector(start) + segment * (index / steps)
            add_point(point, direction)

    def add_arc(cx, cy, start_angle, end_angle):
        for index in range(arc_segments + 1):
            theta = start_angle + (end_angle - start_angle) * index / arc_segments
            add_point((cx + radius * math.cos(theta),
                       cy + radius * math.sin(theta)),
                      (-math.sin(theta), math.cos(theta)))

    half_w, half_d = width / 2.0, depth / 2.0
    add_line((-half_w + radius, -half_d), (half_w - radius, -half_d))
    add_arc(half_w - radius, -half_d + radius, -math.pi / 2.0, 0.0)
    add_line((half_w, -half_d + radius), (half_w, half_d - radius))
    add_arc(half_w - radius, half_d - radius, 0.0, math.pi / 2.0)
    add_line((half_w - radius, half_d), (-half_w + radius, half_d))
    add_arc(-half_w + radius, half_d - radius, math.pi / 2.0, math.pi)
    add_line((-half_w, half_d - radius), (-half_w, -half_d + radius))
    add_arc(-half_w + radius, -half_d + radius, math.pi, 3.0 * math.pi / 2.0)

    centre = Vector(center)
    angle = math.radians(rotation_deg)
    axis = Vector((math.cos(angle), math.sin(angle)))
    normal = Vector((-math.sin(angle), math.cos(angle)))
    points, tangents = [], []
    for point, tangent in zip(local_points, local_tangents):
        points.append(centre + axis * point[0] + normal * point[1])
        tangents.append((axis * tangent.x + normal * tangent.y).normalized())
    return points, tangents


def rounded_prism(name, center, width, depth, rotation_deg, radius, z0, z1, mat):
    """Extrude a rounded-rectangle plan into one floor or ground plate."""
    points, _ = rounded_rectangle_path(
        center, width, depth, rotation_deg, radius, PODIUM_GRID_PITCH)
    count = len(points)
    verts = [(point.x, point.y, z0) for point in points]
    verts += [(point.x, point.y, z1) for point in points]
    faces = [tuple(reversed(range(count))), tuple(range(count, 2 * count))]
    for index in range(count):
        next_index = (index + 1) % count
        faces.append((index, next_index, count + next_index, count + index))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    bpy.context.collection.objects.link(obj)
    return obj


def build_podium(mats, base_rectangles, diamond_grid_only=False):
    """Build one smooth, two-edge Bezier podium around the two tower bases."""
    diamond_mat = mats["podium_diamond"]
    if not diamond_grid_only:
        glass, metal, concrete = (mats["glass"], mats["metal"],
                                  mats["concrete"])
    glass_parts, rail_parts, slab_parts, column_parts = [], [], [], []
    diamond_parts, ceiling_light_parts = [], []
    first, second = base_rectangles[:2]

    def sample_cubic(start, control_1, control_2, end):
        """Sample a cubic by approximately equal three-metre arc lengths."""
        dense = []
        for index in range(129):
            t = index / 128
            u = 1.0 - t
            dense.append(u**3 * start + 3.0 * u*u*t * control_1
                         + 3.0 * u*t*t * control_2 + t**3 * end)
        distances = [0.0]
        for first_point, second_point in zip(dense, dense[1:]):
            distances.append(distances[-1] + (second_point - first_point).length)
        steps = max(1, round(distances[-1] / PODIUM_GRID_PITCH))
        points = [dense[0]]
        segment = 0
        for index in range(1, steps):
            target = distances[-1] * index / steps
            while distances[segment + 1] < target:
                segment += 1
            fraction = ((target - distances[segment])
                        / (distances[segment + 1] - distances[segment]))
            points.append(dense[segment].lerp(dense[segment + 1], fraction))
        points.append(dense[-1])
        return points

    def append_arc(points, centre, radius, start_angle, end_angle):
        steps = max(1, round(abs(end_angle - start_angle) * radius
                             / PODIUM_GRID_PITCH))
        for index in range(steps + 1):
            angle = start_angle + (end_angle - start_angle) * index / steps
            point = centre + radius * Vector((math.cos(angle), math.sin(angle)))
            if not points or (point - points[-1]).length > 1e-6:
                points.append(point)

    def append_line(points, start, end):
        steps = max(1, round((end - start).length / PODIUM_GRID_PITCH))
        for index in range(steps + 1):
            point = start.lerp(end, index / steps)
            if not points or (point - points[-1]).length > 1e-6:
                points.append(point)

    def capsule_outer_route(spec, extra):
        """Outer capsule boundary from its lower to its upper link face."""
        centre, width, depth, rotation = spec
        width, depth = width + 2.0 * extra, depth + 2.0 * extra
        radius, half_width = depth / 2.0, width / 2.0
        axis = Vector((math.cos(math.radians(rotation)),
                       math.sin(math.radians(rotation))))
        normal = Vector((-axis.y, axis.x))
        inner_cap = Vector(centre) + axis * (half_width - radius)
        outer_cap = Vector(centre) - axis * (half_width - radius)

        def world(point):
            return Vector(centre) + axis * point.x + normal * point.y

        # In local space the route deliberately takes the long way around the
        # outward end.  Its two missing inner-cap arcs are replaced below by
        # the two Bezier connection edges.
        angle = PODIUM_BEZIER_ATTACH_ANGLE
        local_points = []
        append_arc(local_points, Vector((half_width - radius, 0.0)), radius,
                   -angle, -math.pi / 2.0)
        append_line(local_points, Vector((half_width - radius, -radius)),
                    Vector((-half_width + radius, -radius)))
        append_arc(local_points, Vector((-half_width + radius, 0.0)), radius,
                   -math.pi / 2.0, -3.0 * math.pi / 2.0)
        append_line(local_points, Vector((-half_width + radius, radius)),
                    Vector((half_width - radius, radius)))
        append_arc(local_points, Vector((half_width - radius, 0.0)), radius,
                   math.pi / 2.0, angle)
        route = [world(point) for point in local_points]

        lower = world(Vector((half_width - radius + radius * math.cos(-angle),
                              radius * math.sin(-angle))))
        upper = world(Vector((half_width - radius + radius * math.cos(angle),
                              radius * math.sin(angle))))
        # Tangents of this outward capsule route at lower/start and upper/end.
        lower_tangent = (axis * math.sin(-angle)
                         - normal * math.cos(-angle)).normalized()
        upper_tangent = (axis * math.sin(angle)
                         - normal * math.cos(angle)).normalized()
        return route, lower, upper, lower_tangent, upper_tangent

    def continuous_outline(extra):
        first_route, first_lower, first_upper, first_lower_t, first_upper_t = (
            capsule_outer_route(first, extra))
        (second_route, second_lower, second_upper, second_lower_t,
         second_upper_t) = capsule_outer_route(second, extra)

        # The local winding of the second inward round end is reversed in the
        # open-book plan.  These are therefore the two same-side pairs in world
        # space: upper-to-upper and lower-to-lower.  Each endpoint handle follows
        # its round end's tangent, so the slab boundary is G1-continuous at all
        # four joins rather than forming a V-shaped kink.
        span_a = second_lower - first_upper
        span_b = first_lower - second_upper
        upper_handle = span_a.length * 0.46
        lower_handle = span_b.length * 0.46
        edge_a = sample_cubic(
            first_upper,
            first_upper + first_upper_t * upper_handle,
            second_lower - second_lower_t * upper_handle,
            second_lower)
        edge_b = sample_cubic(
            second_upper,
            second_upper + second_upper_t * lower_handle,
            first_lower - first_lower_t * lower_handle,
            first_lower)
        # The ring is: podium 1 outer boundary, first Bezier edge, podium 2
        # outer boundary, second Bezier edge.  There are exactly two connecting
        # faces and neither can introduce an internal rail or a sharp joint.
        return first_route + edge_a[1:] + second_route[1:] + edge_b[1:-1]

    def ring_prism(name, ring, z0, z1):
        count = len(ring)
        vertices = [(point.x, point.y, z0) for point in ring]
        vertices += [(point.x, point.y, z1) for point in ring]
        # The joined podium outline is concave.  A single n-gon lets Blender
        # choose an invalid diagonal across the connection; tessellate it
        # explicitly so only the area bounded by the two Bezier edges is filled.
        plan_points = [Vector((point.x, point.y, 0.0)) for point in ring]
        plan_triangles = tessellate_polygon([plan_points])
        faces = []
        for triangle in plan_triangles:
            indices = list(triangle)
            faces.append(tuple(reversed(indices)))
            faces.append(tuple(count + index for index in indices))
        for index in range(count):
            next_index = (index + 1) % count
            faces.append((index, next_index, count + next_index, count + index))
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, [], faces)
        mesh.validate()
        obj = bpy.data.objects.new(name, mesh)
        obj.data.materials.append(concrete)
        bpy.context.collection.objects.link(obj)
        return obj

    def add_perimeter_glass(ring, floor_index, z0, z1):
        for edge_index, point in enumerate(ring):
            nxt = ring[(edge_index + 1) % len(ring)]
            axis = (nxt - point).normalized()
            length = (nxt - point).length
            if length < 0.05:
                continue
            midpoint = (point + nxt) / 2.0
            glass_parts.append(box(
                f"Podium_Glass_{floor_index}_{edge_index}",
                (midpoint.x, midpoint.y, (z0 + z1) / 2.0),
                (max(0.08, length - 0.03), GLASS_T, z1 - z0), glass,
                rot=(0.0, 0.0, math.atan2(axis.y, axis.x))))

    def signed_area(ring):
        return sum(point.x * ring[(index + 1) % len(ring)].y
                   - ring[(index + 1) % len(ring)].x * point.y
                   for index, point in enumerate(ring)) / 2.0

    def add_diamond_grid(ring, floor_index, z0, z1):
        """Overlay two large rows of rhombi on every glazed facade panel."""
        outward_sign = -1.0 if signed_area(ring) > 0.0 else 1.0
        cell_h = (z1 - z0) / PODIUM_DIAMOND_ROWS
        for edge_index, point in enumerate(ring):
            nxt = ring[(edge_index + 1) % len(ring)]
            axis = (nxt - point).normalized()
            length = (nxt - point).length
            if length < 0.05:
                continue
            # The right-hand normal of a counter-clockwise path is exterior.
            outward = outward_sign * Vector((axis.y, -axis.x))
            offset = outward * (GLASS_T / 2.0 + PODIUM_DIAMOND_STANDOFF)
            left, right = point + offset, nxt + offset
            middle = (left + right) / 2.0
            for row in range(PODIUM_DIAMOND_ROWS):
                bottom_z = z0 + row * cell_h
                mid_z = bottom_z + cell_h / 2.0
                top_z = bottom_z + cell_h
                vertices = (
                    Vector((left.x, left.y, mid_z)),
                    Vector((middle.x, middle.y, top_z)),
                    Vector((right.x, right.y, mid_z)),
                    Vector((middle.x, middle.y, bottom_z)),
                )
                for member, (start, end) in enumerate(zip(
                        vertices, vertices[1:] + vertices[:1])):
                    diamond_parts.append(beam_between(
                        f"Podium_DiamondGrid_{floor_index}_{edge_index}_{row}_{member}",
                        start, end, PODIUM_DIAMOND_MEMBER, diamond_mat))

    def point_inside_ring(point, ring):
        """Even-odd containment for the concave continuous podium outline."""
        inside = False
        x, y = point
        for index, first_point in enumerate(ring):
            second_point = ring[(index + 1) % len(ring)]
            if ((first_point.y > y) != (second_point.y > y)):
                crossing = ((second_point.x - first_point.x)
                            * (y - first_point.y)
                            / (second_point.y - first_point.y) + first_point.x)
                if x < crossing:
                    inside = not inside
        return inside

    def edge_distance(point, start, end):
        segment = end - start
        length_sq = segment.length_squared
        if length_sq <= 1e-9:
            return (Vector(point) - start).length
        fraction = min(1.0, max(0.0, (Vector(point) - start).dot(segment)
                                / length_sq))
        return (Vector(point) - (start + fraction * segment)).length

    def add_ceiling_globes(ring, floor_index, ceiling_z):
        """Fill each podium ceiling with small bright, star-like round lamps."""
        min_x = min(point.x for point in ring)
        max_x = max(point.x for point in ring)
        min_y = min(point.y for point in ring)
        max_y = max(point.y for point in ring)
        cool, warm = [], []
        row = 0
        y = min_y + PODIUM_CEILING_LIGHT_PITCH / 2.0
        while y < max_y:
            x = (min_x + PODIUM_CEILING_LIGHT_PITCH / 2.0
                 + (row % 2) * PODIUM_CEILING_LIGHT_PITCH / 2.0)
            column = 0
            while x < max_x:
                point = (x, y)
                clearance = min(edge_distance(point, start,
                                               ring[(index + 1) % len(ring)])
                                for index, start in enumerate(ring))
                if (point_inside_ring(point, ring)
                        and clearance >= PODIUM_CEILING_LIGHT_EDGE_CLEARANCE):
                    centre = (x, y, ceiling_z - PODIUM_CEILING_LIGHT_RADIUS + 0.01)
                    (warm if (row * 7 + column + floor_index) % 6 == 0
                     else cool).append(centre)
                x += PODIUM_CEILING_LIGHT_PITCH
                column += 1
            y += PODIUM_CEILING_LIGHT_PITCH
            row += 1
        ceiling_light_parts.extend((
            spheres_mesh(f"Podium_CeilingLightCool_{floor_index}", cool,
                         PODIUM_CEILING_LIGHT_RADIUS,
                         mats["podium_ceiling_light_cool"]),
            spheres_mesh(f"Podium_CeilingLightWarm_{floor_index}", warm,
                         PODIUM_CEILING_LIGHT_RADIUS,
                         mats["podium_ceiling_light_warm"]),
        ))

    def add_guardrail(ring, floor_index, deck_z):
        for edge_index, point in enumerate(ring):
            nxt = ring[(edge_index + 1) % len(ring)]
            axis = (nxt - point).normalized()
            length = (nxt - point).length
            if length < 0.05:
                continue
            midpoint = (point + nxt) / 2.0
            rail_parts.append(box(
                f"Podium_GalleryRail_{floor_index}_{edge_index}",
                (midpoint.x, midpoint.y, deck_z + PODIUM_CORRIDOR_RAIL_H),
                (length, 0.14, 0.14), metal,
                rot=(0.0, 0.0, math.atan2(axis.y, axis.x))))
            count = max(1, round(length / 4.0))
            for post_index in range(count + 1):
                post = point.lerp(nxt, post_index / count)
                rail_parts.append(box(
                    f"Podium_GalleryPost_{floor_index}_{edge_index}_{post_index}",
                    (post.x, post.y, deck_z + PODIUM_CORRIDOR_RAIL_H / 2.0),
                    (0.12, 0.14, PODIUM_CORRIDOR_RAIL_H), metal,
                    rot=(0.0, 0.0, math.atan2(axis.y, axis.x))))

    if not diamond_grid_only:
        pilotis_ring = continuous_outline(PODIUM_CORRIDOR_DEPTH)
        stride = max(1, round(PODIUM_PILOTIS_COLUMN_PITCH / PODIUM_GRID_PITCH))
        for index in range(0, len(pilotis_ring), stride):
            point = pilotis_ring[index]
            column_parts.append(box(
                f"Podium_PilotisColumn_{index}", (point.x, point.y, H),
                (PODIUM_PILOTIS_COLUMN_SIZE, PODIUM_PILOTIS_COLUMN_SIZE, 2.0 * H),
                concrete))

        # The lowest occupied plate is the ceiling of the two-storey open podium.
        # Give that whole soffit the same bright star-field as the glazed levels so
        # the pilotis stays usable for parking, play, or skating after dark.
        pilotis_fraction = (PODIUM_PILOTIS_FLOORS + 1) / PODIUM_TOTAL_FLOORS
        pilotis_specs = []
        for centre, top_width, top_depth, rotation in (first, second):
            pilotis_specs.append((
                centre,
                top_width + 2.0 * PODIUM_BOTTOM_LENGTH_MARGIN * (1.0 - pilotis_fraction),
                top_depth + (PODIUM_BOTTOM_DEPTH - top_depth) * (1.0 - pilotis_fraction),
                rotation))
        saved_first, saved_second = first, second
        first, second = pilotis_specs
        pilotis_ceiling_ring = continuous_outline(PODIUM_CORRIDOR_DEPTH)
        first, second = saved_first, saved_second
        add_ceiling_globes(pilotis_ceiling_ring, PODIUM_PILOTIS_FLOORS,
                           PODIUM_PILOTIS_FLOORS * H - SLAB_T)

    for floor_index in range(PODIUM_PILOTIS_FLOORS, PODIUM_TOTAL_FLOORS):
        fraction = (floor_index + 1) / PODIUM_TOTAL_FLOORS
        body_specs = []
        for centre, top_width, top_depth, rotation in (first, second):
            width = top_width + 2.0 * PODIUM_BOTTOM_LENGTH_MARGIN * (1.0 - fraction)
            depth = top_depth + (PODIUM_BOTTOM_DEPTH - top_depth) * (1.0 - fraction)
            body_specs.append((centre, width, depth, rotation))
        # Reuse the same two Bezier edges at the facade and at the outer
        # gallery rail; only the offset changes, so no duplicate inner edge
        # or railing can appear in the connection zone.
        saved_first, saved_second = first, second
        first, second = body_specs
        facade_ring = continuous_outline(0.0)
        gallery_ring = (continuous_outline(PODIUM_BALCONY_DEPTH)
                        if not diamond_grid_only else None)
        first, second = saved_first, saved_second
        z0 = (PODIUM_PILOTIS_CEILING_Z
              + (floor_index - PODIUM_PILOTIS_FLOORS) * PODIUM_H)
        z1 = z0 + PODIUM_H
        if not diamond_grid_only:
            # The third podium level starts directly above the two-storey pilotis.
            # Give its glazed retail enclosure a real continuous floor at z=8 m;
            # the later plates remain the ceiling/floor plates between upper levels.
            if floor_index == PODIUM_PILOTIS_FLOORS:
                slab_parts.append(ring_prism(
                    f"Podium_ContinuousBezierFloor_{floor_index}_Base", gallery_ring,
                    z0 - SLAB_T, z0))
            slab_parts.append(ring_prism(
                f"Podium_ContinuousBezierFloor_{floor_index}", gallery_ring,
                z1 - SLAB_T, z1))
            add_perimeter_glass(facade_ring, floor_index, z0, z1 - SLAB_T)
        add_diamond_grid(facade_ring, floor_index, z0, z1 - SLAB_T)
        if not diamond_grid_only:
            if floor_index == PODIUM_PILOTIS_FLOORS:
                add_guardrail(gallery_ring, floor_index, z0)
            add_ceiling_globes(gallery_ring, floor_index, z1 - SLAB_T)
            add_guardrail(gallery_ring, floor_index, z1)

    if diamond_grid_only:
        return {"Podium_Diamond_Grid": join(diamond_parts,
                                               "Podium_Diamond_Grid")}

    garden_planters, garden_foliage, garden_trunks = podium_roof_garden(
        base_rectangles, PODIUM_TOP_Z, mats)

    return {
        "Podium_Glass": join(glass_parts, "Podium_Glass"),
        "Podium_Diamond_Grid": join(diamond_parts, "Podium_Diamond_Grid"),
        "Podium_Ceiling_Lights": join(ceiling_light_parts,
                                        "Podium_Ceiling_Lights"),
        "Podium_Mullions": join(rail_parts, "Podium_Mullions"),
        "Podium_Floor_Plates": join(slab_parts, "Podium_Floor_Plates"),
        "Podium_Structure": join(column_parts, "Podium_Structure"),
        "Podium_Garden_Planters": join(garden_planters, "Podium_Garden_Planters"),
        "Podium_Garden_Foliage": join(garden_foliage, "Podium_Garden_Foliage"),
        "Podium_Garden_Trunks": join(garden_trunks, "Podium_Garden_Trunks"),
    }


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
    elif hasattr(scene, "eevee"):
        for attr, value in (("taa_render_samples", 128), ("use_gtao", True),
                            # The preview-glass reflection leg must be able to
                            # see scene geometry, not only the world sky.
                            ("use_raytracing", True)):
            if hasattr(scene.eevee, attr):
                setattr(scene.eevee, attr, value)

    # Keep this stored Cycles setting clean even when EEVEE is the active engine:
    # Filter Glossy frosts smooth glass if a later final render switches engines.
    if hasattr(scene.cycles, "blur_glossy"):
        scene.cycles.blur_glossy = 0.0

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
    # A telephoto lens so the tower verticals stay parallel instead of keystoning
    # inward. Combined with a camera lifted to near the roof line (below), the
    # look direction is nearly horizontal, so the facades read flat rather than
    # leaning. The reach scales with the lens to keep both towers in frame.
    cam_data.lens = 85.0
    cam = bpy.data.objects.new("Camera", cam_data)

    # Frame the whole two-tower site: pull back proportionally to its envelope.
    reach = max(SITE_WIDTH, SITE_DEPTH, SITE_TOP_Z) * 1.35 * (cam_data.lens / 40.0)
    target = Vector((SITE_CENTER_X, SITE_CENTER_Y, SITE_TOP_Z * 0.52))
    eye = Vector((SITE_CENTER_X + reach * 0.78,
                  SITE_CENTER_Y - reach * 1.05, SITE_TOP_Z * 1.02))
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
    x_grid, y_grid = col_grid(W), col_grid(D)
    perimeter_grid_columns = (2 * max(0, len(x_grid) - 2)
                              + 2 * max(0, len(y_grid) - 2))
    print(f"perimeter columns    : {perimeter_grid_columns} outer-grid + 4 corner, "
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
        print("tower perimeter cols  : original grid runs 0.0 m -> core bulkhead")
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
                r3d.view_location = Vector(
                    (SITE_CENTER_X, SITE_CENTER_Y, SITE_TOP_Z * 0.5))
                r3d.view_distance = diag * 1.6
                # A 3/4 view from the south-east: the lit side, matching where the
                # render cameras sit.
                r3d.view_rotation = Euler(
                    (math.radians(72.0), 0.0, math.radians(38.0)), "XYZ"
                ).to_quaternion()
                r3d.view_perspective = "PERSP"
                # Keep Material Preview consistent when the saved file is
                # reopened: the third world thumbnail is forest.exr, with the
                # requested 30% background opacity and blur.
                space.shading.type = "MATERIAL"
                space.shading.studio_light = "forest.exr"
                space.shading.studiolight_background_alpha = 0.3
                space.shading.studiolight_background_blur = 0.3
                space.shading.use_scene_world_render = True
                space.shading.use_scene_lights_render = True
                # Far clip has to clear the pull-back or the model is culled and
                # you open onto an empty grey viewport — worse than being inside.
                space.clip_end = max(space.clip_end, diag * 6.0)
                space.clip_start = 0.5
                space.lens = 35.0


def transform_objects(objects, x_offset, y_offset, rotation_deg=0.0):
    """Place one generated tower as a group around its local (0, 0) centre."""
    transform = (Matrix.Translation(Vector((x_offset, y_offset, 0.0)))
                 @ Matrix.Rotation(math.radians(rotation_deg), 4, "Z"))
    for obj in objects.values():
        if obj is not None:
            obj.matrix_world = transform @ obj.matrix_world


def book_layout(first_w, second_w):
    """Return the second tower centre/rotation for the open-book plan."""
    second_outward_deg = BOOK_FIRST_OUTWARD_DEG - BOOK_OPEN_ANGLE
    spine_x = first_w / 2.0 + BOOK_EDGE_CLEARANCE / 2.0
    second_radius = second_w / 2.0 + BOOK_EDGE_CLEARANCE / 2.0
    outward = Vector((math.cos(math.radians(second_outward_deg)),
                      math.sin(math.radians(second_outward_deg))))
    second_center = Vector((spine_x, 0.0)) + outward * second_radius
    # The local +X end is the inner short end; the outward page direction is -X.
    second_rotation = second_outward_deg + 180.0
    return second_center, second_rotation


def footprint_bounds(center, width, depth, rotation_deg):
    """Axis-aligned bounds of a rotated rectangular tower footprint."""
    angle = math.radians(rotation_deg)
    half_x = (abs(math.cos(angle)) * width / 2.0
              + abs(math.sin(angle)) * depth / 2.0)
    half_y = (abs(math.sin(angle)) * width / 2.0
              + abs(math.cos(angle)) * depth / 2.0)
    return ((center.x - half_x, center.x + half_x),
            (center.y - half_y, center.y + half_y))


def rectangle_corners(center, width, depth, rotation_deg):
    """Plan corners of a rotated rectangular tower footprint."""
    angle = math.radians(rotation_deg)
    axis = Vector((math.cos(angle), math.sin(angle)))
    normal = Vector((-math.sin(angle), math.cos(angle)))
    centre = Vector(center)
    return [
        tuple(centre + sx * axis * width / 2.0
              + sy * normal * depth / 2.0)
        for sx, sy in ((-1, -1), (-1, 1), (1, 1), (1, -1))
    ]


def main():
    global SITE_WIDTH, SITE_CENTER_X, SITE_CENTER_Y, SITE_DEPTH, SITE_TOP_Z

    reset_scene()
    shared_mats = materials.build_all(engine=RENDER_ENGINE, wall_color=WALL_COLOR,
                                      glass_tint=GLASS_TINT)
    configure_tower(2, 18, core_column_bays=2)
    first_objects = build(reset=False, mats=shared_mats, add_trusses=True,
                          truss_object_name="Structural_Trusses_LowerTower")
    first_w, first_d, first_top = W, D, CORE_TOP_Z
    report(first_objects, "existing tower (2 groups x 17 floors, 18 rooms)")

    configure_tower(3, 20, core_column_bays=COMPANION_CORE_COLUMN_BAYS)
    second_objects = build(reset=False, mats=shared_mats, add_trusses=True)
    second_w, second_d, second_top = W, D, CORE_TOP_Z
    second_center, second_rotation = book_layout(first_w, second_w)
    transform_objects(second_objects, second_center.x, second_center.y,
                      second_rotation)

    podium_first_w = first_w + 2.0 * PODIUM_LENGTH_MARGIN
    podium_second_w = second_w + 2.0 * PODIUM_LENGTH_MARGIN
    podium_depth = PODIUM_DEPTH
    podium_bases = (
        (Vector((0.0, 0.0)), podium_first_w, podium_depth, 0.0),
        (second_center, podium_second_w, podium_depth, second_rotation),
    )
    podium_objects = build_podium(shared_mats, podium_bases)
    first_bounds = footprint_bounds(Vector((0.0, 0.0)), first_w, first_d, 0.0)
    second_bounds = footprint_bounds(second_center, second_w, second_d,
                                     second_rotation)
    podium_footprint = []
    footprint_points = [corner for width, depth, angle, centre in (
        (podium_first_w, podium_depth, 0.0, Vector((0.0, 0.0))),
        (podium_second_w, podium_depth, second_rotation, second_center))
        for corner in rectangle_corners(centre, width, depth, angle)]
    min_x = min(point[0] for point in footprint_points)
    max_x = max(point[0] for point in footprint_points)
    min_y = min(point[1] for point in footprint_points)
    max_y = max(point[1] for point in footprint_points)
    SITE_WIDTH = max_x - min_x
    SITE_CENTER_X = (min_x + max_x) / 2.0
    SITE_DEPTH = max_y - min_y
    SITE_CENTER_Y = (min_y + max_y) / 2.0
    SITE_TOP_Z = max(first_top, second_top, PODIUM_TOP_Z)

    report(second_objects, "new adjacent tower (3 groups x 17 floors, 20 rooms)")
    print("=== two-tower site ===")
    print(f"open-book angle     : {BOOK_OPEN_ANGLE:.1f} degrees")
    print(f"central clear gap    : {TOWER_GAP:.1f} m target")
    print(f"second tower rotation: {second_rotation:.1f} degrees")
    print(f"overall envelope     : {SITE_WIDTH:.1f} x {SITE_DEPTH:.1f} m")
    print(f"site centre          : x = {SITE_CENTER_X:.1f}, y = {SITE_CENTER_Y:.1f} m")
    print(f"highest core top     : {SITE_TOP_Z:.2f} m")
    print("=== continuous Bezier podium ===")
    print(f"top / bottom depth   : {podium_depth:.1f} / {PODIUM_BOTTOM_DEPTH:.1f} m")
    print(f"open pilotis floors  : {PODIUM_PILOTIS_FLOORS}")
    print(f"occupied floors      : {PODIUM_OCCUPIED_FLOORS}")
    print("connection edges     : 2 cubic Bezier curves")
    print(f"base widths          : {podium_first_w:.1f} / {podium_second_w:.1f} m")
    print(f"top / tower soffit   : {PODIUM_TOP_Z:.1f} m")
    print("=====================\n")
    setup_render()
    frame_viewport()

    os.makedirs(OUT_DIR, exist_ok=True)
    blend_path = os.path.join(OUT_DIR, "highrise_house.blend")
    bpy.context.scene["podium_top_z"] = PODIUM_TOP_Z
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    if "--no-glb" not in sys.argv:
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
