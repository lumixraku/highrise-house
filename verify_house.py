"""Geometry checks for the generated high-rise house.

Run headless:
    blender --background --factory-startup \
        --python verify_house.py -- out/highrise_house.blend
"""

import sys

import bpy

W, D, H = 70.0, 30.0, 4.0
TOTAL_FLOORS = 40
PILOTIS_FLOORS = 3
TOWER_FLOORS = TOTAL_FLOORS - PILOTIS_FLOORS
WIN_H, VENT_H = 1.50, 0.30
CORNER_PIER = 4.0
OPEN_W, OPEN_D = W - 2 * CORNER_PIER, D - 2 * CORNER_PIER
SPANDREL_H = (H - WIN_H - 2 * VENT_H) / 2.0
VENT_LO_Z = SPANDREL_H
WIN_Z = VENT_LO_Z + VENT_H
MULLION_W = 0.09
WINDOWS_LONG = 30
PANE_GLASS_LONG = (OPEN_W - (WINDOWS_LONG + 1) * MULLION_W) / WINDOWS_LONG
PANE_PITCH = PANE_GLASS_LONG + MULLION_W
WINDOWS_SHORT = max(1, round((OPEN_D - MULLION_W) / PANE_PITCH))
SOLID_BASE_FLOORS = 1
SOLID_TOP_FLOORS = 2
GLAZED_FLOORS = TOWER_FLOORS - SOLID_BASE_FLOORS - SOLID_TOP_FLOORS
FIRST_GLAZED = SOLID_BASE_FLOORS
LAST_GLAZED = TOWER_FLOORS - SOLID_TOP_FLOORS - 1
BASE_Z = PILOTIS_FLOORS * H
TOP_Z = BASE_Z + TOWER_FLOORS * H
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
                 "Vent_Louvres", "Vent_Shadowboxes", "Floor_Plates", "Structure"):
        check(f"object present: {name}", name in objs)
    if failures:
        sys.exit(1)

    # --- windows -------------------------------------------------------
    glass = objs["Windows_Glass"]
    gz = z_clusters(glass)
    check("glass forms 2 Z levels per glazed floor", len(gz) == GLAZED_FLOORS * 2,
          f"{len(gz)} levels for {GLAZED_FLOORS} glazed floors")

    bands = list(zip(gz[0::2], gz[1::2]))
    heights = [round(hi - lo, 5) for lo, hi in bands]
    check("every window is 1.50 m tall",
          all(abs(h - WIN_H) < EPS for h in heights), f"heights={set(heights)}")

    centres_rel = [round(((lo + hi) / 2 - BASE_Z) % H, 5) for lo, hi in bands]
    check("every window is vertically centred in its floor",
          all(abs(c - H / 2) < EPS for c in centres_rel),
          f"centre offsets={set(centres_rel)}")

    floors_seen = sorted({int(((lo + hi) / 2 - BASE_Z) // H) for lo, hi in bands})
    check("one window band per glazed floor, none on the blank floors",
          floors_seen == list(range(FIRST_GLAZED, LAST_GLAZED + 1)),
          f"glazed floors={floors_seen[0]}..{floors_seen[-1]} ({len(floors_seen)})")

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

    # The ribbon stops CORNER_PIER short of every corner. The joined object's
    # overall bbox cannot show this (the E/W panes fix the X extent at ~W), so
    # each facade must be measured on its own.
    gb = world_bounds(glass)
    x_span, y_span = facade_span(glass, "S"), facade_span(glass, "E")
    check(f"long-face glazing stops {CORNER_PIER} m short of both corners",
          abs(x_span - OPEN_W) < 0.02,
          f"opening={x_span:.3f} m, expected {OPEN_W:.3f} m")
    check(f"short-face glazing stops {CORNER_PIER} m short of both corners",
          abs(y_span - OPEN_D) < 0.02,
          f"opening={y_span:.3f} m, expected {OPEN_D:.3f} m")
    check("all four facades have the same pier width",
          abs((W - x_span) / 2 - CORNER_PIER) < 0.02
          and abs((D - y_span) / 2 - CORNER_PIER) < 0.02,
          f"long {(W - x_span) / 2:.3f} m, short {(D - y_span) / 2:.3f} m")
    check("window is still the majority of each facade",
          x_span / W > 0.6 and y_span / D > 0.6,
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
    check(f"clear glass per pane is {PANE_GLASS_LONG:.4f} m",
          abs(pitches[0] - MULLION_W - PANE_GLASS_LONG) < 1e-3,
          f"{pitches[0] - MULLION_W:.4f} m between mullion faces")
    # End mullions must sit wholly inside the opening, flush to the pier face,
    # not straddling the opening edge with half their width inside the pier.
    edge = OPEN_W / 2 - MULLION_W / 2
    check("end mullions sit flush inside the opening, not inside the pier",
          abs(min(xs) + edge) < 1e-3 and abs(max(xs) - edge) < 1e-3,
          f"first={min(xs):.4f}, last={max(xs):.4f}, expected +/-{edge:.4f}")
    check("30 panes of glass + 31 mullions fill the opening exactly",
          abs(WINDOWS_LONG * PANE_GLASS_LONG
              + (WINDOWS_LONG + 1) * MULLION_W - OPEN_W) < 1e-6,
          f"{WINDOWS_LONG} x {PANE_GLASS_LONG:.4f} + 31 x {MULLION_W} = {OPEN_W:.4f} m")

    # --- ventilation strips --------------------------------------------
    louv = objs["Vent_Louvres"]
    lx, ly = facade_span(louv, "S"), facade_span(louv, "E")
    check("louvres are the same length as the window (long face)",
          abs(lx - x_span) < 0.05, f"louvre={lx:.3f} vs glass={x_span:.3f}")
    check("louvres are the same length as the window (short face)",
          abs(ly - y_span) < 0.05, f"louvre={ly:.3f} vs glass={y_span:.3f}")
    check("louvres also stop short of the corners",
          abs(lx - OPEN_W) < 0.05 and abs(ly - OPEN_D) < 0.05,
          f"{lx:.3f} x {ly:.3f}")

    shadow = objs["Vent_Shadowboxes"]
    sz = z_clusters(shadow)
    check("vent bands: 2 per glazed floor -> 4 Z levels each",
          len(sz) == GLAZED_FLOORS * 4, f"{len(sz)} levels")

    vbands = list(zip(sz[0::2], sz[1::2]))
    vheights = [round(hi - lo, 5) for lo, hi in vbands]
    check("every vent band is 0.30 m tall",
          all(abs(h - VENT_H) < EPS for h in vheights), f"heights={set(vheights)}")

    # A vent band must sit flush against the window: one directly below, one above.
    tops = {round(hi, 4) for _, hi in vbands}
    bots = {round(lo, 4) for lo, _ in vbands}
    below_ok = all(round(lo, 4) in tops for lo, _ in bands)
    above_ok = all(round(hi, 4) in bots for _, hi in bands)
    check("a 0.30 m vent sits flush below every window", below_ok)
    check("a 0.30 m vent sits flush above every window", above_ok)

    # --- pilotis -------------------------------------------------------
    struct = objs["Structure"]
    for name in ("Facade_Spandrels", "Windows_Glass", "Vent_Louvres", "Floor_Plates"):
        zmin = world_bounds(objs[name])[2][0]
        check(f"{name} stays above the pilotis zone", zmin >= BASE_Z - EPS,
              f"zmin={zmin:.3f} >= {BASE_Z}")

    sb = world_bounds(struct)
    check("structure reaches the ground", sb[2][0] <= 0.0 + EPS, f"zmin={sb[2][0]:.3f}")
    check("structure reaches the roof/parapet", sb[2][1] >= TOP_Z, f"zmax={sb[2][1]:.3f}")

    cols = [o for o in bpy.data.objects if o.name.startswith("Column_")]
    check("pilotis columns merged into Structure (none left loose)", not cols)

    # --- floor plates --------------------------------------------------
    plates = objs["Floor_Plates"]
    pz = z_clusters(plates)
    check("one floor plate per occupied floor, blank ones included",
          len(pz) == TOWER_FLOORS * 2, f"{len(pz)} levels")

    # --- overall envelope ----------------------------------------------
    all_z = max(world_bounds(o)[2][1] for o in objs.values())
    check(f"total height matches {TOTAL_FLOORS} floors + parapet", all_z >= TOP_Z + 1.0,
          f"top={all_z:.2f} m")

    # Footprint must actually be the requested 70 x 30 m.
    facade = objs["Facade_Spandrels"]
    fb = world_bounds(facade)
    check("footprint width is 70 m", abs((fb[0][1] - fb[0][0]) - W) < 0.02,
          f"{fb[0][1] - fb[0][0]:.3f} m")
    check("footprint depth is 30 m", abs((fb[1][1] - fb[1][0]) - D) < 0.02,
          f"{fb[1][1] - fb[1][0]:.3f} m")

    # --- corners are solid --------------------------------------------
    # Test per connected piece by bounding-box overlap. Sampling vertices inside
    # a z-slice would miss any box that spans the slice without a vertex in it.
    def pieces_overlapping_corner(obj, zlo, zhi):
        hits = 0
        for lo, hi in piece_bounds(obj):
            if hi[2] <= zlo or lo[2] >= zhi:      # no vertical overlap
                continue
            # overlaps a corner square if it reaches past the pier line in BOTH axes
            if (max(abs(lo[0]), abs(hi[0])) > W / 2 - CORNER_PIER + 0.05
                    and max(abs(lo[1]), abs(hi[1])) > D / 2 - CORNER_PIER + 0.05):
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
          0.95 in floor_rel and 3.05 in floor_rel, f"levels in floor={floor_rel}")

    print(f"\n{checks - len(failures)}/{checks} checks passed")
    if failures:
        print("failed: " + ", ".join(failures))
        sys.exit(1)
    print("all geometry checks passed")


main()
