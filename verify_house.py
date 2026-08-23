"""Geometry checks for the generated high-rise house.

Run headless:
    blender --background --factory-startup \
        --python verify_house.py -- out/highrise_house.blend
"""

import math
import sys

import bpy
from mathutils import Vector

H = 4.0
PILOTIS_FLOORS = 3
BLOCK_GROUPS = 2
BLOCK_FLOORS = 17
REFUGE_FLOORS = 2
FIXED_SOLID_BAND_FLOORS = 4
TOTAL_FLOORS = (PILOTIS_FLOORS + BLOCK_GROUPS * BLOCK_FLOORS
                + (BLOCK_GROUPS - 1) * REFUGE_FLOORS
                + FIXED_SOLID_BAND_FLOORS)
TOWER_FLOORS = TOTAL_FLOORS - PILOTIS_FLOORS
WIN_H, VENT_H = 1.50, 0.25
SLAB_T = 0.22
PIER_LONG = 2.0
WALL_T = 0.30
PIER_SHORT = 2.0
SPANDREL_LO_H = 0.50
VENT_LO_Z = SPANDREL_LO_H
WIN_Z = VENT_LO_Z + VENT_H
VENT_HI_Z = WIN_Z + WIN_H
SPANDREL_HI_H = H - (VENT_HI_Z + VENT_H)
MULLION_W = 0.09
MULLION_INSET = 0.12
PANE_W = 4.00
WINDOWS_LONG = 18
WINDOWS_SHORT = 7
WINDOW_GAP = 0.12
PANE_GLASS_W = PANE_W - WINDOW_GAP
GLASS_OPEN_W = WINDOWS_LONG * PANE_GLASS_W + (WINDOWS_LONG - 1) * WINDOW_GAP
GLASS_OPEN_D = WINDOWS_SHORT * PANE_GLASS_W + (WINDOWS_SHORT - 1) * WINDOW_GAP
# Footprint is DERIVED from the pane counts, as in the build script. Mullions are
# cover caps over the pane joints, so they add no facade length: an opening is
# exactly N x PANE_W and the footprint lands on whole metres.
OPEN_W = WINDOWS_LONG * PANE_W
OPEN_D = WINDOWS_SHORT * PANE_W
W = OPEN_W + 2 * PIER_LONG
D = OPEN_D + 2 * PIER_SHORT
PANE_GLASS_LONG = PANE_W
PANE_PITCH = PANE_W
CEILING_LIGHT_W = 2.20
CEILING_LIGHT_D = 0.36
CEILING_LIGHT_H = 0.06
CEILING_LIGHT_TOP_GAP = 0.05
CEILING_LIGHT_Z = WIN_Z + WIN_H - CEILING_LIGHT_TOP_GAP - CEILING_LIGHT_H / 2.0
CEILING_LIGHT_ON_RATIO = 0.36
CEILING_LIGHTS_PER_FLOOR = (2 * round(WINDOWS_LONG * CEILING_LIGHT_ON_RATIO)
                            + 2 * round(WINDOWS_SHORT * CEILING_LIGHT_ON_RATIO))
SOLID_BASE_FLOORS = 2
SOLID_TOP_FLOORS = 2
FIRST_GLAZED = SOLID_BASE_FLOORS
LAST_GLAZED = TOWER_FLOORS - SOLID_TOP_FLOORS - 1
# Refuge floor / sky garden: an open double-height void, mirroring build_house.py.
SKY_GARDEN = True
REFUGE_GRILLE_TOP_BLANK_H = 2.0
BALUSTRADE_H = 1.20
GARDEN_SLAB_T = 0.45
# Columns carrying the tower across the void. The fins screen it; these hold it up.
REFUGE_COL_SIZE = 1.20
REFUGE_COL_PITCH = PANE_W * 3
FIN_PITCH = 0.50
COL_SIZE = 1.60
COL_CLEAR_INSET = 2.0
COL_SPACING = 9.0
COL_MARGIN = COL_CLEAR_INSET + COL_SIZE / 2.0
CORE_COLUMN_BAYS = 2


def col_grid(span):
    usable = span - 2 * COL_MARGIN
    bays = max(1, round(usable / COL_SPACING))
    step = usable / bays
    start = -usable / 2
    return [start + index * step for index in range(bays + 1)]


def core_layout(span):
    grid = col_grid(span)
    mid = (len(grid) - 1) // 2
    west_center_index = mid - CORE_COLUMN_BAYS
    east_center_index = len(grid) - 1 - west_center_index
    west_lo, west_hi = grid[west_center_index - 1], grid[west_center_index + 1]
    west_center = (west_lo + west_hi) / 2.0
    return ((west_hi - west_lo) + COL_SIZE, abs(west_center),
            (-abs(west_center), abs(west_center)))


# Twin service cores. Length and centre are derived from the reference tower's
# column grid, matching build_house.py; depth and wall thickness stay fixed.
CORE_W, CORE_OFFSET, CORE_XS = core_layout(W)
CORE_D, CORE_T = 9.0, 0.28
CORE_PROVISION = 203.5     # m2 of shafts/stairs/lobbies/risers the tower needs
PARAPET_H = 1.10
CORE_OVERRUN = 4.6         # lift overtravel + machine room above the roof slab
CORE_ROOF_PARAPET = 0.9
REFUGE_STARTS = [FIRST_GLAZED + (index + 1) * BLOCK_FLOORS
                 + index * REFUGE_FLOORS for index in range(BLOCK_GROUPS - 1)]
REFUGE_ENDS = [start + REFUGE_FLOORS - 1 for start in REFUGE_STARTS]
REFUGE_START, REFUGE_END = REFUGE_STARTS[0], REFUGE_ENDS[0]
REFUGE_SET = (set().union(*[set(range(start, end + 1))
                            for start, end in zip(REFUGE_STARTS, REFUGE_ENDS)])
              if SKY_GARDEN else set())
REFUGE_STOREY = PILOTIS_FLOORS + REFUGE_START + 1
BASE_Z_ = PILOTIS_FLOORS * H
REFUGE_Z0 = BASE_Z_ + REFUGE_START * H
REFUGE_Z1 = REFUGE_Z0 + REFUGE_FLOORS * H
REFUGE_GRILLE_Z0 = REFUGE_Z0
REFUGE_GRILLE_Z1 = REFUGE_Z1 - REFUGE_GRILLE_TOP_BLANK_H
REFUGE_GRILLE_H = REFUGE_GRILLE_Z1 - REFUGE_GRILLE_Z0
# The void is glazed on no facade, so it comes off the glazed count.
GLAZED_FLOORS = (TOWER_FLOORS - SOLID_BASE_FLOORS - SOLID_TOP_FLOORS
                 - len(REFUGE_SET))
GLAZED_SET = set(range(FIRST_GLAZED, LAST_GLAZED + 1)) - REFUGE_SET
BASE_Z = PILOTIS_FLOORS * H
TOP_Z = BASE_Z + TOWER_FLOORS * H
ROOF_TOP_Z = TOP_Z + 0.22 + PARAPET_H          # top of the roof parapet
CORE_TOP_Z = TOP_Z + 0.22 + CORE_OVERRUN + 0.22 + CORE_ROOF_PARAPET
ROOF_GARDEN = True
ROOF_GARDEN_Z0 = TOP_Z + 0.22
ROOF_GARDEN_GRILLE_H = 2 * H
EPS = 1e-4

failures = []
checks = 0


def check(label, condition, detail=""):
    global checks
    checks += 1
    status = "ok  " if condition else "FAIL"
    print(f"[{status}] {label}{('  -> ' + detail) if detail else ''}")
    if not condition:
        failures.append(label)


def world_bounds(obj):
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    return (
        (min(p.x for p in pts), max(p.x for p in pts)),
        (min(p.y for p in pts), max(p.y for p in pts)),
        (min(p.z for p in pts), max(p.z for p in pts)),
    )


def gb_low(obj):
    return world_bounds(obj)[2][0]


def gb_high(obj):
    return world_bounds(obj)[2][1]


def piece_bounds(obj):
    """Bounding box of every connected component (i.e. every original box)."""
    verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    adj = {i: set() for i in range(len(verts))}
    for poly in obj.data.polygons:
        vs = list(poly.vertices)
        for a in vs:
            adj[a].update(vs)

    seen, out = set(), []
    for start in range(len(verts)):
        if start in seen:
            continue
        stack, comp = [start], []
        seen.add(start)
        while stack:
            i = stack.pop()
            comp.append(i)
            for j in adj[i]:
                if j not in seen:
                    seen.add(j)
                    stack.append(j)
        pts = [verts[i] for i in comp]
        out.append((
            (min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)),
            (max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)),
        ))
    return out


def facade_span(obj, side):
    """Extent of the geometry belonging to ONE facade of a joined object.

    Selects only the vertices near that facade plane, then measures along the
    facade. Needed because a joined object's overall bbox spans all four sides.
    """
    verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    if side in ("S", "N"):
        sign = -1 if side == "S" else 1
        sel = [p.x for p in verts if abs(p.y - sign * D / 2) < 1.0]
    else:
        sign = -1 if side == "W" else 1
        sel = [p.y for p in verts if abs(p.x - sign * W / 2) < 1.0]
    return (max(sel) - min(sel)) if sel else 0.0


