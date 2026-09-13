"""Verify the editable The Stack proposal scene."""

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

    def top_of(prefix):
        zs = [(obj.matrix_world @ Vector(corner)).z
              for obj in bpy.data.objects
              if obj.name.startswith(prefix) and obj.type == "MESH"
              for corner in obj.bound_box]
        return max(zs) if zs else None

    def world_size(obj):
        pts = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        return tuple(max(p[i] for p in pts) - min(p[i] for p in pts)
                     for i in range(3))

    def center_z(obj):
        pts = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        return (min(p.z for p in pts) + max(p.z for p in pts)) / 2

    braces = [obj for obj in bpy.data.objects
              if obj.name.startswith("Stack_Core_Brace_")]
    brace_centers = sorted({round(center_z(o), 2) for o in braces})
    brace_z = [p.z for o in braces
               for p in (o.matrix_world @ Vector(c) for c in o.bound_box)]
    brace_low, brace_high = (min(brace_z), max(brace_z)) if brace_z else (0, 0)
    mall_lights = [obj for obj in bpy.data.objects
                   if obj.name.startswith("Stack_Mall_Ceiling_Lights")]
    base_glass = [obj for obj in bpy.data.objects
                  if "Base_Glass" in obj.name]
    room_objs = [obj for obj in bpy.data.objects
                 if obj.name.startswith("Stack_Room_Lights_")]
    refuge_glow = [obj for obj in bpy.data.objects
                   if obj.name.startswith("Stack_Refuge_Ceiling_Lights")]

    def light_z(objs):
        return [(obj.matrix_world @ v.co).z for obj in objs
                for v in obj.data.vertices]

    def covers(levels, zs):
        return all(any(level - 0.5 < z < level for z in zs)
                   for level in levels)

    def footprint(obj):
        pts = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        return (min(p.x for p in pts), max(p.x for p in pts),
                min(p.y for p in pts), max(p.y for p in pts))

    def hits_core(obj):
        x0, x1, y0, y1 = footprint(obj)
        for core in (bpy.data.objects.get("Stack_Core_West"),
                     bpy.data.objects.get("Stack_Core_East")):
            if core is None:
                continue
            cx0, cx1, cy0, cy1 = footprint(core)
            if (x0 < cx1 - 0.01 and x1 > cx0 + 0.01
                    and y0 < cy1 - 0.01 and y1 > cy0 + 0.01):
                return True
        return False

    mall_floors = scene.get("mall_floors", 10)
    office_floors = scene.get("office_floors", 25)
    apartment_floors = scene.get("apartment_floors", 29)
    refuge_open_h = scene.get("refuge_open_height_m", 5.0)
    storeys, sz = [], 0.0
    for floors, height in ((mall_floors, 5.0), (office_floors, 5.0),
                           (apartment_floors, 4.0)):
        for _ in range(floors):
            sz += height
            storeys.append(round(sz, 3))
    # Zone boundaries follow from the floor counts alone; nothing here is a
    # hard-coded elevation.
    level_base = mall_floors * 5.0
    level_apartment = level_base + office_floors * 5.0
    level_roof = level_apartment + apartment_floors * 4.0
    model_height = level_roof + scene.get("crown_height_m", 0.0)
    level_office_high = level_base + 13 * 5.0
    refuge_spans = ((level_base, level_base + 5.0),
                    (level_office_high + 5.0, level_office_high + 10.0),
                    (level_apartment - 5.0, level_apartment))
    # All three refuge plates are dropped, so each open volume reads double
    # height and the garden deck is enclosed by the curtain wall of the band
    # below it.
    mall_levels, upper_levels = storeys[:mall_floors], storeys[mall_floors:]
    # The ground hall is double height: the first retail plate is lifted two
    # storeys, so the levels below it carry neither a plate nor a ceiling ring.
    mall_ground_height = scene.get("mall_ground_height_m", 5.0)
    # The top mall plate is the refuge floor, dropped so the refuge opens
    # downward, so it carries no plate and no ceiling ring.
    mall_plate_levels = [z for z in mall_levels
                         if mall_ground_height - 0.01 <= z < level_base - 0.01]
    refuge_levels = [z for z in upper_levels
                     if any(z0 < z <= z1 for z0, z1 in refuge_spans)]
    frost_alpha = None
    frost = bpy.data.materials.get("Stack_Glass_Frost")
    if frost and frost.use_nodes:
        bsdf = frost.node_tree.nodes.get("Principled BSDF")
        if bsdf and "Alpha" in bsdf.inputs:
            frost_alpha = bsdf.inputs["Alpha"].default_value

    checks = {
        "published height metadata": scene.get("published_height_m") == 356.8,
        "published level metadata": scene.get("published_levels") == 77,
        "image-scaled width": abs(scene.get("estimated_width_m") - 115.0) < 0.01,
        "image-scaled depth": abs(scene.get("estimated_depth_m") - 40.0) < 0.01,
        "elevation pixel basis": scene.get("elevation_width_pixels") == 321
        and scene.get("elevation_depth_pixels") == 94
        and scene.get("elevation_height_pixels") == 992,
        "band sequence recorded": scene.get("facade_bands") ==
        "base,refuge,garden,diagrid,refuge,fins,refuge,brick",
        "storey program recorded": scene.get("floor_count") == 64
        and scene.get("mall_floors") == 10
        and scene.get("office_floors") == 25
        and scene.get("apartment_floors") == 29,
        # The plate at the bottom of every refuge is dropped, so each open floor
        # reads as a double-height (10 m) garden, not a 5 m slot.
        "refuge storeys are double height": refuge_open_h == 2 * 5.0
        and not any(abs(center_z(obj) - z0) < 0.2
                    for obj in bpy.data.objects
                    if obj.name.startswith("Stack_Floor_Slab")
                    for z0, _ in refuge_spans),
        # The mall refuge floor is a mall plate, dropped too so that refuge also
        # opens downward into the storey below.
        "mall refuge opens downward": not any(
            abs(obj.location.z - level_base) < 0.2
            for obj in bpy.data.objects
            if obj.name.startswith("Stack_Mall_Slab")),
        "storey heights recorded": scene.get("storey_heights_m") ==
        "mall 5.0, office 5.0, apartment 4.0",
        # Office and apartment plates run to the roof; six are split around the
        # wind slots, so the object count exceeds the number of storeys.
        "floor plates to roof": 55 <= count("Stack_Floor_Slab") <= 100,
        # The mall carries one ring of retail plates per storey, all below the
        # office zone.
        "mall storey plates": count("Stack_Mall_Slab") >= 4 * len(mall_plate_levels)
        and all(obj.location.z <= level_base for obj in bpy.data.objects
                if obj.name.startswith("Stack_Mall_Slab")),
        # The ground hall has no plate: the lowest retail plate is suspended two
        # storeys up, so the base reads as a 10 m open volume.
        "suspended first floor": mall_ground_height == 2 * 5.0
        and not any(obj.location.z < mall_ground_height - 0.1
                    for obj in bpy.data.objects
                    if obj.name.startswith("Stack_Mall_Slab")),
        # The hall is served by several escalator runs up to the suspended first
        # plate, spread around the atrium, not only by the long hall escalator.
        "ground hall escalators": scene.get("base_escalators", 0) >= 4
        and count("Stack_Base_Escalator_Up_") >= 4,
        # Those runs must stay in the floor ring, not pass through the cores.
        "ground escalators clear the cores": not any(
            hits_core(obj) for obj in bpy.data.objects
            if obj.name.startswith("Stack_Base_Escalator_Up_")),
        "long escalator in base": count("Stack_Base_Escalator") >= 2
        and count("Stack_Base_Tread") > 10,
        # The base is a frosted glass wall with a frame heavy enough to read at
        # render scale, not an invisible sheet of clear glass.
        "frosted base glazing": frost_alpha is not None
        and 0.35 <= frost_alpha <= 0.85
        and count("Base_Glass") >= 4 and count("Base_Mullion") >= 8
        and max((max(o.dimensions.x, o.dimensions.y) for o in bpy.data.objects
                 if "Base_Mullion" in o.name), default=0.0) >= 0.25,
        # The base glass is grouped two storeys high on the floor plates: four
        # groups at the top of the mall, the lowest storeys left as openwork.
        "base glass grouped two storeys": (
            len(base_glass) == 4 * len(("N", "S", "E", "W"))
            and all(abs(o.dimensions.z - 2 * 5.0) < 0.01 for o in base_glass)
            and min(o.location.z - o.dimensions.z / 2 for o in base_glass)
            >= level_base - 4 * 2 * 5.0 - 0.01),
        "dual cores": all(f"Stack_Core_{side}" in names
                          for side in ("West", "East")),
        # Five ties, not six: the apartment base stays open across the void, so
        # the cores are tied at the band boundaries except LEVEL_APARTMENT.
        "core transfer links": count("Stack_Core_Transfer_") == 5,
        "core X-bracing": scene.get("core_bracing") == 5
        and len(braces) == 20
        and count("Stack_Core_Brace_Chord_") == 0
        and all(world_size(o)[1] > 10.0 for o in braces),
        # The diagonals run into the concrete and stay within its depth, so the
        # connection is buried in the core rather than poking out of it.
        "core braces meet the cores": (
            bpy.data.objects.get("Stack_Core_East") is not None
            and all(footprint(o)[1]
                    > footprint(bpy.data.objects["Stack_Core_East"])[0] + 1.0
                    and footprint(o)[3]
                    < footprint(bpy.data.objects["Stack_Core_East"])[3] + 0.01
                    for o in braces)),
        # Four perimeter columns near the E/W facade, tied to the cores by
        # horizontal trusses at the refuge levels.
        "outrigger columns": count("Stack_Outrigger_Column") == 4,
        "outrigger trusses": count("Stack_Outrigger_Chord") == 16
        and count("Stack_Outrigger_Diag") == 16,
        # Every X must have the same proportions, so all braces share one
        # bounding-box height and the diagonals keep a constant angle.
        "uniform X-braces": len({round(world_size(o)[2], 1)
                                 for o in braces}) == 1,
        # Braces and the gaps between them are the same height, including the
        # gaps at the bottom and top, so the brace centres are evenly spaced
        # and no brace touches the ground or the roof.
        "evenly spaced core braces": len(brace_centers) == 5
        and max(b - a for a, b in zip(brace_centers, brace_centers[1:]))
        - min(b - a for a, b in zip(brace_centers, brace_centers[1:])) < 0.05
        and brace_low > 5.0
        and brace_high < scene.get("model_height_m") - 5.0,
        # The mall ceilings are continuous bright rings on every storey.
        "mall ceiling lights": len(mall_lights) == 1
        and len(mall_lights[0].data.vertices) > 0
        and covers(mall_plate_levels, light_z(mall_lights)),
        # Offices and apartments use the house panel lights on every storey,
        # with lit and switched-off fixtures and both colour temperatures. The
        # open refuge storeys take no panel grid, only a perimeter cove.
        "apartment ceiling lights": len(room_objs) == 3
        and all(len(obj.data.vertices) > 0 for obj in room_objs)
        and covers([z for z in upper_levels
                    if z not in refuge_levels
                    and z not in (level_base, level_office_high + 5.0,
                                  level_apartment - 5.0,
                                  level_apartment + 13 * 4.0)],
                   light_z(room_objs)),
        # Lights hang from a plate: no panel may sit under a dropped refuge
        # plate with nothing above it to fix to.
        "no floating lights": not any(
            abs(z - (level_apartment - 5.0 - 0.19)) < 0.1
            for z in light_z(room_objs)),
        "refuge ceilings are a continuous cove": len(refuge_glow) == 1
        and max((max(obj.dimensions.x, obj.dimensions.y)
                 for obj in refuge_glow), default=0.0) >= 100.0
        and covers(refuge_levels, light_z(refuge_glow)),
        "no panels on the refuge storeys": not any(
            z0 + 0.1 < z < z1 - 0.1 for z in light_z(room_objs)
            for z0, z1 in refuge_spans),
        # The void is open air, not a room, so its ceilings take no panel
        # lights: none may sit in the opening except on the occupied bridge.
        "no ceiling lights in the open void": not any(
            abs(p.x) < (scene.get("void_width_m") or 0.0) / 2 - 0.01
            and level_apartment <= p.z <= level_roof - 3 * 4.0
            and not (level_apartment + 11 * 4.0) < p.z
            < (level_apartment + 14 * 4.0)
            for obj in room_objs for p in
            (obj.matrix_world @ v.co for v in obj.data.vertices)),
        # The open refuge plates and the top roof are all planted decks with a
        # perimeter running track, not bare plates.
        "planted decks": all(
            count(f"{name}_Lawn") > 0 and count(f"{name}_Track_") >= 4
            for name in ("Stack_Refuge_Mall_Garden",
                         "Stack_Refuge_Office_Garden",
                         "Stack_Refuge_Apartment_Garden", "Stack_Roof")),
        "camera assigned": scene.camera is not None,
        "viewport framed on building": any(
            area.spaces.active.region_3d is not None
            and area.spaces.active.region_3d.view_distance > 300
            for screen in bpy.data.screens for area in screen.areas
            if area.type == "VIEW_3D"),
    }
    for label, marker in BAND_MARKERS.items():
        checks[label] = count(marker) > 0
    height = scene.get("model_height_m")
    checks["model height recorded"] = height == model_height
    # The top of the building is the open glass edge, not a ceiling: the glass
    # runs on well above the highest floor plate.
    glass_top = top_of("N_Brick") or 0.0
    checks["crown reaches top surface"] = abs(glass_top - height) < 0.05
    checks["cores flush with top"] = abs(
        (top_of("Stack_Core_") or 0.0) - height) < 0.05
    checks["no core protrudes above top"] = (
        top_of("Stack_Core_") or 0.0) <= height + 0.01
    # The three refuge storeys carry no facade element at all, so the plates read
    # straight through them.
    checks["open refuge storeys"] = (
        scene.get("refuge_floors") == 3
        and scene.get("refuge_levels_m") ==
        f"{level_base}-{level_base + 5.0}, "
        f"{level_office_high + 5.0}-{level_office_high + 10.0}, "
        f"{level_apartment - 5.0}-{level_apartment}"
        and not any(o.name[:2] in ("N_", "S_", "E_", "W_")
                    and any(z0 < o.location.z < z1 for z0, z1 in refuge_spans)
                    for o in bpy.data.objects))
    # The four faces must each carry the wrapping bands.
    checks["bands wrap four faces"] = all(
        count(f"{face}_Diagrid") > 0 and count(f"{face}_Fin") > 0
        and count(f"{face}_Brick_Mullion") > 0 for face in ("N", "S", "E", "W"))
    # The former louvre band and its inverted-triangle eye are gone: that block
    # is presented with the same fine vertical fin grid as the band below, which
    # now runs unbroken up to the apartment refuge.
    louver_low, louver_high = level_base + 21 * 5.0, level_apartment - 5.0
    fin_z = [(o.matrix_world @ Vector(c)).z for o in bpy.data.objects
             if o.name.startswith("N_Fin") for c in o.bound_box]
    checks["eye band replaced by vertical grid"] = (
        count("_Louver") == 0 and count("_Eye") == 0
        and bool(fin_z) and min(fin_z) <= louver_low + 0.1
        and max(fin_z) >= louver_high - 0.1)
    top_plate = (top_of("Stack_Floor_Slab") or 0.0) - 0.14
    checks["open glazed crown"] = (
        count("Stack_Roof_Slab") == 0
        and count("Stack_Roof_Step_") == 0
        and glass_top - top_plate >= 2 * 4.0)
    checks["slender slab proportion"] = 2.5 < (
        scene.get("estimated_width_m") / scene.get("estimated_depth_m")) < 3.9
    # One large void pierces the upper band and splits its backing.
    checks["apartment void"] = (
        scene.get("voids") == 1
        and count("Stack_Void_") >= 2
        and count("N_Brick_Glass") > 1 and count("S_Brick_Glass") > 1)
    wall = bpy.data.objects.get("Stack_Void_0_Wall_W")
    checks["apartment void is a tall slot"] = (
        wall is not None and wall.dimensions.z > 30.0)
    # The void's two inward faces are glazed, not plain concrete.
    checks["void inward faces are glazed"] = (
        wall is not None and wall.data.materials
        and wall.data.materials[0].name == "Stack_Glass_Dark")
    # The void's head and sill are the floor plates, so each level keeps a
    # single slab instead of a slab plus a separate lining.
    checks["void edges reuse the floor slabs"] = not any(
        n.startswith("Stack_Void_") and n.rsplit("_", 1)[-1] in ("Lintel", "Sill")
        for n in names)
    # The bridge is glazed across the void in the apartment band's curtain-wall
    # language over all three storeys, including the middle one, so the chevron
    # truss is covered by glass rather than exposed. The truss storey is
    # structure, so it still takes no ceiling fixtures.
    checks["bridge is glazed across the void"] = (
        count("Bridge_Glass") >= 6 and count("Bridge_Spandrel") >= 6
        and count("Bridge_Mullion") >= 40 and count("Bridge_Transom") >= 6)
    bridge_truss_z0 = level_apartment + 12 * 4.0
    bridge_truss_z1 = level_apartment + 13 * 4.0
    checks["bridge truss storey is behind glass"] = any(
        bridge_truss_z0 < center_z(o) < bridge_truss_z1
        for o in bpy.data.objects if "Bridge_Glass" in o.name)
    # The whole truss storey wraps a chevron truss on all four facades at the
    # full building width and depth, not just the bridge span across the void.
    truss_z0, truss_z1 = bridge_truss_z0, bridge_truss_z1
    truss_x = [abs((o.matrix_world @ Vector(c)).x)
               for o in bpy.data.objects if "BridgeTruss" in o.name
               for c in o.bound_box]
    checks["truss storey wraps the whole floor"] = (
        all(count(f"{f}_BridgeTruss_Diag") >= 4 for f in ("N", "S", "E", "W"))
        and count("BridgeTruss_Diag") >= 20
        and count("BridgeTruss_Post") >= 20
        and count("BridgeTruss_Chord") >= 8
        and bool(truss_x)
        and max(truss_x) > (scene.get("estimated_width_m") or 0.0) / 2 - 1.0)
    # The apartment curtain wall runs on over that storey on every face, so the
    # truss is wrapped by the apartment facade instead of standing in the clear.
    checks["truss storey is wrapped by the apartment facade"] = any(
        "_Brick" in o.name and truss_z0 < center_z(o) < truss_z1
        for o in bpy.data.objects)
    bridge_mid_z1 = level_apartment + 13 * 4.0
    checks["bridge middle has no ceiling lights"] = not any(
        abs(p.z - bridge_mid_z1) < 0.3
        for o in room_objs
        for p in (o.matrix_world @ v.co for v in o.data.vertices))
    # All three refuges stand on an Abeno Harukas-style chevron belt truss
    # wrapped on all four faces, on the storey directly BENEATH the running-track
    # deck, not on the track level itself.
    belt_z = [(o.matrix_world @ Vector(c)).z for o in bpy.data.objects
              if "Refuge_Belt_" in o.name for c in o.bound_box]
    checks["refuge belt trusses"] = (
        all(count(f"Refuge_Belt_{int(z)}_{part}") >= 4
            for z in (level_base, level_office_high + 5.0, level_apartment - 5.0)
            for part in ("Diag", "Post"))
        and bool(belt_z)
        and max(belt_z) < level_apartment - 10.0 + 0.5)
    # The mid-office refuge is three stacked parts: the chevron belt inside the
    # diagrid glazing below, the running-track storey glazed by the diagrid band
    # carried on over it, and the fully open storey above. The facade stays one
    # form down the band, so the refuge glazing matches the diagrid below.
    checks["mid-office refuge truss and garden"] = (
        count("Refuge_Belt_120_Diag") >= 4
        and count("Refuge_Belt_120_Post") >= 4
        and count("Stack_Refuge_Office_Garden_Lawn") > 0
        and count("Stack_Refuge_Office_Garden_Track_") >= 4
        and any(abs(center_z(o) - level_office_high) < 0.2
                for o in bpy.data.objects
                if o.name.startswith("Stack_Floor_Slab")))
    # The diagrid band runs on over the running-track storey, so its top is the
    # refuge's open edge and the track glazing keeps the diagrid form.
    level_office_low = level_base + 5 * 5.0
    diagrid_z = [(o.matrix_world @ Vector(c)).z for o in bpy.data.objects
                 if "_Diagrid" in o.name for c in o.bound_box]
    checks["diagrid carries over the track storey"] = (
        bool(diagrid_z)
        and abs(min(diagrid_z) - level_office_low) < 0.6
        and abs(max(diagrid_z) - (level_office_high + 5.0)) < 0.6)
    # The void's bottom is open too: the two halves are not joined there, so no
    # plate may span the opening at the apartment's lowest level.
    def spans_void(obj):
        pts = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        half = (scene.get("void_width_m") or 0.0) / 2
        return (half and min(p.x for p in pts) < -half + 1e-6
                and max(p.x for p in pts) > half - 1e-6)

    bottom_slabs = [obj for obj in bpy.data.objects
                    if obj.type == "MESH"
                    and (obj.name.startswith("Stack_Floor_Slab")
                         or obj.name.startswith("Stack_Core_Transfer_")
                         or obj.name.endswith("_Brick_Transom"))
                    and abs(center_z(obj) - level_apartment) < 0.2]
    checks["void bottom is open"] = (
        bool(bottom_slabs) and not any(spans_void(o) for o in bottom_slabs))
    # The apartment refuge cove is split by the void too: each tower half closes
    # its own ring, so no cove geometry may sit inside the opening.
    cove_x = [abs((obj.matrix_world @ v.co).x)
              for obj in bpy.data.objects
              if obj.name.startswith("Stack_Refuge_Ceiling_Lights")
              for v in obj.data.vertices
              if level_apartment - 0.5 < (obj.matrix_world @ v.co).z
              < level_apartment + 0.1]
    checks["refuge cove is split at the void"] = (
        bool(cove_x)
        and min(cove_x) >= (scene.get("void_width_m") or 0.0) / 2 - 0.1)
    # The upper band must read as narrow vertical strips (the Abeno Harukas
    # curtain-wall proportion): fine vertical mullions on a ~1.25 m module.
    mullion_x = sorted({round(obj.location.x, 3)
                        for obj in bpy.data.objects
                        if obj.name.startswith("N_Brick_Mullion")})
    gaps = [b - a for a, b in zip(mullion_x, mullion_x[1:])]
    checks["apartment band is vertical strips"] = (
        len(mullion_x) > 80 and bool(gaps)
        and 1.0 < gaps[len(gaps) // 2] < 1.5)
    # The void edges land on mullion centres, so the windows on the two tower
    # halves beside the opening are whole rather than cut in half.
    checks["void edges land on the mullion grid"] = (
        bool(scene.get("void_width_m"))
        and round(scene.get("void_width_m") / 2, 3)
        in {round(x, 3) for x in mullion_x})
    # The upper band is glass and frame; no solid masonry backing may show.
    checks["apartment band is glazed"] = (
        count("Brick_Glass") > 0 and count("Brick_Back") == 0)
    # The lower quarter of each storey is a light blue spandrel panel, per the
    # Abeno Harukas facade, not a white or masonry band.
    spandrel = bpy.data.materials.get("Stack_Spandrel_Blue")
    spandrel_color = None
    if spandrel and spandrel.use_nodes:
        bsdf = spandrel.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            spandrel_color = tuple(bsdf.inputs["Base Color"].default_value)
    checks["apartment spandrel is light blue"] = (
        count("Brick_Spandrel") > 0 and spandrel_color is not None
        and spandrel_color[2] > spandrel_color[0] and spandrel_color[0] > 0.5)
    # The apartment frame is a matte white, not a dark reflective metal.
    apartment_frame = bpy.data.materials.get("Stack_Apartment_Frame")
    frame_color = None
    if apartment_frame and apartment_frame.use_nodes:
        bsdf = apartment_frame.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            frame_color = tuple(bsdf.inputs["Base Color"].default_value)
    checks["apartment frame is white"] = (
        count("Brick_Mullion") > 0 and frame_color is not None
        and min(frame_color[:3]) > 0.8
        and max(frame_color[:3]) - min(frame_color[:3]) < 0.05)

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
