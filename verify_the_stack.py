"""Verify the editable The Stack proposal scene."""

import sys

import bpy
from mathutils import Vector

BAND_MARKERS = {
    "base glazing": "Base_Glass",
    "diagrid band": "Diagrid",
    "garden band": "Garden_Canopy",
    "louvre band": "Louver",
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

    mall_floors = scene.get("mall_floors", 14)
    storeys, sz = [], 0.0
    for floors, height in ((mall_floors, 5.0),
                           (scene.get("office_floors", 25), 5.0),
                           (scene.get("apartment_floors", 31), 4.0)):
        for _ in range(floors):
            sz += height
            storeys.append(round(sz, 3))
    mall_levels, upper_levels = storeys[:mall_floors], storeys[mall_floors:]
    refuge_levels = [z for z in upper_levels
                     if any(z0 < z <= z1 for z0, z1 in ((70.0, 75.0),
                                                        (190.0, 195.0)))]
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
        "base,refuge,garden,diagrid,fins,louver,refuge,brick",
        "storey program recorded": scene.get("floor_count") == 68
        and scene.get("mall_floors") == 14
        and scene.get("office_floors") == 25
        and scene.get("apartment_floors") == 29,
        "storey heights recorded": scene.get("storey_heights_m") ==
        "mall 5.0, office 5.0, apartment 4.0",
        # Office and apartment plates run to the roof; six are split around the
        # wind slots, so the object count exceeds the number of storeys.
        "floor plates to roof": 55 <= count("Stack_Floor_Slab") <= 100,
        # The mall carries one ring of retail plates per storey, all below the
        # office zone.
        "mall storey plates": count("Stack_Mall_Slab") >= 40
        and all(obj.location.z <= 70.0 for obj in bpy.data.objects
                if obj.name.startswith("Stack_Mall_Slab")),
        "long escalator in base": count("Stack_Base_Escalator") >= 2
        and count("Stack_Base_Tread") > 10,
        # The base is a frosted glass wall with a frame heavy enough to read at
        # render scale, not an invisible sheet of clear glass.
        "frosted base glazing": frost_alpha is not None
        and 0.35 <= frost_alpha <= 0.85
        and count("Base_Glass") >= 4 and count("Base_Mullion") >= 8
        and max((max(o.dimensions.x, o.dimensions.y) for o in bpy.data.objects
                 if "Base_Mullion" in o.name), default=0.0) >= 0.25,
        # The base glass is grouped three storeys high on the floor plates: four
        # groups at the top of the mall, the lowest storeys left as openwork.
        "base glass grouped three storeys": (
            len(base_glass) == 4 * len(("N", "S", "E", "W"))
            and all(abs(o.dimensions.z - 3 * 5.0) < 0.01 for o in base_glass)
            and min(o.location.z - o.dimensions.z / 2 for o in base_glass)
            >= 10.0 - 0.01),
        "dual cores": all(f"Stack_Core_{side}" in names
                          for side in ("West", "East")),
        "core transfer links": count("Stack_Core_Transfer_") == 6,
        "core X-bracing": scene.get("core_bracing") == 5
        and len(braces) == 20
        and count("Stack_Core_Brace_Chord_") == 0
        and all(world_size(o)[1] > 10.0 for o in braces),
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
        and covers(mall_levels, light_z(mall_lights)),
        # Offices and apartments use the house panel lights on every storey,
        # with lit and switched-off fixtures and both colour temperatures. The
        # open refuge storeys take no panel grid, only a perimeter cove.
        "apartment ceiling lights": len(room_objs) == 3
        and all(len(obj.data.vertices) > 0 for obj in room_objs)
        and covers([z for z in upper_levels if z not in refuge_levels],
                   light_z(room_objs)),
        "refuge ceilings are a continuous cove": len(refuge_glow) == 1
        and max((max(obj.dimensions.x, obj.dimensions.y)
                 for obj in refuge_glow), default=0.0) >= 100.0
        and covers(refuge_levels, light_z(refuge_glow)),
        "no panels on the refuge storeys": not any(
            z0 + 0.1 < z < z1 - 0.1 for z in light_z(room_objs)
            for z0, z1 in ((70.0, 75.0), (190.0, 195.0))),
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
    checks["model height recorded"] = height == 321.8
    # The top of the building is the open glass edge, not a ceiling: the glass
    # runs on well above the highest floor plate.
    glass_top = top_of("N_Brick") or 0.0
    checks["crown reaches top surface"] = abs(glass_top - height) < 0.05
    checks["cores flush with top"] = abs(
        (top_of("Stack_Core_") or 0.0) - height) < 0.05
    checks["no core protrudes above top"] = (
        top_of("Stack_Core_") or 0.0) <= height + 0.01
    # The two refuge storeys carry no facade element at all, so the plates read
    # straight through them.
    checks["open refuge storeys"] = (
        scene.get("refuge_floors") == 2
        and scene.get("refuge_levels_m") == "70.0-75.0, 190.0-195.0"
        and not any(o.name[:2] in ("N_", "S_", "E_", "W_")
                    and (70.0 < o.location.z < 75.0
                         or 190.0 < o.location.z < 195.0)
                    for o in bpy.data.objects))
    # The four faces must each carry the wrapping bands.
    checks["bands wrap four faces"] = all(
        count(f"{face}_Diagrid") > 0 and count(f"{face}_Fin") > 0
        and count(f"{face}_Brick_Mullion") > 0 for face in ("N", "S", "E", "W"))
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
    # The three-storey bridge across the void is occupied, so the opening is
    # glazed across it in the same curtain-wall language as the apartment band.
    checks["bridge across the void is glazed"] = (
        count("Bridge_Glass") == 2 * 3 and count("Bridge_Spandrel") == 2 * 3
        and count("Bridge_Mullion") >= 8 and count("Bridge_Transom") >= 8)
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
