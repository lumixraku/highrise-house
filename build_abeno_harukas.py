"""Body-first procedural reconstruction of Abeno Harukas.

This pass intentionally models only the primary massing: three volumes of
different heights stand on the same ground plane and connect horizontally,
south to north (low, middle, high). Each volume is a different quadrilateral
in plan: the long connecting edges are slanted — they tilt along the
north-south axis instead of running straight east-west. The middle volume's
east side extends outward while its west side approaches the high volume.
Open truss bands sit just below the low/middle rooflines and near the
tower top (tops z 80/195/285 m, 7.5 m tall = 1.5 storeys), hollow
chevron rings recessed behind the continuous curtain wall; one-storey
staggered mid-office trusses stand exposed between them, and a vertical
hanging-truss mast runs on each side facade of the middle volume.
Chevron density follows face width (about 12 m per group, seven groups
on the long faces). The service core follows the
published linked-void scheme: four lower corner service zones (z 0-80 m,
every volume), a braced steel middle core with west eco-voids and east
lift banks (z 80-195 m, middle and high volumes), and an upper atrium
frame with a slim service core continuing to the roof (z 195-300 m, high
volume only), with transfer ties at the zone boundaries. Floor slabs run every 5 m with actual openings where the
core passes, and stay clear of the truss bands' interiors. Facade
grids, core and slabs are schematic.
"""

import argparse
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from materials import (make_concrete, make_glass, make_ground, make_metal,
                       make_wall)

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
TRUSS_BAND_H = 7.5      # belt truss bands: 1.5x the one-storey staggered
                        # trusses, per the figure's proportions
TRUSS_BAND_H_PARTIAL = 5.0  # the staggered mid-office trusses: one storey
# Belt band tops: just below the low/middle roofs (80/195 m) plus one
# near the top of the tower (285 m, floors 56-57, leaving the observatory
# floors 58-60 above it), each wrapping every volume tall enough to carry
# it. The belt bands stay behind the continuous curtain wall. No band at
# the ground level or at the 300 m roof.
TRUSS_BAND_TOPS = (80.0, 195.0, 285.0)
# Mid-office trusses each wrap a single volume, staggered between the two
# big roof bands (floors 25-26 on the middle volume, floors 31-32 on the
# high volume), per the published void-structure figure; unlike the roof
# bands they do not run through the adjoining volume, and they are
# exposed — the curtain wall splits around them (no glazing there).
TRUSS_BAND_TOPS_PARTIAL = {"Middle": (130.0,), "High": (160.0,)}
TRUSS_SPACING = 12.0    # chevron spacing; the ~86 m front faces get 7 groups
TRUSS_INSET = 0.07      # truss stands inside the glass line, deep enough
                        # that the chunky posts never cross the facade
