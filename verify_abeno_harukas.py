"""Verify the generated Abeno Harukas scene's documented hard constraints."""

import os
import sys

import bpy


def bounds(obj):
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    return tuple((min(getattr(p, axis) for p in points),
                  max(getattr(p, axis) for p in points))
                 for axis in ("x", "y", "z"))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    blend_path = argv[0] if argv else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "out", "abeno_harukas.blend")
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene
    objects = {obj.name: obj for obj in bpy.data.objects}

    checks = []
    checks.append(("documented architectural height", scene.get("source_height_m") == 300.0))
    checks.append(("documented floor count", scene.get("source_floor_count") == 60))
    checks.append(("annex and three tower facade volumes", all(
        f"{name}_Glass_S" in objects for name in ("Annex", "Lower", "Middle", "Upper"))))
    checks.append(("grounded west annex represented", "Annex_Glass_S" in objects and
                   abs(bounds(objects["Annex_Glass_S"])[2][0]) < 0.01 and
                   bounds(objects["Annex_Glass_S"])[0][0] <
                   bounds(objects["Lower_Glass_S"])[0][0]))
    checks.append(("two exposed megatruss zones", all(any(
        obj.name.startswith(prefix) for obj in objects.values())
        for prefix in ("Lower_Megatruss", "Middle_Megatruss"))))
    checks.append(("two setback sky gardens", all(
        name in objects for name in ("Lower_Sky_Garden_Terrace",
                                     "Middle_Sky_Garden_Terrace"))))
    roof = objects.get("Roof_Helipad")
    checks.append(("roof reaches 300 m", roof is not None and abs(bounds(roof)[2][1] - 300.0) < 0.01))
    checks.append(("plan dimensions labelled approximate",
                   str(scene.get("plan_dimension_status", "")).startswith("Approximate")))
    east_edges = [bounds(objects[f"{name}_Glass_S"])[0][1]
                  for name in ("Lower", "Middle", "Upper")]
    checks.append(("three tower tiers share east edge",
                   max(east_edges) - min(east_edges) < 0.01))
    lower = objects["Lower_Glass_S"]
    middle = objects["Middle_Glass_S"]
    upper = objects["Upper_Glass_S"]
    tier_names = ("Lower", "Middle", "Upper")
    tier_widths = [bounds(objects[f"{name}_Glass_S"])[0][1] -
                   bounds(objects[f"{name}_Glass_S"])[0][0]
                   for name in tier_names]
    tier_depths = [bounds(objects[f"{name}_Glass_W"])[1][1] -
                   bounds(objects[f"{name}_Glass_W"])[1][0]
                   for name in tier_names]
    tier_centers_y = [sum(bounds(objects[f"{name}_Glass_W"])[1]) / 2.0
                      for name in tier_names]
    checks.append(("section-derived tier heights",
                   abs(bounds(lower)[2][1] - 80.0) < 0.01 and
                   abs(bounds(middle)[2][0] - 80.0) < 0.01 and
                   abs(bounds(middle)[2][1] - 195.0) < 0.01 and
                   abs(bounds(upper)[2][0] - 195.0) < 0.01))
    checks.append(("three tiers are long thin bars in plan",
                   all(width / depth >= ratio for width, depth, ratio in zip(
                       tier_widths, tier_depths, (1.75, 2.0, 2.5)))))
    checks.append(("short dimension steps back and shifts north",
                   tier_depths[0] > tier_depths[1] > tier_depths[2] and
                   tier_centers_y[0] < tier_centers_y[1] < tier_centers_y[2]))
    checks.append(("lower and middle facade recesses", all(
        name in objects for name in ("Lower_Facade_Recess", "Middle_Facade_Recess"))))
    checks.append(("upper shaft narrower than middle shaft", objects["Upper_Glass_S"].dimensions.x <
                   objects["Middle_Glass_S"].dimensions.x))
    checks.append(("orthographic review cameras", all(
        name in objects and objects[name].data.type == "ORTHO"
        for name in ("Harukas_Front_Camera", "Harukas_Side_Camera"))))

    failed = [name for name, passed in checks if not passed]
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}: {name}")
    if failed:
        raise SystemExit(f"{len(failed)} verification checks failed")
    print(f"All {len(checks)} checks passed")


main()
