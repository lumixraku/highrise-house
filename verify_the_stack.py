"""Verify the editable The Stack proposal scene."""

import re
import sys

import bpy
from mathutils import Vector

BAND_MARKERS = {
    "base glazing": "Base_Glass",
    "diagrid band": "Diagrid",
    "garden band": "Garden_Canopy",
    "fin band": "Fin",
    "masonry band": "Brick_Mullion",
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
    # Each refuge is one open three-storey volume: a planted garden deck on its
    # bottom plate, the belt truss in the storey above it, and the fully open
    # storey on top carrying the ceiling. The deck and ceiling plates stay, and
    # the two floors between them are dropped, so the garden reads as a single
    # tall volume with the ceiling three storeys up. Four of them: mall, office,
    # apartment base and mid-apartment.
    refuge_decks = (level_base - 10.0, level_base + 60.0,
                    level_base + 110.0, level_apartment + 12 * 4.0)
    refuge_storey = tuple(5.0 if i < 3 else 4.0
                          for i in range(len(refuge_decks)))
    refuge_truss_bottoms = tuple(deck + h
                                 for deck, h in zip(refuge_decks, refuge_storey))
    refuge_drops = tuple(deck + 2 * h
                         for deck, h in zip(refuge_decks, refuge_storey))
    refuge_ceilings = tuple(deck + 3 * h
                            for deck, h in zip(refuge_decks, refuge_storey))
    # The open garden air: from each deck plate up to its ceiling.
    refuge_volumes = tuple(zip(refuge_decks, refuge_ceilings))
    # The full three-storey component, deck plate included.
    refuge_spans = tuple(zip(refuge_decks, refuge_ceilings))
    # The top (open) storey of each component.
    refuge_open_spans = tuple((drop, ceiling)
                              for drop, ceiling in zip(refuge_drops,
                                                       refuge_ceilings))
    # The two offset apartment voids sit against the two core inner faces.
    core_inner = 20.0
    void_width = scene.get("void_width_m", 15.0)
    void_height = scene.get("void_height_m", 20.0)

    def span(text):
        return tuple(float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text))

    void_x = [span(part) for part in scene.get("void_x_spans_m",
                                               "-20--5;5-20").split(";")]
    void_z = [span(part) for part in scene.get("void_z_spans_m",
                                               "187-207;223-243").split(";")]
    void_spans = tuple((xa, xb, za, zb)
                       for (xa, xb), (za, zb) in zip(void_x, void_z))
    shaft_x, shaft_y = (float(part)
                        for part in scene.get("spine_shaft_m", "20x12").split("x"))
    shaft_half_x, shaft_half_y = shaft_x / 2, shaft_y / 2
    width = scene.get("estimated_width_m", 115.0)
    depth = scene.get("estimated_depth_m", 40.0)
    facade_half = width / 2 + 0.30

    mall_levels = storeys[:mall_floors]
    upper_levels = storeys[mall_floors:]
    mall_ground_height = scene.get("mall_ground_height_m", 5.0)
    mall_plate_levels = [z for z in mall_levels
                         if mall_ground_height - 0.01 <= z < level_base - 0.01
                         and z not in refuge_drops
                         and z not in refuge_truss_bottoms]
    refuge_levels = [z for z in upper_levels
                     if any(z0 < z <= z1 for z0, z1 in refuge_volumes)]
    expected_room_levels = [z for z in upper_levels
                            if z not in refuge_levels
                            and z not in refuge_drops]
    frost_alpha = None
    frost = bpy.data.materials.get("Stack_Glass_Frost")
    if frost and frost.use_nodes:
        bsdf = frost.node_tree.nodes.get("Principled BSDF")
        if bsdf and "Alpha" in bsdf.inputs:
            frost_alpha = bsdf.inputs["Alpha"].default_value
    spandrel = bpy.data.materials.get("Stack_Spandrel_Blue")
    spandrel_color = None
    if spandrel and spandrel.use_nodes:
        bsdf = spandrel.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            spandrel_color = tuple(bsdf.inputs["Base Color"].default_value)
    apartment_frame = bpy.data.materials.get("Stack_Apartment_Frame")
    frame_color = None
    if apartment_frame and apartment_frame.use_nodes:
        bsdf = apartment_frame.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            frame_color = tuple(bsdf.inputs["Base Color"].default_value)

    mall_lights = objects("Stack_Mall_Ceiling_Lights")
    base_glass = [obj for obj in bpy.data.objects if "Base_Glass" in obj.name]
    room_objs = objects("Stack_Room_Lights_")
    refuge_glow = objects("Stack_Refuge_Ceiling_Lights")
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

    checks = {
        "published height metadata": scene.get("published_height_m") == 356.8,
        "published level metadata": scene.get("published_levels") == 77,
        "image-scaled width": abs(scene.get("estimated_width_m") - 115.0) < 0.01,
        "image-scaled depth": abs(scene.get("estimated_depth_m") - 40.0) < 0.01,
        "elevation pixel basis": scene.get("elevation_width_pixels") == 321
        and scene.get("elevation_depth_pixels") == 94
        and scene.get("elevation_height_pixels") == 992,
        "band sequence recorded": scene.get("facade_bands") ==
        "base,refuge,garden,diagrid,refuge,fins,refuge,brick,refuge,brick",
        "storey program recorded": scene.get("floor_count") == 64
        and scene.get("mall_floors") == 10
        and scene.get("office_floors") == 25
        and scene.get("apartment_floors") == 29,
        "storey heights recorded": scene.get("storey_heights_m") ==
        "mall 5.0, office 5.0, apartment 4.0",
        # Each refuge is one three-storey volume — a garden deck on the bottom
        # plate, the belt truss above it, an open storey carrying the ceiling —
        # so it reads as a tall garden room, not a stack of thin layers. The two
        # floors between the deck and the ceiling are dropped. There are four
        # such refuges, the fourth in the apartment zone between the two voids.
        "refuge is a four three-storey volume": scene.get(
            "refuge_floors") == 3
        and scene.get("refuges") == 4
        and scene.get("refuge_layers") == "garden,truss,open"
        and all(ceiling - deck in (15.0, 12.0)
                for (deck, ceiling) in refuge_spans)
        and not any(abs(center_z(obj) - z) < 0.2
                    for obj in bpy.data.objects
                    if obj.name.startswith("Stack_Floor_Slab")
                    for z in refuge_truss_bottoms + refuge_drops),
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
        # cores from the mall top to the roof, running along the depth at the
        # centreline so it never enters either apartment vent void.
        "public escalator spine": len(spine_runs) >= 50
        and max((z for vs in spine_centers.values() for _, _, z in vs),
                default=0) > level_roof - 5.0,
        "spine stays clear of the vents": all(
            abs(x) < width / 2 for vs in spine_centers.values()
            for x, _, _ in vs)
        and max((abs(x) for vs in spine_centers.values()
                 for x, _, _ in vs), default=0.0) < 3.0,
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
        # The retail runs hug the ring around the atrium opening; the spine runs
        # cross the shaft along its depth and reach the plates past the shaft
        # hole, so neither floats over an opening.
        "escalators keep off the openings": all(
            (bounds(o)[0] >= 30.0 or bounds(o)[1] <= -30.0
             or bounds(o)[2] >= 14.0 or bounds(o)[3] <= -14.0)
            for o in escalators
            if o.name.startswith("Stack_Mall_Escalator_"))
        and max((max(abs(bounds(o)[2]), abs(bounds(o)[3]))
                 for o in escalators
                 if o.name.startswith("Stack_Spine_Escalator_")),
                default=0.0) > 6.0,
        "escalators clear the cores": not any(hits_core(o) for o in escalators),
        "escalators stay inside the envelope": all(
            abs(center(o)[0]) <= facade_half and center(o)[2] <= model_height + 0.5
            for o in escalators),
        # The base is a frosted glass wall with a frame heavy enough to read.
        "frosted base glazing": frost_alpha is not None
        and 0.35 <= frost_alpha <= 0.85
        and count("Base_Glass") >= 4 and count("Base_Mullion") >= 8
        and max((max(o.dimensions.x, o.dimensions.y) for o in bpy.data.objects
                 if "Base_Mullion" in o.name), default=0.0) >= 0.25,
        "base glass grouped two storeys": (
            len(base_glass)
            == int((level_base - mall_ground_height) / (2 * 5.0))
            * len(("N", "S", "E", "W"))
            and all(abs(o.dimensions.z - 2 * 5.0) < 0.01 for o in base_glass)
            and min(o.location.z - o.dimensions.z / 2 for o in base_glass)
            >= mall_ground_height - 0.01),
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
        "outrigger columns": count("Stack_Outrigger_Column") == 4,
        "outrigger trusses": count("Stack_Outrigger_Chord") == 32
        and count("Stack_Outrigger_Diag") == 32,
        "uniform X-braces": len({round(world_size(o)[2], 1)
                                 for o in braces}) == 1,
        "evenly spaced core braces": len(brace_centers) == 5
        and max(b - a for a, b in zip(brace_centers, brace_centers[1:]))
        - min(b - a for a, b in zip(brace_centers, brace_centers[1:])) < 0.05
        and brace_low > 5.0
        and brace_high < model_height - 5.0,
        # The mall ceiling is continuous bright rings; the offices and apartments
        # take the house panel grid; the open refuges take a perimeter cove.
        "mall ceiling lights": len(mall_lights) == 1
        and len(mall_lights[0].data.vertices) > 0
        and covers(mall_plate_levels, light_z(mall_lights)),
        "office and apartment ceiling lights": len(room_objs) == 3
        and all(len(obj.data.vertices) > 0 for obj in room_objs)
        and covers(expected_room_levels, light_z(room_objs)),
        "no floating lights": not any(
            abs(z - (drop - 0.19)) < 0.1
            for z in light_z(room_objs) for drop in refuge_drops),
        "refuge ceilings are a continuous cove": len(refuge_glow) == 1
        and max((max(obj.dimensions.x, obj.dimensions.y)
                 for obj in refuge_glow), default=0.0) >= 100.0
        and covers(refuge_ceilings, light_z(refuge_glow)),
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
        "garden trees grow through the truss storey": all(
            count(f"{name}_Canopy") >= 12
            for name in ("Stack_Refuge_Mall_Garden",
                         "Stack_Refuge_Office_Garden",
                         "Stack_Refuge_Apartment_Garden",
                         "Stack_Refuge_Apartment_Mid_Garden", "Stack_Roof"))
        and all(max(((obj.matrix_world @ Vector(c)).z
                     for obj in bpy.data.objects
                     if obj.name.startswith(f"{name}_Canopy")
                     for c in obj.bound_box), default=0.0) <= deck + 10.5
                for name, deck in (("Stack_Refuge_Mall_Garden", refuge_decks[0]),
                                   ("Stack_Refuge_Office_Garden",
                                    refuge_decks[1]),
                                   ("Stack_Refuge_Apartment_Garden",
                                    refuge_decks[2]),
                                   ("Stack_Refuge_Apartment_Mid_Garden",
                                    refuge_decks[3]))),
        "camera assigned": scene.camera is not None,
        "viewport framed on building": any(
            area.spaces.active.region_3d is not None
            and area.spaces.active.region_3d.view_distance > 300
            for screen in bpy.data.screens for area in screen.areas
            if area.type == "VIEW_3D"),
        "model height recorded": scene.get("model_height_m") == model_height,
        "crown reaches top surface": abs(
            (top_of("N_Brick") or 0.0) - model_height) < 0.05,
        "cores flush with top": abs(
            (top_of("Stack_Core_") or 0.0) - model_height) < 0.05,
        "no core protrudes above top": (
            top_of("Stack_Core_") or 0.0) <= model_height + 0.01,
        # Only the top storey of each three-layer refuge carries no facade at
        # all; the truss and deck storeys below it are wrapped.
        "open refuge slits": (
            scene.get("refuge_floors") == 3
            and scene.get("refuges") == 4
            and scene.get("refuge_levels_m") == ", ".join(
                f"{a:g}-{b:g}"
                for a, b in zip(refuge_decks, refuge_ceilings))
            and scene.get("refuge_open_levels_m") == ", ".join(
                f"{a:g}-{b:g}" for a, b in refuge_open_spans)
            and not any(o.name[:2] in ("N_", "S_", "E_", "W_")
                        and any(z0 < o.location.z < z1
                                for z0, z1 in refuge_open_spans)
                        for o in bpy.data.objects)),
        # The garden and truss storeys of each refuge are wrapped by the same
        # facade style as the group that carries them, so the band reads
        # continuously through the refuge.
        "gardens wrapped by their band's own facade": all(
            any(style in o.name
                and bounds(o)[4] <= z0 + 0.01 and bounds(o)[5] >= z1 - 0.01
                for o in bpy.data.objects
                if o.name[:2] in ("N_", "S_", "E_", "W_"))
            for (z0, z1), style in zip(
                zip(refuge_decks, refuge_drops),
                ("Base_", "Diagrid", "Fin", "Brick"))),
        "bands wrap four faces": all(
            count(f"{face}_Diagrid") > 0 and count(f"{face}_Fin") > 0
            and count(f"{face}_Brick_Mullion") > 0
            for face in ("N", "S", "E", "W")),
        "eye band replaced by vertical grid": count("_Louver") == 0
        and count("_Eye") == 0,
        "open glazed crown": count("Stack_Roof_Slab") == 0
        and count("Stack_Roof_Step_") == 0
        and (top_of("N_Brick") or 0.0) - level_roof >= 2 * 4.0,
        "slender slab proportion": 2.5 < (
            scene.get("estimated_width_m") / scene.get("estimated_depth_m")) < 3.9,
        # The apartment band is pierced by two offset voids, not one big slot,
        # and no bridge connects the halves.
        "two offset apartment voids": scene.get("voids") == 2
        and scene.get("void_x_spans_m") == "-20--2.5;2.5-20"
        and count("N_Brick_Glass") > 2 and count("S_Brick_Glass") > 2,
        # Each opening is now more than twice the original 15 x 20 m (300 m2).
        "voids enlarged past twice the area": scene.get(
            "void_area_m2", 0.0) >= 600.0
        and abs(scene.get("void_area_m2", 0.0) - void_width * void_height) < 0.01,
        "void openings are punched in the band": all(
            not any(x0 < center(obj)[0] < x1 and z0 < center(obj)[2] < z1
                    for obj in bpy.data.objects
                    if obj.name.startswith(("N_Brick_Mullion", "N_Brick_Glass",
                                            "S_Brick_Mullion", "S_Brick_Glass")))
            for x0, x1, z0, z1 in void_spans),
        # Each vent opening sits directly on the open storey of a walking-garden
        # refuge, so the opening and that empty layer connect.
        "each vent sits on a refuge open storey": all(
            any(abs(z0 - ceiling) < 0.01 for ceiling in refuge_ceilings)
            for x0, x1, z0, z1 in void_spans),
        # The missing X-facing sides are closed with the same curtain wall as the
        # exterior apartment band (glass, spandrel, mullions, transoms), while
        # the long N/S faces stay fully open — those are the ventilation
        # openings, so no glass may be added across them.
        "void X-sides wear the apartment curtain wall": (
            count("Stack_Void_CW_Mullion") >= 100
            and count("Stack_Void_CW_Glass") >= 30
            and count("Stack_Void_CW_Spandrel") >= 30
            and count("Stack_Void_CW_Transom") >= 60
            and not any("Void_Infill" in o.name for o in bpy.data.objects)),
        # The X-facing lining runs the void's full height from its base, so both
        # opposite faces read glazed storey for storey, down to the layer that
        # opens onto the refuge garden below.
        "void X-lining reaches the void base": all(
            any(abs(bounds(o)[4] - z0) < 0.05
                for o in bpy.data.objects
                if o.name.startswith("Stack_Void_CW_Mullion"))
            for x0, x1, z0, z1 in void_spans),
        # The lining sits inside the opening, clear of the core face behind it,
        # so no member intersects the concrete (which is what read as z-fighting
        # along the void edge).
        "void lining clear of the cores": all(
            not any(
                bounds(o)[0] < cx1 and bounds(o)[1] > cx0
                and bounds(o)[2] < cy1 and bounds(o)[3] > cy0
                and bounds(o)[4] < cz1 and bounds(o)[5] > cz0
                for o in bpy.data.objects
                if o.name.startswith("Stack_Void_CW_"))
            for cx0, cx1, cy0, cy1, cz0, cz1 in (
                bounds(bpy.data.objects["Stack_Core_West"]),
                bounds(bpy.data.objects["Stack_Core_East"]))),
        # The mid-apartment refuge is an empty storey, so no apartment-band
        # mullion may run through it: each stays inside one of the brick bands.
        "apartment mullions stay inside their band": all(
            not (bounds(o)[4] < 234.95 and bounds(o)[5] > 231.05)
            for o in bpy.data.objects
            if o.name.startswith(("N_Brick_Mullion", "S_Brick_Mullion",
                                  "E_Brick_Mullion", "W_Brick_Mullion"))),
        "void edges land on the mullion grid": all(
            round(edge, 3) in {round(obj.location.x, 3)
                               for obj in bpy.data.objects
                               if obj.name.startswith("N_Brick_Mullion")}
            for edge in (void_spans[0][0], void_spans[0][1],
                         void_spans[1][0], void_spans[1][1])
            if abs(edge) < width / 2),
        "apartment band is vertical strips": (
            len({round(obj.location.x, 3) for obj in bpy.data.objects
                 if obj.name.startswith("N_Brick_Mullion")}) > 80),
        "apartment band is glazed": count("Brick_Glass") > 0
        and count("Brick_Back") == 0,
        "apartment spandrel is light blue": count("Brick_Spandrel") > 0
        and spandrel_color is not None
        and spandrel_color[2] > spandrel_color[0] and spandrel_color[0] > 0.5,
        "apartment frame is white": count("Brick_Mullion") > 0
        and frame_color is not None
        and min(frame_color[:3]) > 0.8
        and max(frame_color[:3]) - min(frame_color[:3]) < 0.05,
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
