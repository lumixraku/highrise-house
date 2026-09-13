"""Check The Stack scene for coplanar overlapping faces (z-fighting).

Two faces that lie on the same plane and overlap render as a flickering speckle
(z-fighting). This walks every axis-aligned face, buckets the faces by plane,
and counts overlapping pairs between different objects. Crossing members are
kept on separate depth planes in the generator, so the count is a regression
guard: the budget fails the check if coplanar overlaps creep back in.

Run after building:
    blender --background --factory-startup --python-exit-code 1 \
        --python check_stack_zfight.py -- out/the_stack.blend
"""

import sys
from collections import defaultdict

import bpy
from mathutils import Vector

EPS = 6e-4          # plane coincidence tolerance, metres
MIN_AREA = 1e-4     # ignore slivers below this overlap area, m^2
BUDGET = 500        # coplanar overlapping face pairs allowed in the scene
FACADE_BUDGET = 10  # ... and among curtain-wall members, which read in renders


def main():
    blend = sys.argv[sys.argv.index("--") + 1]
    bpy.ops.wm.open_mainfile(filepath=blend)

    buckets = defaultdict(list)
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        matrix = obj.matrix_world
        normals = matrix.to_3x3()
        base = obj.name.split(".")[0]
        mesh = obj.data
        for poly in mesh.polygons:
            normal = normals @ poly.normal
            length = normal.length
            if length < 1e-9:
                continue
            normal = normal / length
            axis = max(range(3), key=lambda i: abs(normal[i]))
            if abs(normal[axis]) < 0.9999:
                continue
            sign = 1 if normal[axis] > 0 else -1
            corners = [matrix @ mesh.vertices[v].co for v in poly.vertices]
            offset = sum(c[axis] for c in corners) / len(corners)
            other = [i for i in range(3) if i != axis]
            bounds = (min(c[other[0]] for c in corners),
                      max(c[other[0]] for c in corners),
                      min(c[other[1]] for c in corners),
                      max(c[other[1]] for c in corners))
            buckets[(axis, sign, round(offset, 3))].append((base,) + bounds)

    total, facade = 0, 0
    facade_marks = ("Brick_", "Void_CW_", "Base_Glass", "Base_Mullion",
                    "Base_Transom", "Diagrid_", "Garden_Glass", "Fins_Glass",
                    "_Fin", "_Mullion", "_Transom", "_Spandrel")
    for faces in buckets.values():
        if len(faces) < 2:
            continue
        faces.sort(key=lambda f: f[1])
        for i, a in enumerate(faces):
            for b in faces[i + 1:]:
                if b[1] >= a[2] - EPS:
                    break
                if a[0] == b[0]:
                    continue
                overlap = (min(a[2], b[2]) - max(a[1], b[1])) * \
                          (min(a[4], b[4]) - max(a[3], b[3]))
                if overlap <= MIN_AREA:
                    continue
                total += 1
                if "Escalator" in a[0] or "Escalator" in b[0]:
                    continue
                if any(m in a[0] for m in facade_marks) and \
                        any(m in b[0] for m in facade_marks):
                    facade += 1

    print(f"coplanar overlapping face pairs: {total} "
          f"(curtain wall: {facade})")
    failed = total > BUDGET or facade > FACADE_BUDGET
    print("FAIL" if failed else "PASS")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
