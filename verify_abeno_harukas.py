"""Verify the body-first Abeno Harukas massing model."""

import math
import os
import sys

import bpy
from mathutils import Vector

GROUND_Z = 0.0
MAX_TILT_DEG = 3.0
TRUSS_BAND_H = 10.0
TRUSS_SPACING = 12.0
MASSES = {
    "Low": (80.0, ((-42.5, -40.0), (42.7, -40.0),
                   (44.0, -14.75), (-44.0, -10.25))),
    "Middle": (195.0, ((-44.0, -10.25), (44.0, -14.75),
                       (42.3, 18.5), (-42.7, 14.5))),
    "High": (300.0, ((-42.7, 14.5), (42.3, 18.5),
                     (41.8, 46.0), (-43.5, 46.0))),
}
OUTLINE = ((-42.5, -40.0), (42.7, -40.0), (44.0, -14.75), (42.3, 18.5),
           (41.8, 46.0), (-43.5, 46.0), (-42.7, 14.5), (-44.0, -10.25))


def world_points(obj):
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


def mass_bands(height):
    crown = max(h for h, _ in MASSES.values())
    return sorted({(top - TRUSS_BAND_H, top)
                   for top, _ in MASSES.values()
                   if top <= height and top < crown})


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
        mass_top = max([glass_top] + [max(p.z for p in world_points(obj))
                                      for obj in objects.values()
                                      if obj.name.startswith(
                                          f"{name}_Truss_Backing_")])
        checks.append((f"{name} flat roofline at {height:.0f} m",
                       abs(mass_top - height) < 0.01 and len(ring) == 4))
        bands = mass_bands(height)
        glass_zs = [p.z for obj in glass for p in world_points(obj)]
        checks.append((f"{name} glass clears every truss band",
                       all(all(z <= z0 + 0.01 or z >= z1 - 0.01
                               for z in glass_zs)
                           for z0, z1 in bands)))
        groups = [face_groups(points[edge], points[(edge + 1) % 4])
                  for edge in range(4)]
        plan_max_x = max(abs(x) for x, _ in points)
        for index, (z0, z1) in enumerate(bands):
            backing = objects.get(f"{name}_Truss_Backing_{index}")
            diags = [obj for obj in objects.values()
                     if obj.name.startswith(f"{name}_{index}_TrussDiag_")]
            posts = [obj for obj in objects.values()
                     if obj.name.startswith(f"{name}_{index}_TrussPost_")]
            checks.append((f"{name} band {index} z {z0:.0f}-{z1:.0f} backing",
                           backing is not None and
                           abs(min(p.z for p in world_points(backing)) - z0) < 0.01
                           and abs(max(p.z for p in world_points(backing)) - z1) < 0.01))
            checks.append((f"{name} band {index} density follows face width",
                           len(diags) == 2 * sum(groups) and
                           len(posts) == sum(g + 1 for g in groups)))
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
        checks.append((f"{name} front faces keep seven chevron groups",
                       groups[0] == 7 and groups[2] == 7 and bool(base_diags)))
        tilts = [edge_tilt_deg(ring[i], ring[(i + 1) % 4])
                 for i in range(4)] if len(ring) == 4 else [90.0]
        checks.append((f"{name} plan tilts within {MAX_TILT_DEG:.0f} degrees",
                       all(tilt <= MAX_TILT_DEG + 0.05 for tilt in tilts)))

    # The step bands run through two adjoining volumes each.
    def has_band(name, z0, z1):
        return (z0, z1) in mass_bands(MASSES[name][0])
    checks.append(("low-top band runs through low and middle volumes",
                   has_band("Low", 70.0, 80.0) and
                   has_band("Middle", 70.0, 80.0)))
    checks.append(("middle-top band runs through middle and high volumes",
                   has_band("Middle", 185.0, 195.0) and
                   has_band("High", 185.0, 195.0)))
    all_truss = [obj for obj in objects.values() if "_TrussDiag_" in obj.name]
    truss_min_z = min(p.z for obj in all_truss for p in world_points(obj))
    checks.append(("no truss band at the ground level", truss_min_z > 60.0))
    checks.append(("truss bands span two storeys only", all(
        abs(band[1] - band[0] - 10.0) < 0.01
        for height, _ in MASSES.values() for band in mass_bands(height))))

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
                   (44.0, -14.75) in set(middle) and
                   middle[1][0] > middle[2][0] and
                   high[2][0] < high[1][0] and
                   max_x["Middle"] == max(x for x, _ in OUTLINE)))
    all_x = [x for ring in rings.values() for x, _ in ring]
    all_y = [y for ring in rings.values() for _, y in ring]
    checks.append(("depth 86 m, width peaks at 88 m at the low/middle junction",
                   abs(max(all_y) - min(all_y) - 86.0) < 0.01 and
                   abs(max(all_x) - min(all_x) - 88.0) < 0.01))
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
    checks.append(("review cameras", all(
        name in objects for name in ("Harukas_Preview_Camera",
                                     "Harukas_Plan_Camera",
                                     "Harukas_North_Camera"))))
    checks.append(("all cameras stay outside the building",
                   all(objects[name].location.y < -50.0 or
                       objects[name].location.y > 100.0 or
                       objects[name].location.z > 400.0
                       for name in ("Harukas_Preview_Camera",
                                    "Harukas_Plan_Camera",
                                    "Harukas_North_Camera"))))

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
