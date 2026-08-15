"""Render extra views of the built model.

    blender --background --factory-startup \
        --python render_views.py -- out/highrise_house.blend
"""

import math
import os
import sys

import bpy
from mathutils import Vector

VIEWS = [
    # name,          camera position,             look-at,            lens
    ("front",        (0.0, -96.0, 30.0),          (0.0, 0.0, 30.0),   48.0),
    ("base_pilotis", (34.0, -30.0, 6.0),          (0.0, 0.0, 11.0),   34.0),
    ("floor_detail", (26.0, -16.0, 30.0),         (0.0, 0.0, 29.0),   80.0),
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

    for name, eye, target, lens in VIEWS:
        cam.data.lens = lens
        aim(cam, eye, target)
        scene.render.filepath = os.path.join(out_dir, f"view_{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"rendered {name}")


main()