TRUSS_POST_W = 1.80     # chunky boundary posts
TRUSS_DIAG_W = 0.70     # diagonals thickened to match
TRUSS_CHORD_W = 0.40
MAST_CELL_H = 10.0      # two-storey pyramid cells
# Vertical hanging-truss mast on the east and west facades of the middle
# volume only, one strip per face near the middle/high junction, running
# from the 15F belt band up to the 37F belt band, per the published
# section. Like every truss it stays within the envelope — recessed at
# TRUSS_INSET behind the curtain wall glass. The tower zone masts are
# interior — the braced atrium flank walls. (volume, y centre, z0, z1)
FACADE_MASTS = (
    ("Middle", 11.0, 80.0, 187.5),
)
# Service core, published linked-void scheme: four lower corner service
# zones (z 0-80 m, every volume), a braced steel middle core with west
# eco-voids and east lift banks (z 80-195 m, middle and high volumes), and
# an upper atrium frame with X-braced flank walls up to the top truss band
# (z 195-277.5 m) plus unbraced crown floors above the top band.
# Transfer ties link the corner zones to the spine at z 80 m and the spine
# to the atrium columns at z 195 m. Schematic, not as-built.
CORE_ZONE_LOW = (0.0, 80.0)
CORE_ZONE_MID = (80.0, 195.0)
CORE_ZONE_TOP = (195.0, 300.0)
CORNER_ZONE_SIZE = 8.0
CORNER_ZONE_MARGIN = CORNER_ZONE_SIZE / 2 + 1.0
CORE_SPINE_W = 20.0   # braced spine, X
CORE_SPINE_D = 12.0   # braced spine, Y
CORE_VOID_W = 12.0    # eco-void strip west of the spine
CORE_VOID_GAP = 0.6   # void frame stands clear of the spine west face
CORE_LIFTS = 3        # lift shafts east of the spine
CORE_LIFT_W = 3.6
CORE_LIFT_D = 7.0
CORE_LIFT_GAP = 0.8
CORE_LIFT_OFFSET = 1.0
BRACE_TIERS = 4
BRACE_BAYS = 2
BRACE_W = 0.35
ATRIUM_W = 26.0
ATRIUM_D = 15.0
ATRIUM_COL = 1.0
# Vertical truss walls flanking the atrium void, X-braced in two-storey
# cells from the middle-roof band up to the top band (z 195-277.5), per the
# hanging-truss figure; the crown floors above the top band stay unbraced.
ATRIUM_BRACE_TOP = 277.5
ATRIUM_BRACE_TIERS = 9
# Slim upper service core (lifts + stairs) continuing to the roof, standing
# just east of the atrium and stacking over the lift banks below.
UPPER_CORE_W = 8.0
UPPER_CORE_D = 12.0
UPPER_CORE_DX = ATRIUM_W / 2 + 1.0 + UPPER_CORE_W / 2
# Floor slabs every 5 m, inset from the glass line, with actual openings
# where the core passes; slab edges stop 5 cm short of the core walls so
# no faces are coplanar. Slabs stay clear of the truss bands.
STOREY_H = 5.0
SLAB_T = 0.3
SLAB_INSET = 0.3
OPENING_TOL = 0.1
SOURCES = {
    "source_height_m": 300.0,
    "source_floor_count": 60,
    "mass_layout": "Three volumes on one ground plane, connected south to north: low, middle, high.",
    "mass_heights_m": "80 / 195 / 300, flat roofs.",
    "plan_shape": "Three different quadrilaterals; long connecting edges tilt along the north-south axis, all within 3 degrees.",
    "truss_zones": "Hollow truss rings (chevron faces on all four sides, open interior, no solid backing): belt bands 7.5 m tall (1.5x the one-storey staggered trusses) just below the low/middle roofs plus one near the tower top (tops z 80/195/285 m), wrapping every volume tall enough and recessed behind the continuous curtain wall, plus one-storey staggered mid-office trusses each wrapping a single volume (floors 25-26 on the middle volume, floors 31-32 on the high volume), exposed — the glass splits around them; ~12 m chevron spacing (7 groups on the long faces).",
    "core_scheme": "Linked-void scheme: four lower corner service zones (z 0-80 m, every volume), braced steel middle core with west eco-voids and east lift banks (z 80-195 m, middle/high), upper atrium frame with X-braced flank walls up to the top truss band (z 195-277.5 m) plus slim service core continuing to the roof (z 195-300 m, high); transfer ties at z 80/195 m. Schematic, not as-built.",
    "floor_slabs": "5 m storeys, 0.3 m slabs inset 0.3 m from the plan, with actual core/atrium openings; clear of the truss bands.",
    "model_scope": "Body-first massing pass; facade grids schematic; linked-void core and floor slabs modelled; interior systems deferred.",
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


def plan_centre(points):
    return (sum(x for x, _ in points) / 4, sum(y for _, y in points) / 4)


def rect_points(cx, cy, w, d):
    return ((cx - w / 2, cy - d / 2), (cx + w / 2, cy - d / 2),
            (cx + w / 2, cy + d / 2), (cx - w / 2, cy + d / 2))


def quad_inset(points, margin):
    """Inward offset of a convex plan quad: every edge moves toward the
    centroid by ``margin``; returns the four inset corners in order."""
    centre = Vector((*plan_centre(points),))
    lines = []
    for i in range(4):
        a = Vector(points[i])
        b = Vector(points[(i + 1) % 4])
        normal = Vector((-(b.y - a.y), b.x - a.x)).normalized()
        if normal.dot(centre - a) < 0:
            normal = -normal
        lines.append((a + normal * margin, normal))
    inset = []
    for i in range(4):
        p0, n0 = lines[i]
        p1, n1 = lines[(i + 1) % 4]
        det = n0.x * n1.y - n1.x * n0.y
        c0, c1 = n0.dot(p0), n1.dot(p1)
        inset.append(((c0 * n1.y - c1 * n0.y) / det,
                      (n0.x * c1 - n1.x * c0) / det))
    return tuple(inset)


def truss_face(name, points, edge, z0, z1, metal):
    """Complete upward chevrons with both ends on the lower chord, plus
    boundary posts and top/bottom chords. Group count follows the face width
    so the density matches the seven-group front faces. The post at k=0 is
    skipped: the previous face's last post stands at the shared corner."""
    a, b = points[edge], points[(edge + 1) % 4]
    width = math.hypot(b[0] - a[0], b[1] - a[1])
    groups = max(1, round(width / TRUSS_SPACING))
    for k in range(1, groups + 1):
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


def facade_mast(name, pa, pb, z0, z1, metal):
    """One vertical hanging-truss mast: two chunky posts with upward
    pyramid (A-frame) cells stacked vertically — each cell's two diagonals
    run from the bottom corners up to the apex at the top centre — plus a
    rung at every cell joint."""
    cells = max(1, round((z1 - z0) / MAST_CELL_H))
    mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
    beam(f"{name}_MastPost_A", (*pa, z0), (*pa, z1), TRUSS_POST_W, metal)
    beam(f"{name}_MastPost_B", (*pb, z0), (*pb, z1), TRUSS_POST_W, metal)
    for i in range(cells + 1):
        z = z0 + (z1 - z0) * i / cells
        beam(f"{name}_MastRung_{i}", (*pa, z), (*pb, z),
             TRUSS_DIAG_W, metal)
    for i in range(cells):
        za = z0 + (z1 - z0) * i / cells
        zb = z0 + (z1 - z0) * (i + 1) / cells
        beam(f"{name}_MastDiag_{i}_L", (pa[0], pa[1], za),
             (mid[0], mid[1], zb), TRUSS_DIAG_W, metal)
        beam(f"{name}_MastDiag_{i}_R", (pb[0], pb[1], za),
             (mid[0], mid[1], zb), TRUSS_DIAG_W, metal)


def facade_masts(name, points, metal, bands):
    """Hanging-truss masts on the volume's east and west faces, at the
    published section's positions, recessed at TRUSS_INSET within the
    envelope like the truss bands. Each mast is a vertical extension of
    the main trusses: exactly one chevron bay wide, snapped to the face's
    chevron grid so its posts continue the belt bands' posts. The masts
    stop at the exposed truss bands they meet (the band chords carry them
    across), so no mast members clutter the bands."""
    quad = inset_points(points, TRUSS_INSET)
    gaps = [(z0, z1) for z0, z1, exposed in bands if exposed]
    for side, edge in (("E", 1), ("W", 3)):
        a = Vector(quad[edge])
        b = Vector(quad[(edge + 1) % 4])
        groups = max(1, round((b - a).length / TRUSS_SPACING))
        for index, (_, y, z0, z1) in enumerate(
                m for m in FACADE_MASTS if m[0] == name):
            t = min(max((y - a.y) / (b.y - a.y), 0.0), 1.0)
            bay = min(int(t * groups), groups - 1)
            pa = a.lerp(b, bay / groups)
            pb = a.lerp(b, (bay + 1) / groups)
            segments = [(z0, z1)]
            for gap_z0, gap_z1 in gaps:
                segments = [part for s0, s1 in segments for part in
                            ((s0, min(s1, gap_z0)), (max(s0, gap_z1), s1))
                            if part[1] - part[0] > 0.05]
            for segment, (s0, s1) in enumerate(segments):
                facade_mast(f"{name}_Mast_{side}_{index}_{segment}",
                            pa, pb, s0, s1, metal)


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


def mass_bands(name, height):
    """Truss bands carried by one volume, as (z0, z1, exposed) triples:
    the 1.5-storey belt bands wrap every volume tall enough and stay
    behind the continuous curtain wall, while each one-storey staggered
    mid-office truss wraps only its own volume and stands exposed — the
    glass splits around it."""
    bands = [(top - TRUSS_BAND_H, top, False)
             for top in TRUSS_BAND_TOPS if top <= height]
    bands += [(top - TRUSS_BAND_H_PARTIAL, top, True)
              for top in TRUSS_BAND_TOPS_PARTIAL.get(name, ())
              if top <= height]
    return sorted(bands)


def glass_spans(height, openings):
    """Glass spans, splitting the curtain wall only around the exposed
    truss zones; the wrapped belt bands keep their glazing."""
    spans = []
    z = 0.0
    for z0, z1 in openings:
        if z0 > z:
            spans.append((z, z0))
        z = z1
    if z < height:
        spans.append((z, height))
    return spans


def build_mass(name, height, points, glass, metal, truss, stone,
               blockout):
    if blockout:
        body = prism(f"{name}_Body", points, 0.0, height, stone)
        body["tier"] = name
        body["height_m"] = height
        return body
    bands = mass_bands(name, height)
    # The curtain wall runs continuously past the belt bands (each band
    # is a hollow ring of chevron trusses on the four faces, recessed
    # behind the glass and reading through it) and splits only around the
    # exposed staggered mid-office trusses.
    exposed = [(z0, z1) for z0, z1, exp in bands if exp]
    body = None
    for index, (z0, z1) in enumerate(glass_spans(height, exposed)):
        body = prism(f"{name}_Glass_{index}", points, z0, z1, glass)
        facade_grid(f"{name}_{index}", points, z0, z1, metal)
    for index, (z0, z1, _) in enumerate(bands):
        for edge in range(4):
            truss_face(f"{name}_{index}", points, edge, z0, z1, truss)
    facade_masts(name, points, truss, bands)
    body["tier"] = name
    body["height_m"] = height
    body["plan_shape"] = "quadrilateral"
    body["truss_bands"] = len(bands)
    return body


def ring_beams(name, points, levels, width, material):
    for level, z in enumerate(levels):
        for edge in range(4):
            beam(f"{name}_Ring_{level}_{edge}", (*points[edge], z),
                 (*points[(edge + 1) % 4], z), width, material)


def build_core(name, height, points, concrete, steel):
    """Linked-void service core for one volume: corner service zones in the
    lower zone, a braced steel spine with west eco-void and east lift banks
    in the middle zone, and an atrium frame in the upper zone (high volume
    only). Transfer ties connect the zones at the boundaries."""
    cx, cy = plan_centre(points)
    z0, z1 = CORE_ZONE_LOW
    corners = quad_inset(points, CORNER_ZONE_MARGIN)
    for i, (x, y) in enumerate(corners):
        prism(f"{name}_Core_Corner_{i}",
              rect_points(x, y, CORNER_ZONE_SIZE, CORNER_ZONE_SIZE),
              z0, z1, concrete)
    if height < CORE_ZONE_MID[1]:
        return
    z0, z1 = CORE_ZONE_MID
    spine = rect_points(cx, cy, CORE_SPINE_W, CORE_SPINE_D)
    prism(f"{name}_Core_Spine", spine, z0, z1, steel)
    # X-bracing on the south/north spine faces, per bay and tier, standing
    # just proud of the wall so the bracing reads on the surface.
    for face, sy in (("S", -1.0), ("N", 1.0)):
        y = cy + sy * (CORE_SPINE_D / 2 + BRACE_W / 2 + 0.03)
        for tier in range(BRACE_TIERS):
            za = z0 + (z1 - z0) * tier / BRACE_TIERS
            zb = z0 + (z1 - z0) * (tier + 1) / BRACE_TIERS
            for bay in range(BRACE_BAYS):
                xa = cx - CORE_SPINE_W / 2 + CORE_SPINE_W * bay / BRACE_BAYS
                xb = xa + CORE_SPINE_W / BRACE_BAYS
                beam(f"{name}_Core_Brace_{face}_{tier}_{bay}_A",
                     (xa, y, za), (xb, y, zb), BRACE_W, steel)
                beam(f"{name}_Core_Brace_{face}_{tier}_{bay}_B",
                     (xa, y, zb), (xb, y, za), BRACE_W, steel)
    # West eco-void: an open strip outlined by slim columns and ring beams,
    # standing just clear of the spine's west face.
    void = rect_points(cx - CORE_SPINE_W / 2 - CORE_VOID_GAP
                       - CORE_VOID_W / 2, cy, CORE_VOID_W, CORE_SPINE_D)
    for i, (x, y) in enumerate(void):
        prism(f"{name}_Core_Void_Col_{i}", rect_points(x, y, 0.8, 0.8),
              z0, z1, steel)
    ring_beams(f"{name}_Core_Void", void, (z0, z1), 0.5, steel)
    # East lift banks: individual shafts in a row along X.
    x = cx + CORE_SPINE_W / 2 + CORE_LIFT_OFFSET
    for k in range(CORE_LIFTS):
        prism(f"{name}_Core_Lift_{k}",
              rect_points(x + CORE_LIFT_W / 2, cy, CORE_LIFT_W, CORE_LIFT_D),
              z0, z1, concrete)
        x += CORE_LIFT_W + CORE_LIFT_GAP
    # Transfer ties at z 80 m: corner service zones to the spine base.
    for i, (x, y) in enumerate(corners):
        tx = cx + math.copysign(CORE_SPINE_W / 2, x - cx)
        ty = cy + math.copysign(CORE_SPINE_D / 2, y - cy)
        beam(f"{name}_Core_Link_{i}", (x, y, z0), (tx, ty, z0), 0.6,
             concrete)
    if height < CORE_ZONE_TOP[1]:
        return
    z0, z1 = CORE_ZONE_TOP
    # Slim service core continuing to the roof, east of the atrium and
    # stacking over the lift banks below.
    prism(f"{name}_Core_Upper",
          rect_points(cx + UPPER_CORE_DX, cy, UPPER_CORE_W, UPPER_CORE_D),
          z0, z1, concrete)
    atrium = rect_points(cx, cy, ATRIUM_W, ATRIUM_D)
    for i, (x, y) in enumerate(atrium):
        prism(f"{name}_Atrium_Col_{i}",
              rect_points(x, y, ATRIUM_COL, ATRIUM_COL), z0, z1, steel)
        # Transfer ties at z 195 m: spine top corners to the atrium columns.
        sx = cx + math.copysign(CORE_SPINE_W / 2, x - cx)
        sy = cy + math.copysign(CORE_SPINE_D / 2, y - cy)
        beam(f"{name}_Atrium_Link_{i}", (sx, sy, z0), (x, y, z0), 0.5,
             steel)
    ring_beams(f"{name}_Atrium", atrium, (z0, z1), 0.6, steel)
    # Vertical truss walls flanking the atrium void: the east and west
    # faces are X-braced from the middle-roof band up to the top band.
    ya, yb = cy - ATRIUM_D / 2, cy + ATRIUM_D / 2
    for face, sx in (("W", -1.0), ("E", 1.0)):
        x = cx + sx * ATRIUM_W / 2
        for tier in range(ATRIUM_BRACE_TIERS):
            za = z0 + (ATRIUM_BRACE_TOP - z0) * tier / ATRIUM_BRACE_TIERS
            zb = (z0 + (ATRIUM_BRACE_TOP - z0) * (tier + 1)
                  / ATRIUM_BRACE_TIERS)
            beam(f"{name}_Atrium_Brace_{face}_{tier}_A",
                 (x, ya, za), (x, yb, zb), BRACE_W, steel)
            beam(f"{name}_Atrium_Brace_{face}_{tier}_B",
                 (x, yb, za), (x, ya, zb), BRACE_W, steel)


def floor_levels(name, height):
    """One slab per storey up to the roof (top flush with the storey level),
    skipping levels strictly inside a truss band; the slab at a band's
    bottom level stays — the truss ring stands on that floor plate."""
    bands = mass_bands(name, height)
    levels = []
    for i in range(1, int(round(height / STOREY_H)) + 1):
        z = i * STOREY_H
        if all(z <= z0 + 0.05 or z - SLAB_T >= z1 + 0.05
               for z0, z1, _ in bands):
            levels.append(z)
    return levels


def core_openings(points, height, z):
    """Slab openings where the core passes: corner service zones in the
    lower zone, spine + eco-void + lift banks in the middle zone, and the
    atrium void in the upper zone. Openings grow 5 cm so slab edges never
    touch the core walls."""
    cx, cy = plan_centre(points)
    openings = []
    if z <= CORE_ZONE_LOW[1] + 0.01:
        for x, y in quad_inset(points, CORNER_ZONE_MARGIN):
            openings.append(rect_points(x, y, CORNER_ZONE_SIZE + OPENING_TOL,
                                        CORNER_ZONE_SIZE + OPENING_TOL))
    if height >= CORE_ZONE_MID[1] and \
            CORE_ZONE_MID[0] - 0.01 <= z <= CORE_ZONE_MID[1] + 0.01:
        openings.append(rect_points(cx, cy, CORE_SPINE_W + OPENING_TOL,
                                    CORE_SPINE_D + OPENING_TOL))
        openings.append(rect_points(
            cx - CORE_SPINE_W / 2 - CORE_VOID_GAP - CORE_VOID_W / 2, cy,
            CORE_VOID_W + OPENING_TOL, CORE_SPINE_D + OPENING_TOL))
        x = cx + CORE_SPINE_W / 2 + CORE_LIFT_OFFSET
        for _ in range(CORE_LIFTS):
            openings.append(rect_points(x + CORE_LIFT_W / 2, cy,
                                        CORE_LIFT_W + OPENING_TOL,
                                        CORE_LIFT_D + OPENING_TOL))
            x += CORE_LIFT_W + CORE_LIFT_GAP
    if height >= CORE_ZONE_TOP[1] and z > CORE_ZONE_TOP[0] + 0.01:
        openings.append(rect_points(cx, cy, ATRIUM_W + OPENING_TOL,
                                    ATRIUM_D + OPENING_TOL))
        openings.append(rect_points(cx + UPPER_CORE_DX, cy,
                                    UPPER_CORE_W + OPENING_TOL,
                                    UPPER_CORE_D + OPENING_TOL))
    return openings


def core_floor(name, outline, openings, z, material):
    """One floor slab: the inset plan quad with actual holes where the core
    passes, as a holed 2D curve extruded to slab thickness, top flush with
    the storey level."""
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "2D"
    curve.fill_mode = "BOTH"
    curve.extrude = SLAB_T / 2
    for loop in (outline, *openings):
        spline = curve.splines.new("POLY")
        spline.points.add(len(loop) - 1)
        for point, (x, y) in zip(spline.points, loop):
            point.co = (x, y, 0.0, 1.0)
        spline.use_cyclic_u = True
    obj = bpy.data.objects.new(name, curve)
    COLLECTION.objects.link(obj)
    obj.location.z = z - SLAB_T / 2
    curve.materials.append(material)
    return obj


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
        "core": camera("Harukas_Core_Camera", (225, -325, 185), (0, 5, 150), lens=40),
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
    parser.add_argument("--views", nargs="+",
                        default=["preview", "plan", "north", "core"])
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])

    bpy.ops.wm.read_factory_settings(use_empty=True)
    glass = make_glass(name="Harukas_Body_Glass", engine="BLENDER_EEVEE", tint=(0.78, 0.92, 0.98))
    metal = make_metal(name="Harukas_Schematic_Mullions")
    # The trusses are white-painted steel, per the reference photos.
    truss = make_wall(name="Harukas_Truss_White",
                      color=(0.92, 0.92, 0.90))
    stone = make_wall(name="Harukas_Blockout_Stone", color=(0.31, 0.37, 0.40))
    ground_mat = make_ground(name="Harukas_Ground")
    for name, height, points in MASSES:
        collection(name)
        build_mass(name, height, points, glass, metal, truss, stone,
                   args.blockout)
    if not args.blockout:
        concrete = make_concrete(name="Harukas_Core_Concrete")
        steel = make_metal(name="Harukas_Core_Steel", color=(0.30, 0.34, 0.38))
        collection("Core")
        for name, height, points in MASSES:
            build_core(name, height, points, concrete, steel)
        slab = make_concrete(name="Harukas_Floor_Slabs",
                             color=(0.58, 0.57, 0.54))
        collection("Floors")
        for name, height, points in MASSES:
            outline = quad_inset(points, SLAB_INSET)
            for z in floor_levels(name, height):
                core_floor(f"{name}_Floor_{int(round(z / STOREY_H)):02d}",
                           outline, core_openings(points, height, z), z, slab)
    cameras = setup_scene(args, ground_mat)
    frame_viewport(cameras["preview"].location, (0, 5, 135))
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "abeno_harukas.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    if not args.no_render:
        scene = bpy.context.scene
        for view in args.views:
            if view == "core" and args.blockout:
                continue
            scene.camera = cameras[view]
            scene.render.filepath = os.path.join(OUT_DIR, f"abeno_harukas_{view}.png")
            if view == "core":
                # Hide the facade and floor collections only for this
                # render; the saved full model keeps everything visible.
                facades = [bpy.data.collections[f"Harukas_{name}"]
                           for name, _, _ in MASSES]
                facades.append(bpy.data.collections["Harukas_Floors"])
                for item in facades:
                    item.hide_render = True
                bpy.ops.render.render(write_still=True)
                for item in facades:
                    item.hide_render = False
            else:
                bpy.ops.render.render(write_still=True)
    print(f"Built body-first Harukas model: {len(bpy.data.objects)} objects")
    print(f"Saved editable model: {path}")


if __name__ == "__main__":
    main()
