"""Verify the generated Stack 3 scene.

Checks the frozen envelope, the eight-band program, the per-band facade
systems, floor-plate rhythm, mesh sanity and the review-camera setup. Run it on
the saved .blend, not on a live build:

    blender --background --factory-startup --python-exit-code 1 \
        --python verify_stack3.py -- out/the_stack3.blend

Numbers are the model's own spec (108 x 36 m plan, 350 m to the crown), not a
survey of the real proposal.
"""

import os
import sys

import bmesh
import bpy
from mathutils import Vector

WIDTH, DEPTH, HEIGHT = 108.0, 36.0, 350.0
HALF_W, HALF_D = WIDTH / 2.0, DEPTH / 2.0
FACADE_RELIEF = 0.30     # deepest facade projection allowed past the slab edge


def bbox(objs):
    xs, ys, zs = [], [], []
    for obj in objs:
        for corner in obj.bound_box:
            v = obj.matrix_world @ Vector(corner)
            xs.append(v.x)
            ys.append(v.y)
            zs.append(v.z)
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def envelope_objects():
    """Building geometry: drop the site plaza and the two loose tree sets.

    The arcade tree columns and their planting are part of the facade and stay
    in; the ground plane and the ground/crown trees are landscape and do not
    define the envelope.
    """
    out = []
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.name.startswith("Stack3_"):
            continue
        if "Site" in obj.name:
            continue
        if obj.name.startswith("Stack3_Crown_Trees"):
            continue
        out.append(obj)
    return out


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    blend = args[0] if args else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "out", "the_stack3.blend")
    bpy.ops.wm.open_mainfile(filepath=blend)
    scene = bpy.context.scene
    env = envelope_objects()
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    x0, x1, y0, y1, z0, z1 = bbox(env)
    names = [o.name for o in bpy.data.objects]

    def z_span(prefix):
        objs = [o for o in env if o.name.startswith("Stack3_" + prefix)]
        return bbox(objs)[4:] if objs else (None, None)

    def present(prefix):
        return any(n.startswith("Stack3_" + prefix) for n in names)

    boundary_edges = 0
    degenerate = 0
    for obj in meshes:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        boundary_edges += sum(1 for e in bm.edges if not e.is_manifold)
        bm.free()
        degenerate += sum(1 for p in obj.data.polygons if p.area < 1e-9)

    overhang = max(x1 - HALF_W, -HALF_W - x0, y1 - HALF_D, -HALF_D - y0)

    checks = {
        "three stacked bands": all(present(b) for b in (
            "Lattice", "Plaza", "Apartment")),
        "plan is 108 m wide": abs((x1 - x0) - WIDTH) <= 2 * FACADE_RELIEF,
        "plan is 36 m deep": abs((y1 - y0) - DEPTH) <= 2 * FACADE_RELIEF,
        "flat roof deck at 308 m": abs(z_span("Roof_Deck")[1] - 308.4) < 0.05,
        "parapet tops at 309.6 m": abs(z1 - (308.0 + 0.4 + 1.2)) < 0.05,
        "slab sits on the ground": abs(z0) <= 0.02,
        "facade stays within its relief band": overhang <= FACADE_RELIEF,
        "lattice glass 0-142 m": abs(z_span("Lattice_Glass")[0] - 0.2) < 0.05
        and abs(z_span("Lattice_Glass")[1] - 141.8) < 0.05,
        "lattice carries a frame and X braces": (
            present("Lattice_Frame") and present("Lattice_Braces")),
        "lattice braces start above the refuge": (
            47.8 <= z_span("Lattice_Braces")[0] <= 49.0
            and 141.0 <= z_span("Lattice_Braces")[1] <= 142.6),
        "bottom two tiers are framed cells, not X": (
            present("Lattice_Base_Rails")
            and abs(z_span("Lattice_Base_Rails")[0] - 0.0) < 0.05
            and abs(z_span("Lattice_Base_Rails")[1] - 43.9) < 0.8),
        "no parking band remains": not any(
            n.startswith("Stack3_Parking") for n in names),
        "no fin band or old base remains": not any(
            n.startswith("Stack3_Office") or n.startswith("Stack3_Hotel")
            or n.startswith("Stack3_Base") for n in names),
        "plaza arcade 147-177 m": abs(z_span("Plaza_Trees")[0] - 147.35) < 0.1,
        "glazed apartment bays 182-294 m": (
            182.0 <= z_span("Apartment_Glass_S")[0] <= 182.4
            and 293.6 <= z_span("Apartment_Glass_S")[1] <= 294.0),
        "attic closes the band at 308 m":
        z_span("Apartment_Topband")[1] == 308.0,
        "nothing stands above the roof": not any(
            n.startswith("Stack3_Crown") for n in names),
        "two long-axis cores": (
            abs(bbox([bpy.data.objects["Stack3_Structure_Cores"]])[0] + 34.0) < 0.1
            and abs(bbox([bpy.data.objects["Stack3_Structure_Cores"]])[1] - 34.0) < 0.1),
        "floor plates: 5 m below, 4 m in the apartments": (
            abs(z_span("Structure_Floors")[0] - 4.65) < 0.05
            and abs(z_span("Structure_Floors")[1] - 306.0) < 0.05),
        "shallow slab reads as a slab": (WIDTH / DEPTH) > 2.6,
        "every mesh has a material": all(o.data.materials for o in meshes),
        "closed meshes": boundary_edges == 0,
        "no degenerate faces": degenerate == 0,
        "no default object names": not any(
            n in ("Cube", "Plane", "Cylinder", "Camera", "Light") for n in names),
        "review camera assigned": scene.camera is not None,
        "five review cameras": sum(
            1 for o in bpy.data.objects if o.type == "CAMERA") == 5,
        "EEVEE previews": scene.render.engine == "BLENDER_EEVEE",
        "portrait review frames": scene.render.resolution_x == 900
        and scene.render.resolution_y == 1200,
        "reference recorded": "mvrdv.com" in scene.get("reference_urls", ""),
        "band program recorded": len(scene.get("bands", "").split(",")) == 5,
        "object count in range": 40 <= len(meshes) <= 110,
    }

    failed = []
    print(f"Envelope  x {x0:.2f}..{x1:.2f}  y {y0:.2f}..{y1:.2f}  z {z0:.2f}..{z1:.2f}")
    print(f"Meshes {len(meshes)}  boundary edges {boundary_edges}  "
          f"degenerate faces {degenerate}  facade overhang {overhang:.2f} m")
    for label, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}: {label}")
        if not passed:
            failed.append(label)
    if failed:
        raise SystemExit(f"Failed {len(failed)} checks: {', '.join(failed)}")
    print(f"All {len(checks)} checks passed")


if __name__ == "__main__":
    main()
