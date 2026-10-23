"""Verify the generated Centre Pompidou scene."""

import sys

import bpy

FLOOR_H = 10.0


def main():
    blend = sys.argv[sys.argv.index("--") + 1]
    bpy.ops.wm.open_mainfile(filepath=blend)
    names = [obj.name for obj in bpy.data.objects]
    flights = [
        obj for obj in bpy.data.objects
        if "_Flight" in obj.name and obj.name.startswith("Escalator_")
    ]
    left_flights = [obj for obj in flights if obj.name.startswith("Escalator_Left_Facade_Up")]
    right_flights = [obj for obj in flights if obj.name.startswith("Escalator_Right_Facade_Up")]
    braces = [
        obj for obj in bpy.data.objects
        if obj.name.startswith("White_Frame_Brace")
    ]
    short_braces = [
        obj for obj in bpy.data.objects
        if obj.name.startswith("Short_Frame_Brace")
    ]
    continuous_tubes = [
        obj for obj in bpy.data.objects
        if obj.name.endswith("_Continuous_Glass_Tube")
    ]
    balcony_slabs = [
        obj for obj in bpy.data.objects
        if obj.name.startswith("Perimeter_Balcony_Slab")
    ]
    frame_columns = [
        obj for obj in bpy.data.objects
        if obj.name.startswith("White_Frame_Column")
    ]
    checks = {
        "seven storeys bounded by eight slabs": sum(name.startswith("Floor_Slab") for name in names) == 8,
        "216 metre facade": abs(max(obj.dimensions.x for obj in bpy.data.objects if obj.name.startswith("Floor_Slab")) - 216.0) < 0.01,
        "10 metre storeys": all(abs(a.location.z - b.location.z - 10.0) < 0.01 for a, b in zip(sorted((obj for obj in bpy.data.objects if obj.name.startswith("Floor_Slab")), key=lambda obj: obj.location.z)[1:], sorted((obj for obj in bpy.data.objects if obj.name.startswith("Floor_Slab")), key=lambda obj: obj.location.z)[:-1])),
        "70 metre superstructure": abs(max(obj.location.z for obj in bpy.data.objects if obj.name.startswith("Floor_Slab")) - 70.0) < 0.01,
        "open ground floor": not any(obj.name.startswith("Curtain_Wall_Panel") and obj.location.z < FLOOR_H / 2 for obj in bpy.data.objects),
        "no opaque facade shadow shell": not any(name.startswith("Interior_Shadow") for name in names),
        "reflective transparent facade glass": (
            bpy.data.materials.get("Facade_Glass") is not None
            and bpy.data.materials["Facade_Glass"].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value <= 0.03
            and bpy.data.materials["Facade_Glass"].node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value >= 0.85
        ),
        "four additional frame groups": sum(name.startswith("White_Frame_Column") for name in names) == 36,
        "diagonal braces": sum(name.startswith("White_Frame_Brace") for name in names) == 204,
        "braces only on upper six storeys": min(obj.location.z for obj in braces) >= 15.0,
        "short facade diagonal braces": len(short_braces) == 60 and min(obj.location.z for obj in short_braces) >= 15.0,
        "twelve X escalator flights": len(flights) == 12,
        "six flights on each route": len(left_flights) == 6 and len(right_flights) == 6,
        "one escalator on each long facade": (
            all(obj.location.y < -30.0 for obj in left_flights)
            and all(obj.location.y > 30.0 for obj in right_flights)
        ),
        "mirror-symmetric facade routes": all(
            abs(left.location.y + right.location.y) < 0.01
            and abs(left.location.x + right.location.x) < 0.01
            for left, right in zip(sorted(left_flights, key=lambda obj: obj.location.z),
                                   sorted(right_flights, key=lambda obj: obj.location.z))
        ),
        "seven landings per route": sum("_Horizontal_Landing" in name for name in names) == 14,
        "both routes span the facade": all(max(obj.location.x for obj in route) - min(obj.location.x for obj in route) > 130.0 for route in (left_flights, right_flights)),
        "routes run in opposite directions": all(obj["route_direction"] == 1 for obj in left_flights) and all(obj["route_direction"] == -1 for obj in right_flights),
        "flight slope at or below 30 degrees": all(abs(obj["slope_degrees"]) <= 30.0 for obj in flights),
        "detailed escalator treads": sum("_Tread" in name for name in names) == 420,
        "two watertight continuous glass tubes": len(continuous_tubes) == 2,
        "each tube crosses all landings": all(len(obj.data.splines[0].bezier_points) == 14 for obj in continuous_tubes),
        "dense enclosure hoops": sum("_Enclosure_Rib" in name for name in names) >= 48,
        "landing enclosure hoops": sum("_Landing_Rib" in name for name in names) == 98,
        "no outer truss cage": not any(name.startswith("Escalator_Outer_Frame") for name in names),
        "no redundant escalator cantilevers": not any(name.startswith("Escalator_Extended_Cantilever") for name in names),
        "facade glazing": sum(name.startswith("Curtain_Wall") for name in names) >= 100,
        "short facade glass": sum(name.startswith("Short_Facade_Glass_Panel") for name in names) == 60,
        "no thin facade columns": not any(
            name.startswith("Curtain_Wall_Mullion")
            or name.startswith("Short_Facade_Mullion")
            for name in names
        ),
        "balcony on every upper level": (
            len(balcony_slabs) == 28
            and sorted({round(obj.location.z - 0.05, 3) for obj in balcony_slabs})
            == [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0]
        ),
        "four metre wraparound balconies": (
            all(abs(obj.dimensions.x - 4.0) < 0.01 or abs(obj.dimensions.y - 4.0) < 0.01
                for obj in balcony_slabs)
            and sum(name.startswith("Perimeter_Balcony_Railing") for name in names) == 28
        ),
        "frame supports below balcony walking surface": all(
            max(frame.location.z + 0.28 for frame in bpy.data.objects
                if (frame.name.startswith("White_Frame_Horizontal")
                    or frame.name.startswith("Short_Frame_Horizontal")
                    or frame.name.startswith("Facade_Panel_Standoff"))
                and abs(frame.location.z - (obj.location.z - 0.40)) < 0.01)
            < obj.location.z + 0.16
            for obj in balcony_slabs
        ),
        "four metre glass-to-frame clearance": (
            min(abs(obj.location.y) - 0.32 - 30.0 for obj in frame_columns) >= 4.0
        ),
        "column-free interior": not any(name.startswith("Interior_Structural_Column") for name in names),
        "no interior trusses": not any(name.startswith("Interior_Exposed_Truss") for name in names),
        "no internal service cores": not any(name.startswith("Service_Core_Shaft") for name in names),
        "no internal lift shafts": not any(name.startswith("Lift_Shaft") for name in names),
        "ceiling grid": sum(name.startswith("Ceiling_Grid_Main") for name in names) == 105,
        "facade standoffs": sum(name.startswith("Facade_Panel_Standoff") for name in names) == 238,
        "blue services": any(name.startswith("Blue_") for name in names),
        "green services": any(name.startswith("Green_") for name in names),
        "yellow services": any(name.startswith("Yellow_") for name in names),
        "red circulation": any(name.startswith("Red_") for name in names),
        "services mirrored on both long facades": all(
            any(name.startswith(prefix) and obj.location.y < -30.0 for name, obj in ((o.name, o) for o in bpy.data.objects))
            and any(name.startswith(prefix) and obj.location.y > 30.0 for name, obj in ((o.name, o) for o in bpy.data.objects))
            for prefix in ("Blue_Air_Duct", "Green_Water_Pipe", "Yellow_Electrical", "Red_Circulation")
        ),
        "camera assigned": bpy.context.scene.camera is not None,
    }
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
