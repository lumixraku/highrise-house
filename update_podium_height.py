"""Rebuild only the podium after changing its storey height.

Run:
    blender --background --python update_podium_height.py -- out/highrise_house.blend
"""

import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_house as house

PODIUM_ROOTS = {
    "Podium_Ceiling_Lights", "Podium_Diamond_Grid", "Podium_Floor_Plates",
    "Podium_Garden_Foliage", "Podium_Garden_Planters", "Podium_Garden_Trunks",
    "Podium_Glass", "Podium_Mullions", "Podium_Pilotis_Ceiling_Lights",
    "Podium_Structure",
}
TOWER_ROOTS = {
  "Ceiling_Lights", "Facade_Spandrels", "Floor_Plates", "Pilotis_Arcades",
  "Sky_Garden_Grille", "Sky_Garden_Planting", "Sky_Garden_Trunks",
  "Structural_Trusses", "Structural_Trusses_LowerTower",
  "Vent_Louvres", "Vent_Shadowboxes", "Window_Mullions", "Windows_Glass",
}


def remove_podium_meshes():
    for obj in tuple(bpy.data.objects):
        if obj.type == "MESH" and obj.name.split(".")[0] in PODIUM_ROOTS:
            bpy.data.objects.remove(obj, do_unlink=True)


def raise_tower_meshes(delta_z):
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.name.split(".")[0] in TOWER_ROOTS:
            obj.location.z += delta_z


def raise_structure_above_podium(old_top, delta_z):
    """Lift only Structure vertices already above the old podium roof."""
    if abs(delta_z) < 1e-9:
        return
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.name.split(".")[0] != "Structure":
            continue
        for vertex in obj.data.vertices:
            world_z = (obj.matrix_world @ vertex.co).z
            if world_z >= old_top - 1e-4:
                vertex.co.z += delta_z


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    source_path = os.path.abspath(argv[0] if argv else "out/highrise_house.blend")
    blend_path = os.path.abspath(argv[1]) if len(argv) > 1 else source_path
    bpy.ops.wm.open_mainfile(filepath=source_path)
    # Both podium and tower bases derive from the podium top.  Store that value
    # on the scene so future runs use the actual previous top rather than
    # applying the lift twice.
    former_podium_top_z = bpy.context.scene.get(
        "podium_top_z", house.PODIUM_PILOTIS_FLOORS * house.PODIUM_PILOTIS_H
        + house.PODIUM_OCCUPIED_FLOORS * house.H)
    delta = house.PODIUM_TOP_Z - former_podium_top_z
    raise_tower_meshes(delta)
    raise_structure_above_podium(former_podium_top_z, delta)
    remove_podium_meshes()

    mats = {
        "concrete": bpy.data.materials["Concrete"],
        "glass": bpy.data.materials["Glass"],
        "metal": bpy.data.materials["LouvreMetal"],
        "podium_diamond": bpy.data.materials["PodiumDiamondWhite"],
        "podium_ceiling_light_cool": bpy.data.materials["PodiumCeilingLight_Cool"],
        "podium_ceiling_light_warm": bpy.data.materials["PodiumCeilingLight_Warm"],
        "foliage": bpy.data.materials["Foliage"],
        "trunk": bpy.data.materials["Trunk"],
    }
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
    house.build_podium(mats, podium_specs)
    bpy.context.scene["podium_top_z"] = house.PODIUM_TOP_Z
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"rebuilt 6 m podium and raised towers by {delta:.1f} m -> {blend_path}")


if __name__ == "__main__":
    main()
