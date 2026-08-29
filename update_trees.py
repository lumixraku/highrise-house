"""Update only tree and planting meshes in an existing high-rise scene.

Run:
    blender --background --python update_trees.py -- out/highrise_house.blend
"""

import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_house as house


def remove_meshes(names):
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    blend_path = os.path.abspath(argv[0] if argv else "out/highrise_house.blend")
    bpy.ops.wm.open_mainfile(filepath=blend_path)

    foliage_mat = bpy.data.materials["Foliage"]
    trunk_mat = bpy.data.materials["Trunk"]
    concrete_mat = bpy.data.materials["Concrete"]
    remove_meshes(("Podium_Garden_Planters", "Podium_Garden_Foliage",
                   "Podium_Garden_Trunks"))

    house.configure_tower(2, 18, core_column_bays=2)
    first_w = house.W
    house.configure_tower(3, 20, core_column_bays=house.COMPANION_CORE_COLUMN_BAYS)
    second_w = house.W
    second_center, second_rotation = house.book_layout(first_w, second_w)

    podium_specs = (
        (Vector((0.0, 0.0)), first_w + 2.0 * house.PODIUM_LENGTH_MARGIN,
         house.PODIUM_DEPTH, 0.0),
        (second_center, second_w + 2.0 * house.PODIUM_LENGTH_MARGIN,
         house.PODIUM_DEPTH, second_rotation),
    )
    planters, foliage, trunks = house.podium_roof_garden(
        podium_specs, house.PODIUM_TOTAL_FLOORS * house.H,
        {"concrete": concrete_mat, "foliage": foliage_mat, "trunk": trunk_mat})
    house.join(planters, "Podium_Garden_Planters")
    house.join(foliage, "Podium_Garden_Foliage")
    house.join(trunks, "Podium_Garden_Trunks")

    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"updated only tree meshes -> {blend_path}")


if __name__ == "__main__":
    main()
