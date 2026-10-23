"""Verify the editable The Stack proposal scene."""

import math
import re
import sys

import bpy
from mathutils import Vector

BAND_MARKERS = {
    "glass envelope": "N_Glass",
    "facade cage columns": "Stack_Facade_Column",
    "facade cage beams": "Stack_Facade_Beam",
    "roof garden": "Stack_Roof_Canopy",
}


def main():
    blend = sys.argv[sys.argv.index("--") + 1]
    bpy.ops.wm.open_mainfile(filepath=blend)
    scene = bpy.context.scene
    names = [obj.name for obj in bpy.data.objects]

    def count(fragment):
        return sum(fragment in name for name in names)

    def objects(prefix):
        return [obj for obj in bpy.data.objects if obj.name.startswith(prefix)]

    def top_of(prefix):
        zs = [(obj.matrix_world @ Vector(corner)).z
              for obj in bpy.data.objects
              if obj.name.startswith(prefix) and obj.type == "MESH"
              for corner in obj.bound_box]
        return max(zs) if zs else None

    def bounds(obj):
        pts = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        return (min(p.x for p in pts), max(p.x for p in pts),
                min(p.y for p in pts), max(p.y for p in pts),
                min(p.z for p in pts), max(p.z for p in pts))

    def world_size(obj):
        x0, x1, y0, y1, z0, z1 = bounds(obj)
        return (x1 - x0, y1 - y0, z1 - z0)

    def center_z(obj):
        x0, x1, y0, y1, z0, z1 = bounds(obj)
        return (z0 + z1) / 2

    def center(obj):
        x0, x1, y0, y1, z0, z1 = bounds(obj)
        return ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)

    def light_z(objs):
        return [(obj.matrix_world @ v.co).z for obj in objs
                for v in obj.data.vertices]

    def light_points(objs):
        return [(obj.matrix_world @ v.co) for obj in objs
                for v in obj.data.vertices]

    def covers(levels, zs):
        return all(any(level - 0.5 < z < level for z in zs)
                   for level in levels)

    def hits_core(obj):
        x0, x1, y0, y1, _, _ = bounds(obj)
        for core in (bpy.data.objects.get("Stack_Core_West"),
                     bpy.data.objects.get("Stack_Core_East")):
            if core is None:
                continue
            cx0, cx1, cy0, cy1, _, _ = bounds(core)
            if (x0 < cx1 - 0.01 and x1 > cx0 + 0.01
                    and y0 < cy1 - 0.01 and y1 > cy0 + 0.01):
                return True
        return False

    def run_indices(fragment):
        pattern = re.compile(re.escape(fragment) + r"(\d+)_")
        out = set()
        for name in names:
            match = pattern.match(name)
            if match:
                out.add(int(match.group(1)))
        return out

    mall_floors = scene.get("mall_floors", 10)
    office_floors = scene.get("office_floors", 25)
    apartment_floors = scene.get("apartment_floors", 29)
    storeys, sz = [], 0.0
    for floors, height in ((mall_floors, 5.0), (office_floors, 5.0),
                           (apartment_floors, 4.0)):
        for _ in range(floors):
            sz += height
            storeys.append(round(sz, 3))
    # Zone boundaries follow from the floor counts alone.
    level_base = mall_floors * 5.0
    level_apartment = level_base + office_floors * 5.0
    level_roof = level_apartment + apartment_floors * 4.0
    model_height = level_roof + scene.get("crown_height_m", 0.0)
    # Each refuge is one two-storey volume: a planted garden deck on its bottom
    # plate, with the chunky chevron belt truss spanning both storeys above it to
    # the ceiling plate. The storey line between the deck and the ceiling is
    # dropped, so the garden and the truss read as one volume. Four of them:
    # mall, office, apartment base and mid-apartment, every deck landing on a
    # facade-cage beam so the truss frames the grid.
    refuge_decks = (level_base - 10.0, level_base + 50.0,
                    level_apartment, level_apartment + 15 * 4.0)
    refuge_storey = (5.0, 5.0, 4.0, 4.0)
    refuge_truss_bottoms = refuge_decks
    refuge_drops = tuple(deck + h
                         for deck, h in zip(refuge_decks, refuge_storey))
    refuge_ceilings = tuple(deck + 2 * h
                            for deck, h in zip(refuge_decks, refuge_storey))
    refuge_volumes = tuple(zip(refuge_decks, refuge_ceilings))
    refuge_spans = tuple(zip(refuge_decks, refuge_ceilings))

    def span(text):
        # "a-b", where either end may itself be negative ("-20--2.5").
        match = re.match(r"^(-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)$", text)
        return float(match.group(1)), float(match.group(2))

    void_x = [span(part) for part in scene.get("void_x_spans_m",
                                               "-20--5;5-20").split(";")]
    void_z = [span(part) for part in scene.get("void_z_spans_m",
                                               "187-207;223-243").split(";")]
    void_spans = tuple((xa, xb, za, zb)
                       for (xa, xb), (za, zb) in zip(void_x, void_z))
    void_area = sum((xb - xa) * (zb - za) for xa, xb, za, zb in void_spans)
    shaft_x, shaft_y = (float(part)
                        for part in scene.get("spine_shaft_m", "20x12").split("x"))
    shaft_half_x, shaft_half_y = shaft_x / 2, shaft_y / 2
    width = scene.get("estimated_width_m", 115.0)
    depth = scene.get("estimated_depth_m", 40.0)
    facade_half = width / 2 + 0.30
    # The facade cage grid, recomputed the way the generator lays it: prongs on
    # a ~FRAME_SPAN module across the face, rungs on the refuge truss lines plus
    # one more group above the top truss, so every rung sits on a truss line and
    # on a floor line.
    frame_span, frame_square, frame_gap = 20.0, 1.5, 0.05
    frame_col_gap = frame_gap + 0.03
    x_bays = max(1, round(width / frame_span))
    y_bays = max(1, round(depth / frame_span))
    grid_x = [-width / 2 + frame_square / 2
              + k * (width - frame_square) / x_bays
              for k in range(x_bays + 1)]
    grid_z = [0.0] + [float(deck) for deck in refuge_decks]
    grid_z.append(grid_z[-1] + 3 * frame_span)
    facade_x_cells = [(z0, z1) for z0, z1 in zip(grid_z, grid_z[1:])
                      if level_base <= (z0 + z1) / 2 <= level_apartment]
    # Full-height edge columns, plus split interior columns (mall below, tower
    # above) that leave the diamond bay clear.
    column_lengths = (model_height - 2 * frame_col_gap,
                      facade_x_cells[0][0] - frame_col_gap,
                      model_height - facade_x_cells[-1][1] - frame_col_gap)

    def on_grid(line, lines):
        return any(abs(line - g) < 0.02 for g in lines)

    belt_decks = sorted({int(name.split("Refuge_Belt_")[1].split("_")[0])
                         for name in names if "Refuge_Belt_" in name})

    mall_levels = storeys[:mall_floors]
    upper_levels = storeys[mall_floors:]
    mall_ground_height = scene.get("mall_ground_height_m", 5.0)
    mall_plate_levels = [z for z in mall_levels
                         if mall_ground_height - 0.01 <= z <= refuge_decks[0]
                         and z not in refuge_drops]
    refuge_levels = [z for z in upper_levels
                     if any(z0 < z <= z1 for z0, z1 in refuge_volumes)]
    expected_room_levels = [z for z in upper_levels
                            if z not in refuge_levels
                            and z not in refuge_drops]

    mall_lights = objects("Stack_Mall_Ceiling_Lights")
    room_objs = objects("Stack_Room_Lights_")
    braces = objects("Stack_Core_Brace_")
    brace_centers = sorted({round(center_z(o), 2) for o in braces})
    brace_z = [p.z for o in braces
               for p in (o.matrix_world @ Vector(c) for c in o.bound_box)]
    brace_low, brace_high = (min(brace_z), max(brace_z)) if brace_z else (0, 0)
    spine_runs = run_indices("Stack_Spine_Escalator_")
    mall_runs = run_indices("Stack_Mall_Escalator_")
    escalators = [obj for obj in bpy.data.objects
                  if "Escalator" in obj.name]
    spine_objs = [obj for obj in bpy.data.objects
                  if obj.name.startswith("Stack_Spine_Escalator_")]
    spine_centers = {i: [center(o) for o in spine_objs
                         if o.name.startswith(f"Stack_Spine_Escalator_{i}_")]
                     for i in spine_runs}
    # The route's runs, grouped back per storey. The office shaft is a long
    # crossed-diagonal composition (two star-ordered diagonals that intersect over
    # the centre); the apartment shaft above is a plain one-plane switchback.
    spine_run = {}
    for obj in spine_objs:
        i = int(obj.name.split("_")[3])
        x0, x1, y0, y1, z0, z1 = bounds(obj)
        if i in spine_run:
            px0, px1, py0, py1, pz0, pz1 = spine_run[i]
            x0, x1 = min(px0, x0), max(px1, x1)
            y0, y1 = min(py0, y0), max(py1, y1)
            z0, z1 = min(pz0, z0), max(pz1, z1)
        spine_run[i] = (x0, x1, y0, y1, z0, z1)
    # Run direction, from the bottom landing to the top one, so the slant signs
    # (and therefore whether two diagonals cross) are known.
    spine_dir = {}
    for obj in spine_objs:
        if obj.name.endswith("_Landing_Bottom") or obj.name.endswith("_Landing_Top"):
            i = int(obj.name.split("_")[3])
            tag = "b" if obj.name.endswith("_Bottom") else "t"
            here = spine_dir.setdefault(i, {})
            here[tag] = center(obj)

    def mid_z(i):
        return (spine_run[i][4] + spine_run[i][5]) / 2

    spine_vec = {i: (d["t"][0] - d["b"][0], d["t"][1] - d["b"][1])
                 for i, d in spine_dir.items() if "b" in d and "t" in d}
    spine_low = [i for i in spine_vec if mid_z(i) < level_apartment]
    spine_up = [i for i in spine_vec if mid_z(i) >= level_apartment]
    spine_low_vec = [spine_vec[i] for i in spine_low]
    # The pitch of each run, from its inclined belt: the climb over the run.
    spine_pitch = []
    for obj in spine_objs:
        if not obj.name.endswith("_Belt"):
            continue
        x0, x1, y0, y1, z0, z1 = bounds(obj)
        horiz = max(x1 - x0, y1 - y0)
        if horiz > 0.5:
            spine_pitch.append(math.degrees(math.atan((z1 - z0) / horiz)))

    checks = {
        "published height metadata": scene.get("published_height_m") == 356.8,
        "published level metadata": scene.get("published_levels") == 77,
        "image-scaled width": abs(scene.get("estimated_width_m") - 115.0) < 0.01,
        "image-scaled depth": abs(scene.get("estimated_depth_m") - 40.0) < 0.01,
        "elevation pixel basis": scene.get("elevation_width_pixels") == 321
        and scene.get("elevation_depth_pixels") == 94
        and scene.get("elevation_height_pixels") == 992,
        "single glass envelope recorded": scene.get("facade_bands") == "glass",
        "storey program recorded": scene.get("floor_count") == 64
        and scene.get("mall_floors") == 10
        and scene.get("office_floors") == 22
        and scene.get("apartment_floors") == 32,
        "storey heights recorded": scene.get("storey_heights_m") ==
        "mall 5.0, office 5.0, apartment 4.0",
        # Each refuge is one two-storey volume — a garden deck on the bottom
        # plate with the chunky chevron belt truss spanning both storeys above it
        # to the ceiling plate. The storey line between the deck and the ceiling
        # is dropped. There are four such refuges, the fourth in the apartment
        # zone between the two voids.
        "refuge is a four two-storey volume": scene.get(
            "refuge_floors") == 2
        and scene.get("refuges") == 4
        and scene.get("refuge_layers") == "garden,truss"
        and all(ceiling - deck in (10.0, 8.0)
                for (deck, ceiling) in refuge_spans)
        and not any(abs(center_z(obj) - z) < 0.2
                    for obj in bpy.data.objects
                    if obj.name.startswith("Stack_Floor_Slab")
                    for z in refuge_drops),
        "refuge garden decks exist": all(
            any(abs(center_z(obj) - deck) < 0.2 for obj in bpy.data.objects
                if obj.name.startswith(("Stack_Floor_Slab", "Stack_Mall_Slab")))
            for deck in refuge_decks),
        "mall garden deck is a mall ring plate": any(
            abs(center_z(obj) - refuge_decks[0]) < 0.2
            for obj in bpy.data.objects
            if obj.name.startswith("Stack_Mall_Slab")),
        "mall storey plates": count("Stack_Mall_Slab") >= 4 * len(
            mall_plate_levels)
        and all(obj.location.z <= level_base for obj in bpy.data.objects
                if obj.name.startswith("Stack_Mall_Slab")),
        "suspended first floor": mall_ground_height == 2 * 5.0
        and not any(obj.location.z < mall_ground_height - 0.1
                    for obj in bpy.data.objects
                    if obj.name.startswith("Stack_Mall_Slab")),
        "ground hall escalators": scene.get("base_escalators", 0) >= 4
        and len(run_indices("Stack_Base_Escalator_Up_")) >= 4,
        "ground escalators clear the cores": not any(
            hits_core(obj) for obj in bpy.data.objects
            if obj.name.startswith("Stack_Base_Escalator_Up_")),
        "base hall escalator components": count("Stack_Base_Escalator") >= 10,
        # The retail atrium climbs as a rectangular helix (a "回" in plan): a run
        # on each face of the ring, one storey per run at a real ~30-degree
        # pitch, always on the ring plate beside the opening.
        "retail atrium helix": len(mall_runs) >= 4
        and scene.get("escalator_helix") == "true"
        and abs(scene.get("mall_escalator_pitch_deg", 0.0) - 30.0) < 0.01
        and not any(hits_core(obj) for obj in bpy.data.objects
                    if obj.name.startswith("Stack_Mall_Escalator_")),
        # One continuous public escalator chain climbs the shaft between the
        # cores from the mall top to the roof.
        "public escalator spine": len(spine_runs) >= 40
        and max((z for vs in spine_centers.values() for _, _, z in vs),
                default=0) > level_roof - 5.0,
        "spine circles the shaft": max(
            (abs(x) for vs in spine_centers.values() for x, _, _ in vs),
            default=0.0) > 3.0,
        # The lower shaft is a crossed-diagonal composition: a rising and a
        # falling diagonal climb the shaft and intersect over the centre.
        "office spine is crossed diagonals": any(
            dx > 1.0 and dy > 1.0 for dx, dy in spine_low_vec)
        and any(dx > 1.0 and dy < -1.0 for dx, dy in spine_low_vec),
        # Above the apartment line the route is a plain one-plane switchback.
        "apartment spine is a switchback": bool(spine_up)
        and max(abs(spine_vec[i][0]) for i in spine_up) < 2.0
        and min(abs(spine_vec[i][1]) for i in spine_up) > 4.0,
        # Each run is pitched like a real escalator (~30°), not a long ramp.
        "spine runs are pitched ~30°": 25.0 <= min(spine_pitch)
        and max(spine_pitch) <= 40.0,
        # Each run is a flat inclined belt with side balustrades, handrails and a
        # landing at each end, so it reads like a stair rather than a tube.
        "escalator runs are flat bands": sum(
            o.name.endswith("_Belt") for o in escalators) > 0
        and sum("_Balustrade" in o.name for o in escalators)
        >= 2 * sum(o.name.endswith("_Belt") for o in escalators)
        and sum("_Handrail" in o.name for o in escalators)
        >= 2 * sum(o.name.endswith("_Belt") for o in escalators)
        and sum("_Landing_" in o.name for o in escalators)
        >= 2 * sum(o.name.endswith("_Belt") for o in escalators)
        and not any("_Beam" in o.name or "_Tread" in o.name for o in escalators),
        # The retail runs hug the ring around the atrium opening; the spine helix
        # stays inside the central shaft, so neither crosses an opening's edge.
        "escalators keep off the openings": all(
            (bounds(o)[0] >= 30.0 or bounds(o)[1] <= -30.0
             or bounds(o)[2] >= 14.0 or bounds(o)[3] <= -14.0)
            for o in escalators
            if o.name.startswith("Stack_Mall_Escalator_")),
        "spine stays inside the shaft": all(
            max(abs(bounds(o)[0]), abs(bounds(o)[1])) <= shaft_half_x + 0.6
            and max(abs(bounds(o)[2]), abs(bounds(o)[3])) <= shaft_half_y + 0.6
            for o in escalators
            if o.name.startswith("Stack_Spine_Escalator_")),
        "escalators clear the cores": not any(hits_core(o) for o in escalators),
        "escalators stay inside the envelope": all(
            abs(center(o)[0]) <= facade_half and center(o)[2] <= model_height + 0.5
            for o in escalators),
        "dual cores": all(f"Stack_Core_{side}" in names
                          for side in ("West", "East")),
        "no inter-core transfer beams": count("Stack_Core_Transfer_") == 0,
        # The giant spatial X-braces stay between the cores, using their full
        # depth; the escalator chain climbs the same shaft, weaving past them.
        "core X-bracing": scene.get("core_bracing") == 5
        and len(braces) == 20
        and count("Stack_Core_Brace_Chord_") == 0
        and all(world_size(o)[1] > 10.0 for o in braces),
        "core braces meet the cores": (
            bpy.data.objects.get("Stack_Core_East") is not None
            and all(bounds(o)[1]
                    > bounds(bpy.data.objects["Stack_Core_East"])[0] + 1.0
                    and bounds(o)[3]
                    < bounds(bpy.data.objects["Stack_Core_East"])[3] + 0.01
                    for o in braces)),
        "outrigger trusses": count("Stack_Outrigger_Chord") == 32
        and count("Stack_Outrigger_Diag") == 32,
        # The facade cage: chunky square prongs and rungs, on the 40 m vertical
        # module, flush with the glass on all four faces, so the tower reads as a
        # grid of tall rectangles; every rung lands on a floor line. The office
        # cells take diamonds instead, so only the edge columns run full height
        # there; the interior ones are split out (mall below, tower above).
        "facade cage columns": (
            count("Stack_Facade_Column") == 4 * (x_bays + y_bays)
            and all(abs(o.dimensions.x - frame_square) < 0.01
                    and abs(o.dimensions.y - frame_square) < 0.01
                    and any(abs(o.dimensions.z - z) < 0.15
                            for z in column_lengths)
                    for o in objects("Stack_Facade_Column"))),
        "facade cage beams": (
            count("Stack_Facade_Beam") == 4 * len(grid_z)
            and all(abs(o.dimensions.z - frame_square) < 0.01
                    and (abs(o.dimensions.x - frame_square) < 0.01
                         or abs(o.dimensions.y - frame_square) < 0.01)
                    for o in objects("Stack_Facade_Beam"))),
        "facade rungs land on floor lines": all(
            abs(g) < 0.02 or any(abs(g - level) < 0.02 for level in storeys)
            for g in grid_z),
        "facade cage is flush with the glass": all(
            bounds(o)[3] <= depth / 2 + 0.33
            and bounds(o)[2] >= -(depth / 2 + 0.33)
            and bounds(o)[1] <= width / 2 + 0.33
            and bounds(o)[0] >= -(width / 2 + 0.33)
            for o in objects("Stack_Facade_")),
        # Each office cell carries a tall steel diamond (three across the long
        # faces, one on the short), its vertices landing on the cell's trusses,
        # so the two cells stack into one two-diamond band.
        "facade office X-braces": (
            count("_Facade_X")
            == 8 * (x_bays // 2 + y_bays // 2) * len(facade_x_cells)
            and all(min(z0 for z0, _ in facade_x_cells) - 0.6 < bounds(o)[4]
                    and bounds(o)[5]
                    < max(z1 for _, z1 in facade_x_cells) + 0.6
                    for o in bpy.data.objects if "_Facade_X" in o.name)),
        "uniform X-braces": len({round(world_size(o)[2], 1)
                                 for o in braces}) == 1,
        "evenly spaced core braces": len(brace_centers) == 5
        and max(b - a for a, b in zip(brace_centers, brace_centers[1:]))
        - min(b - a for a, b in zip(brace_centers, brace_centers[1:])) < 0.05
        and brace_low > 5.0
        and brace_high < model_height - 5.0,
        # The mall ceiling is continuous bright rings; the offices and apartments
        # take the house panel grid; the open refuges take no ceiling lights at
        # all — their open-air gardens are lit by the track lamps instead.
        "mall ceiling lights": len(mall_lights) == 1
        and len(mall_lights[0].data.vertices) > 0
        and covers(mall_plate_levels, light_z(mall_lights)),
        "office and apartment ceiling lights": len(room_objs) == 3
        and all(len(obj.data.vertices) > 0 for obj in room_objs)
        and covers(expected_room_levels, light_z(room_objs)),
        "no floating lights": not any(
            abs(z - (drop - 0.19)) < 0.1
            for z in light_z(room_objs) for drop in refuge_drops),
        "no refuge ceiling cove": count("Stack_Refuge_Ceiling_Lights") == 0,
        "no panels on the refuge storeys": not any(
            z0 + 0.1 < z < z1 - 0.1 for z in light_z(room_objs)
            for z0, z1 in refuge_volumes),
        # The public shaft and the two voids are open air, so no floor plate and
        # no panel light may sit over them.
        "public shaft is open": not any(
            bounds(obj)[0] < 0.0 < bounds(obj)[1]
            and bounds(obj)[2] < 0.0 < bounds(obj)[3]
            for obj in bpy.data.objects
            if obj.name.startswith(("Stack_Floor_Slab", "Stack_Mall_Slab"))),
        "no lights in the shaft or voids": not any(
            (abs(p.x) < shaft_half_x and abs(p.y) < shaft_half_y)
            or any(x0 < p.x < x1 and z0 <= p.z < z1
                   for x0, x1, z0, z1 in void_spans)
            for p in light_points(room_objs)),
        # The three refuge decks and the roof are planted sky gardens, and the
        # trees stay inside the single glazed garden storey so the open storey
        # above them remains empty; that is what keeps each refuge at three
        # layers (truss, glazing, open) instead of reading as four.
        "planted decks": all(
            count(f"{name}_Lawn") > 0 and count(f"{name}_Track_") >= 4
            for name in ("Stack_Refuge_Mall_Garden",
                         "Stack_Refuge_Office_Garden",
                         "Stack_Refuge_Apartment_Garden",
                         "Stack_Refuge_Apartment_Mid_Garden", "Stack_Roof")),
        # A street lamp — a slim pole with a warm glowing head — every few
        # metres along the inner edge of each garden's running track.
        "garden lamps line the tracks": all(
            count(f"{name}_Lamp_Post") >= 10
            and count(f"{name}_Lamp_Head") >= 10
            for name in ("Stack_Refuge_Mall_Garden",
                         "Stack_Refuge_Office_Garden",
                         "Stack_Refuge_Apartment_Garden",
                         "Stack_Refuge_Apartment_Mid_Garden", "Stack_Roof")),
        "garden trees grow through the truss storey": all(
            count(f"{name}_Canopy") >= 12
            for name in ("Stack_Refuge_Mall_Garden",
                         "Stack_Refuge_Office_Garden",
                         "Stack_Refuge_Apartment_Garden",
                         "Stack_Refuge_Apartment_Mid_Garden", "Stack_Roof"))
        and all(max(((obj.matrix_world @ Vector(c)).z
                     for obj in bpy.data.objects
                     if obj.name.startswith(f"{name}_Canopy")
                     for c in obj.bound_box), default=0.0) <= ceiling - 0.5
                for name, ceiling in (("Stack_Refuge_Mall_Garden",
                                       refuge_ceilings[0]),
                                      ("Stack_Refuge_Office_Garden",
                                       refuge_ceilings[1]),
                                      ("Stack_Refuge_Apartment_Garden",
                                       refuge_ceilings[2]),
                                      ("Stack_Refuge_Apartment_Mid_Garden",
                                       refuge_ceilings[3]))),
        "camera assigned": scene.camera is not None,
        "viewport framed on building": any(
            area.spaces.active.region_3d is not None
            and area.spaces.active.region_3d.view_distance > 300
            for screen in bpy.data.screens for area in screen.areas
            if area.type == "VIEW_3D"),
        "model height recorded": scene.get("model_height_m") == model_height,
        "crown reaches top surface": abs(
            (top_of("N_Glass") or 0.0) - model_height) < 0.05,
        "cores flush with top": abs(
            (top_of("Stack_Core_") or 0.0) - model_height) < 0.05,
        "no core protrudes above top": (
            top_of("Stack_Core_") or 0.0) <= model_height + 0.01,
        # Each refuge is a garden deck; every one carries the chunky chevron
        # belt truss spanning both storeys above the deck. Every belt truss foot
        # sits on a facade cage rung, so the trusses mark the cell boundaries.
        "refuge belt trusses": (
            scene.get("refuge_floors") == 2
            and scene.get("refuges") == 4
            and scene.get("refuge_layers") == "garden,truss"
            and scene.get("refuge_open_levels_m") == ""
            and scene.get("refuge_levels_m") == ", ".join(
                f"{a:g}-{b:g}"
                for a, b in zip(refuge_decks, refuge_ceilings))
            and belt_decks == sorted(int(d) for d in refuge_truss_bottoms)
            and all(min(abs(deck - g) for g in grid_z) < 1.6
                    for deck in refuge_truss_bottoms)),
        # The belt truss may not overhang the corners: a round post left on the
        # building corner would stick out past the envelope by its own radius.
        "refuge structure stays inside the envelope": not any(
            max(bounds(o)[1] - (width / 2 + 0.301),
                -(bounds(o)[0] + width / 2 + 0.301),
                bounds(o)[3] - (depth / 2 + 0.301),
                -(bounds(o)[2] + depth / 2 + 0.301)) > 0.01
            for o in bpy.data.objects
            if "Refuge_Belt" in o.name),
        "eye band replaced by vertical grid": count("_Louver") == 0
        and count("_Eye") == 0,
        "open glazed crown": count("Stack_Roof_Slab") == 0
        and count("Stack_Roof_Step_") == 0
        and (top_of("N_Glass") or 0.0) - level_roof >= 2 * 4.0,
        "slender slab proportion": 2.5 < (
            scene.get("estimated_width_m") / scene.get("estimated_depth_m")) < 3.9,
        # The envelope is one glass skin on all four faces; its only breaks are
        # the two ventilation openings.
        "glass envelope wraps four faces": all(
            count(f"{face}_Glass") > 0 for face in ("N", "S", "E", "W")),
        "two offset vents": scene.get("voids") == 2 and len(void_spans) == 2
        and void_spans[0][1] <= void_spans[1][0],
        # Each vent is one whole facade cell: one long-face bay wide (the ~19 m
        # cell) by one 60 m truss group high, its edges on grid lines.
        "vents are whole grid cells": all(
            on_grid(x0, grid_x) and on_grid(x1, grid_x)
            and on_grid(z0, grid_z) and on_grid(z1, grid_z)
            and abs((x1 - x0) - (grid_x[3] - grid_x[2])) < 0.02
            and abs((z1 - z0) - (grid_z[2] - grid_z[1])) < 0.02
            for x0, x1, z0, z1 in void_spans),
        "vents are punched in the glass": all(
            not any(x0 < center(obj)[0] < x1 and z0 < center(obj)[2] < z1
                    for obj in bpy.data.objects
                    if obj.name.startswith(("N_Glass", "S_Glass")))
            for x0, x1, z0, z1 in void_spans),
        # The two vents reach down to the mid-apartment refuge's deck and the
        # upper one rises over it, so the refuge sits in the openings' band.
        "vents span the mid refuge": (
            void_spans[0][3] <= refuge_decks[3] + 0.1
            and void_spans[1][2] <= refuge_decks[3] + 0.1
            and void_spans[1][3] >= refuge_ceilings[3] - 0.1),
        "voids enlarged past twice the area": void_area >= 600.0
        and abs(scene.get("void_area_m2", 0.0) - void_area) < 1.0,
        "no bridge remains": count("Bridge") == 0,
    }
    for label, marker in BAND_MARKERS.items():
        checks[label] = count(marker) > 0

    failed = []
    for label, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}: {label}")
        if not passed:
            failed.append(label)
    if failed:
        raise SystemExit(f"Failed {len(failed)} checks: {', '.join(failed)}")
    print(f"All {len(checks)} checks passed")


if __name__ == "__main__":
    main()
