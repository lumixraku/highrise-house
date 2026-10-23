"""Verify the body-first Abeno Harukas massing model."""

import math
import os
import sys

import bpy
from mathutils import Vector

GROUND_Z = 0.0
MAX_STANDARD_TILT_DEG = 3.0
MIDDLE_SIDE_TILT_DEG = 5.0
TRUSS_BAND_H = 7.5
TRUSS_BAND_H_PARTIAL = 5.0
TRUSS_BAND_TOPS = (80.0, 195.0, 270.0)
TRUSS_BAND_TOPS_PARTIAL = {"Middle": (130.0,), "High": (160.0,)}
TRUSS_SPACING = 12.0
TRUSS_CHORD_W = 0.40
MULLION_SPACING = 1.25
SHORT_GLASS_FRACTION = 0.25
CURTAIN_GAP = 0.10
LIGHT_ROW_PITCH = 3.0
LIGHT_STRIP_W = 0.30
LIGHT_EDGE_CLEAR = 0.6
LIGHT_MIN_LEN = 1.5
MASSES = {
    "Low": (80.0, ((-42.5, -40.0), (42.7, -40.0),
                   (45.21, -14.75), (-44.87, -10.25))),
    "Middle": (195.0, ((-44.87, -10.25), (45.21, -14.75),
                        (42.3, 18.5), (-42.7, 14.5))),
    "High": (300.0, ((-42.7, 14.5), (42.3, 18.5),
                     (41.8, 46.0), (-43.5, 46.0))),
}
OUTLINE = ((-42.5, -40.0), (42.7, -40.0), (45.21, -14.75), (42.3, 18.5),
           (41.8, 46.0), (-43.5, 46.0), (-42.7, 14.5), (-44.87, -10.25))
# Linked-void service core (mirrors build_abeno_harukas.py).
CORE_ZONE_MID = (80.0, 195.0)
CORE_ZONE_TOP = (195.0, 300.0)
CORNER_ZONE_SIZE = 8.0
CORNER_ZONE_MARGIN = CORNER_ZONE_SIZE / 2 + 1.0
CORE_SPINE_W = 20.0
CORE_SPINE_D = 12.0
CORE_VOID_W = 12.0
CORE_VOID_GAP = 0.6
CORE_LIFTS = 3
CORE_LIFT_W = 3.6
CORE_LIFT_D = 7.0
CORE_LIFT_GAP = 0.8
CORE_LIFT_OFFSET = 1.0
BRACE_TIERS = 4
BRACE_BAYS = 2
ATRIUM_W = 26.0
ATRIUM_D = 15.0
ATRIUM_BRACE_TOP = 262.5
ATRIUM_BRACE_TIERS = 9
MAST_CELL_H = 10.0
# Facade hanging-truss masts (volume, face, y centre, z0, z1), mirrored
# from the builder; one strip on the wider three-group side face at each
# side: the middle volume's east face and the high volume's west face.
FACADE_MASTS = (
    ("Middle", "E", 11.0, 80.0, 187.5),
    ("High", "W", 20.0, 80.0, 187.5),
)
UPPER_CORE_W = 8.0
UPPER_CORE_D = 12.0
UPPER_CORE_DX = ATRIUM_W / 2 + 1.0 + UPPER_CORE_W / 2
STOREY_H = 5.0
SLAB_T = 0.3
SLAB_INSET = 0.3
OPENING_TOL = 0.1


def world_points(obj):
    if obj.type != "MESH":
        # Floor slabs are holed 2D curves: evaluate to mesh first.
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        points = [obj.matrix_world @ vertex.co for vertex in mesh.vertices]
        evaluated.to_mesh_clear()
        return points
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def ring_xy(obj, z):
    return [(round(point.x, 3), round(point.y, 3))
            for point in world_points(obj) if abs(point.z - z) < 0.01]


