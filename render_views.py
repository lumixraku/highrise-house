"""Render extra views of the built model.

    blender --background --factory-startup \
        --python render_views.py -- out/highrise_house.blend
"""

import math
import os
import sys

import bpy
from mathutils import Vector

# Footprint is derived from the window module in build_house.py; keep in sync.
W, D, TOP_Z = 76.0, 32.0, 160.0

VIEWS = [
    # name,          camera position,               look-at,             lens
    ("front",        (0.0, -440.0, 78.0),           (0.0, 0.0, 78.0),    42.0),
    ("base_pilotis", (92.0, -78.0, 8.0),            (0.0, 0.0, 18.0),    32.0),
    ("floor_detail", (D / 2 + 30.0, -42.0, 58.0),   (0.0, 0.0, 56.0),    70.0),
    ("corner",       (182.0, -228.0, 112.0),        (0.0, 0.0, 76.0),    38.0),
]


def aim(cam, eye, target):
    eye, target = Vector(eye), Vector(target)
    cam.location = eye
    cam.rotation_euler = (target - eye).normalized().to_track_quat("-Z", "Y").to_euler()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.open_mainfile(filepath=argv[0])

    scene = bpy.context.scene
    out_dir = os.path.dirname(os.path.abspath(argv[0]))
    cam = scene.camera

    # A 160 m tower does not fit a landscape frame; render these views portrait.
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1400

    for name, eye, target, lens in VIEWS:
        cam.data.lens = lens
        aim(cam, eye, target)
        scene.render.filepath = os.path.join(out_dir, f"view_{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"rendered {name}")


main()