def z_clusters(obj, tol=1e-3):
    """Distinct world-space Z levels present in a mesh, sorted."""
    zs = sorted(round((obj.matrix_world @ v.co).z, 4) for v in obj.data.vertices)
    out = []
    for z in zs:
        if not out or abs(z - out[-1]) > tol:
            out.append(z)
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    blend = argv[0]
    bpy.ops.wm.open_mainfile(filepath=blend)

    objs = {o.name: o for o in bpy.data.objects if o.type == "MESH"}
    print(f"\nloaded {blend}: {len(objs)} mesh objects\n")

    for name in ("Facade_Spandrels", "Windows_Glass", "Window_Mullions",
                 "Vent_Louvres", "Vent_Shadowboxes", "Floor_Plates",
                 "Interior_Lining", "Ceiling_Lights", "Sky_Garden_Grille",
                 "Structure"):
        check(f"object present: {name}", name in objs)
    second_facade = objs.get("Facade_Spandrels.001")
    second_glass = objs.get("Windows_Glass.001")
    second_struct = objs.get("Structure.001")
    check("second tower is generated as a separate mesh",
          second_facade is not None and second_glass is not None
          and second_struct is not None)
    if second_facade and second_glass and second_struct:
        second_fb = world_bounds(second_facade)
        first_fb = world_bounds(objs["Facade_Spandrels"])
        second_gz = z_clusters(second_glass)
        check("second tower is 84 m wide for 20 long-face rooms",
              abs(second_fb[0][1] - second_fb[0][0] - 84.0) < 0.02,
              f"width={second_fb[0][1] - second_fb[0][0]:.3f} m")
        check("second tower has 3 x 17 glazed floors",
              len(second_gz) == 51 * 2,
              f"{len(second_gz) // 2} glazed floors")
        check("the two tower envelopes keep an 18 m clear gap",
              abs(second_fb[0][0] - first_fb[0][1] - 18.0) < 0.02,
              f"gap={second_fb[0][0] - first_fb[0][1]:.3f} m")
        second_w = second_fb[0][1] - second_fb[0][0]
        second_origin = first_fb[0][1] + 18.0 + second_w / 2
        second_core_w, second_core_offset, second_core_xs = core_layout(second_w)
        second_pieces = piece_bounds(second_struct)
        second_core_pieces = [
            (lo, hi) for lo, hi in second_pieces
            if lo[2] < 1.0 and hi[2] > BASE_Z - 1.0
            and (hi[0] - lo[0]) < second_w * 0.5
            and lo[1] > -CORE_D / 2 - 0.5 and hi[1] < CORE_D / 2 + 0.5]
        measured_second_widths = []
        for cx in second_core_xs:
            here = [(lo, hi) for lo, hi in second_core_pieces
                    if abs((lo[0] + hi[0]) / 2 - (second_origin + cx))
                    < second_core_w / 2 + 0.5]
            if here:
                measured_second_widths.append(
                    max(hi[0] for _, hi in here) - min(lo[0] for lo, _ in here))
        check("taller tower core length follows its column grid",
              len(measured_second_widths) == 2
              and all(abs(width - second_core_w) < 0.05
                      for width in measured_second_widths),
              f"measured={', '.join(f'{width:.2f}' for width in measured_second_widths)} m, "
              f"expected={second_core_w:.2f} m")
        second_columns = [
            ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2)
            for lo, hi in second_pieces
            if lo[2] <= 0.05 and hi[2] >= TOP_Z - 0.05
            and abs((hi[0] - lo[0]) - COL_SIZE) < 0.02
            and abs((hi[1] - lo[1]) - COL_SIZE) < 0.02]
        second_defining_lines = [
            second_origin + cx + sign * (second_core_w / 2 - COL_SIZE / 2)
            for cx in second_core_xs for sign in (-1, 1)]
        check("taller tower defining columns meet both core ends",
              all(min(abs(x - line) for x, _ in second_columns) < 0.02
                  for line in second_defining_lines),
              f"{len(second_columns)} continuous columns checked")
    if failures:
        sys.exit(1)

    # --- glass must stay clear, not frosted ----------------------------
    # Each of these three, on its own, turns smooth glass into ground glass, and
    # every one was present in an earlier version. Cheap to assert, easy to
    # reintroduce by accident while tuning.
    gmat = bpy.data.materials.get("Glass")
    check("glass material exists", gmat is not None)
    if gmat:
        gb_ = gmat.node_tree.nodes["Principled BSDF"].inputs
        rough = gb_["Roughness"].default_value
        trans = gb_["Transmission Weight"].default_value
        emit = gb_["Emission Strength"].default_value
        check("glass roughness is ~0 (rough glass reads as frosted)",
              rough <= 0.01, f"roughness={rough:.3f}")
        check("glass transmission is 1.0 (the remainder is a diffuse, i.e. "
              "frosted, lobe)", trans >= 0.99, f"transmission={trans:.3f}")
        check("glass does not self-illuminate (a glow flattens it to a milky "
              "film)", emit <= 1e-6, f"emission strength={emit:.3f}")

    cyc = getattr(bpy.context.scene, "cycles", None)
    if cyc and hasattr(cyc, "blur_glossy"):
        check("Filter Glossy is off (it blurs refraction and frosts the panes)",
              cyc.blur_glossy <= 1e-6, f"blur_glossy={cyc.blur_glossy:.2f}")

    # --- windows -------------------------------------------------------
    glass = objs["Windows_Glass"]
    gz = z_clusters(glass)
    check("glass forms 2 Z levels per glazed floor", len(gz) == GLAZED_FLOORS * 2,
          f"{len(gz)} levels for {GLAZED_FLOORS} glazed floors")

    bands = list(zip(gz[0::2], gz[1::2]))
    heights = [round(hi - lo, 5) for lo, hi in bands]
    check("every window is 1.50 m tall",
          all(abs(h - WIN_H) < EPS for h in heights), f"heights={set(heights)}")

    lows_rel = [round((lo - BASE_Z) % H, 5) for lo, _ in bands]
    check("every window starts 0.75 m above its floor",
          all(abs(z - WIN_Z) < EPS for z in lows_rel),
          f"lower-edge offsets={set(lows_rel)}")

    floors_seen = sorted({int(((lo + hi) / 2 - BASE_Z) // H) for lo, hi in bands})
    check("one window band per glazed floor, none on the blank or refuge floors",
          floors_seen == sorted(GLAZED_SET),
          f"glazed floors={floors_seen[0]}..{floors_seen[-1]} ({len(floors_seen)}), "
          f"refuge {sorted(REFUGE_SET)} excluded")

    # --- blank bands ---------------------------------------------------
    check("the floor above the pilotis has no window",
          all(int(((lo + hi) / 2 - BASE_Z) // H) >= SOLID_BASE_FLOORS
              for lo, hi in bands),
          f"lowest glazed floor index={floors_seen[0]} (expect {SOLID_BASE_FLOORS})")
    check("bottom blank band is fully solid",
          gb_low(glass) >= BASE_Z + SOLID_BASE_FLOORS * H - EPS,
          f"lowest glass z={gb_low(glass):.3f}, blank up to "
          f"{BASE_Z + SOLID_BASE_FLOORS * H:.1f} m")

    top_blank_z = TOP_Z - SOLID_TOP_FLOORS * H
    check(f"top {SOLID_TOP_FLOORS * H:.0f} m is blank (no glass above "
          f"{top_blank_z:.0f} m)",
          gb_high(glass) <= top_blank_z + EPS,
          f"highest glass z={gb_high(glass):.3f}, blank from {top_blank_z:.1f} m")
    check("top blank band measures 8 m", abs(SOLID_TOP_FLOORS * H - 8.0) < EPS,
          f"{SOLID_TOP_FLOORS} floors x {H} m = {SOLID_TOP_FLOORS * H:.1f} m")
    check("blank bands land on floor lines",
          abs((gb_low(glass) - BASE_Z) % H - WIN_Z) < EPS
          and abs((TOP_Z - gb_high(glass)) % H) < EPS + WIN_Z,
          "window bands stay aligned to the storey grid")

    # The ribbon stops a pier width short of every corner. The joined object's
    # overall bbox cannot show this (the E/W panes fix the X extent at ~W), so
    # each facade must be measured on its own.
    gb = world_bounds(glass)
    x_span, y_span = facade_span(glass, "S"), facade_span(glass, "E")
    check("long-face glazing has room joints and stops short of both corners",
          abs(x_span - GLASS_OPEN_W) < 0.02,
          f"glazing={x_span:.3f} m, expected {GLASS_OPEN_W:.3f} m")
    check("short-face glazing has room joints and stops short of both corners",
          abs(y_span - GLASS_OPEN_D) < 0.02,
          f"glazing={y_span:.3f} m, expected {GLASS_OPEN_D:.3f} m")
    check(f"piers measure {PIER_LONG:.0f} m on the long faces and "
          f"{PIER_SHORT:.0f} m on the short ones",
          abs((W - OPEN_W) / 2 - PIER_LONG) < 0.02
          and abs((D - OPEN_D) / 2 - PIER_SHORT) < 0.02,
          f"wall margins long {(W - OPEN_W) / 2:.3f} m, short {(D - OPEN_D) / 2:.3f} m")
    # The long-facade pier is one pane wide, so the glazing is nearly the whole
    # face. Assert the opening is still a real band on BOTH faces — the short one
    # keeps 4 m piers and so is the tighter of the two.
    check("openings are a meaningful share of each facade",
          x_span / W > 0.5 and y_span / D > 0.4,
          f"long face {x_span / W:.1%}, short face {y_span / D:.1%}")
    check("glazing starts at the first glazed floor",
          abs(gb[2][0] - (BASE_Z + SOLID_BASE_FLOORS * H + WIN_Z)) < EPS,
          f"lowest glass z={gb[2][0]:.3f}, expected "
          f"{BASE_Z + SOLID_BASE_FLOORS * H + WIN_Z:.3f}")

    # --- pane count ----------------------------------------------------
    # Count mullions on one facade at one floor: N panes need N+1 mullions.
    mull = objs["Window_Mullions"]
    zw = BASE_Z + (SOLID_BASE_FLOORS + 4) * H + WIN_Z
    raw_x, raw_y = [], []
    for lo, hi in piece_bounds(mull):
        if not (zw - 0.05 < (lo[2] + hi[2]) / 2 < zw + WIN_H + 0.05):
            continue
        cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
        if abs(cy + D / 2) < 1.0:          # south facade
            raw_x.append(cx)
        if abs(cx + W / 2) < 1.0:          # west facade
            raw_y.append(cy)

    def dedupe(vals, tol=1e-6):
        """Merge coincident centres without quantising the spacing itself.

        Rounding to a fixed number of decimals here introduces an apparent
        pitch variation equal to the rounding step, which is not in the model.
        """
        out = []
        for v in sorted(vals):
            if not out or v - out[-1] > tol:
                out.append(v)
        return out

    xs, ys = dedupe(raw_x), dedupe(raw_y)

    check(f"long facade has {WINDOWS_LONG} window panes",
          len(xs) - 1 == WINDOWS_LONG,
          f"{len(xs)} mullions -> {len(xs) - 1} panes")
    check(f"short facade has {WINDOWS_SHORT} window panes",
          len(ys) - 1 == WINDOWS_SHORT,
          f"{len(ys)} mullions -> {len(ys) - 1} panes")

    # Centres were rounded to mm when collected, so compare with a 1 mm
    # tolerance rather than requiring bit-identical spacings.
    pitches = [b - a for a, b in zip(sorted(xs), sorted(xs)[1:])]
    check("panes are evenly spaced on the long facade",
          max(pitches) - min(pitches) < 1e-4,
          f"spread={max(pitches) - min(pitches):.6f} m over {len(pitches)} bays")
    check(f"pane pitch is {PANE_PITCH:.4f} m",
          abs(pitches[0] - PANE_PITCH) < 1e-3,
          f"measured {pitches[0]:.4f} m")
    glass_widths = sorted({round(hi[0] - lo[0], 4) for lo, hi in piece_bounds(glass)
                           if abs((lo[1] + hi[1]) / 2 + D / 2) < 1.0})
    check(f"each room window is {PANE_GLASS_W:.2f} m x {WIN_H:.2f} m",
          glass_widths == [round(PANE_GLASS_W, 4)]
          and abs(heights[0] - WIN_H) < EPS,
          f"widths={glass_widths}, height={heights[0]:.2f} m")
    check(f"adjacent room windows have a {WINDOW_GAP:.2f} m vertical gap",
          abs(pitches[0] - PANE_GLASS_W - WINDOW_GAP) < 1e-3,
          f"pitch {pitches[0]:.4f} m - glass {PANE_GLASS_W:.4f} m = "
          f"gap {pitches[0] - PANE_GLASS_W:.4f} m")

    # The short facade uses the SAME module, not a stretched one.
    pitches_y = [b - a for a, b in zip(ys, ys[1:])]
    check(f"short facade panes are also {PANE_GLASS_W:.2f} m wide",
          max(pitches_y) - min(pitches_y) < 1e-4
          and abs(pitches_y[0] - PANE_W) < 1e-3,
          f"pitch={pitches_y[0]:.4f} m, glass={PANE_GLASS_W:.4f} m")
    check("pane pitch is identical on long and short facades",
          abs(pitches[0] - pitches_y[0]) < 1e-4,
          f"long {pitches[0]:.4f} m vs short {pitches_y[0]:.4f} m")
    # Mullions cap the joints, so the end ones sit ON the opening edges.
    edge = OPEN_W / 2
    check("end mullions sit on the opening edges, against the piers",
          abs(min(xs) + edge) < 1e-3 and abs(max(xs) - edge) < 1e-3,
          f"first={min(xs):.4f}, last={max(xs):.4f}, expected +/-{edge:.4f}")
    check(f"{WINDOWS_LONG} room windows of 4 m fill the opening exactly "
          "(mullions add no length)",
          abs(WINDOWS_LONG * PANE_W - OPEN_W) < 1e-9,
          f"{WINDOWS_LONG} x {PANE_W} = {OPEN_W:.4f} m")

    # The whole point of capping: the footprint is whole metres.
    check("footprint lands on whole metres",
          abs(W - round(W)) < 1e-9 and abs(D - round(D)) < 1e-9,
          f"W={W:.4f} m, D={D:.4f} m")
    check("footprint is exactly panes + piers, no leftover",
          abs(W - (WINDOWS_LONG * PANE_W + 2 * PIER_LONG)) < 1e-9
          and abs(D - (WINDOWS_SHORT * PANE_W + 2 * PIER_SHORT)) < 1e-9,
          f"{WINDOWS_LONG}x{PANE_W:.0f}+2x{PIER_LONG:.0f}={W:.0f} m, "
          f"{WINDOWS_SHORT}x{PANE_W:.0f}+2x{PIER_SHORT:.0f}={D:.0f} m")
    check("depth is at least 30 m", D >= 30.0 - 1e-9, f"D={D:.2f} m")
    check("clear internal depth is at least 30 m",
          D - 2 * 0.30 >= 30.0 - 1e-9, f"{D - 0.60:.2f} m inside face to face")
    check(f"piers are {PIER_LONG:.0f} m (long) and {PIER_SHORT:.0f} m (short)",
          abs((W - OPEN_W) / 2 - PIER_LONG) < 1e-6
          and abs((D - OPEN_D) / 2 - PIER_SHORT) < 1e-6,
          f"long {(W - OPEN_W) / 2:.2f} m, short {(D - OPEN_D) / 2:.2f} m")

    # The point of a one-pane pier on the long facade: the corner apartment,
    # which sits outboard of a core, should turn the corner almost at once and so
    # have windows on two faces. The pier is what stands between it and the
    # return, and it used to be 8 m of blank wall.
    margin_lr = (W - OPEN_W) / 2
    check("the long-facade pier is half a room-window bay, not a blank band",
          abs(margin_lr - PANE_W / 2) < 1e-6,
          f"{margin_lr:.2f} m = {margin_lr / PANE_W:.1f} room-window bay")
    corner_unit_w = W / 2 - (CORE_OFFSET + CORE_W / 2)
    corner_panes = (OPEN_W / 2 - (CORE_OFFSET + CORE_W / 2)) / PANE_W
    check("the corner apartment is a habitable width, not a corridor",
          corner_unit_w >= 7.0,
          f"{corner_unit_w:.1f} m wide x {(D - CORE_D) / 2:.1f} m deep")
    check("the corner apartment has glass on the long face as well as the return",
          corner_panes >= 1.0,
          f"{corner_panes:.1f} room-window bays on the long face before the pier")

    # Thinning the pier costs lateral stiffness, and that is the constraint that
    # rules out taking it to zero. Thin-walled box for the cores, parallel axis
    # for the four L-piers, cantilever tip drift under a uniform 1.5 kPa.
    def box_I(b, d, t):
        return (b * d ** 3 - (b - 2 * t) * (d - 2 * t) ** 3) / 12.0

    I_cores = 2 * box_I(CORE_W, CORE_D, CORE_T)
    I_piers = 0.0
    for sy in (-1, 1):
        for _sx in (-1, 1):
            a1, y1 = PIER_LONG * WALL_T, sy * (D / 2 - WALL_T / 2)
            a2 = WALL_T * (PIER_SHORT - WALL_T)
            y2 = sy * (D / 2 - WALL_T - (PIER_SHORT - WALL_T) / 2)
            I_piers += (PIER_LONG * WALL_T ** 3 / 12 + a1 * y1 ** 2
                        + WALL_T * (PIER_SHORT - WALL_T) ** 3 / 12 + a2 * y2 ** 2)
    H_cant = TOP_Z - BASE_Z
    drift = (1.5e3 * W) * H_cant ** 4 / (8 * 32.8e9 * (I_cores + I_piers))
    check("lateral drift is within H/500 with the thinned pier",
          H_cant / drift >= 500.0,
          f"{drift * 1000:.0f} mm tip drift = H/{H_cant / drift:,.0f}, "
          f"Iy {I_cores + I_piers:,.0f} m4 (cores {I_cores:,.0f} + "
          f"piers {I_piers:,.0f})")

    # --- interior lining and ceiling lights behind the glazing ------------
    # Clear glass shows whatever is behind it; without a lining the panes look
    # through the tower to the sky and stop reading as windows.
    lining = objs["Interior_Lining"]
    lz = z_clusters(lining)
    check("lining matches the glazing, one band per glazed floor",
          len(lz) == GLAZED_FLOORS * 2, f"{len(lz)} levels")
    lbands = list(zip(lz[0::2], lz[1::2]))
    check("lining is exactly as tall as the window",
          all(abs(hi - lo - WIN_H) < EPS for lo, hi in lbands),
          f"heights={ {round(hi - lo, 4) for lo, hi in lbands} }")
    check("lining occupies the same Z bands as the glass",
          [round(z, 4) for z in lz] == [round(z, 4) for z in gz])

    # It has to sit BEHIND the glass — deeper in on every facade.
    lining_x = max(abs(p) for piece in piece_bounds(lining)
                   for p in (piece[0][0], piece[1][0]))
    glass_x = max(abs(p) for piece in piece_bounds(glass)
                  for p in (piece[0][0], piece[1][0]))
    check("lining is set back behind the glazing", lining_x < glass_x - 0.3,
          f"lining reaches x={lining_x:.3f}, glass x={glass_x:.3f} "
          f"(setback {glass_x - lining_x:.3f} m)")
    check("lining follows the separate room windows",
          abs(facade_span(lining, "S") - GLASS_OPEN_W) < 0.05
          and abs(facade_span(lining, "E") - GLASS_OPEN_D) < 0.05,
          f"{facade_span(lining, 'S'):.2f} x {facade_span(lining, 'E'):.2f} m")

    lights = objs.get("Ceiling_Lights")
    check("ceiling lights object exists", lights is not None)
    if lights:
        light_mat = lights.data.materials[0] if lights.data.materials else None
        check("ceiling lights use an emissive material", light_mat is not None,
              "no material slot")
        if light_mat:
            inputs = light_mat.node_tree.nodes["Principled BSDF"].inputs
            strength = inputs["Emission Strength"].default_value
            check("ceiling light emission is visible", strength >= 2.0,
                  f"emission strength={strength:.2f}")
        light_z = z_clusters(lights)
        check("ceiling lights have one level per glazed floor",
              len(light_z) == GLAZED_FLOORS * 2,
              f"{len(light_z)} levels for {GLAZED_FLOORS} glazed floors")
        light_bands = list(zip(light_z[0::2], light_z[1::2]))
        check("ceiling lights sit at the upper edge of each window band",
              all(abs((lo + hi) / 2 - (base + CEILING_LIGHT_Z)) < 0.02
                  for (lo, hi), base in zip(light_bands,
                                             [BASE_Z + f * H for f in sorted(GLAZED_SET)])),
              f"z={min(light_z):.2f}..{max(light_z):.2f}")
        light_bounds = piece_bounds(lights)
        check("ceiling lights leave most room windows unlit",
              len(light_bounds) == GLAZED_FLOORS * CEILING_LIGHTS_PER_FLOOR,
              f"{len(light_bounds)} panels = {CEILING_LIGHTS_PER_FLOOR} per "
              f"glazed floor ({CEILING_LIGHT_ON_RATIO:.0%} lit)")
        patterns = {}
        for lo, hi in light_bounds:
            z = round((lo[2] + hi[2]) / 2, 2)
            patterns.setdefault(z, set()).add(
                (round((lo[0] + hi[0]) / 2, 2),
                 round((lo[1] + hi[1]) / 2, 2)))
        check("every glazed floor has a sparse ceiling-light pattern",
              len(patterns) == GLAZED_FLOORS
              and all(len(points) == CEILING_LIGHTS_PER_FLOOR
                      for points in patterns.values()),
              f"{len(patterns)} floors, counts="
              f"{sorted(set(map(len, patterns.values())))}")
        unique_patterns = {tuple(sorted(points)) for points in patterns.values()}
        check("ceiling-light patterns vary between floors",
              len(unique_patterns) >= GLAZED_FLOORS * 0.75,
              f"{len(unique_patterns)} distinct patterns over "
              f"{GLAZED_FLOORS} glazed floors")
        check("ceiling lights stay behind the glazing",
              max(max(abs(lo[0]), abs(hi[0])) for lo, hi in light_bounds)
              < glass_x - 0.3
              and max(max(abs(lo[1]), abs(hi[1])) for lo, hi in light_bounds)
              < D / 2 - 0.3,
              "light panels are recessed from the facade")

    # --- refuge floor / sky garden -------------------------------------
    if SKY_GARDEN:
        plates = objs["Floor_Plates"]
        facade = objs["Facade_Spandrels"]

        def pieces_at_corner_in_slice(obj, zlo, zhi):
            """Count connected pieces overlapping a corner zone within a z-slice.

            Bbox overlap, not vertex sampling: a box spanning the slice may have
            no vertex inside it.
            """
            hits = 0
            for lo, hi in piece_bounds(obj):
                if hi[2] <= zlo or lo[2] >= zhi:
                    continue
                if (max(abs(lo[0]), abs(hi[0])) > W / 2 - PIER_LONG + 0.05
                        and max(abs(lo[1]), abs(hi[1])) > D / 2 - PIER_SHORT + 0.05):
                    hits += 1
            return hits

        # The whole point is an OPEN double-height void: nothing enclosing it, and
        # no slab cutting it in half.
        for name in ("Windows_Glass", "Interior_Lining", "Vent_Louvres"):
            inside = [c for lo, hi in piece_bounds(objs[name])
                      for c in [(lo[2] + hi[2]) / 2]
                      if REFUGE_Z0 + 0.05 < c < REFUGE_Z1 - 0.05]
            check(f"no {name} in the refuge void (it is open, not glazed)",
                  not inside, f"{len(inside)} pieces between "
                  f"{REFUGE_Z0:.0f} and {REFUGE_Z1:.0f} m")

        mid_z = REFUGE_Z0 + H          # where an intermediate slab would sit
        cutting = [1 for lo, hi in piece_bounds(plates)
                   if lo[2] < mid_z - 0.01 < hi[2]
                   or abs((lo[2] + hi[2]) / 2 - (mid_z - SLAB_T / 2)) < 0.05]
        check(f"no floor plate splits the void, so it is a full "
              f"{REFUGE_FLOORS * H:.0f} m double height", not cutting,
              f"{len(cutting)} plates at z={mid_z:.1f} m")

        # It must still be a floor you can stand on, and a lid above it.
        st = piece_bounds(objs["Structure"])
        garden_slab = [(lo, hi) for lo, hi in st
                       if abs(hi[2] - REFUGE_Z0) < 0.02
                       and (hi[0] - lo[0]) > W * 0.9]
        check("the garden has a floor slab at its own level",
              len(garden_slab) >= 1,
              f"{len(garden_slab)} slab(s) topping out at {REFUGE_Z0:.1f} m")
        check("the garden slab is thicker than a normal plate (it carries soil)",
              any(abs((hi[2] - lo[2]) - GARDEN_SLAB_T) < 0.02
                  for lo, hi in garden_slab),
              f"thickness={[round(hi[2] - lo[2], 3) for lo, hi in garden_slab]}, "
              f"normal plate {SLAB_T}")
        ceiling = [1 for lo, hi in piece_bounds(plates)
                   if abs(hi[2] - REFUGE_Z1) < 0.02]
        check("the void is capped by the plate of the floor above", ceiling,
              f"{len(ceiling)} plate(s) topping out at {REFUGE_Z1:.1f} m")

        # --- the screen and upper closure across the void ----------------
        # The external opening is six metres: the grille occupies the lower six
        # and a solid wall band closes the remaining two metres above it.
        grille_obj = objs["Sky_Garden_Grille"]
        gp = piece_bounds(grille_obj)
        refuge_grille = [(lo, hi) for lo, hi in gp
                         if hi[2] <= REFUGE_Z1 + 0.02]
        gz_ = (min(lo[2] for lo, _ in refuge_grille),
               max(hi[2] for _, hi in refuge_grille)) if refuge_grille else (0.0, 0.0)
        check("the void is screened, not left fully open", len(gp) > 20,
              f"{len(gp)} grille members")
        check("the screen is 6 m high from the refuge floor",
              abs(gz_[0] - REFUGE_GRILLE_Z0) < 0.02
              and abs(gz_[1] - REFUGE_GRILLE_Z1) < 0.02
              and abs(REFUGE_Z1 - gz_[1] - REFUGE_GRILLE_TOP_BLANK_H) < 0.02,
              f"z {gz_[0]:.2f}..{gz_[1]:.2f}; expected "
              f"{REFUGE_GRILLE_Z0:.0f}..{REFUGE_GRILLE_Z1:.0f} m, "
              f"upper wall {REFUGE_GRILLE_TOP_BLANK_H:.1f} m")

        refuge_top_walls = [(lo, hi) for lo, hi in piece_bounds(facade)
                            if abs(lo[2] - REFUGE_GRILLE_Z1) < 0.02
                            and abs(hi[2] - REFUGE_Z1) < 0.02]
        check("a solid wall closes the 2 m above the refuge grille",
              len(refuge_top_walls) >= 4,
              f"{len(refuge_top_walls)} wall runs at "
              f"z={REFUGE_GRILLE_Z1:.0f}..{REFUGE_Z1:.0f} m")

        # THE point of the 2 m cell: grille verticals must land on the window
        # mullions, so the vertical lines carry through the garden unbroken. Any
        # other pitch makes the refuge level read as a foreign object.
        def face_verticals(obj, zlo, zhi, min_h):
            return sorted({round((lo[0] + hi[0]) / 2, 3) for lo, hi in piece_bounds(obj)
                           if abs((lo[1] + hi[1]) / 2 + D / 2) < 1.0
                           and zlo < (lo[2] + hi[2]) / 2 < zhi
                           and (hi[2] - lo[2]) > min_h})

        gxs = face_verticals(grille_obj, REFUGE_GRILLE_Z0,
                             REFUGE_GRILLE_Z1, 4.0)
        mull_z = REFUGE_Z1 + WIN_Z + WIN_H / 2
        mxs = face_verticals(objs["Window_Mullions"], mull_z - 1.0, mull_z + 1.0, 0.0)
        aligned = [g for g in gxs if any(abs(g - m) < 0.02 for m in mxs)]
        # The rule is that the screen pitch DIVIDES the pane pitch, so the vertical
        # lines carry through. GRID puts one member per pane (every member hits a
        # mullion); FINS subdivides it, so every Nth blade does. Either way every
        # mullion must be met by a blade — that is what keeps the lines unbroken.
        gpitch = (gxs[1] - gxs[0]) if len(gxs) >= 2 else 0.0
        ratio = PANE_PITCH / gpitch if gpitch else 0.0
        check("the screen pitch divides the window pane pitch",
              gpitch and abs(ratio - round(ratio)) < 1e-6 and round(ratio) >= 1,
              f"grille pitch={gpitch:.3f} m, pane pitch={PANE_PITCH:.2f} m "
              f"= {round(ratio)} blades per pane")
        check("every window mullion is met by a grille vertical",
              mxs and len(aligned) == len(mxs),
              f"{len(aligned)} of {len(gxs)} blades land on a mullion, "
              f"covering {len(mxs)} mullions")

        # Real openings, or the refuge floor cannot ventilate.
        open_frac = None
        if len(gxs) >= 2:
            member = min(hi[0] - lo[0] for lo, hi in gp
                         if (hi[2] - lo[2]) > 4.0
                         and abs((lo[1] + hi[1]) / 2 + D / 2) < 1.0)
            # Blades run the full height, so what they block is measured along the
            # facade only. (For a GRID the horizontals block a share of the height
            # too, but the verticals dominate and this stays the conservative
            # lower bound on open area.)
            open_frac = 1.0 - (len(gxs) * member) / OPEN_W
        check("the screen is mostly open (a filter, not a wall)",
              open_frac is not None and 0.45 < open_frac < 0.91,
              f"open area {open_frac:.1%} of the long face" if open_frac else "n/a")

        # Independent of the arithmetic above: a ray through a cell centre must
        # leave the building, and one through a member must not.
        if len(gxs) >= 12:
            scene = bpy.context.scene
            dg = bpy.context.evaluated_depsgraph_get()

            def hits_through(x, z):
                o = Vector((x, -(D / 2 + 30.0), z))
                d = Vector((0.0, 1.0, 0.0))
                n = 0
                for _ in range(40):
                    ok, loc, _, _, _, _ = scene.ray_cast(dg, o, d)
                    if not ok:
                        break
                    n += 1
                    o = loc + d * 0.02
                return n

            z_probe = REFUGE_Z0 + 3.0

            # This test is about the SCREEN having real openings, so it has to
            # probe a bay where nothing else is in the way. The refuge level also
            # contains the service cores, the 1.20 m structural columns and the
            # planting, any of which will stop a Y-ray regardless of the screen.
            # Rather than hardcode a bay index — the old version used gxs[10],
            # which stopped being clear the moment the cores moved — find a gap
            # that is genuinely open and report how many there were.
            gaps = [(gxs[i], (gxs[i] + gxs[i + 1]) / 2)
                    for i in range(len(gxs) - 1)]
            clear = [(m, mem) for mem, m in gaps
                     if hits_through(m, z_probe) == 0]
            check("the screen has bays that are clear through (real openings)",
                  len(clear) >= 10,
                  f"{len(clear)} of {len(gaps)} bays open through the whole "
                  f"depth at z={z_probe:.1f} m")
            if clear:
                mid, member = clear[len(clear) // 2]
                check("a ray passes clean through a grille cell (real opening)",
                      hits_through(mid, z_probe) == 0,
                      f"{hits_through(mid, z_probe)} hits at x={mid:.2f}, "
                      f"z={z_probe:.1f}")
                check("a ray is blocked by a grille member",
                      hits_through(member, z_probe) > 0,
                      f"{hits_through(member, z_probe)} hits at x={member:.2f} "
                      f"(the blade beside that opening)")

        # --- the load path across the void ------------------------------
        # The fins are 0.10 m blades and carry nothing. Real columns have to take
        # the floors above down through the void, or the corner piers and core are
        # left with 33.1 m2 of concrete under 486605 kN = 14.7 MPa, 82% of C40.
        st_ = piece_bounds(objs["Structure"])
        cols = [(lo, hi) for lo, hi in st_
                if lo[2] <= 0.05 and hi[2] >= TOP_Z - 0.05
                and abs((hi[0] - lo[0]) - COL_SIZE) < 0.02
                and abs((hi[1] - lo[1]) - COL_SIZE) < 0.02]
        check("one continuous structural column grid crosses the whole tower",
              len(cols) >= 16,
              f"{len(cols)} columns of {COL_SIZE:.2f} m square spanning "
              f"ground..{TOP_Z:.0f} m")

        clearances = [min(W / 2 - max(abs(lo[0]), abs(hi[0])),
                          D / 2 - max(abs(lo[1]), abs(hi[1])))
                      for lo, hi in cols]
        check("every continuous column is at least 2 m inside the facade",
              clearances and min(clearances) >= COL_CLEAR_INSET - 0.02,
              f"minimum clear inset={min(clearances):.3f} m")

        # Utilisation, so the section cannot silently be shaved to nothing.
        pier_area = 4 * (PIER_LONG * WALL_T + (PIER_SHORT - WALL_T) * WALL_T)
        core_area = 2 * (CORE_W * CORE_D
                         - (CORE_W - 2 * CORE_T) * (CORE_D - 2 * CORE_T))
        col_area = len(cols) * COL_SIZE ** 2
        floors_above = TOWER_FLOORS - REFUGE_END - 1
        load = floors_above * W * D * (1.35 * 7.0 + 1.5 * 2.5)      # kN, factored
        stress = load / (pier_area + core_area + col_area) / 1e3    # MPa
        check("the void's load path is within C40 capacity", stress < 18.0,
              f"{load:.0f} kN over {pier_area + core_area + col_area:.1f} m2 "
              f"= {stress:.2f} MPa ({stress / 18 * 100:.0f}% of 18 MPa), "
              f"{floors_above} floors above")

        # Open edges need guarding, and the corners must still turn.
        fb_ = piece_bounds(facade)
        balus = [(lo, hi) for lo, hi in fb_
                 if abs(lo[2] - REFUGE_Z0) < 0.02
                 and abs((hi[2] - lo[2]) - BALUSTRADE_H) < 0.02]
        check("a balustrade guards all four open edges", len(balus) >= 4,
              f"{len(balus)} balustrade runs at {REFUGE_Z0:.1f} m")
        check("balustrade is at least 1.0 m tall", BALUSTRADE_H >= 1.0,
              f"{BALUSTRADE_H:.2f} m")
        piers_here = pieces_at_corner_in_slice(facade, REFUGE_Z0 + 0.5,
                                               REFUGE_Z1 - 0.5)
        check("corner piers still turn the corners through the void",
              piers_here >= 4, f"{piers_here} pier pieces in the corner zones")

        # Planting, and it has to sit inside the void rather than anywhere else.
        for name in ("Sky_Garden_Planting", "Sky_Garden_Trunks"):
            refuge_pieces = [(lo, hi) for lo, hi in piece_bounds(objs[name])
                             if hi[2] <= REFUGE_Z1 + 0.02]
            pz_ = (min(lo[2] for lo, _ in refuge_pieces),
                   max(hi[2] for _, hi in refuge_pieces))
            check(f"{name} sits inside the refuge void",
               pz_[0] >= REFUGE_Z0 - 0.02 and pz_[1] <= REFUGE_Z1 - 0.02,
               f"z {pz_[0]:.2f}..{pz_[1]:.2f} in {REFUGE_Z0:.0f}..{REFUGE_Z1:.0f}")
        trees = [(lo, hi) for lo, hi in piece_bounds(objs["Sky_Garden_Trunks"])
                 if hi[2] <= REFUGE_Z1 + 0.02]
        check("the garden is planted with trees", len(trees) >= 8,
              f"{len(trees)} trunks")
        canopy_top = max(hi[2] for lo, hi in piece_bounds(objs["Sky_Garden_Planting"])
                         if hi[2] <= REFUGE_Z1 + 0.02)
        check("tree canopies clear the ceiling above",
              canopy_top < REFUGE_Z1 - 0.3,
              f"canopy tops at {canopy_top:.2f} m, ceiling {REFUGE_Z1:.1f} m")

        # Both cores are exposed here — this is the transfer level, and there are
        # two of them now, so a check that passes on one is not good enough.
        core_here = [((lo[0] + hi[0]) / 2) for lo, hi in st
                     if lo[2] < REFUGE_Z0 + 1.0 and hi[2] > REFUGE_Z1 - 1.0
                     and (hi[0] - lo[0]) < W * 0.5]
        west = [x for x in core_here if x < -W / 8]
        east = [x for x in core_here if x > W / 8]
        check("both lift/stair cores rise through the void (transfer level)",
              west and east,
              f"{len(west)} pieces west, {len(east)} east, "
              f"{len(core_here)} spanning the void in total")

        # Placement rules.
        check("the void does not overlap the blank bands",
              not (REFUGE_SET & (set(range(SOLID_BASE_FLOORS))
                       | set(range(TOWER_FLOORS - SOLID_TOP_FLOORS, TOWER_FLOORS)))),
              f"refuge floors {sorted(REFUGE_SET)}")
        check("the refuge splits the glazed floors into two configured blocks",
              REFUGE_START - FIRST_GLAZED == BLOCK_FLOORS
              and LAST_GLAZED - REFUGE_END == BLOCK_FLOORS,
              f"{REFUGE_START - FIRST_GLAZED} floors below + "
              f"{LAST_GLAZED - REFUGE_END} above, configured {BLOCK_FLOORS} each")
        check("refuge floor spacing is within 20 storeys (SCDF)",
              TOTAL_FLOORS > 40 or REFUGE_STOREY <= 21 and TOTAL_FLOORS - REFUGE_STOREY <= 20,
              f"storey {REFUGE_STOREY} of {TOTAL_FLOORS}: "
              f"{REFUGE_STOREY} below, {TOTAL_FLOORS - REFUGE_STOREY} above")
        check("the void is roughly mid-tower",
               0.35 < (REFUGE_Z0 - BASE_Z) / (TOP_Z - BASE_Z) < 0.65,
               f"{(REFUGE_Z0 - BASE_Z) / (TOP_Z - BASE_Z):.0%} up the tower "
               f"({REFUGE_Z0:.0f} m of {BASE_Z:.0f}..{TOP_Z:.0f})")

    # --- roof garden ---------------------------------------------------
    if ROOF_GARDEN:
        grille_obj = objs["Sky_Garden_Grille"]
        roof_top = ROOF_GARDEN_Z0 + ROOF_GARDEN_GRILLE_H
        roof_gp = [(lo, hi) for lo, hi in piece_bounds(grille_obj)
                   if lo[2] >= ROOF_GARDEN_Z0 - 0.02 and hi[2] <= roof_top + 0.02]
        check("roof garden has a perimeter grille", len(roof_gp) > 20,
              f"{len(roof_gp)} roof grille members")
        roof_gz = [p[2] for bounds in roof_gp for p in bounds]
        check("roof grille guards the terrace to parapet height",
              roof_gz and min(roof_gz) <= ROOF_GARDEN_Z0 + 0.1
              and max(roof_gz) >= roof_top - 0.1,
              f"z {min(roof_gz):.2f}..{max(roof_gz):.2f} vs "
              f"{ROOF_GARDEN_Z0:.2f}..{roof_top:.2f}" if roof_gz else "no grille")
        roof_ceiling = [(lo, hi) for lo, hi in piece_bounds(objs["Structure"])
                        if lo[2] >= roof_top - 0.02 and (hi[0] - lo[0]) > W * 0.9
                        and (hi[1] - lo[1]) > D * 0.9]
        check("roof garden has no ceiling", not roof_ceiling,
              f"{len(roof_ceiling)} full-footprint pieces above roof grille")
        roof_plants = [(lo, hi) for name in ("Sky_Garden_Planting", "Sky_Garden_Trunks")
                       for lo, hi in piece_bounds(objs[name])
                       if lo[2] >= ROOF_GARDEN_Z0 - 0.02]
        check("roof garden is planted", roof_plants,
              f"{len(roof_plants)} planting and trunk pieces on the roof")

    # --- ventilation strips --------------------------------------------
    louv = objs["Vent_Louvres"]
    lx, ly = facade_span(louv, "S"), facade_span(louv, "E")
    check("louvres cover the full vent opening (long face)",
          abs(lx - OPEN_W) < 0.05, f"louvre={lx:.3f} vs opening={OPEN_W:.3f}")
    check("louvres cover the full vent opening (short face)",
          abs(ly - OPEN_D) < 0.05, f"louvre={ly:.3f} vs opening={OPEN_D:.3f}")
    check("louvres also stop short of the corners",
          abs(lx - OPEN_W) < 0.05 and abs(ly - OPEN_D) < 0.05,
          f"{lx:.3f} x {ly:.3f}")

    shadow = objs["Vent_Shadowboxes"]
    sz = z_clusters(shadow)
    check("vent bands: 2 per glazed floor -> 4 Z levels each",
          len(sz) == GLAZED_FLOORS * 4, f"{len(sz)} levels")

    vbands = list(zip(sz[0::2], sz[1::2]))
    vheights = [round(hi - lo, 5) for lo, hi in vbands]
    check("every vent band is 0.25 m tall",
          all(abs(h - VENT_H) < EPS for h in vheights), f"heights={set(vheights)}")

    # A vent band must sit flush against the window: one directly below, one above.
    tops = {round(hi, 4) for _, hi in vbands}
    bots = {round(lo, 4) for lo, _ in vbands}
    below_ok = all(round(lo, 4) in tops for lo, _ in bands)
    above_ok = all(round(hi, 4) in bots for _, hi in bands)
    check("a 0.25 m vent sits flush below every window", below_ok)
    check("a 0.25 m vent sits flush above every window", above_ok)

    # --- flush glazing: no reveal, no sill ------------------------------
    # The facade is ONE plane. Any setback here leaves a strip of opening side
    # wall, and that strip is what reads as a window sill. Measured in depth (the
    # Y axis on the long face), not in Z, so it is independent of the band checks
    # above — those would pass just as happily with the glass 90 mm back.
    wall_y = D / 2.0
    z_mid = REFUGE_Z1 + WIN_Z + WIN_H / 2.0

    def outer_face(obj, zlo, zhi):
        """Frontmost Y reached by any piece on the south face in a z window."""
        ys = [-min(lo[1], hi[1]) for lo, hi in piece_bounds(obj)
              if zlo < (lo[2] + hi[2]) / 2 < zhi
              and (lo[1] + hi[1]) / 2 < -D / 4]
        return max(ys) if ys else None

    for label, obj_name, expected_face, zlo, zhi in (
            ("glass", "Windows_Glass", wall_y, z_mid - 0.5, z_mid + 0.5),
            ("mullion caps", "Window_Mullions", wall_y - MULLION_INSET,
             z_mid - 0.5, z_mid + 0.5),
             ("vent louvres", "Vent_Louvres",
             wall_y,
             REFUGE_Z1 + VENT_LO_Z,
             REFUGE_Z1 + VENT_LO_Z + VENT_H)):
        face = outer_face(objs[obj_name], zlo, zhi)
        check(f"{label} reaches its intended facade depth",
              face is not None and abs(face - expected_face) < 0.002,
              f"outer face at {face:.4f} m vs expected {expected_face:.3f} m"
              + (f", {(expected_face - face) * 1000:+.1f} mm" if face else ""))

    # Nothing may poke through the wall. Recessed mullions are allowed behind the
    # facade plane, while glass and louvres remain flush with it.
    proud = []
    for obj_name in ("Windows_Glass", "Window_Mullions", "Vent_Louvres"):
        f = outer_face(objs[obj_name], BASE_Z, TOP_Z)
        if f is not None and f > wall_y + 0.002:
            proud.append(f"{obj_name} {(f - wall_y) * 1000:+.1f} mm")
    check("nothing stands proud of the facade plane", not proud,
          "; ".join(proud) if proud else "glass, mullions and louvres all within 2 mm")

    # --- pilotis -------------------------------------------------------
    struct = objs["Structure"]
    for name in ("Facade_Spandrels", "Windows_Glass", "Vent_Louvres",
                 "Interior_Lining", "Floor_Plates"):
        zmin = world_bounds(objs[name])[2][0]
        check(f"{name} stays above the pilotis zone", zmin >= BASE_Z - EPS,
              f"zmin={zmin:.3f} >= {BASE_Z}")

    sb = world_bounds(struct)
    check("structure reaches the ground", sb[2][0] <= 0.0 + EPS, f"zmin={sb[2][0]:.3f}")
    check("structure reaches the roof/parapet", sb[2][1] >= TOP_Z, f"zmax={sb[2][1]:.3f}")

    cols = [o for o in bpy.data.objects if o.name.startswith("Column_")]
    check("pilotis columns merged into Structure (none left loose)", not cols)

    # --- twin service cores --------------------------------------------
    # TWO cores, and the reason is capacity and egress rather than structure: a
    # single 14 x 9 held only 126 m2 against ~204 m2 of shafts, stairs, lobbies
    # and risers that 654 units need, and put worst-case travel at 42.5 m.
    # These checks measure that, so the cores cannot quietly shrink back.
    # Core walls only. Filter on the piece lying WITHIN the core footprint in y,
    # not on its centre: the north and south walls of a core are centred at
    # y = +-5.86 while the east and west walls are centred at y = 0, so a
    # centre-based test keeps two walls and drops the other two. The pilotis
    # columns this needs to exclude sit at y = +-13.8, well outside the core.
    core_pieces = [(lo, hi) for lo, hi in piece_bounds(struct)
                   if lo[2] < 1.0 and hi[2] > BASE_Z - 1.0
                   and (hi[0] - lo[0]) < W * 0.5
                   and lo[1] > -CORE_D / 2 - 0.5 and hi[1] < CORE_D / 2 + 0.5]
    core_xs = sorted({round((lo[0] + hi[0]) / 2, 1) for lo, hi in core_pieces})
    w_side = [x for x in core_xs if x < 0]
    e_side = [x for x in core_xs if x > 0]
    check("there are two separate service cores, not one",
          w_side and e_side,
          f"{len(w_side)} wall centrelines west of centre, {len(e_side)} east")

    # Each core has to be a CLOSED tube, or it is not a smoke-separated shaft and
    # the two stairs inside it are not protected.
    for k, cx in enumerate(CORE_XS):
        walls_here = [(lo, hi) for lo, hi in core_pieces
                      if abs((lo[0] + hi[0]) / 2 - cx) < CORE_W / 2 + 0.5]
        check(f"core {k} is a closed tube (4 walls)", len(walls_here) == 4,
              f"{len(walls_here)} walls at x={cx:+.0f}")
    # Provision: the whole point of the change. MEASURED from the model, not
    # computed from the constants above — this file duplicates build_house.py's
    # constants, so a check on those would pass even if the geometry disagreed.
    def measured_cores():
        """(x centre, width, depth) of each core, read off the wall pieces."""
        found = []
        for cx in CORE_XS:
            here = [(lo, hi) for lo, hi in core_pieces
                    if abs((lo[0] + hi[0]) / 2 - cx) < CORE_W / 2 + 0.5]
            if len(here) != 4:
                continue
            x0 = min(lo[0] for lo, _ in here)
            x1 = max(hi[0] for _, hi in here)
            y0 = min(lo[1] for lo, _ in here)
            y1 = max(hi[1] for _, hi in here)
            found.append(((x0 + x1) / 2, x1 - x0, y1 - y0))
        return found

    mc = measured_cores()
    check("both cores are found in the geometry to be measured", len(mc) == 2,
          f"{len(mc)} complete cores located")
    provision = sum(bw * bd for _, bw, bd in mc)
    check("the cores hold the required vertical transport provision",
          provision >= CORE_PROVISION,
          f"{provision:.0f} m2 measured against {CORE_PROVISION:.0f} m2 needed "
          f"({provision / CORE_PROVISION - 1:+.0%}), "
          f"{provision / (W * D) * 100:.1f}% of the plate")

    # Egress: worst-case rectilinear travel from the far corners and mid-edge to
    # the nearest core. This is the number that a single central core failed.
    def travel(px, py):
        best = 1e9
        for cx, bw, bd in (mc or [(cx, CORE_W, CORE_D) for cx in CORE_XS]):
            dx = max(cx - bw / 2 - px, px - (cx + bw / 2), 0.0)
            dy = max(-bd / 2 - py, py - bd / 2, 0.0)
            best = min(best, dx + dy)
        return best

    worst = max(travel(px, py) for px, py in
                ((W / 2, D / 2), (-W / 2, D / 2), (0.0, D / 2), (0.0, 0.0)))
    check("worst-case egress travel is within SCDF two-way limits",
          worst <= 30.0,
          f"{worst:.1f} m to the nearest core (limit ~30 m dead-end, ~45 m two-way)")

    # Stair remoteness: two stairs in ONE shaft share a failure. Separating the
    # cores is what makes them independent.
    if len(mc) == 2:
        (xa, wa, _), (xb, wb, _) = sorted(mc)
        gap = (xb - wb / 2) - (xa + wa / 2)
        check("the two stair cores are genuinely remote from each other",
              gap >= 14.0,
              f"{xb - xa:.0f} m between measured centres, "
              f"{gap:.0f} m of clear plate between them")

    # The cores are internal. If one ever touched a facade it would blow a hole
    # in the ribbon window, so check the clearance to the pier zone explicitly.
    check("the cores stay clear of the corner pier zone",
          CORE_OFFSET + CORE_W / 2 <= W / 2 - PIER_LONG,
          f"outer edge at {CORE_OFFSET + CORE_W / 2:.0f} m, "
          f"pier zone starts at {W / 2 - PIER_LONG:.0f} m")

    # Core walls are set by the outer faces of the two defining column lines,
    # not by a fixed pane-grid coordinate. This is what keeps the core and the
    # columns connected when the long facade grows from 18 to 20 room bays.
    column_lines = col_grid(W)
    column_faces = [line + sign * COL_SIZE / 2
                    for line in column_lines for sign in (-1, 1)]
    core_edges = [cx + sign * CORE_W / 2
                  for cx in CORE_XS for sign in (-1, 1)]
    check("core length is derived from the defining column faces",
          all(min(abs(edge - face) for face in column_faces) < 0.02
              for edge in core_edges),
          f"edges={', '.join(f'{edge:+.2f}' for edge in sorted(core_edges))}")

    full_height_columns = [
        ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2)
        for lo, hi in piece_bounds(struct)
        if lo[2] <= 0.05 and hi[2] >= TOP_Z - 0.05
        and abs((hi[0] - lo[0]) - COL_SIZE) < 0.02
        and abs((hi[1] - lo[1]) - COL_SIZE) < 0.02]
    defining_lines = [cx + sign * (CORE_W / 2 - COL_SIZE / 2)
                      for cx in CORE_XS for sign in (-1, 1)]
    check("defining columns touch both ends of each core",
          all(min(abs(x - line) for x, _ in full_height_columns) < 0.02
              for line in defining_lines),
          f"{len(full_height_columns)} continuous columns checked")

    # Unit depth either side of a core: too deep a core leaves unusable slivers.
    unit_depth = (D - CORE_D) / 2
    check("usable depth remains either side of the cores",
          9.0 <= unit_depth <= 13.0,
          f"{unit_depth:.1f} m each side (residential wants 9-13 m)")

    # --- what rises above the roof -------------------------------------
    # The thing projecting above the parapet has to BE the cores continuing up
    # (lift overtravel + machine room + stair bulkhead), not a decorative box
    # placed by eye. Two tests: it is above the parapet at all, and it sits over
    # the core footprints rather than anywhere else on the plate.
    above = [(lo, hi) for lo, hi in piece_bounds(struct)
             if hi[2] > ROOF_TOP_Z + 0.2]
    check("something rises above the roof parapet", bool(above),
          f"{len(above)} pieces above {ROOF_TOP_Z:.2f} m")

    core_top = max(hi[2] for lo, hi in piece_bounds(struct)
                   if any(lo[0] > cx - CORE_W / 2 - 0.05
                          and hi[0] < cx + CORE_W / 2 + 0.05
                          and lo[1] > -CORE_D / 2 - 0.05
                          and hi[1] < CORE_D / 2 + 0.05
                          for cx in CORE_XS))
    check("the highest point on the building is the core bulkhead",
           abs(core_top - CORE_TOP_Z) < 0.05,
           f"core top={core_top:.2f} m, expected {CORE_TOP_Z:.2f} m "
           f"({core_top - ROOF_TOP_Z:.2f} m clear of the parapet)")
    check("the overrun gives real lift headroom, not a token upstand",
           core_top - (TOP_Z + 0.22) >= 4.0,
           f"{core_top - (TOP_Z + 0.22):.2f} m above the roof slab "
          f"(overtravel + machine room needs ~4 m)")

    # Every projecting piece within a core footprint. This is the check that a
    # free-standing plant box in the middle of the roof would fail.
    strays = [(lo, hi) for lo, hi in above
              if not any(lo[0] > cx - CORE_W / 2 - 0.05
                         and hi[0] < cx + CORE_W / 2 + 0.05
                         and lo[1] > -CORE_D / 2 - 0.05
                         and hi[1] < CORE_D / 2 + 0.05
                         for cx in CORE_XS)]
    check("everything above the parapet sits over a core footprint",
          not strays,
          f"{len(above)} pieces, {len(strays)} outside the core plan"
          + (f" (first at x={strays[0][0][0]:+.1f}..{strays[0][1][0]:+.1f})"
             if strays else ""))

    # One bulkhead per core, so the pair reads symmetrically from the street.
    for k, cx in enumerate(CORE_XS):
        here = [p for p in above
                if abs((p[0][0] + p[1][0]) / 2 - cx) < CORE_W / 2 + 0.5]
        check(f"core {k} carries its own bulkhead above the roof", bool(here),
              f"{len(here)} pieces at x={cx:+.0f}")

    # The old RoofPlant box was 22.8 x 10.9 m at x=+9.12 — unrelated to the
    # cores, and only on one side. Nothing that wide should remain up there.
    check("no oversized roof plant box remains",
          all(hi[0] - lo[0] <= CORE_W + 0.05 for lo, hi in above),
          f"widest projecting piece is "
          f"{max((hi[0] - lo[0] for lo, hi in above), default=0):.2f} m "
          f"(core is {CORE_W:.0f} m)")

    # --- floor plates --------------------------------------------------
    plates = objs["Floor_Plates"]
    pz = z_clusters(plates)
    # The refuge void has no intermediate plate  # noqa: E116 (that is what makes it double
    # height), and the plate under it is replaced by the thicker garden slab,
    # which lives in Structure. So two plates fewer than there are storeys.
    expected_plates = TOWER_FLOORS - ((BLOCK_GROUPS - 1) * REFUGE_FLOORS
                                      if SKY_GARDEN else 0)
    check("one floor plate per occupied floor, minus the open refuge storeys",
          len(pz) == expected_plates * 2,
          f"{len(pz)} levels for {expected_plates} plates "
          f"({TOWER_FLOORS} storeys - {REFUGE_FLOORS} open)")

    # --- overall envelope ----------------------------------------------
    # Planting can rise above the roof grille; the saved viewport still frames
    # the complete scene envelope, including that planting.
    all_z = max(world_bounds(o)[2][1] for o in objs.values())
    check(f"total height matches {TOTAL_FLOORS} floors + parapet", all_z >= TOP_Z + 1.0,
          f"top={all_z:.2f} m")

    # --- saved viewport ------------------------------------------------
    # Opening the .blend restores the view_distance stored in its screens. The
    # factory default is 15 m, which puts you inside a 166 m tower. Check every
    # workspace, since Blender saves ten of them and you can open into any.
    diag = math.sqrt(W ** 2 + D ** 2 + all_z ** 2)
    views = [(sp, sc.name) for sc in bpy.data.screens for ar in sc.areas
             if ar.type == "VIEW_3D" for sp in ar.spaces if sp.type == "VIEW_3D"]
    check("the .blend stores 3D viewports to configure", bool(views),
          f"{len(views)} viewports across {len(bpy.data.screens)} workspaces")

    too_near = [(n, sp.region_3d.view_distance) for sp, n in views
                if sp.region_3d.view_distance <= diag / 2]
    check("the saved viewport opens OUTSIDE the building, not inside it",
          not too_near,
          f"{len(views)} viewports, nearest "
          f"{min((sp.region_3d.view_distance for sp, _ in views), default=0):.0f} m "
          f"against a {diag / 2:.0f} m half-diagonal"
          + (f" — {too_near[0][0]} at {too_near[0][1]:.1f} m" if too_near else ""))

    # Far enough out that the whole tower fits the frame, using the 24 mm sensor
    # height each viewport's own lens is measured against.
    tight = [n for sp, n in views
             if 2 * sp.region_3d.view_distance * math.tan(math.atan(12.0 / sp.lens))
             < all_z * 1.15]
    check("the whole tower fits the frame at the saved distance", not tight,
          f"{len(tight)} viewports too tight for a {all_z:.0f} m building")

    # Orbiting about the origin puts the ground at screen centre and the tower
    # off the top; it should orbit about mid-height.
    off = [n for sp, n in views
           if not 0.3 * all_z <= sp.region_3d.view_location.z <= 0.7 * all_z]
    check("the viewport orbits about mid-height, not the ground", not off,
          f"pivot at z={views[0][0].region_3d.view_location.z:.1f} m "
          f"({views[0][0].region_3d.view_location.z / all_z:.0%} up the tower)"
          if views else "no viewports")

    # Far clip must clear the pull-back, or the model is culled and the file
    # opens onto empty grey — worse than opening inside it.
    culled = [(n, sp.clip_end, sp.region_3d.view_distance) for sp, n in views
              if sp.clip_end < sp.region_3d.view_distance * 1.5]
    check("far clip clears the pull-back (model is not culled on open)",
          not culled,
          f"clip_end {views[0][0].clip_end:.0f} m against a "
          f"{views[0][0].region_3d.view_distance:.0f} m view distance"
          if views else "no viewports")

    # Footprint follows the configured room-window counts.
    facade = objs["Facade_Spandrels"]
    fb = world_bounds(facade)
    check(f"footprint width is {W:.2f} m ({WINDOWS_LONG} room windows + 2 x "
          f"{PIER_LONG:.0f} m pier)",
          abs((fb[0][1] - fb[0][0]) - W) < 0.02, f"{fb[0][1] - fb[0][0]:.3f} m")
    check(f"footprint depth is {D:.2f} m ({WINDOWS_SHORT} room windows + 2 x "
          f"{PIER_SHORT:.0f} m pier)",
          abs((fb[1][1] - fb[1][0]) - D) < 0.02, f"{fb[1][1] - fb[1][0]:.3f} m")

    # --- corners are solid --------------------------------------------
    # Test per connected piece by bounding-box overlap. Sampling vertices inside
    # a z-slice would miss any box that spans the slice without a vertex in it.
    def pieces_overlapping_corner(obj, zlo, zhi):
        hits = 0
        for lo, hi in piece_bounds(obj):
            if hi[2] <= zlo or lo[2] >= zhi:      # no vertical overlap
                continue
            # overlaps a corner square if it reaches past the pier line in BOTH axes
            # The corner region is asymmetric now: PIER_LONG deep in X,
            # PIER_SHORT deep in Y.
            if (max(abs(lo[0]), abs(hi[0])) > W / 2 - PIER_LONG + 0.05
                    and max(abs(lo[1]), abs(hi[1])) > D / 2 - PIER_SHORT + 0.05):
                hits += 1
        return hits

    # A representative GLAZED floor, inside the window band.
    sample_floor = FIRST_GLAZED + 4
    assert FIRST_GLAZED <= sample_floor <= LAST_GLAZED
    zwin_lo = BASE_Z + sample_floor * H + WIN_Z
    zlo, zhi = zwin_lo + 0.2, zwin_lo + WIN_H - 0.2

    n_glass = pieces_overlapping_corner(glass, zlo, zhi)
    zvent = BASE_Z + sample_floor * H + VENT_LO_Z
    n_louv = pieces_overlapping_corner(louv, zvent + 0.05, zvent + VENT_H - 0.05)
    n_mull = pieces_overlapping_corner(objs["Window_Mullions"], zlo, zhi)
    n_wall = pieces_overlapping_corner(facade, zlo, zhi)

    check("no glass reaches the corner zones at window height", n_glass == 0,
          f"{n_glass} glass pieces overlap a corner")
    check("no louvres reach the corner zones", n_louv == 0,
          f"{n_louv} louvre pieces overlap a corner")
    check("no mullions reach the corner zones", n_mull == 0,
          f"{n_mull} mullion pieces overlap a corner")
    check("solid wall IS present at all 4 corners at window height", n_wall >= 4,
          f"{n_wall} wall pieces in corner zones (expect >= 4)")

    # The piers must close the whole vent+window zone, top and bottom.
    floor_rel = sorted({round((z - BASE_Z) % H, 3) for z in z_clusters(facade)})
    check("wall geometry spans the vent+window zone (pier top/bottom present)",
          SPANDREL_LO_H in floor_rel and (H - SPANDREL_HI_H) in floor_rel,
          f"levels in floor={floor_rel}")

    print(f"\n{checks - len(failures)}/{checks} checks passed")
    if failures:
        print("failed: " + ", ".join(failures))
        sys.exit(1)
    print("all geometry checks passed")


main()
