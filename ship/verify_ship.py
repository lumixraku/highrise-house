"""Verify the converted ship scene: geometry, waterline, materials, cameras."""

import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
BLEND = os.path.join(HERE, "out", "elegant_ship.blend")
OUT = os.path.dirname(BLEND)

bpy.ops.wm.open_mainfile(filepath=BLEND)

ok = True


def check(cond, msg):
    global ok
    print(("PASS " if cond else "FAIL ") + msg)
    ok = ok and bool(cond)


ship = bpy.data.collections.get("Ship")
check(ship is not None, "Ship collection exists")
meshes = [o for o in ship.objects if o.type == "MESH"]
check(len(meshes) >= 20, f"{len(meshes)} ship mesh objects")

mn = Vector((1e9, 1e9, 1e9))
mx = Vector((-1e9, -1e9, -1e9))
verts = 0
tris = 0
for ob in meshes:
    verts += len(ob.data.vertices)
    tris += sum(len(p.vertices) - 2 for p in ob.data.polygons)
    for c in ob.bound_box:
        w = ob.matrix_world @ Vector(c)
        mn = Vector((min(mn[i], w[i]) for i in range(3)))
        mx = Vector((max(mx[i], w[i]) for i in range(3)))
print(f"geometry: {verts} verts, {tris} tris")
print(f"bounds:   {tuple(round(v, 2) for v in mn)} .. {tuple(round(v, 2) for v in mx)}")

check(20 < tris < 200000, "triangle budget")
check(abs(mn.z) < 0.5, "hull sits on the waterline (z=0)")
check(300 < mx.x - mn.x < 380, "ship length ~345 m")
check(50 < mx.y - mn.y < 80, "beam ~64 m")
check(45 < mx.z - mn.z < 70, "height ~58 m")
check(abs((mn.x + mx.x) / 2) < 2.0 and abs((mn.y + mx.y) / 2) < 2.0,
      "ship centred on the origin")

mats = {m.name for m in bpy.data.materials if m.users}
for name in ("Hull_Purple", "Superstructure_White", "Window_Glass",
             "Deck_Wood", "Lifeboat_Orange", "Pool_Water"):
    check(name in mats, f"material {name}")

purple = bpy.data.materials.get("Hull_Purple")
if purple and purple.use_nodes:
    bsdf = purple.node_tree.nodes.get("Principled BSDF")
    col = bsdf.inputs["Base Color"].default_value
    # linear RGB of SKP sRGB (0.282, 0.239, 0.545) — blue channel dominates
    check(col[2] > col[0] and col[2] > col[1], "Hull_Purple is actually purple")
else:
    check(False, "Hull_Purple has a Principled shader")

for extra in ("Hull_Decks", "Bow_Front_Fill", "Bow_Front_Wall",
              "Deck_Fills", "Deck_Liners", "Deck_Fascia"):
    check(extra not in bpy.data.objects, f"no invented geometry {extra}")
for invented in ("Bow_Shell", "Stern_Shell", "Bow_Deck"):
    check(invented not in bpy.data.objects, f"hull not reshaped: no {invented}")
for needed in ("Interior_Decks", "Window_Frames"):
    ob = bpy.data.objects.get(needed)
    check(ob is not None and len(ob.data.polygons) > 100, f"{needed} present")
for name in ("Window_Glass", "Glass_Frosted", "Glass_Ribbed"):
    m = bpy.data.materials.get(name)
    b = m.node_tree.nodes["Principled BSDF"] if m else None
    check(b is not None and b.inputs["Roughness"].default_value == 0.0
          and b.inputs["Transmission Weight"].default_value == 1.0,
          f"{name} is clear glass")

for cam in ("CAM_Hero", "CAM_Side", "CAM_Aerial", "CAM_Bow", "CAM_Overview"):
    check(cam in bpy.data.objects, f"camera {cam}")
for image in ("hero.png", "side.png", "aerial.png", "bow.png"):
    p = os.path.join(OUT, image)
    check(os.path.exists(p) and os.path.getsize(p) > 10000, f"render {image}")

print("RESULT:", "OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
