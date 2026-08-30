"""Update only the star lights beneath the podium pilotis ceiling.

Run:
    blender --background --python update_podium_pilotis_lights.py -- out/highrise_house.blend
"""

import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_house as house


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    blend_path = os.path.abspath(argv[0] if argv else "out/highrise_house.blend")
    bpy.ops.wm.open_mainfile(filepath=blend_path)

    existing = bpy.data.objects.get("Podium_Pilotis_Ceiling_Lights")
    if existing:
        bpy.data.objects.remove(existing, do_unlink=True)

    slab = bpy.data.objects["Podium_Floor_Plates"]
    bounds = [slab.matrix_world @ vertex.co for vertex in slab.data.vertices]
    min_x, max_x = min(point.x for point in bounds), max(point.x for point in bounds)
    min_y, max_y = min(point.y for point in bounds), max(point.y for point in bounds)
    soffit_z = house.PODIUM_PILOTIS_CEILING_Z - house.SLAB_T
    radius = house.PODIUM_CEILING_LIGHT_RADIUS
    pitch = house.PODIUM_CEILING_LIGHT_PITCH
    clearance = house.PODIUM_CEILING_LIGHT_EDGE_CLEARANCE
    depsgraph = bpy.context.evaluated_depsgraph_get()

    def under_soffit(x, y):
        hit, location, _, _, obj, _ = bpy.context.scene.ray_cast(
            depsgraph, (x, y, soffit_z - 0.50), (0.0, 0.0, 1.0), distance=1.0)
        return (hit and obj.name == slab.name and abs(location.z - soffit_z) < 0.02)

    cool, warm = [], []
    row = 0
    y = min_y + pitch / 2.0
    while y < max_y:
        x = min_x + pitch / 2.0 + (row % 2) * pitch / 2.0
        column = 0
        while x < max_x:
            # Test the centre and its four surrounding points to keep every
            # globe clear of the curved slab edge, matching upper podium lamps.
            if all(under_soffit(x + dx, y + dy)
                   for dx, dy in ((0.0, 0.0), (clearance, 0.0),
                                  (-clearance, 0.0), (0.0, clearance),
                                  (0.0, -clearance))):
                centre = (x, y, soffit_z - radius + 0.01)
                (warm if (row * 7 + column + house.PODIUM_PILOTIS_FLOORS) % 6 == 0
                 else cool).append(centre)
            x += pitch
            column += 1
        y += pitch
        row += 1

    lights = (
        house.spheres_mesh("Podium_PilotisLightCool", cool, radius,
                           bpy.data.materials["PodiumCeilingLight_Cool"]),
        house.spheres_mesh("Podium_PilotisLightWarm", warm, radius,
                           bpy.data.materials["PodiumCeilingLight_Warm"]),
    )
    house.join(lights, "Podium_Pilotis_Ceiling_Lights")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"updated {len(cool) + len(warm)} pilotis ceiling lights -> {blend_path}")


if __name__ == "__main__":
    main()
