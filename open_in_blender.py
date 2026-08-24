"""Open the model in the Blender GUI with materials already visible.

    blender out/highrise_house.blend --python open_in_blender.py

Or use the wrapper:  ./view.sh

Why this exists: Blender opens every 3D viewport in SOLID shading, which ignores
materials and draws everything flat grey — so the file looks uniformly grey-white
however good the materials are. Setting the mode from a --background run does not
help, because viewport state is only written back when a real UI exists. This
script runs inside the GUI session, after the window is up, and switches the
viewport to rendered shading.
"""

import bpy

# Open directly in Material Preview (the third viewport sphere): its EEVEE view
# is fast, keeps the non-ray-traced glass reflection, and shows the room lights.
SHADING = "MATERIAL"


def apply(mode=SHADING):
    touched = 0
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type != "VIEW_3D":
                    continue
                space.shading.type = mode
                # Use the scene's sky and sun, not the viewport's studio defaults.
                space.shading.use_scene_world_render = True
                space.shading.use_scene_lights_render = True
                # Frame the whole building.
                space.clip_end = 4000.0
                touched += 1
    print(f"[open_in_blender] set {touched} viewport(s) to {mode}")
    return touched


def frame_all():
    """Zoom to the building so it is not off-screen on open."""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != "VIEW_3D":
                continue
            with bpy.context.temp_override(window=window, area=area):
                try:
                    bpy.ops.view3d.view_all(center=False)
                except RuntimeError:
                    pass
            break


if apply():
    frame_all()
else:
    # No UI yet (e.g. run with --background): retry once the window exists.
    def _later():
        if apply():
            frame_all()
            return None
        return 0.2
    bpy.app.timers.register(_later, first_interval=0.3)
