"""Geometry checks for the generated high-rise house.

Run headless:
    blender --background --factory-startup \
        --python verify_house.py -- out/highrise_house.blend
"""

import sys

import bpy

W, D, H = 20.0, 14.0, 4.0
PILOTIS_FLOORS, TOWER_FLOORS = 3, 12
WIN_H, VENT_H = 1.50, 0.30
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
    check("glass forms 2 Z levels per floor", len(gz) == TOWER_FLOORS * 2,
          f"{len(gz)} levels")

    bands = list(zip(gz[0::2], gz[1::2]))
    heights = [round(hi - lo, 5) for lo, hi in bands]
    check("every window is 1.50 m tall",
          all(abs(h - WIN_H) < EPS for h in heights), f"heights={set(heights)}")

    centres_rel = [round(((lo + hi) / 2 - BASE_Z) % H, 5) for lo, hi in bands]
    check("every window is vertically centred in its floor",
          all(abs(c - H / 2) < EPS for c in centres_rel),
          f"centre offsets={set(centres_rel)}")

    floors_seen = sorted({int(((lo + hi) / 2 - BASE_Z) // H) for lo, hi in bands})
    check("one window band per occupied floor",
          floors_seen == list(range(TOWER_FLOORS)), f"floors={floors_seen}")

    # The ribbon wraps all four facades, so it must cover essentially the whole
    # footprint in both axes (allowing only the facade inset).
    gb = world_bounds(glass)
    x_span, y_span = gb[0][1] - gb[0][0], gb[1][1] - gb[1][0]
    check("glazing spans the full building width (X)", x_span >= W * 0.98,
          f"span={x_span:.3f} m of {W} m footprint ({x_span / W:.1%})")
    check("glazing spans the full building depth (Y)", y_span >= D * 0.98,
          f"span={y_span:.3f} m of {D} m footprint ({y_span / D:.1%})")
    check("glazing starts at the first occupied floor",
          abs(gb[2][0] - (BASE_Z + 1.25)) < EPS, f"lowest glass z={gb[2][0]:.3f}")

    # --- ventilation strips --------------------------------------------
    louv = objs["Vent_Louvres"]
    lb = world_bounds(louv)
    check("louvres match the window width in X",
          abs((lb[0][1] - lb[0][0]) - (gb[0][1] - gb[0][0])) < 0.35,
          f"louvre X span={lb[0][1] - lb[0][0]:.3f} vs glass {gb[0][1] - gb[0][0]:.3f}")
    check("louvres match the window depth in Y",
          abs((lb[1][1] - lb[1][0]) - (gb[1][1] - gb[1][0])) < 0.35,
          f"louvre Y span={lb[1][1] - lb[1][0]:.3f} vs glass {gb[1][1] - gb[1][0]:.3f}")

    shadow = objs["Vent_Shadowboxes"]
    sz = z_clusters(shadow)
    check("vent bands: 2 per floor -> 4 Z levels per floor",
          len(sz) == TOWER_FLOORS * 4, f"{len(sz)} levels")

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
    check("one floor plate per occupied floor", len(pz) == TOWER_FLOORS * 2,
          f"{len(pz)} levels")

    # --- overall envelope ----------------------------------------------
    all_z = max(world_bounds(o)[2][1] for o in objs.values())
    check("total height matches 15 floors + parapet", all_z >= TOP_Z + 1.0,
          f"top={all_z:.2f} m")

    print(f"\n{checks - len(failures)}/{checks} checks passed")
    if failures:
        print("failed: " + ", ".join(failures))
        sys.exit(1)
    print("all geometry checks passed")


main()