def edge_tilt_deg(a, b):
    """Tilt of a plan edge from its dominant axis: long edges run along X,
    side edges run along Y."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    if abs(dx) >= abs(dy):
        return math.degrees(math.atan2(abs(dy), abs(dx)))
    return math.degrees(math.atan2(abs(dx), abs(dy)))


def face_groups(a, b):
    width = math.hypot(b[0] - a[0], b[1] - a[1])
    return max(1, round(width / TRUSS_SPACING))


def mass_bands(name, height):
    bands = [(top - TRUSS_BAND_H, top, False)
             for top in TRUSS_BAND_TOPS if top <= height]
    bands += [(top - TRUSS_BAND_H_PARTIAL, top, True)
              for top in TRUSS_BAND_TOPS_PARTIAL.get(name, ())
              if top <= height]
    return sorted(bands)


def plan_centre(points):
    return (sum(x for x, _ in points) / 4, sum(y for _, y in points) / 4)


def rect_points(cx, cy, w, d):
    return ((cx - w / 2, cy - d / 2), (cx + w / 2, cy - d / 2),
            (cx + w / 2, cy + d / 2), (cx - w / 2, cy + d / 2))


def quad_inset(points, margin):
    """Inward offset of a convex plan quad (mirrors the builder)."""
    centre = plan_centre(points)
    lines = []
    for i in range(4):
        a, b = points[i], points[(i + 1) % 4]
        nx, ny = -(b[1] - a[1]), b[0] - a[0]
        scale = math.hypot(nx, ny)
        nx, ny = nx / scale, ny / scale
        if nx * (centre[0] - a[0]) + ny * (centre[1] - a[1]) < 0:
            nx, ny = -nx, -ny
        lines.append((a[0] + nx * margin, a[1] + ny * margin, nx, ny))
    inset = []
    for i in range(4):
        x0, y0, n0x, n0y = lines[i]
        x1, y1, n1x, n1y = lines[(i + 1) % 4]
        det = n0x * n1y - n1x * n0y
        c0 = n0x * x0 + n0y * y0
        c1 = n1x * x1 + n1y * y1
        inset.append(((c0 * n1y - c1 * n0y) / det,
                      (n0x * c1 - n1x * c0) / det))
    return tuple(inset)


def inside_quad(points, p, margin):
    """True when p sits at least ``margin`` inside every edge of the quad."""
    centre = plan_centre(points)
    for i in range(4):
        a, b = points[i], points[(i + 1) % 4]
        nx, ny = -(b[1] - a[1]), b[0] - a[0]
        scale = math.hypot(nx, ny)
        nx, ny = nx / scale, ny / scale
        if nx * (centre[0] - a[0]) + ny * (centre[1] - a[1]) < 0:
            nx, ny = -nx, -ny
        if (p[0] - a[0]) * nx + (p[1] - a[1]) * ny < margin:
            return False
    return True


def quad_edge_distance(points, p):
    """Planar distance from p to the nearest edge of a plan quad."""
    best = float("inf")
    q = Vector((p.x, p.y, 0.0))
    for i in range(4):
        a = Vector((*points[i], 0.0))
        ab = Vector((*points[(i + 1) % 4], 0.0)) - a
        t = max(0.0, min(1.0, (q - a).dot(ab) / ab.length_squared))
        best = min(best, (q - (a + ab * t)).length)
    return best


def expected_curtain_panes(name, height, points):
    """Mirror of the builder: modules per face times floored storeys."""
    modules = sum(
        max(1, round(math.hypot(points[(edge + 1) % 4][0] - points[edge][0],
                                points[(edge + 1) % 4][1] - points[edge][1])
                     / MULLION_SPACING))
        for edge in range(4))
    return len(floor_levels(name, height)) * modules


def inside_core_opening(p):
    """True when a point falls inside any modelled core slab opening."""
    for height, points in MASSES.values():
        for rect in core_openings(points, height, p.z):
            if inside_quad(rect, (p.x, p.y), 0.0):
                return True
    return False


def line_span_in_quad(points, y):
    """Mirror of the builder: horizontal span of a quad at y."""
    xs = []
    for i in range(4):
        a, b = points[i], points[(i + 1) % 4]
        if (a[1] - y) * (b[1] - y) <= 0 and abs(a[1] - b[1]) > 1e-9:
            t = (y - a[1]) / (b[1] - a[1])
            xs.append(a[0] + t * (b[0] - a[0]))
    return (min(xs), max(xs)) if len(xs) >= 2 else None


def subtract_intervals(span, blocks):
    segments = [span]
    for b0, b1 in blocks:
        updated = []
        for s0, s1 in segments:
            if b1 <= s0 or b0 >= s1:
                updated.append((s0, s1))
                continue
            if b0 > s0:
                updated.append((s0, b0))
            if b1 < s1:
                updated.append((b1, s1))
        segments = updated
    return segments


def expected_light_strips(name, height, points):
    """Mirror of the builder: one strip per free row segment per storey."""
    ys = [point[1] for point in points]
    rows = []
    y = min(ys) + LIGHT_EDGE_CLEAR
    while y <= max(ys) - LIGHT_EDGE_CLEAR:
        rows.append(y)
        y += LIGHT_ROW_PITCH
    total = 0
    for top in floor_levels(name, height):
        z = top - 0.3 - 0.05
        openings = core_openings(points, height, z)
        for y in rows:
            span = line_span_in_quad(points, y)
            if span is None:
                continue
            x0, x1 = span[0] + LIGHT_EDGE_CLEAR, span[1] - LIGHT_EDGE_CLEAR
            blocks = []
            for rect in openings:
                ry = [point[1] for point in rect]
                if min(ry) - LIGHT_STRIP_W / 2 <= y \
                        <= max(ry) + LIGHT_STRIP_W / 2:
                    rx = [point[0] for point in rect]
                    blocks.append((min(rx) - LIGHT_EDGE_CLEAR,
                                   max(rx) + LIGHT_EDGE_CLEAR))
            total += sum(1 for s0, s1 in subtract_intervals((x0, x1), blocks)
                         if s1 - s0 >= LIGHT_MIN_LEN)
    return total


def z_range(obj):
    zs = [p.z for p in world_points(obj)]
    return min(zs), max(zs)


def beam_touches(obj, e0, e1, tol=0.5):
    pts = world_points(obj)
    return (min((p - Vector(e0)).length for p in pts) <= tol and
            min((p - Vector(e1)).length for p in pts) <= tol)


def floor_levels(name, height):
    """Mirror of the builder: one slab per storey, clear of truss bands."""
    levels = []
    for i in range(1, int(round(height / STOREY_H)) + 1):
        z = i * STOREY_H
        if all(z <= z0 + 0.05 or z - SLAB_T >= z1 + 0.05
               for z0, z1, _ in mass_bands(name, height)):
            levels.append(z)
    return levels


def core_openings(points, height, z):
    """Mirror of the builder: slab openings where the core passes."""
    cx, cy = plan_centre(points)
    openings = []
    if z <= 80.0 + 0.01:
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


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    path = argv[0] if argv else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "out", "abeno_harukas.blend")
    bpy.ops.wm.open_mainfile(filepath=path)
    scene = bpy.context.scene
    objects = {obj.name: obj for obj in bpy.data.objects}
    checks = []
    checks.append(("documented height", scene.get("source_height_m") == 300.0))
    checks.append(("three mass bodies", all(
        f"{name}_Glass_0" in objects for name in MASSES)))

    rings = {}
    for name, (height, points) in MASSES.items():
        glass = [obj for obj in objects.values()
                 if obj.name.startswith(f"{name}_Glass_")]
        glass_top = max((max(p.z for p in world_points(obj)) for obj in glass),
                        default=0.0)
        top_glass = next((obj for obj in glass
                          if abs(max(p.z for p in world_points(obj)) - glass_top)
                          < 0.01), None)
        ring = ring_xy(top_glass, glass_top) if top_glass else []
        rings[name] = ring
        checks.append((f"{name} plan corners",
                       ring == [tuple(point) for point in points]))
        # The flat roofline is carried either by the glass (exact) or by
        # the top truss chords — square-section beams centred on the band
        # top, overshooting the roofline by half the chord width.
        chord_tops = [max(p.z for p in world_points(obj))
                      for obj in objects.values()
                      if obj.name.startswith(f"{name}_")
                      and "TrussChordTop" in obj.name]
        mass_top = max([glass_top] + chord_tops)
        checks.append((f"{name} flat roofline at {height:.0f} m",
                       height - 0.01 <= mass_top
                       <= height + TRUSS_CHORD_W / 2 + 0.01
                       and len(ring) == 4))
        bands = mass_bands(name, height)
        spans = sorted((min(p.z for p in world_points(obj)),
                        max(p.z for p in world_points(obj)))
                       for obj in glass)
        checks.append((f"{name} curtain wall wraps the belt bands and "
                       "exposes the staggered trusses",
                       all(any(sz0 <= z0 + 0.01 and sz1 >= z1 - 0.01
                               for sz0, sz1 in spans)
                           for z0, z1, exp in bands if not exp) and
                       all(all(sz1 <= z0 + 0.01 or sz0 >= z1 - 0.01
                               for sz0, sz1 in spans)
                           for z0, z1, exp in bands if exp)))
        groups = [face_groups(points[edge], points[(edge + 1) % 4])
                  for edge in range(4)]
        plan_max_x = max(abs(x) for x, _ in points)
        for index, (z0, z1, _exp) in enumerate(bands):
            diags = [obj for obj in objects.values()
                     if obj.name.startswith(f"{name}_{index}_TrussDiag_")]
            posts = [obj for obj in objects.values()
                     if obj.name.startswith(f"{name}_{index}_TrussPost_")]
            checks.append((f"{name} band {index} z {z0:.0f}-{z1:.0f} hollow, "
                           "no solid backing or interior web forest",
                           objects.get(f"{name}_Truss_Backing_{index}")
                           is None and
                           not any(obj.name.startswith(
                               f"{name}_{index}_TrussWeb_")
                               for obj in objects.values())))
            checks.append((f"{name} band {index} density follows face width",
                           len(diags) == 2 * sum(groups) and
                           len(posts) == sum(groups)))
            diag_zs = [p.z for obj in diags for p in world_points(obj)]
            checks.append((f"{name} band {index} truss spans its zone",
                           abs(min(diag_zs) - z0) < 0.5 and
                           abs(max(diag_zs) - z1) < 0.5))
            truss_max_x = max(abs(p.x) for obj in diags
                              for p in world_points(obj))
            checks.append((f"{name} band {index} recessed inside the glass line",
                           truss_max_x < plan_max_x))
        base_diags = [obj for obj in objects.values()
                      if obj.name.startswith(f"{name}_0_TrussDiag_")]
        checks.append((f"{name} glass stands on the ground",
                       glass and abs(min(p.z for obj in glass
                                         for p in world_points(obj))) < 0.01))
        checks.append((f"{name} chevron groups follow the fixed span",
                       all(group == max(1, round(math.hypot(
                           points[(edge + 1) % 4][0] - points[edge][0],
                           points[(edge + 1) % 4][1] - points[edge][1])
                           / TRUSS_SPACING))
                           for edge, group in enumerate(groups))
                       and bool(base_diags)))
        tilts = [edge_tilt_deg(ring[i], ring[(i + 1) % 4])
                 for i in range(4)] if len(ring) == 4 else [90.0]
        if name == "Middle":
            checks.append(("Middle side edges flare outward at 5 degrees",
                           all(abs(tilts[index] - MIDDLE_SIDE_TILT_DEG) < 0.05
                               for index in (1, 3))))
            checks.append(("Middle connecting edges retain shallow plan tilt",
                           tilts[0] <= MAX_STANDARD_TILT_DEG + 0.05 and
                           tilts[2] <= MAX_STANDARD_TILT_DEG + 0.05))
        elif name == "High":
            checks.append((f"{name} plan tilts within "
                           f"{MAX_STANDARD_TILT_DEG:.0f} degrees",
                           all(tilt <= MAX_STANDARD_TILT_DEG + 0.05
                               for tilt in tilts)))

    # The roof belt bands run through every volume tall enough; the two
    # staggered mid-office trusses each wrap a single volume.
    def has_band(name, z0, z1):
        return any(z0 == b0 and z1 == b1
                   for b0, b1, _ in mass_bands(name, MASSES[name][0]))
    checks.append(("low-top band runs through low and middle volumes",
                   has_band("Low", 72.5, 80.0) and
                   has_band("Middle", 72.5, 80.0)))
    checks.append(("middle-top band runs through middle and high volumes",
                   has_band("Middle", 187.5, 195.0) and
                   has_band("High", 187.5, 195.0)))
    checks.append(("staggered mid-office trusses each wrap one volume",
                   has_band("Middle", 125.0, 130.0) and
                   not has_band("High", 125.0, 130.0) and
                   has_band("High", 155.0, 160.0) and
                   not has_band("Middle", 155.0, 160.0) and
                   not has_band("Low", 125.0, 130.0) and
                   not has_band("Low", 155.0, 160.0)))
    checks.append(("top band wraps the high volume just below the crown",
                   has_band("High", 262.5, 270.0) and
                   not has_band("Middle", 262.5, 270.0) and
                   not has_band("Low", 262.5, 270.0)))
    # Hanging-truss masts on the wide three-group side faces, band to band.
    for name, (height, points) in MASSES.items():
        for index, (_, side, y, z0, z1) in enumerate(
                m for m in FACADE_MASTS if m[0] == name):
            gaps = [(b0, b1) for b0, b1, exp in mass_bands(name, height)
                    if exp]
            segments = [(z0, z1)]
            for gap_z0, gap_z1 in gaps:
                segments = [part for s0, s1 in segments for part in
                            ((s0, min(s1, gap_z0)), (max(s0, gap_z1), s1))
                            if part[1] - part[0] > 0.05]
            expected = sum(3 * max(1, round((s1 - s0) / MAST_CELL_H)) + 3
                           for s0, s1 in segments)
            members = [obj for obj in objects.values()
                       if obj.name.startswith(
                           f"{name}_Mast_{side}_{index}_")]
            member_zs = [p.z for obj in members
                         for p in world_points(obj)]
            checks.append((f"{name} {side} mast {index} "
                           f"z {z0:.0f}-{z1:.0f} member count",
                           len(members) == expected and
                           abs(min(member_zs) - z0) < 0.5 and
                           abs(max(member_zs) - z1) < 0.5))
            checks.append((f"{name} {side} mast {index} stays inside "
                           "the glass line",
                           all(inside_quad(points, (p.x, p.y), 0.0)
                               for obj in members
                               for p in world_points(obj))))
    checks.append(("masts only on the wide three-group side faces",
                   not any(obj.name.startswith(("Middle_Mast_W_",
                                                "High_Mast_E_",
                                                "Low_Mast_"))
                           for obj in objects.values())))
    all_truss = [obj for obj in objects.values() if "_TrussDiag_" in obj.name]
    truss_min_z = min(p.z for obj in all_truss for p in world_points(obj))
    checks.append(("no truss band at the ground level", truss_min_z > 60.0))
    checks.append(("belt bands 1.5x the one-storey staggered trusses",
                   all(abs(z1 - z0 - (TRUSS_BAND_H_PARTIAL if exp
                                      else TRUSS_BAND_H)) < 0.01
                       for name, (height, _) in MASSES.items()
                       for z0, z1, exp in mass_bands(name, height))))

    low, middle, high = rings["Low"], rings["Middle"], rings["High"]
    checks.append(("low and middle share their connecting edge",
                   set(low[2:]) == set(middle[:2])))
    checks.append(("middle and high share their connecting edge",
                   set(middle[2:]) == set(high[:2])))
    plans = {tuple(sorted(ring)) for ring in rings.values()}
    checks.append(("three different plans", len(plans) == 3))

    # The long connecting edges tilt along the north-south axis.
    low_divide = low[2][1] - low[3][1]
    middle_divide = middle[2][1] - middle[3][1]
    checks.append(("connecting edges are slanted in plan",
                   abs(low_divide) > 1.0 and abs(middle_divide) > 1.0))
    checks.append(("the two connecting edges slant opposite ways",
                   low_divide * middle_divide < 0.0))
    checks.append(("outer short edges stay straight east-west",
                   abs(low[1][1] - low[0][1]) < 0.01 and
                   abs(high[2][1] - high[3][1]) < 0.01))

    max_x = {name: max(x for x, _ in ring) for name, ring in rings.items()}
    checks.append(("middle east side extends outward",
                   (45.21, -14.75) in set(middle) and
                   middle[1][0] > middle[2][0] and
                   high[2][0] < high[1][0] and
                   max_x["Middle"] == max(x for x, _ in OUTLINE)))
    all_y = [y for ring in rings.values() for _, y in ring]
    checks.append(("overall depth stays 86 m",
                   abs(max(all_y) - min(all_y) - 86.0) < 0.01))
    checks.append(("middle widest at its low-side face",
                   (middle[1][0] - middle[0][0]) >
                   (middle[2][0] - middle[3][0])))
    middle_west_mean = (middle[0][0] + middle[3][0]) / 2.0
    high_west_mean = (high[0][0] + high[3][0]) / 2.0
    checks.append(("middle west side stays near the high volume",
                   abs(middle_west_mean - high_west_mean) < 2.0))

    ground = objects.get("Ground_Tower_Footprint")
    checks.append(("ground matches the union of the three plans",
                   ground is not None and
                   set(ring_xy(ground, GROUND_Z)) == set(OUTLINE)))

    # Interior roller blinds: one panel per glass module per floored
    # storey, in three balanced states, hung just inside the facade.
    curtains = objects.get("Harukas_Curtains")
    expected_panes = sum(expected_curtain_panes(name, height, points)
                         for name, (height, points) in MASSES.items())
    checks.append(("a curtain pane for every glass module and floored storey",
                   curtains is not None and expected_panes > 0 and
                   curtains.get("total_panes") == expected_panes))
    checks.append(("three curtain states, all present and balanced",
                   curtains is not None and
                   curtains.get("rolled_up") > 0 and
                   curtains.get("half_down") > 0 and
                   curtains.get("fully_down") > 0 and
                   curtains.get("rolled_up") + curtains.get("half_down")
                   + curtains.get("fully_down") == expected_panes and
                   curtains.get("visible_panels") ==
                   curtains.get("half_down") + curtains.get("fully_down") and
                   max(curtains.get("rolled_up"),
                       curtains.get("half_down"),
                       curtains.get("fully_down"))
                   - min(curtains.get("rolled_up"),
                         curtains.get("half_down"),
                         curtains.get("fully_down")) <= 1))
    curtain_points = world_points(curtains) if curtains else []
    gaps = [min(quad_edge_distance(points, p)
                for _, points in MASSES.values()) for p in curtain_points]
    checks.append(("curtain panels hang just inside the facade (5-12 cm)",
                   bool(gaps) and min(gaps) >= 0.05 and
                   max(gaps) <= 0.12 and
                   all(0.0 < p.z <= 300.0 for p in curtain_points)))
    checks.append(("curtains use the frosted roller-blind material",
                   curtains is not None and bool(curtains.data.materials) and
                   "Frosted" in curtains.data.materials[0].name))

    # Ceiling strip lights: concentric rings of long fixtures around the
    # core on every floor, in a seeded lit/off mix.
    light_states = ("daylight", "warm", "off")
    light_objs = {state: objects.get(
        f"Harukas_Ceiling_Lights_{state.capitalize()}") for state in light_states}
    expected_strips = sum(expected_light_strips(name, height, points)
                          for name, (height, points) in MASSES.items())
    actual_strips = sum(obj.get("strip_count", 0)
                        for obj in light_objs.values() if obj)
    checks.append(("ceiling strip lights ring the core on every floor",
                   expected_strips > 0 and
                   all(light_objs[state] is not None for state in light_states)
                   and actual_strips == expected_strips))
    checks.append(("some ceiling lights are lit and some are off",
                   all(light_objs[state] is not None for state in light_states)
                   and light_objs["off"].get("strip_count") > 0 and
                   light_objs["daylight"].get("strip_count") > 0 and
                   light_objs["warm"].get("strip_count") > 0 and
                   light_objs["daylight"].get("strip_count")
                   + light_objs["warm"].get("strip_count")
                   < actual_strips))
    light_points = [p for obj in light_objs.values() if obj
                    for p in world_points(obj)]
    checks.append(("ceiling lights stay inside the plan and clear of the core",
                   bool(light_points) and
                   all(any(inside_quad(points, (p.x, p.y), 0.05)
                           for _, points in MASSES.values())
                       for p in light_points) and
                   not any(inside_core_opening(p) for p in light_points)))

    checks.append(("review cameras", all(
        name in objects for name in ("Harukas_Preview_Camera",
                                     "Harukas_Plan_Camera",
                                     "Harukas_North_Camera",
                                     "Harukas_Core_Camera"))))
    checks.append(("all cameras stay outside the building",
                   all(objects[name].location.y < -50.0 or
                       objects[name].location.y > 100.0 or
                       objects[name].location.z > 400.0
                       for name in ("Harukas_Preview_Camera",
                                    "Harukas_Plan_Camera",
                                    "Harukas_North_Camera",
                                    "Harukas_Core_Camera"))))

    # Linked-void service core: four lower corner service zones, a braced
    # steel middle core with west eco-voids and east lift banks, and an
    # upper atrium frame; transfer ties at the zone boundaries.
    for name, (height, points) in MASSES.items():
        cx, cy = plan_centre(points)
        corners = quad_inset(points, CORNER_ZONE_MARGIN)
        core_objs = [obj for obj in objects.values()
                     if obj.name.startswith((f"{name}_Core_",
                                             f"{name}_Atrium_"))]
        checks.append((f"{name} core clears the facade by 0.5 m",
                       bool(core_objs) and
                       all(inside_quad(points, (p.x, p.y), 0.5)
                           for obj in core_objs
                           for p in world_points(obj))))
        zones = [objects.get(f"{name}_Core_Corner_{i}") for i in range(4)]
        checks.append((f"{name} four lower corner service zones z 0-80",
                       all(zone is not None and
                           abs(z_range(zone)[0]) < 0.01 and
                           abs(z_range(zone)[1] - 80.0) < 0.01
                           for zone in zones)))
        checks.append((f"{name} corner zones sit on the inset plan corners",
                       all(zone is not None and
                           sorted(ring_xy(zone, 80.0)) ==
                           sorted((round(px, 3), round(py, 3))
                                  for px, py in rect_points(
                                      corners[i][0], corners[i][1],
                                      CORNER_ZONE_SIZE, CORNER_ZONE_SIZE))
                           for i, zone in enumerate(zones))))
        spine = objects.get(f"{name}_Core_Spine")
        if height < CORE_ZONE_MID[1]:
            checks.append((f"{name} no middle core above its roof",
                           spine is None and
                           objects.get(f"{name}_Core_Upper") is None and
                           not any(obj.name.startswith(f"{name}_Atrium_")
                                   for obj in core_objs)))
            continue
        checks.append((f"{name} braced steel spine z 80-195",
                       spine is not None and
                       abs(z_range(spine)[0] - 80.0) < 0.01 and
                       abs(z_range(spine)[1] - 195.0) < 0.01))
        braces = [obj for obj in core_objs
                  if obj.name.startswith(f"{name}_Core_Brace_")]
        checks.append((f"{name} spine X-bracing covers both faces",
                       len(braces) == 4 * BRACE_TIERS * BRACE_BAYS))
        void_cols = [obj for obj in core_objs
                     if obj.name.startswith(f"{name}_Core_Void_Col_")]
        checks.append((f"{name} west eco-void outlined by four columns",
                       len(void_cols) == 4 and all(
                           abs(z_range(col)[0] - 80.0) < 0.01 and
                           abs(z_range(col)[1] - 195.0) < 0.01
                           for col in void_cols)))
        lifts = [objects.get(f"{name}_Core_Lift_{k}")
                 for k in range(CORE_LIFTS)]
        checks.append((f"{name} east lift banks z 80-195",
                       all(lift is not None and
                           abs(z_range(lift)[0] - 80.0) < 0.01 and
                           abs(z_range(lift)[1] - 195.0) < 0.01
                           for lift in lifts)))
        checks.append((f"{name} lift banks east of spine, eco-void west",
                       all(lift is not None and
                           min(p.x for p in world_points(lift)) >
                           cx + CORE_SPINE_W / 2 for lift in lifts) and
                       all(max(p.x for p in world_points(col)) <=
                           cx - CORE_SPINE_W / 2 + 0.01
                           for col in void_cols)))
        for i, (x, y) in enumerate(corners):
            link = objects.get(f"{name}_Core_Link_{i}")
            tx = cx + math.copysign(CORE_SPINE_W / 2, x - cx)
            ty = cy + math.copysign(CORE_SPINE_D / 2, y - cy)
            checks.append((f"{name} z 80 transfer tie {i} endpoints",
                           link is not None and
                           beam_touches(link, (x, y, 80.0),
                                        (tx, ty, 80.0))))
        cols = [objects.get(f"{name}_Atrium_Col_{i}") for i in range(4)]
        upper = objects.get(f"{name}_Core_Upper")
        if height < CORE_ZONE_TOP[1]:
            checks.append((f"{name} no atrium frame below the crown zone",
                           not any(col is not None for col in cols) and
                           upper is None))
            continue
        lift_row_east = (cx + CORE_SPINE_W / 2 + CORE_LIFT_OFFSET
                         + 3 * CORE_LIFT_W + 2 * CORE_LIFT_GAP)
        checks.append((f"{name} upper service core z 195-300",
                       upper is not None and
                       abs(z_range(upper)[0] - 195.0) < 0.01 and
                       abs(z_range(upper)[1] - 300.0) < 0.01))
        checks.append((f"{name} upper service core east of the atrium",
                       upper is not None and
                       min(p.x for p in world_points(upper)) >
                       cx + ATRIUM_W / 2))
        checks.append((f"{name} upper service core stacks over lift banks",
                       upper is not None and
                       min(p.x for p in world_points(upper)) >=
                       cx + CORE_SPINE_W / 2 + CORE_LIFT_OFFSET - 0.01 and
                       max(p.x for p in world_points(upper)) <=
                       lift_row_east + 0.01))
        checks.append((f"{name} upper atrium frame columns z 195-300",
                       all(col is not None and
                           abs(z_range(col)[0] - 195.0) < 0.01 and
                           abs(z_range(col)[1] - 300.0) < 0.01
                           for col in cols)))
        rings = [obj for obj in core_objs
                 if obj.name.startswith(f"{name}_Atrium_Ring_")]
        checks.append((f"{name} atrium ring beams at base and crown",
                       len(rings) == 8))
        braces = [obj for obj in core_objs
                  if obj.name.startswith(f"{name}_Atrium_Brace_")]
        brace_zs = [p.z for obj in braces for p in world_points(obj)]
        checks.append((f"{name} atrium flank walls braced up to the top band",
                       len(braces) == 4 * ATRIUM_BRACE_TIERS and
                       abs(min(brace_zs) - CORE_ZONE_TOP[0]) < 0.5 and
                       abs(max(brace_zs) - ATRIUM_BRACE_TOP) < 0.5))
        atrium = rect_points(cx, cy, ATRIUM_W, ATRIUM_D)
        for i, (x, y) in enumerate(atrium):
            link = objects.get(f"{name}_Atrium_Link_{i}")
            sx = cx + math.copysign(CORE_SPINE_W / 2, x - cx)
            sy = cy + math.copysign(CORE_SPINE_D / 2, y - cy)
            checks.append((f"{name} z 195 transfer tie {i} endpoints",
                           link is not None and
                           beam_touches(link, (sx, sy, 195.0),
                                        (x, y, 195.0))))
    checks.append(("facade collections stay visible in the saved model",
                   all(not bpy.data.collections[f"Harukas_{name}"].hide_render
                       for name in MASSES)))

    # Floor slabs: one per storey with actual core/atrium openings, inset
    # from the plan and clear of the truss bands.
    for name, (height, points) in MASSES.items():
        levels = floor_levels(name, height)
        outline = quad_inset(points, SLAB_INSET)
        slab_objs = [(objects.get(f"{name}_Floor_"
                                  f"{int(round(z / STOREY_H)):02d}"), z)
                     for z in levels]
        checks.append((f"{name} floor slabs follow storeys, clear of bands",
                       all(slab is not None for slab, _ in slab_objs) and
                       len(slab_objs) > 0))
        checks.append((f"{name} floor slabs top out at storey levels",
                       all(abs(z_range(slab)[0] - (z - SLAB_T)) < 0.01 and
                           abs(z_range(slab)[1] - z) < 0.01
                           for slab, z in slab_objs if slab is not None)))
        checks.append((f"{name} floor slabs stay inside the plan",
                       all(inside_quad(points, (p.x, p.y), 0.25)
                           for slab, _ in slab_objs if slab is not None
                           for p in world_points(slab))))
        checks.append((f"{name} floor outlines and openings are cut",
                       all(all(corner in {(round(p.x, 3), round(p.y, 3))
                                          for p in world_points(slab)}
                               for loop in (outline,
                                            *core_openings(points, height, z))
                               for corner in ((round(qx, 3), round(qy, 3))
                                              for qx, qy in loop))
                           for slab, z in slab_objs if slab is not None)))
        checks.append((f"{name} floor slabs keep core openings clear",
                       all(not inside_quad(loop, (p.x, p.y), 0.01)
                           for slab, z in slab_objs if slab is not None
                           for loop in core_openings(points, height, z)
                           for p in world_points(slab))))
    checks.append(("floor collection stays visible in the saved model",
                   "Harukas_Floors" in bpy.data.collections and
                   not bpy.data.collections["Harukas_Floors"].hide_render))

    eye = None
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                region = area.spaces.active.region_3d
                if region is not None:
                    eye = (region.view_location
                           - region.view_distance
                           * (region.view_rotation @ Vector((0, 0, -1))))
    checks.append(("default viewport opens outside the building",
                   eye is not None and
                   (eye.y < -50.0 or abs(eye.x) > 60.0 or eye.z > 400.0)))

    failed = [name for name, passed in checks if not passed]
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}: {name}")
    if failed:
        raise SystemExit(f"{len(failed)} verification checks failed")
    print(f"All {len(checks)} checks passed")


main()
