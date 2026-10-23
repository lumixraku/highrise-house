"""Measure the rendered glass, since 'is it frosted?' cannot be eyeballed here.

    blender --background --factory-startup --python measure_glass.py -- \
        out/highrise_house.blend

Renders a tight crop of the facade and reports, for glass pixels only:

  brightness / green bias  — is it a bright tinted pane or a dark smoked panel?
  local contrast (stdev)   — THE frosted test. A rough or partly-diffuse pane
                             averages its surroundings, so neighbouring pixels
                             converge and the stdev collapses. Clear glass keeps
                             sharp detail: sky reflection, mullion, room fixture,
                             all distinct, so the stdev stays high.

Glass pixels are found by ray-casting the camera through each pixel and keeping
only the hits on Windows_Glass. Whole-frame averages are useless here: spandrel
covers most of the facade and drowns the panes out.
"""

import statistics
import sys

import bpy
from mathutils import Vector


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.open_mainfile(filepath=argv[0])

    scene = bpy.context.scene
    # Close in on a few glazed floors so panes cover a useful share of the frame.
    cam = scene.camera
    cam.location = Vector((70.0, -95.0, 74.0))
    target = Vector((0.0, 0.0, 70.0))
    cam.rotation_euler = (target - cam.location).normalized() \
        .to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 135.0

    res = 320
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.cycles.samples = 256
    out = "/tmp/glass_probe.png"
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)

    img = bpy.data.images.load(out)
    px = list(img.pixels)
    w, h = img.size

    # Classify each pixel by what the camera ray hits.
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mw = cam.matrix_world
    frame = cam.data.view_frame(scene=scene)
    tr, br, bl, tl = [mw @ v for v in frame]
    origin = mw.translation

    glass, wall = [], []
    step = 2                     # every other pixel is plenty and 4x faster
    for y in range(0, h, step):
        fy = (y + 0.5) / h
        left = bl.lerp(tl, fy)
        right = br.lerp(tr, fy)
        for x in range(0, w, step):
            fx = (x + 0.5) / w
            point = left.lerp(right, fx)
            direction = (point - origin).normalized()
            hit, _, _, _, obj, _ = scene.ray_cast(depsgraph, origin, direction)
            if not hit or obj is None:
                continue
            i = (y * w + x) * 4
            rgb = (px[i], px[i + 1], px[i + 2])
            if obj.name == "Windows_Glass":
                glass.append(rgb)
            elif obj.name == "Facade_Spandrels":
                wall.append(rgb)

    def stats(label, samples):
        if not samples:
            print(f"{label}: no pixels found")
            return None
        n = len(samples)
        r = sum(s[0] for s in samples) / n
        g = sum(s[1] for s in samples) / n
        b = sum(s[2] for s in samples) / n
        lum = [0.2126 * s[0] + 0.7152 * s[1] + 0.0722 * s[2] for s in samples]
        sd = statistics.pstdev(lum)
        print(f"{label}: n={n}  R={r:.3f} G={g:.3f} B={b:.3f}  "
              f"mean_lum={sum(lum) / n:.3f}  stdev={sd:.3f}  "
              f"range={min(lum):.3f}..{max(lum):.3f}  "
              f"green_bias={g - (r + b) / 2:+.3f}")
        return {"lum": sum(lum) / n, "sd": sd, "green": g - (r + b) / 2,
                "min": min(lum), "max": max(lum)}

    print()
    gs = stats("glass", glass)
    ws = stats("wall ", wall)

    if gs and ws:
        print()
        # A frosted pane is a low-variance pane: it blurs whatever is behind and
        # around it, so neighbouring pixels converge. Clear glass holds sharp
        # sky/room-fixture/mullion detail and stays far more varied than matte wall.
        # Caveat: the wall is the DENOMINATOR, so this ratio also moves when the
        # walls themselves get more varied. Since the sky garden was added the
        # probe frame includes walls shadowed by the void, which took the wall's
        # own stdev from 0.020 to 0.064 and dropped this ratio from ~3.9x to ~1.3x
        # with the glass pixels completely unchanged. Read the glass stdev and
        # dynamic range as the primary frosted test; treat this ratio as
        # meaningful only against a comparable frame.
        print(f"glass/wall contrast ratio: {gs['sd'] / ws['sd']:.2f}x  "
              "(clear glass should be well above 1; see caveat in source)")
        print(f"glass dynamic range      : {gs['max'] - gs['min']:.3f}  "
              "(frosted glass compresses this)")
        print(f"glass brightness vs wall : {gs['lum'] / ws['lum']:.2f}x")

    bpy.data.images.remove(img)


main()
