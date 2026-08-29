"""Update only the facade-aligned arches above the podium roof.

Run:
    blender --background --python update_pilotis_arcades.py -- out/highrise_house.blend
"""

import math
import os
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_house as house


def remove_arcades():
    for name in ("Pilotis_Arcades", "Pilotis_Arcades.001"):
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)


def remove_old_transition_band(object_names, z0, z1):
    """Remove only legacy faces that would block the raised arcade."""
    for name in object_names:
        obj = bpy.data.objects.get(name)
        if not obj:
            continue
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        faces = [
            face for face in bm.faces
            if all(z0 - 1e-4 <= (obj.matrix_world @ vertex.co).z <= z1 + 1e-4
                   for vertex in face.verts)
        ]
        if faces:
            bmesh.ops.delete(bm, geom=faces, context="FACES")
            bm.to_mesh(mesh)
            mesh.update()
        bm.free()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    blend_path = os.path.abspath(argv[0] if argv else "out/highrise_house.blend")
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    remove_arcades()
    remove_old_transition_band(("Facade_Spandrels", "Facade_Spandrels.001"),
                               house.BASE_Z, house.BASE_Z + house.H)
    remove_old_transition_band(("Structure", "Structure.001"),
                               house.BASE_Z - house.SLAB_T, house.BASE_Z)
    facade_mat = bpy.data.materials["Spandrel"]

    house.configure_tower(2, 18, core_column_bays=2)
    first_w = house.W
    house.pilotis_arcades(facade_mat)

    house.configure_tower(3, 20, core_column_bays=house.COMPANION_CORE_COLUMN_BAYS)
    second_w = house.W
    second_centre, second_rotation = house.book_layout(first_w, second_w)
    second_arcade = house.pilotis_arcades(facade_mat)
    transform = (Matrix.Translation(Vector((second_centre.x, second_centre.y, 0.0)))
                 @ Matrix.Rotation(math.radians(second_rotation), 4, "Z"))
    second_arcade.matrix_world = transform @ second_arcade.matrix_world

    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"updated only pilotis facade arcades -> {blend_path}")


if __name__ == "__main__":
    main()
