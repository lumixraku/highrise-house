"""Update only the podium's external diamond lattice in an existing scene.

Run:
    blender --background --python update_podium_diamond_grid.py -- out/highrise_house.blend
"""

import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import materials
import build_house as house


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    blend_path = os.path.abspath(argv[0] if argv else "out/highrise_house.blend")
    bpy.ops.wm.open_mainfile(filepath=blend_path)

    grid = bpy.data.objects.get("Podium_Diamond_Grid")
    if grid:
        bpy.data.objects.remove(grid, do_unlink=True)
    white = materials.make_podium_diamond()
    house.configure_tower(2, 18, core_column_bays=2)
    first_w = house.W
    house.configure_tower(3, 20,
                          core_column_bays=house.COMPANION_CORE_COLUMN_BAYS)
    second_w = house.W
    second_centre, second_rotation = house.book_layout(first_w, second_w)
    podium_specs = (
        (Vector((0.0, 0.0)), first_w + 2.0 * house.PODIUM_LENGTH_MARGIN,
         house.PODIUM_DEPTH, 0.0),
        (second_centre, second_w + 2.0 * house.PODIUM_LENGTH_MARGIN,
         house.PODIUM_DEPTH, second_rotation),
    )
    updated = house.build_podium({"podium_diamond": white}, podium_specs,
                                 diamond_grid_only=True)
    count = len(updated["Podium_Diamond_Grid"].data.vertices) // 8

    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"rebuilt {count} evenly spaced podium diamond members -> {blend_path}")


if __name__ == "__main__":
    main()
