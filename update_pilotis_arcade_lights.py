"""Update only the recessed lights inside the pilotis arcades.

Run:
    blender --background --python update_pilotis_arcade_lights.py -- out/highrise_house.blend
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_house as house


def remove_arcade_lights():
    """Remove only the separate arcade-fixture mesh and its point lamps."""
    for obj in list(bpy.data.objects):
        if (obj.name.startswith("Pilotis_Arcade_Lights")
                or obj.name.startswith("Pilotis_Arcade_Point_")):
            bpy.data.objects.remove(obj, do_unlink=True)


def add_lights_for_tower(block_groups, windows_long, core_column_bays,
                         transform=None):
    house.configure_tower(block_groups, windows_long,
                          core_column_bays=core_column_bays)
    lamps = house.pilotis_arcade_lights({
        "podium_ceiling_light_cool": bpy.data.materials["PodiumCeilingLight_Cool"],
        "podium_ceiling_light_warm": bpy.data.materials["PodiumCeilingLight_Warm"],
    })
    if transform is not None:
        lamps.matrix_world = transform @ lamps.matrix_world


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    blend_path = os.path.abspath(argv[0] if argv else "out/highrise_house.blend")
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    remove_arcade_lights()

    house.configure_tower(2, 18, core_column_bays=2)
    first_w = house.W
    add_lights_for_tower(2, 18, 2)

    house.configure_tower(3, 20,
                          core_column_bays=house.COMPANION_CORE_COLUMN_BAYS)
    second_w = house.W
    second_centre, second_rotation = house.book_layout(first_w, second_w)
    transform = (Matrix.Translation(Vector((second_centre.x, second_centre.y, 0.0)))
                 @ Matrix.Rotation(math.radians(second_rotation), 4, "Z"))
    add_lights_for_tower(3, 20, house.COMPANION_CORE_COLUMN_BAYS, transform)

    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"updated only pilotis arcade lights -> {blend_path}")


if __name__ == "__main__":
    main()
