"""Build a Blender scene of the largest of the three ships in
``longtest 25.skp``: the 345 x 64 x 58 m purple-hulled liner.

The previous conversion invented extra geometry (V-stem, full-beam
bulkhead, convex-hull deck fills, promenade liners) and recolored the
slate-blue hull as navy.  This rebuild is a faithful import:

* keep the SketchUp mesh and material colours, hull shape untouched
  (no lofted bow/stern skins);
* drop zero-area triangles;
* push coplanar material layers a few centimetres apart so they stop
  z-fighting;
* add a solid deck slab on every storey inside the SKP walls, and
  clear reflective glass divided by frames;
* centre the waterline at the origin.

Run:
    blender --background --factory-startup --python-exit-code 1 \\
        --python build_ship.py
    blender ... --python build_ship.py -- --no-render
"""

from __future__ import annotations

import json
import math
import os
import random
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shared"))
from materials import (CEILING_LIGHT_DAYLIGHT, CEILING_LIGHT_WARM,  # noqa: E402
                       make_ceiling_light, make_glass)

DATA = os.path.join(HERE, "ship_data")
OUT = os.path.join(HERE, "out")

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
RENDER = "--no-render" not in ARGS

# sRGB SketchUp factors from the SKP (mat 26 = slate-blue / "purple" hull).
# last field is an optional SKP texture; we skip it at ship scale.
MATS = {
    0:  ("Hull_White",           (1.000, 1.000, 1.000), 0.34, 0.00, 1.00, None),
    1:  ("Hull_Shadow",          (0.416, 0.416, 0.416), 0.42, 0.10, 1.00, None),
    2:  ("Trim_DarkBrown",       (0.200, 0.141, 0.102), 0.55, 0.00, 1.00, None),
    3:  ("Pale_Blue",            (0.941, 0.973, 1.000), 0.35, 0.00, 1.00, None),
    4:  ("Light_Grey",           (0.749, 0.749, 0.749), 0.40, 0.10, 1.00, None),
    5:  ("Hull_Charcoal",        (0.318, 0.318, 0.318), 0.28, 0.10, 1.00, None),
    6:  ("Superstructure_White", (1.000, 1.000, 1.000), 0.32, 0.00, 1.00, None),
    7:  ("Trim_Green",           (0.561, 0.737, 0.561), 0.45, 0.00, 1.00, None),
    8:  ("Glass_Canopy",         (0.243, 0.357, 0.020), 0.06, 0.05, 0.18, None),
    9:  ("Glass_Canopy_Back",    (0.243, 0.357, 0.020), 0.06, 0.05, 0.18, None),
    10: ("Off_White",            (0.961, 0.961, 0.961), 0.38, 0.00, 1.00, None),
    11: ("Window_Glass",         (0.835, 0.878, 0.878), 0.08, 0.05, 0.55, "tex_0.jpg"),
    12: ("Panel_Grey",           (0.600, 0.600, 0.600), 0.45, 0.10, 1.00, "tex_1.jpg"),
    13: ("Deck_Wood",            (0.800, 0.690, 0.498), 0.52, 0.00, 1.00, "tex_2.jpg"),
    14: ("Wood_Siding_Back",     (0.800, 0.690, 0.498), 0.52, 0.00, 1.00, "tex_2.jpg"),
    15: ("Beadboard",            (0.855, 0.561, 0.353), 0.50, 0.00, 1.00, "tex_3.jpg"),
    16: ("Glass_Frosted",        (0.722, 0.722, 0.722), 0.22, 0.00, 0.80, "tex_4.jpg"),
    17: ("Glass_Ribbed",         (0.553, 0.620, 0.569), 0.16, 0.10, 0.75, "tex_5.jpg"),
    18: ("Glass_Ribbed_Back",    (0.553, 0.620, 0.569), 0.16, 0.10, 0.75, "tex_5.jpg"),
    19: ("Cladding_White",       (0.812, 0.812, 0.812), 0.42, 0.00, 1.00, "tex_6.jpg"),
    20: ("Cladding_White_Back",  (0.812, 0.812, 0.812), 0.42, 0.00, 1.00, "tex_6.jpg"),
    21: ("Deck_Beige",           (0.961, 0.961, 0.863), 0.45, 0.00, 1.00, None),
    22: ("Siding_Wood",          (0.749, 0.518, 0.392), 0.52, 0.00, 1.00, "tex_7.jpg"),
    23: ("Deck_Tan",             (0.635, 0.494, 0.373), 0.55, 0.00, 1.00, "tex_8.jpg"),
    24: ("Accent_LightBlue",     (0.635, 0.733, 0.812), 0.36, 0.00, 1.00, None),
    25: ("Pool_Water",           (0.498, 1.000, 0.831), 0.04, 0.00, 1.00, None),
    26: ("Hull_Purple",          (0.282, 0.239, 0.545), 0.28, 0.05, 1.00, None),
    27: ("Glass_Block",          (0.486, 0.486, 0.475), 0.12, 0.15, 0.80, "tex_9.jpg"),
    28: ("White_Soft",           (0.886, 0.886, 0.886), 0.38, 0.00, 1.00, None),
    29: ("Glass_Block_Back",     (0.486, 0.486, 0.475), 0.12, 0.15, 0.80, "tex_9.jpg"),
    30: ("Siding_Wood_Back",     (0.749, 0.518, 0.392), 0.52, 0.00, 1.00, "tex_7.jpg"),
    31: ("Aquamarine_Back",      (0.498, 1.000, 0.831), 0.15, 0.00, 1.00, None),
    32: ("Accent_LightBlue_2",   (0.635, 0.733, 0.812), 0.36, 0.00, 1.00, None),
    33: ("Detail_Dark_Back",     (0.318, 0.318, 0.318), 0.50, 0.30, 1.00, None),
    34: ("Glass_Resin",          (0.722, 0.722, 0.722), 0.20, 0.00, 0.80, "tex_4.jpg"),
    35: ("Lawn_Green",           (0.416, 0.616, 0.216), 0.70, 0.00, 1.00, "tex_10.jpg"),
    36: ("Detail_Charcoal",      (0.216, 0.216, 0.216), 0.45, 0.20, 1.00, None),
    37: ("Lifeboat_Orange",      (1.000, 0.247, 0.000), 0.38, 0.00, 1.00, None),
    38: ("Deck_Beige_Back",      (0.961, 0.961, 0.863), 0.45, 0.00, 1.00, None),
    39: ("Accent_Red",           (1.000, 0.255, 0.275), 0.38, 0.00, 1.00, None),
}

# World-space mid-point of the SKP purple ship (before centering).
SHIP_CENTER = ((-53.16 + 291.84) / 2, (-252.09 + -188.09) / 2)
SHIP_WATERLINE = 0.0

# Storey levels (m above waterline) that get a full deck slab: the hull
# decks behind the portholes and every superstructure storey, read from the
# SKP glazing/cladding bands (18-22.5-27, then 3 m to 39, roof 39.5, top 44).
DECK_LEVELS = (6.0, 9.0, 12.0, 15.0, 18.0, 22.5, 27.0, 30.0, 33.0, 36.0,
               39.5, 44.0)
DECK_CELL = 0.2          # raster resolution of the deck outline
DECK_T = 0.30            # slab thickness
DECK_DROP = 0.04         # slab top below the storey level (under SKP decks)
DECK_SPECKLE = 6         # cells: opening radius against stray slab bits
DECK_GAP = 8             # cells: closes wall gaps up to ~3 m (balcony doors)

# Curtain-wall frames on every glazed face.
GLASS_TINT = (0.93, 0.97, 1.00)
FRAME_SPACING = 1.5      # mullion module along the pane
FRAME_EDGE = (0.12, 0.14)   # boundary frame width, depth
FRAME_MULLION = (0.08, 0.10)  # thinner depth than edges: no coplanar joints
FRAME_END_GAP = 0.015    # bar ends pulled in off the surfaces panes meet
FRAMED_GLASS = ("Window_Glass", "Glass_Frosted", "Glass_Ribbed",
                "Glass_Ribbed_Back")
# SKP paints the whole porthole storey as Window_Glass / Frosted / Ribbed.
# Only the ~1.8 m circular ports are glass; the rest of that storey is hull.
PORTHOLE_Z0, PORTHOLE_Z1 = 17.5, 22.5
PORTHOLE_DISK_AREA = 0.35   # one 22-gon port fan triangle is ~0.2 m2
HULL_FROM_GLASS = 6         # Superstructure_White
GLASS_MATS = (8, 9, 11, 16, 17, 18, 27, 29, 34)


def srgb_to_linear(c: float) -> float:
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def is_glass(name: str) -> bool:
    return name.startswith("Glass") or name == "Window_Glass"


def make_material(idx: int) -> bpy.types.Material:
    name, color, rough, metal, alpha, _tex = MATS[idx]
    if is_glass(name):
        # clear, reflective float glass shared with the other buildings
        return make_glass(name=name, engine="BLENDER_EEVEE", tint=GLASS_TINT)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    lin = tuple(srgb_to_linear(c) for c in color)
    bsdf.inputs["Base Color"].default_value = (*lin, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Alpha"].default_value = alpha
    bsdf.inputs["IOR"].default_value = 1.45
    if name == "Hull_Purple":
        bsdf.inputs["Specular IOR Level"].default_value = 0.55
        bsdf.inputs["Coat Weight"].default_value = 0.25
        bsdf.inputs["Coat Roughness"].default_value = 0.12
    return mat


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.images,
                  bpy.data.cameras, bpy.data.lights):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def _load_ship_triangles():
    data = np.load(os.path.join(DATA, "ship_mesh.npz"))
    meta = json.load(open(os.path.join(DATA, "parts.json")))
    tris, uvs, mats = [], [], []
    for i, part in enumerate(meta["parts"]):
        pos = data[f"p{i}_pos"]
        idx = data[f"p{i}_idx"].ravel().reshape(-1, 3)
        uv = data[f"p{i}_uv"]
        tris.append(pos[idx])
        uvs.append(uv[idx])
        mats.append(np.full(len(idx), part["mat"], dtype=np.int32))
    return np.concatenate(tris), np.concatenate(uvs), np.concatenate(mats)


# Midship curved glass bay, two storeys (z 17.95-22.45-26.95): the SKP has
# it on the -y side only; mirror its glass walls and roof to +y (that side
# already has the 22.45 m deck in between).
ARC_BAY_X = (-17.6, 38.6)
ARC_BAY_Z = (17.8, 27.3)
ARC_BAY_Y = (21.9, 27.3)
ARC_BAY_MATS = (11, 18)   # Window_Glass wall, Glass_Ribbed_Back roof


# Balcony cabins (storeys 26.95-38.95 m): the SKP back wall of every
# balcony is one opaque sheet at |y|=20 (18.7 on the lowest +y storey).
# It is replaced by a sliding glass door per balcony bay, a wall surface
# round it, partitions between the cabins and one ceiling light per cabin.
CABIN_WALL_Y = (20.0, 18.7)
CABIN_Z = (26.9, 39.0)
CABIN_STOREY_H = 3.0
CABIN_Y = 19.98          # new wall plane, just inside the divider ends
CABIN_DEPTH = 7.0        # partition length into the ship
DOOR_JAMB = 0.25
DOOR_SILL = 0.04
DOOR_PANE_Y = (0.05, 0.11)   # the two sliding leaves, set back from the wall
DOOR_BAR = 0.06

# Interior lights after the Harukas strips: rows of long thin fixtures under
# every storey ceiling, plus one panel per cabin; seeded on/off/colour mix.
LIGHT_ROW_PITCH = 3.0
LIGHT_STRIP_W, LIGHT_STRIP_H = 0.30, 0.10
LIGHT_EDGE_CLEAR = 0.6
LIGHT_MIN_LEN = 1.5
LIGHT_MAX_LEN = 12.0
LIGHT_HANG = 2.55        # strip top above the floor on 3 m storeys
LIGHT_SEED = 20261023
LIGHT_ON_RATIO = 0.75
CABIN_LIGHT = (1.2, 0.6, 0.05)   # x, y, z size
CABIN_LIGHT_IN = 2.5             # centre distance inside the wall
LIGHT_CEIL_MAX = 1.2   # a fixture needs a ceiling this close above it
LIGHT_RAYS = 8         # horizontal rays that must all hit the ship
# Top-deck glass houses (z 44 deck, ceilings 46-48 m): the deck mask has no
# room there, so their strip rows follow the ceiling found by ray casts.
TOP_DECK_Z = 43.98
TOP_ROWS_Y = 7.5          # rows at |y| <= this, LIGHT_ROW_PITCH apart
TOP_CEIL_MAX = 5.0        # ceiling search height above the deck
TOP_SAMPLE = 0.5          # x step of the ceiling scan
# A few real light sources so the whole ship glows from inside.  They cast
# no shadows (light goes straight through decks and walls) and the floors
# are light-linked out, so slabs neither block nor receive this light.
INTERIOR_LIGHTS = tuple((x, 0.0, z) for z in (14.0, 34.0)
                        for x in (-100.0, -35.0, 35.0, 100.0))
INTERIOR_LIGHT_POWER = 150000.0  # W per light
INTERIOR_LIGHT_RADIUS = 6.0
INTERIOR_LIGHT_COLOR = (1.0, 0.86, 0.68)
INTERIOR_LIGHT_CUTOFF = 120.0
INTERIOR_LIGHT_SKIP = ("Interior_Decks", "Deck_", "Pool_Water")


def _open_cabin_fronts(T, UV, M):
    """Drop the opaque balcony back walls; return the cabin bays."""
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n /= np.linalg.norm(n, axis=1)[:, None] + 1e-12
    ay = np.abs(T[:, :, 1])
    zmin, zmax = T[:, :, 2].min(1), T[:, :, 2].max(1)
    on = np.zeros(len(T), bool)
    for wy in CABIN_WALL_Y:
        # _fix_coplanar pushes stacked layers a few cm apart
        on |= np.abs(ay - wy).max(1) < 0.1
    sel = (on & (np.abs(n[:, 1]) > 0.99) & np.isin(M, (0, 19))
           & (zmin > CABIN_Z[0]) & (zmax < CABIN_Z[1]))
    runs = {}
    for t in T[sel]:
        key = (int(np.sign(t[0, 1])), round(float(t[:, 2].min()), 2))
        runs.setdefault(key, []).append((t[:, 0].min(), t[:, 0].max()))
    divider = ((np.abs(n[:, 0]) > 0.99) & (ay.min(1) > 19.9)
               & (ay.max(1) < 22.1))
    cabins = []
    for (s, z0), iv in sorted(runs.items()):
        merged = []
        for a, b in sorted(iv):
            if merged and a <= merged[-1][1] + 0.05:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        d = (divider & (np.sign(T[:, 0, 1]) == s) & (zmin > z0 - 0.05)
             & (zmax < z0 + CABIN_STOREY_H + 0.05))
        xs = np.sort(T[d, :, 0].mean(1))
        centres, group = [], []
        for x in xs:
            if group and x - group[-1] > 0.5:
                centres.append((group[0] + group[-1]) / 2)
                group = []
            group.append(x)
        if group:
            centres.append((group[0] + group[-1]) / 2)
        for xa, xb in merged:
            cut = [xa] + [c for c in centres if xa + 0.5 < c < xb - 0.5] + [xb]
            for b0, b1 in zip(cut, cut[1:]):
                cabins.append((s, z0, b0, b1, b0 != xa, b1 != xb))
    print(f"[ship] cabin fronts: {int(sel.sum())} wall tris removed, "
          f"{len(cabins)} balcony bays")
    return T[~sel], UV[~sel], M[~sel], cabins


def _box(verts, faces, x0, x1, y0, y1, z0, z1):
    b = len(verts)
    verts += [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
              (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces += [(b, b + 3, b + 2, b + 1), (b + 4, b + 5, b + 6, b + 7),
              (b, b + 1, b + 5, b + 4), (b + 1, b + 2, b + 6, b + 5),
              (b + 2, b + 3, b + 7, b + 6), (b + 3, b, b + 4, b + 7)]


def _quad(verts, faces, x0, x1, y, z0, z1, s):
    """Flat x-z quad at ``y`` facing ``s`` * y."""
    b = len(verts)
    verts += [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
    faces.append((b, b + 1, b + 2, b + 3) if s < 0 else (b + 3, b + 2, b + 1, b))


def _panel(verts, faces, x0, x1, y0, y1, z):
    """Downward-facing light panel (only its underside is ever seen)."""
    b = len(verts)
    verts += [(x0, y0, z), (x0, y1, z), (x1, y1, z), (x1, y0, z)]
    faces.append((b, b + 1, b + 2, b + 3))


def _add_cabin_fronts(coll, root, cabins):
    """Wall with a two-leaf sliding glass door per balcony bay, plus the
    partitions between cabins."""
    wv, wf, gv, gf, fv, ff, pv, pf = [], [], [], [], [], [], [], []
    for s, z0, b0, b1, wall0, wall1 in cabins:
        y = s * CABIN_Y
        # doors run the full storey height: floor to ceiling, no header
        z1 = z0 + CABIN_STOREY_H
        zd = z1 - 0.01
        d0, d1 = b0 + DOOR_JAMB, b1 - DOOR_JAMB
        # wall surface round the door: the two jambs
        b = len(wv)
        for x, z in ((b0, z0), (d0, z0), (d1, z0), (b1, z0),
                     (b0, z1), (d0, z1), (d1, z1), (b1, z1)):
            wv.append((x, y, z))
        quads = ((0, 1, 5, 4), (2, 3, 7, 6))
        wf += [tuple(b + i for i in (q if s < 0 else q[::-1])) for q in quads]
        # two sliding leaves overlapping 10 cm at the meeting stile
        mid = (d0 + d1) / 2
        for (xa, xb), off in zip(((d0, mid + 0.05), (mid - 0.05, d1)),
                                 DOOR_PANE_Y):
            yp = s * (CABIN_Y - off)
            za = z0 + DOOR_SILL
            b = len(gv)
            gv += [(xa, yp, za), (xb, yp, za), (xb, yp, zd), (xa, yp, zd)]
            gf.append((b, b + 1, b + 2, b + 3) if s < 0 else (b + 3, b + 2, b + 1, b))
            # leaf frame: flat strips 1 cm proud of the pane (tri budget);
            # stiles over the full height, rails between them
            yf = yp + s * 0.01
            for ra, rb, rz0, rz1 in ((xa, xa + DOOR_BAR, za, zd),
                                     (xb - DOOR_BAR, xb, za, zd),
                                     (xa + DOOR_BAR, xb - DOOR_BAR, za, za + DOOR_BAR),
                                     (xa + DOOR_BAR, xb - DOOR_BAR, zd - DOOR_BAR, zd)):
                _quad(fv, ff, ra, rb, yf, rz0, rz1, s)
        # partition on each divider line
        if wall0:
            ya, yb = sorted((s * (CABIN_Y - 0.01), s * (CABIN_Y - CABIN_DEPTH)))
            _box(pv, pf, b0 - 0.05, b0 + 0.05, ya, yb, z0 + 0.02, z1 - 0.02)
    glass = bpy.data.materials["Window_Glass"]
    frame = bpy.data.materials.new("Cabin_Door_Frame")
    frame.use_nodes = True
    frame.use_backface_culling = False
    fb = frame.node_tree.nodes["Principled BSDF"]
    fb.inputs["Base Color"].default_value = (0.80, 0.81, 0.82, 1.0)
    fb.inputs["Metallic"].default_value = 0.6
    fb.inputs["Roughness"].default_value = 0.3
    part = bpy.data.materials.new("Cabin_Partition")
    part.use_nodes = True
    part.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (
        0.78, 0.74, 0.66, 1.0)
    for name, v, f, mat in (("Cabin_Walls", wv, wf, bpy.data.materials["Cladding_White"]),
                            ("Cabin_Door_Glass", gv, gf, glass),
                            ("Cabin_Door_Frames", fv, ff, frame),
                            ("Cabin_Partitions", pv, pf, part)):
        ob = _add_object(coll, root, name, v, f, mat)
        for p in ob.data.polygons:
            p.use_smooth = False
    print(f"[ship] cabins: {len(cabins)} sliding doors, "
          f"{len(pf) // 6} partitions")


def _light_state(rng):
    if rng.random() >= LIGHT_ON_RATIO:
        return "off"
    return "warm" if rng.random() < 0.5 else "daylight"


# Hull cabins (storeys 5.95-17.95 m): SKP paints the hull windows as glass
# decals outside a solid plate at |y|=22; behind it the SKP has a 2 m deep
# room strip (inner wall at |y|=20, partitions every 3 m).  Cut the plate
# open behind every window (the SKP outline of each storey's plating is
# kept) and give every window's room a ceiling light plus a soft glow on
# its back wall, so a lit room reads from outside.
HULL_CABIN_Z = (5.9, 18.0)
HULL_STOREYS = (5.95, 8.95, 11.95, 14.95)
HULL_WALL_Y = (22.0, 20.0)
HULL_WINDOW_MATS = (8, 9)        # Glass_Canopy (2 x 1.28), _Back (1.2 sq)
HULL_HOLE_INSET = {8: 0.05, 9: 0.10}   # hole stays behind the glass
HULL_LIGHT_IN = 1.0              # light centre inside the hull plate
HULL_GLOW_Y = HULL_WALL_Y[1] + 0.03   # glow sheet just off the inner wall
HULL_GLOW_STRENGTH = 3.0


def _convex_hull(pts):
    pts = sorted(set(pts))
    def half(seq):
        h = []
        for q in seq:
            while len(h) >= 2 and ((h[-1][0] - h[-2][0]) * (q[1] - h[-2][1])
                                   - (h[-1][1] - h[-2][1]) * (q[0] - h[-2][0])) <= 1e-9:
                h.pop()
            h.append(q)
        return h
    lo, hi = half(pts), half(pts[::-1])
    return lo[:-1] + hi[:-1]


def _poly_area(P):
    return abs(sum(P[i][0] * P[i - 1][1] - P[i - 1][0] * P[i][1]
                   for i in range(len(P)))) / 2


def _clip(P, axis, v, keep_below):
    """Clip convex polygon P (x, z) to axis <= v (or >= v)."""
    out = []
    for i in range(len(P)):
        a, b = P[i - 1], P[i]
        ia = (a[axis] <= v) if keep_below else (a[axis] >= v)
        ib = (b[axis] <= v) if keep_below else (b[axis] >= v)
        if ia != ib:
            t = (v - a[axis]) / (b[axis] - a[axis])
            out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        if ib:
            out.append(b)
    return out


def _open_hull_windows(T, UV, M):
    """Remove the hull plate and inner wall of the window storeys; return
    the plate outlines and the window holes."""
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    a = np.linalg.norm(n, axis=1) / 2
    n /= 2 * a[:, None] + 1e-12
    ay = np.abs(T[:, :, 1])
    side = np.sign(T[:, :, 1].mean(1))
    flat = (np.abs(n[:, 1]) > 0.99) & (np.ptp(ay, 1) < 0.01)
    band = (T[:, :, 2].min(1) > HULL_CABIN_Z[0]) & (T[:, :, 2].max(1) < HULL_CABIN_Z[1])
    plate = flat & band & (np.abs(ay[:, 0] - HULL_WALL_Y[0]) < 0.1) & np.isin(M, (0, 26))
    plates = {}
    for s in (-1, 1):
        for z0 in HULL_STOREYS:
            k = (plate & (M == 26) & (side == s) & (T[:, :, 2].min(1) > z0 - 0.05)
                 & (T[:, :, 2].max(1) < z0 + 3.05))
            pts = [(round(float(x), 3), round(float(z), 3))
                   for x, z in T[k][:, :, [0, 2]].reshape(-1, 2)]
            P = _convex_hull(pts)
            print(f"[ship] hull plate s={s:+d} z={z0}: outline {_poly_area(P):.1f} m2,"
                  f" SKP {a[k].sum():.1f} m2")
            plates[(s, z0)] = (P, float(ay[k].mean()))
    # windows: connected glass pieces outside the plate
    g = (np.isin(M, HULL_WINDOW_MATS) & (ay.min(1) > 21.9) & band)
    G, gm = T[g], M[g]
    key = np.round(G.reshape(-1, 3), 3)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.reshape(-1, 3)
    par = list(range(inv.max() + 1))
    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for t in inv:
        r = find(t[0])
        for v in t[1:]:
            par[find(v)] = r
    roots = np.array([find(t[0]) for t in inv])
    windows = {}
    for r in np.unique(roots):
        k = roots == r
        P = G[k].reshape(-1, 3)
        s = int(np.sign(P[0, 1]))
        z0 = min(HULL_STOREYS, key=lambda z: abs(z + 1.5 - P[:, 2].mean()))
        e = HULL_HOLE_INSET[int(gm[k][0])]
        windows.setdefault((s, z0), []).append(
            (P[:, 0].min() + e, P[:, 0].max() - e, P[:, 2].min() + e, P[:, 2].max() - e))
    for key in windows:
        windows[key].sort()
    drop = plate
    print(f"[ship] hull windows: {sum(len(w) for w in windows.values())} opened, "
          f"{int(drop.sum())} plate tris replaced")
    return T[~drop], UV[~drop], M[~drop], plates, windows


GLASS_BACKING_GAP = 0.4   # opaque sheet this close behind/in front of glass


def _drop_glass_backing(T, UV, M):
    """Remove opaque SKP sheets fully covered by a parallel glass pane
    within GLASS_BACKING_GAP: they make the glazing read as solid."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    a = np.linalg.norm(n, axis=1) / 2
    n /= 2 * a[:, None] + 1e-12
    glass = np.array([is_glass(MATS[m][0]) if m in MATS else False for m in M])
    gk = glass & (np.abs(n[:, 1]) > 0.9) & (a > 0.01)
    G = T[gk].reshape(-1, 3)
    bvh = BVHTree.FromPolygons([Vector(v) for v in G],
                               [(i, i + 1, i + 2) for i in range(0, len(G), 3)])
    cand = np.where(~glass & (np.abs(n[:, 1]) > 0.99) & (a > 0.05))[0]
    dirs = (Vector((0, 1, 0)), Vector((0, -1, 0)))
    drop = np.zeros(len(T), bool)
    for i in cand:
        t = T[i]
        c = t.mean(0)
        pts = [c] + [0.8 * t[j] + 0.1 * t[(j + 1) % 3] + 0.1 * t[(j + 2) % 3]
                     for j in range(3)]
        if all(any(bvh.ray_cast(Vector(q), d, GLASS_BACKING_GAP)[0] is not None
                   for d in dirs) for q in pts):
            drop[i] = True
    print(f"[ship] glass backing: {int(drop.sum())} opaque tris behind glass removed, "
          f"{a[drop].sum():.0f} m2")
    return T[~drop], UV[~drop], M[~drop]


def _add_hull_cabins(coll, root, plates, windows):
    """Hull plate with a hole per window; returns one cabin per window as
    (side, z0, x0, x1) for the lights.  The SKP already has a partition
    wall between every pair of windows."""
    layers = {"Hull_Purple": ([], [], 0.0, 1), "Hull_White": ([], [], -0.05, -1)}
    rooms = []
    for (s, z0), (P, wy) in plates.items():
        holes = windows.get((s, z0), [])
        pieces = []
        if holes:
            hz0 = min(h[2] for h in holes)
            hz1 = max(h[3] for h in holes)
            pieces.append(_clip(P, 1, hz0, True))
            pieces.append(_clip(P, 1, hz1, False))
            mid = _clip(_clip(P, 1, hz0, False), 1, hz1, True)
            edges = [-1e9] + [v for h in holes for v in (h[0], h[1])] + [1e9]
            for xa, xb in zip(edges[0::2], edges[1::2]):
                pieces.append(_clip(_clip(mid, 0, xa, False), 0, xb, True))
            # rows of differing window heights: fill above/below each hole
            for h in holes:
                for za, zb in ((hz0, h[2]), (h[3], hz1)):
                    if zb - za > 1e-3:
                        pieces.append([(h[0], za), (h[1], za), (h[1], zb), (h[0], zb)])
        else:
            pieces.append(P)
        for name, (v, f, dy, out) in layers.items():
            y = s * (wy + dy)
            for Q in pieces:
                if len(Q) < 3 or _poly_area(Q) < 1e-4:
                    continue
                if _poly_area(Q) and sum(Q[i][0] * Q[i - 1][1] - Q[i - 1][0] * Q[i][1]
                                         for i in range(len(Q))) < 0:
                    Q = Q[::-1]          # CCW in (x, z): normal -y
                b = len(v)
                v += [(x, y, z) for x, z in Q]
                idx = list(range(b, b + len(Q)))
                f.append(tuple(idx if s * out < 0 else idx[::-1]))
        # cabins: one per window, partitions halfway between windows
        cx = [(h[0] + h[1]) / 2 for h in holes]
        for i, x in enumerate(cx):
            lo = (x + cx[i - 1]) / 2 if i and x - cx[i - 1] < 3.5 else x - 1.5
            hi = (x + cx[i + 1]) / 2 if i + 1 < len(cx) and cx[i + 1] - x < 3.5 else x + 1.5
            rooms.append((s, z0, lo, hi))
    for name, (v, f, _, _) in layers.items():
        ob = _add_object(coll, root, f"Hull_Cabin_Plate_{name.split('_')[1]}", v, f,
                         bpy.data.materials[name])
        for p in ob.data.polygons:
            p.use_smooth = False
    print(f"[ship] hull cabins: {len(rooms)} rooms lit")
    return rooms


def _ship_bvh(coll):
    T, _ = _world_triangles(coll)
    co = T.reshape(-1, 3)
    return BVHTree.FromPolygons([tuple(v) for v in co],
                                [(i, i + 1, i + 2) for i in range(0, len(co), 3)])


def _indoors(bvh, p):
    """True if ``p`` has a ceiling right above it and is closed in by
    ship geometry (walls or glass) in every horizontal direction."""
    p = Vector(p)
    hit = bvh.ray_cast(p, Vector((0, 0, 1)), LIGHT_CEIL_MAX)
    if hit[0] is None:
        return False
    for k in range(LIGHT_RAYS):
        a = 2 * math.pi * k / LIGHT_RAYS
        if bvh.ray_cast(p, Vector((math.cos(a), math.sin(a), 0)))[0] is None:
            return False
    return True


def _add_lights(coll, root, rooms, cabins, hull_rooms):
    """Strip-light rows over every storey's floor plate and one panel per
    cabin, merged per state (daylight / warm / off).  The deck mask also
    covers open decks and overhangs, so every fixture is ray-tested and
    kept only if it is inside the ship."""
    rng = random.Random(LIGHT_SEED)
    bvh = _ship_bvh(coll)
    dropped = 0
    buf = {k: ([], []) for k in ("daylight", "warm", "off")}
    count = {k: 0 for k in buf}
    x0, y0 = -176.0, -36.0
    cabin_runs = {}
    for s, z0, b0, b1, *_ in cabins:
        level = round(z0 + 0.05, 1)
        cabin_runs.setdefault((level, s), []).append((b0, b1))
    for li, level in enumerate(DECK_LEVELS[:-1]):
        room = rooms.get(level)
        if room is None:
            continue
        nxt = DECK_LEVELS[li + 1]
        top = (level + LIGHT_HANG if nxt - level < 4.0
               else nxt - DECK_T - 0.15)
        z = top - LIGHT_STRIP_H / 2
        for y in np.arange(-31.5, 31.6, LIGHT_ROW_PITCH):
            j = int((y - y0) / DECK_CELL)
            row = room[j]
            d = np.diff(np.concatenate([[0], row.astype(np.int8), [0]]))
            spans = [(x0 + a * DECK_CELL + LIGHT_EDGE_CLEAR,
                      x0 + b * DECK_CELL - LIGHT_EDGE_CLEAR)
                     for a, b in zip(np.where(d == 1)[0], np.where(d == -1)[0])]
            # cabins get their own panels; keep the rows out of them
            if abs(y) > CABIN_Y - CABIN_DEPTH - LIGHT_EDGE_CLEAR:
                for b0, b1 in cabin_runs.get((level, int(np.sign(y))), []):
                    cut = []
                    for a, b in spans:
                        if b1 <= a or b0 >= b:
                            cut.append((a, b))
                            continue
                        if b0 > a:
                            cut.append((a, b0 - LIGHT_EDGE_CLEAR))
                        if b1 < b:
                            cut.append((b1 + LIGHT_EDGE_CLEAR, b))
                    spans = cut
            for a, b in spans:
                if b - a < LIGHT_MIN_LEN:
                    continue
                k = int(np.ceil((b - a) / LIGHT_MAX_LEN))
                step = (b - a) / k
                for i in range(k):
                    sa, sb = a + i * step, a + (i + 1) * step - (0.6 if i < k - 1 else 0)
                    zt = z - LIGHT_STRIP_H / 2 - 0.02
                    if not all(_indoors(bvh, (xx, y, zt))
                               for xx in (sa, (sa + sb) / 2, sb)):
                        dropped += 1
                        continue
                    st = _light_state(rng)
                    v, f = buf[st]
                    _panel(v, f, sa, sb, y - LIGHT_STRIP_W / 2, y + LIGHT_STRIP_W / 2,
                           z - LIGHT_STRIP_H / 2)
                    count[st] += 1
    lx, ly, lz = CABIN_LIGHT
    fixtures = ([(s, z0, b0, b1, CABIN_Y - CABIN_LIGHT_IN) for s, z0, b0, b1, _, _ in cabins]
                + [(s, z0, b0, b1, HULL_WALL_Y[0] - HULL_LIGHT_IN)
                   for s, z0, b0, b1 in hull_rooms])
    # top-deck glass houses: rows under the ray-cast ceiling
    xs = np.arange(-176.0, 176.0, TOP_SAMPLE)
    up, down = Vector((0, 0, 1)), Vector((0, 0, -1))
    n_top = 0
    for y in np.arange(-TOP_ROWS_Y, TOP_ROWS_Y + 0.1, LIGHT_ROW_PITCH):
        ceil = []
        for x in xs:
            p = Vector((x, y, TOP_DECK_Z + 0.3))
            hit = bvh.ray_cast(p, up, TOP_CEIL_MAX)[0]
            flr = bvh.ray_cast(p, down, 0.5)[0]
            ceil.append(round(hit.z, 1) if hit is not None and flr is not None else None)
        runs, i = [], 0
        while i < len(xs):
            if ceil[i] is None:
                i += 1
                continue
            j = i
            while j + 1 < len(xs) and ceil[j + 1] is not None and abs(ceil[j + 1] - ceil[i]) < 0.15:
                j += 1
            runs.append((xs[i] + LIGHT_EDGE_CLEAR, xs[j] - LIGHT_EDGE_CLEAR, ceil[i]))
            i = j + 1
        for a, b, cz in runs:
            if b - a < LIGHT_MIN_LEN:
                continue
            k = int(np.ceil((b - a) / LIGHT_MAX_LEN))
            step = (b - a) / k
            zt = cz - 0.05
            for i in range(k):
                sa, sb = a + i * step, a + (i + 1) * step - (0.6 if i < k - 1 else 0)
                if not all(_indoors(bvh, (xx, y, zt - 0.05))
                           for xx in (sa, (sa + sb) / 2, sb)):
                    dropped += 1
                    continue
                st = _light_state(rng)
                v, f = buf[st]
                _panel(v, f, sa, sb, y - LIGHT_STRIP_W / 2, y + LIGHT_STRIP_W / 2, zt)
                count[st] += 1
                n_top += 1
    print(f"[ship] top glass houses: {n_top} strip lights")
    glow = {k: ([], []) for k in ("daylight", "warm")}
    n_cab = len(cabins)
    for i, (s, z0, b0, b1, yin) in enumerate(fixtures):
        top = z0 + CABIN_STOREY_H - DECK_T - 0.02
        xc, yc = (b0 + b1) / 2, s * yin
        if not _indoors(bvh, (xc, yc, top - lz - 0.02)):
            dropped += 1
            continue
        st = _light_state(rng)
        v, f = buf[st]
        _panel(v, f, xc - lx / 2, xc + lx / 2, yc - ly / 2, yc + ly / 2,
               top - lz)
        count[st] += 1
        if i >= n_cab and st in glow:
            # lit hull room: glow sheet on the back wall, facing the window
            gv, gf = glow[st]
            y, za, zb = s * HULL_GLOW_Y, z0 + 0.05, top - 0.05
            xa, xb = b0 + 0.1, b1 - 0.1
            b = len(gv)
            gv += [(xa, y, za), (xb, y, za), (xb, y, zb), (xa, y, zb)]
            gf.append((b, b + 1, b + 2, b + 3) if s < 0 else (b + 3, b + 2, b + 1, b))
    mats = {
        "daylight": make_ceiling_light(name="Ship_Light_Daylight",
                                       color=CEILING_LIGHT_DAYLIGHT),
        "warm": make_ceiling_light(name="Ship_Light_Warm",
                                   color=CEILING_LIGHT_WARM),
        "off": make_ceiling_light(name="Ship_Light_Off",
                                  color=(0.055, 0.045, 0.035), strength=0.0),
    }
    for st, (v, f) in buf.items():
        ob = _add_object(coll, root, f"Ship_Lights_{st.capitalize()}", v, f, mats[st])
        ob["fixture_count"] = count[st]
        for p in ob.data.polygons:
            p.use_smooth = False
    for st, (v, f) in glow.items():
        col = CEILING_LIGHT_DAYLIGHT if st == "daylight" else CEILING_LIGHT_WARM
        mat = make_ceiling_light(name=f"Ship_Room_Glow_{st.capitalize()}",
                                 color=col, strength=HULL_GLOW_STRENGTH)
        ob = _add_object(coll, root, f"Ship_Room_Glow_{st.capitalize()}", v, f, mat)
        ob["room_count"] = len(f)
        for p in ob.data.polygons:
            p.use_smooth = False
    print(f"[ship] lights: {count}, {dropped} outside the ship dropped; "
          f"hull room glow {[len(g[1]) for g in glow.values()]}")


def _add_interior_lights(coll, root):
    """Shadowless point lights inside the ship; floors are light-linked out."""
    skip = bpy.data.collections.new("Ship_Light_Skip")
    for ob in coll.objects:
        if ob.type == "MESH" and any(ob.name.startswith(k) for k in INTERIOR_LIGHT_SKIP):
            skip.objects.link(ob)
    for i, loc in enumerate(INTERIOR_LIGHTS):
        ld = bpy.data.lights.new(f"Ship_Interior_Light_{i}", "POINT")
        ld.energy = INTERIOR_LIGHT_POWER
        ld.color = INTERIOR_LIGHT_COLOR
        ld.shadow_soft_size = INTERIOR_LIGHT_RADIUS
        ld.use_shadow = False
        ld.use_custom_distance = True
        ld.cutoff_distance = INTERIOR_LIGHT_CUTOFF
        ob = bpy.data.objects.new(ld.name, ld)
        ob.location = loc
        coll.objects.link(ob)
        ob.parent = root
        ob.light_linking.receiver_collection = skip
        for item in skip.collection_objects:
            item.light_linking.link_state = "EXCLUDE"
    print(f"[ship] interior lights: {len(INTERIOR_LIGHTS)} shadowless, "
          f"{len(skip.objects)} floor objects excluded")


def _mirror_arc_bay(T, UV, M):
    """Copy the -y midship arc bay to +y so the ship is Y-symmetric."""
    x = T[:, :, 0] - SHIP_CENTER[0]
    y = T[:, :, 1] - SHIP_CENTER[1]
    sel = (np.isin(M, ARC_BAY_MATS)
           & (x.min(1) >= ARC_BAY_X[0]) & (x.max(1) <= ARC_BAY_X[1])
           & (-y.max(1) >= ARC_BAY_Y[0]) & (-y.min(1) <= ARC_BAY_Y[1])
           & (T[:, :, 2].min(1) >= ARC_BAY_Z[0])
           & (T[:, :, 2].max(1) <= ARC_BAY_Z[1]))
    Tm = T[sel].copy()
    Tm[:, :, 1] = 2 * SHIP_CENTER[1] - Tm[:, :, 1]
    Tm = Tm[:, ::-1]                 # mirroring flips the winding
    UVm = UV[sel][:, ::-1]
    print(f"[ship] arc bay: {int(sel.sum())} tris mirrored to +y")
    return (np.concatenate([T, Tm]), np.concatenate([UV, UVm]),
            np.concatenate([M, M[sel]]))


def _hull_porthole_band(T, UV, M):
    """Keep only the circular ports as glass on the porthole storey.

    SketchUp tagged the whole 18-24 m band Window_Glass / Glass_Frosted /
    Glass_Ribbed.  Keep only the circular ports (tiny fan triangles) as
    glass; every other vertical pane on that storey is hull plating.
    """
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    ln = np.linalg.norm(n, axis=1)
    area = 0.5 * ln
    z0 = T[:, :, 2].min(1)
    z1 = T[:, :, 2].max(1)
    vertical = ln > 1e-5
    vertical[vertical] = np.abs(n[vertical, 2]) < 0.4 * ln[vertical]
    glass = np.isin(M, GLASS_MATS)
    on_storey = (vertical & glass & (z0 >= PORTHOLE_Z0) & (z1 <= PORTHOLE_Z1)
                 & (np.abs(T[:, :, 1] - SHIP_CENTER[1]).min(1) > 30.0))
    disk = area < PORTHOLE_DISK_AREA
    hull = on_storey & ~disk
    M = M.copy()
    M[hull] = HULL_FROM_GLASS
    print(f"[ship] porthole band: {int(hull.sum())} wall tris -> hull, "
          f"{int((on_storey & disk).sum())} circular ports kept as glass")
    return T, UV, M


def _fix_coplanar(T, UV, M, step=0.03):
    """Separate coplanar material layers so EEVEE/Cycles stop z-fighting.

    Planes are grouped regardless of facing (an up-facing roof and a
    down-facing ceiling on the same plane fight just as hard), and each
    minor layer moves along its own normal.  The step is a few centimetres
    so the depth buffer still resolves it from ~800 m away.
    """
    v0 = T[:, 1] - T[:, 0]
    v1 = T[:, 2] - T[:, 0]
    n = np.cross(v0, v1)
    ln = np.linalg.norm(n, axis=1)
    keep = ln > 1e-5
    T, UV, M = T[keep], UV[keep], M[keep]
    n = n[keep] / ln[keep, None]
    area = 0.5 * ln[keep]
    # canonical (unoriented) plane: flip so the dominant component is +
    dom = np.argmax(np.abs(n), axis=1)
    sign = np.sign(n[np.arange(len(n)), dom])
    cn = n * sign[:, None]
    d = (cn * T[:, 0]).sum(1)
    key = np.concatenate([np.round(cn, 2), np.round(d[:, None] * 20)], 1)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    offsets = np.zeros(len(T))
    layers = 0
    for gi in range(len(uniq)):
        sel = np.where(inv == gi)[0]
        if len(sel) < 2:
            continue
        mats = M[sel]
        um = np.unique(mats)
        if len(um) < 2:
            continue
        totals = sorted(((m, area[sel][mats == m].sum()) for m in um),
                        key=lambda x: -x[1])
        for rank, (m, _) in enumerate(totals):
            if rank == 0:
                continue
            offsets[sel[mats == m]] = step * rank
            layers += 1
    T = T + n[:, None, :] * offsets[:, None, None]
    print(f"[ship] coplanar: {layers} material layers separated, "
          f"{len(T)} triangles kept")
    return T, UV, M


def _add_object(coll, root, name, verts, faces, material):
    me = bpy.data.meshes.new(name + "_mesh")
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(material)
    for p in me.polygons:
        p.use_smooth = True
    coll.objects.link(ob)
    ob.parent = root
    return ob


def _world_triangles(coll):
    """(tris, material-name) for every mesh already in the Ship collection."""
    tris, names = [], []
    for ob in coll.objects:
        if ob.type != "MESH":
            continue
        me = ob.data
        me.calc_loop_triangles()
        co = np.zeros(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        mw = np.array(ob.matrix_world)
        co = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
        idx = np.zeros(len(me.loop_triangles) * 3, dtype=np.int32)
        me.loop_triangles.foreach_get("vertices", idx)
        tris.append(co[idx.reshape(-1, 3)])
        names.extend([ob.name] * len(me.loop_triangles))
    return np.concatenate(tris), np.array(names)


def _runs(mask):
    """Label consecutive True runs along axis 1; returns run ids (-1 off)."""
    pad = np.zeros((mask.shape[0], 1), bool)
    start = mask & ~np.concatenate([pad, mask[:, :-1]], 1)
    ids = np.cumsum(start.ravel()).reshape(mask.shape) - 1
    ids[~mask] = -1
    return ids


def _flood_outside(free):
    """Cells of ``free`` connected to the grid border (4-neighbour)."""
    out = np.zeros_like(free)
    out[0, :] = free[0, :]
    out[-1, :] = free[-1, :]
    out[:, 0] = free[:, 0]
    out[:, -1] = free[:, -1]
    prev = -1
    while out.sum() != prev:
        prev = out.sum()
        for transpose in (False, True):
            f = free.T if transpose else free
            o = out.T if transpose else out
            ids = _runs(f)
            hit = np.zeros(ids.max() + 2, bool)
            hit[ids[o & f]] = True
            grown = f & hit[ids]
            out = grown.T | out if transpose else grown | out
    return out


def _dilate(mask, r):
    out = mask.copy()
    for _ in range(r):
        m = out.copy()
        m[1:] |= out[:-1]
        m[:-1] |= out[1:]
        m[:, 1:] |= out[:, :-1]
        m[:, :-1] |= out[:, 1:]
        out = m
    return out


def _raster_tris(tris, x0, y0, nx, ny):
    """Mark grid cells whose centre lies inside any triangle (plan view)."""
    grid = np.zeros((ny, nx), bool)
    for t in tris:
        a, b, c = t[:, :2]
        lo = np.floor((t[:, :2].min(0) - (x0, y0)) / DECK_CELL).astype(int)
        hi = np.ceil((t[:, :2].max(0) - (x0, y0)) / DECK_CELL).astype(int)
        lo = np.clip(lo, 0, (nx, ny))
        hi = np.clip(hi, 0, (nx, ny))
        if (hi <= lo).any():
            continue
        xs = x0 + (np.arange(lo[0], hi[0]) + 0.5) * DECK_CELL
        ys = y0 + (np.arange(lo[1], hi[1]) + 0.5) * DECK_CELL
        px, py = np.meshgrid(xs, ys)
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-9:
            continue
        l1 = ((b[1] - c[1]) * (px - c[0]) + (c[0] - b[0]) * (py - c[1])) / den
        l2 = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (py - c[1])) / den
        inside = (l1 >= -1e-6) & (l2 >= -1e-6) & (l1 + l2 <= 1 + 1e-6)
        grid[lo[1]:hi[1], lo[0]:hi[0]] |= inside
    return grid


def _rect_boxes(mask, x0, y0, z0, z1):
    """Greedy rectangles over ``mask`` turned into closed box geometry."""
    verts, faces = [], []
    ny, nx = mask.shape
    open_rects = {}           # (i0, i1) -> start row
    rects = []
    for j in range(ny + 1):
        row = mask[j] if j < ny else np.zeros(nx, bool)
        d = np.diff(np.concatenate([[0], row.astype(np.int8), [0]]))
        cur = set(zip(np.where(d == 1)[0], np.where(d == -1)[0]))
        for key in list(open_rects):
            if key not in cur:
                rects.append((key[0], key[1], open_rects.pop(key), j))
        for key in cur:
            open_rects.setdefault(key, j)
    for i0, i1, j0, j1 in rects:
        xa, xb = x0 + i0 * DECK_CELL, x0 + i1 * DECK_CELL
        ya, yb = y0 + j0 * DECK_CELL, y0 + j1 * DECK_CELL
        b = len(verts)
        verts += [(xa, ya, z0), (xb, ya, z0), (xb, yb, z0), (xa, yb, z0),
                  (xa, ya, z1), (xb, ya, z1), (xb, yb, z1), (xa, yb, z1)]
        faces += [(b, b + 3, b + 2, b + 1), (b + 4, b + 5, b + 6, b + 7),
                  (b, b + 1, b + 5, b + 4), (b + 1, b + 2, b + 6, b + 5),
                  (b + 2, b + 3, b + 7, b + 6), (b + 3, b, b + 4, b + 7)]
    return verts, faces, len(rects)


def _add_decks(coll, root):
    """A solid slab on every storey so the ship is not a hollow shell.

    Each level is sliced 1.2 m above its floor; the cut through the SKP
    walls is rasterised, small gaps (doors, open bays) are closed by a
    0.6 m dilation, and everything not reachable from outside becomes deck.
    Wherever the SKP already has a horizontal surface at that level the
    slab is left out, so the new slab never lies coplanar with SKP faces.
    """
    T, names = _world_triangles(coll)
    # cabin partitions are interior walls; they must not split the slab
    keep = names != "Cabin_Partitions"
    T, names = T[keep], names[keep]
    x0, y0 = -176.0, -36.0
    nx, ny = int(352 / DECK_CELL), int(72 / DECK_CELL)
    mat = bpy.data.materials.new("Interior_Deck")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.62, 0.56, 0.47, 1.0)
    b.inputs["Roughness"].default_value = 0.6

    nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    nrm /= np.linalg.norm(nrm, axis=1)[:, None] + 1e-12
    horiz = np.abs(nrm[:, 2]) > 0.9
    pool = T[names == "Pool_Water"]
    pool_z = (pool[:, :, 2].min(), pool[:, :, 2].max()) if len(pool) else None
    pool_cells = _raster_tris(pool, x0, y0, nx, ny) if len(pool) else None

    verts, faces, total = [], [], 0
    rooms = {}
    z = T[:, :, 2]
    for li, level in enumerate(DECK_LEVELS):
        # A slab is the floor of the storey above it and the ceiling of the
        # one below, so it is bounded by walls from just under the level up
        # through the next storey.  Stacking cuts closes door/window gaps a
        # single cut would leak through; the short reach below closes the
        # SKP's open-topped bow wedge (its walls stop at z=15).
        above = DECK_LEVELS[li + 1] if li + 1 < len(DECK_LEVELS) else level + 3.0
        # Porthole storey: slice below the circular ports so the cabin
        # floor is bounded by hull plating, not leaked through the disks.
        if abs(level - 18.0) < 0.01:
            cuts = np.arange(level + 0.15, min(level + 1.9, above) - 0.05, 0.3)
        else:
            cuts = np.arange(level - 0.6, above - 0.1, 0.4)
        wall = np.zeros((ny, nx), bool)
        for cut in cuts:
            cross = ((z > cut).sum(1) % 3) != 0
            for t in T[cross]:
                pts = []
                for a, c in ((0, 1), (1, 2), (2, 0)):
                    if (t[a, 2] > cut) != (t[c, 2] > cut):
                        f = (cut - t[a, 2]) / (t[c, 2] - t[a, 2])
                        pts.append(t[a, :2] + f * (t[c, :2] - t[a, :2]))
                if len(pts) != 2:
                    continue
                n = int(np.linalg.norm(pts[1] - pts[0]) / (DECK_CELL / 2)) + 2
                p = np.linspace(pts[0], pts[1], n)
                ij = np.floor((p - (x0, y0)) / DECK_CELL).astype(int)
                ok = ((ij[:, 0] >= 0) & (ij[:, 0] < nx)
                      & (ij[:, 1] >= 0) & (ij[:, 1] < ny))
                wall[ij[ok, 1], ij[ok, 0]] = True
        if not wall.any():
            continue
        closed = _dilate(wall, DECK_GAP)
        inside = ~_flood_outside(~closed)
        # grow back to the wall line, never past the dilated wall band
        deck = _dilate(inside & ~closed, DECK_GAP) & inside
        room = deck.copy()
        existing = horiz & (np.abs(z.mean(1) - level) < 0.3)
        # Porthole storey: SKP only has a thin outer walkway at 18 m, so
        # subtracting those faces would leave the cabin floor empty. Keep
        # the interior fill; skip the existing-deck subtraction here only.
        if abs(level - 18.0) > 0.01:
            deck &= ~_raster_tris(T[existing], x0, y0, nx, ny)
        if pool_cells is not None and pool_z[0] - 0.5 < level < pool_z[1] + 3.0:
            deck &= ~_dilate(pool_cells, 1)
            room &= ~_dilate(pool_cells, 1)
        rooms[level] = room
        # morphological opening drops sub-metre speckles left in balcony bays
        deck &= _dilate(~_dilate(~deck, DECK_SPECKLE), DECK_SPECKLE)
        top = level - DECK_DROP
        v, f, nrect = _rect_boxes(deck, x0, y0, top - DECK_T, top)
        off = len(verts)
        verts += v
        faces += [tuple(i + off for i in face) for face in f]
        total += deck.sum() * DECK_CELL ** 2
        print(f"[ship] deck z={level:5.1f}: {deck.sum() * DECK_CELL ** 2:7.0f} m2, "
              f"{nrect} slabs")
    ob = _add_object(coll, root, "Interior_Decks", verts, faces, mat)
    for p in ob.data.polygons:
        p.use_smooth = False
    print(f"[ship] interior decks: {total:.0f} m2 over {len(DECK_LEVELS)} levels")
    return rooms


# Porthole storey (z 18-22.45): the SKP overhang out to |y|=32 only has the
# 22.45 m deck above it and the loose port disks; no side plating, no floor.
PORT_Z0, PORT_Z1, PORT_TOP = 17.95, 22.45, 19.45
PORT_ZC, PORT_R, PORT_PITCH = 20.95, 0.9, 3.0
PORT_RUNS = ((-127.0, 16), (104.5, 13))   # first centre x, count (SKP)
PORT_Y, PORT_WALL_T = 31.99, 0.15
PORT_SEG = 32
# Bridge front (22.45 m deck outline), port side half, from the side wall
# round to the centreline; mirrored for starboard.
BRIDGE_OUTLINE = ((-141.23, 0.0), (-141.23, 13.82), (-138.36, 17.91),
                  (-135.5, 22.0), (-132.0, 27.0), (-128.5, 32.0))


def _soffit(y):
    """Underside of the porthole overhang: 4.5 m deep at the hull (|y| 22),
    3 m at the outer edge (PORT_Y), so the section is a trapezoid (SKP)."""
    t = min(max((abs(y) - 22.0) / (PORT_Y - 22.0), 0.0), 1.0)
    return PORT_Z0 + (PORT_TOP - PORT_Z0) * t


def _wall_quad(verts, faces, a, b, z0, z1, y_in):
    """Slab of plating between plan points a, b (outer face) z0..z1."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    n = np.array([d[1], -d[0]]) / np.linalg.norm(d)
    if np.dot(n, (a + b) / 2) < 0:
        n = -n
    ia, ib = a - n * y_in, b - n * y_in
    za, zb = z0 if isinstance(z0, tuple) else (z0, z0)
    if z1 - max(za, zb) < 0.01 and z1 - min(za, zb) < 0.01:
        return
    k = len(verts)
    for p, z in ((a, za), (b, zb), (ib, zb), (ia, za)):
        verts.append((p[0], p[1], z))
    for p in (a, b, ib, ia):
        verts.append((p[0], p[1], z1))
    faces += [(k, k + 1, k + 5, k + 4), (k + 3, k + 7, k + 6, k + 2),
              (k, k + 4, k + 7, k + 3), (k + 1, k + 2, k + 6, k + 5),
              (k, k + 3, k + 2, k + 1), (k + 4, k + 5, k + 6, k + 7)]


def _port_tile(verts, faces, cx, s):
    """3x3 m plating tile with a round hole, outer face at y=s*PORT_Y."""
    h = PORT_PITCH / 2
    rings = []
    for y in (PORT_Y, PORT_Y - PORT_WALL_T):
        sq, ci = [], []
        for i in range(PORT_SEG):
            t = 2 * math.pi * i / PORT_SEG
            c, sn = math.cos(t), math.sin(t)
            m = h / max(abs(c), abs(sn))
            sq.append(len(verts))
            verts.append((cx + c * m, s * y, PORT_ZC + sn * m))
            ci.append(len(verts))
            verts.append((cx + c * PORT_R, s * y, PORT_ZC + sn * PORT_R))
        rings.append((sq, ci))
    (so, co), (si, cin) = rings
    for i in range(PORT_SEG):
        j = (i + 1) % PORT_SEG
        faces.append((so[i], so[j], co[j], co[i]))      # outer face
        faces.append((si[i], cin[i], cin[j], si[j]))     # inner face
        faces.append((co[i], co[j], cin[j], cin[i]))    # hole reveal


def _add_porthole_storey(coll, root):
    """Side plating with round holes and a floor for the porthole storey."""
    verts, faces = [], []
    w = PORT_WALL_T
    for s in (1, -1):
        for x0, cnt in PORT_RUNS:
            xa = x0 - PORT_PITCH / 2
            xb = x0 + PORT_PITCH * (cnt - 1) + PORT_PITCH / 2
            for k in range(cnt):
                _port_tile(verts, faces, x0 + k * PORT_PITCH, s)
            # plating above the 3 m port tiles (they start on the soffit edge)
            _wall_quad(verts, faces, (xa, s * PORT_Y), (xb, s * PORT_Y),
                       PORT_ZC + PORT_PITCH / 2, PORT_Z1, w)
            # close each cabin run from the open lifeboat bay
            for xe in (xa, xb):
                if -128.0 < xe < 141.0:
                    _wall_quad(verts, faces, (xe, s * 22.0), (xe, s * PORT_Y),
                               (PORT_Z0, PORT_TOP), PORT_Z1, w)
        # bow: below the SKP glazing (it starts at z 19.45)
        for a, b in zip(BRIDGE_OUTLINE[:-1], BRIDGE_OUTLINE[1:]):
            _wall_quad(verts, faces, (a[0], s * a[1]), (b[0], s * b[1]),
                       (_soffit(a[1]), _soffit(b[1])), PORT_TOP - 0.01, w)
        # stern: the diagonal back to the hull is open in the SKP
        _wall_quad(verts, faces, (142.0, s * PORT_Y), (149.0, s * 22.0),
                   (PORT_TOP, PORT_Z0), PORT_Z1, w)
        # sloped soffit of the overhang, following the 22.45 m deck outline
        outline = [(-135.5, 22.0), (-132.0, 27.0), (-128.5, 32.0),
                   (142.0, 32.0), (149.0, 22.0)]
        k = len(verts)
        for x, y in outline:
            verts.append((x, s * y, _soffit(y) - 0.37))
        for x, y in outline:
            verts.append((x, s * y, _soffit(y) - 0.07))
        n = len(outline)
        faces.append(tuple(range(k, k + n)))
        faces.append(tuple(range(k + n, k + 2 * n)))
        for i in range(n):
            j = (i + 1) % n
            faces.append((k + i, k + j, k + n + j, k + n + i))
    # close the gap between the foredeck (z 14.95) and the bridge floor:
    # front wall under the bridge front, side walls along the hull rim
    rim = ((-141.23, 22.0 * (-141.23 + 172.5) / 44.0), (-128.5, 22.0),
           (-125.5, 22.0))
    gz0, gz1 = 14.95, PORT_Z0 - 0.37
    _wall_quad(verts, faces, (rim[0][0], -rim[0][1]), rim[0], gz0, gz1, w)
    for s in (1, -1):
        for a, b in zip(rim[:-1], rim[1:]):
            _wall_quad(verts, faces, (a[0], s * a[1]), (b[0], s * b[1]),
                       gz0, gz1, w)
    # floor of the bridge overhang over the foredeck (SKP has none)
    outline = ([(x, -y) for x, y in BRIDGE_OUTLINE[::-1]][:-1]
               + list(BRIDGE_OUTLINE[1:]) + [(-125.5, 22.0), (-125.5, -22.0)])
    outline = [(x, y) for x, y in outline if abs(y) <= 22.0]
    top, bot = PORT_Z0 - 0.07, PORT_Z0 - 0.37
    k = len(verts)
    for x, y in outline:
        verts.append((x, y, bot))
    for x, y in outline:
        verts.append((x, y, top))
    n = len(outline)
    faces.append(tuple(range(k, k + n)))
    faces.append(tuple(range(k + n, k + 2 * n)))
    for i in range(n):
        j = (i + 1) % n
        faces.append((k + i, k + j, k + n + j, k + n + i))
    mat = bpy.data.materials["Superstructure_White"]
    ob = _add_object(coll, root, "Porthole_Storey", verts, faces, mat)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    for p in ob.data.polygons:
        p.use_smooth = False
    print(f"[ship] porthole storey: {len(faces)} faces of side plating + floor")


def _bar(verts, faces, p, q, side, normal, width, depth):
    """Box from p to q, ``width`` along ``side`` and ``depth`` along normal."""
    s = side * (width / 2)
    n = normal * (depth / 2)
    # stop the end caps short of the pane edge: there they would lie on
    # the deck/wall plane the pane meets and z-fight with it
    axis = q - p
    length = np.linalg.norm(axis)
    if length > 4 * FRAME_END_GAP:
        axis = axis / length * FRAME_END_GAP
        p, q = p + axis, q - axis
    b = len(verts)
    for e in (p, q):
        verts += [tuple(e - s - n), tuple(e + s - n), tuple(e + s + n),
                  tuple(e - s + n)]
    faces += [(b, b + 1, b + 2, b + 3), (b + 7, b + 6, b + 5, b + 4),
              (b, b + 4, b + 5, b + 1), (b + 1, b + 5, b + 6, b + 2),
              (b + 2, b + 6, b + 7, b + 3), (b + 3, b + 7, b + 4, b)]


def _add_glass_frames(coll, root):
    """Frame every glazed surface: a bar round each pane outline plus
    mullions every FRAME_SPACING, so the panes read as divided glazing."""
    mat = bpy.data.materials.new("Window_Frame")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.80, 0.81, 0.82, 1.0)
    b.inputs["Metallic"].default_value = 0.6
    b.inputs["Roughness"].default_value = 0.3
    verts, faces = [], []
    up = np.array((0.0, 0.0, 1.0))
    for name in FRAMED_GLASS:
        ob = bpy.data.objects.get(name)
        if ob is None:
            continue
        me = ob.data
        co = np.array([v.co[:] for v in me.vertices])
        key = np.round(co, 3)
        _, weld = np.unique(key, axis=0, return_inverse=True)
        weld = weld.ravel()
        edge_count = {}
        for poly in me.polygons:
            vs = [weld[i] for i in poly.vertices]
            for a, c in zip(vs, vs[1:] + vs[:1]):
                k = (min(a, c), max(a, c))
                edge_count[k] = edge_count.get(k, 0) + 1
        first = {}
        for i, w in enumerate(weld):
            first.setdefault(w, i)
        for poly in me.polygons:
            if poly.area < 1.0:
                # circular portholes are a fan of tiny tris; do not mullion them
                continue
            n = np.array(poly.normal[:])
            vs = [weld[i] for i in poly.vertices]
            P = [co[first[w]] for w in vs]
            # outline bars on edges no other pane shares
            for (a, c), pa, pc in zip(zip(vs, vs[1:] + vs[:1]), P, P[1:] + P[:1]):
                if edge_count[(min(a, c), max(a, c))] != 1:
                    continue
                d = pc - pa
                if np.linalg.norm(d) < 0.05:
                    continue
                side = np.cross(n, d / np.linalg.norm(d))
                _bar(verts, faces, pa, pc, side, n, *FRAME_EDGE)
            # mullions: cut the pane by planes s = k * spacing
            if abs(n[2]) > 0.9:
                dirs = (np.array((1.0, 0, 0)), np.array((0, 1.0, 0)))
                spacing = FRAME_SPACING * 2
            else:
                u = np.cross(up, n)
                dirs = (u / np.linalg.norm(u),)
                spacing = FRAME_SPACING
            for u in dirs:
                s = np.array([p @ u for p in P])
                for k in range(int(np.ceil(s.min() / spacing + 1e-6)),
                               int(np.floor(s.max() / spacing - 1e-6)) + 1):
                    sv = k * spacing
                    pts = []
                    for i in range(len(P)):
                        j = (i + 1) % len(P)
                        if (s[i] - sv) * (s[j] - sv) < 0:
                            f = (sv - s[i]) / (s[j] - s[i])
                            pts.append(P[i] + f * (P[j] - P[i]))
                    if len(pts) == 2 and np.linalg.norm(pts[1] - pts[0]) > 0.05:
                        _bar(verts, faces, pts[0], pts[1], u, n, *FRAME_MULLION)
    ob = _add_object(coll, root, "Window_Frames", verts, faces, mat)
    for p in ob.data.polygons:
        p.use_smooth = False
    print(f"[ship] glass frames: {len(faces) // 6} bars")


def build_ship() -> dict:
    T, UV, M = _load_ship_triangles()
    T, UV, M = _mirror_arc_bay(T, UV, M)
    T, UV, M = _hull_porthole_band(T, UV, M)
    T, UV, M = _fix_coplanar(T, UV, M)
    T = T - np.array(
        [SHIP_CENTER[0], SHIP_CENTER[1], SHIP_WATERLINE], dtype=np.float64
    )
    T, UV, M, cabins = _open_cabin_fronts(T, UV, M)
    T, UV, M, hull_plates, hull_windows = _open_hull_windows(T, UV, M)
    T, UV, M = _drop_glass_backing(T, UV, M)

    materials = {i: make_material(i) for i in MATS}
    coll = bpy.data.collections.new("Ship")
    bpy.context.scene.collection.children.link(coll)

    total_v = total_t = 0
    for mi in sorted(set(M.tolist())):
        if mi not in MATS:
            print(f"[ship] skip unknown material {mi}")
            continue
        sel = np.where(M == mi)[0]
        pos = T[sel].reshape(-1, 3).astype(np.float32)
        loop_uv = UV[sel].reshape(-1, 2).astype(np.float32)
        nverts = len(pos)
        idx = np.arange(nverts, dtype=np.int32)

        me = bpy.data.meshes.new(f"{MATS[mi][0]}_mesh")
        me.vertices.add(nverts)
        me.vertices.foreach_set("co", pos.ravel())
        me.loops.add(nverts)
        me.loops.foreach_set("vertex_index", idx)
        me.polygons.add(nverts // 3)
        me.polygons.foreach_set("loop_start", np.arange(0, nverts, 3, dtype=np.int32))
        me.polygons.foreach_set("loop_total", np.full(nverts // 3, 3, dtype=np.int32))
        uv_layer = me.uv_layers.new(name="UVMap")
        uv_layer.data.foreach_set("uv", loop_uv.ravel())
        me.update(calc_edges=True)
        me.validate()

        ob = bpy.data.objects.new(MATS[mi][0], me)
        ob.data.materials.append(materials[mi])
        for p in me.polygons:
            p.use_smooth = False
        coll.objects.link(ob)
        total_v += nverts
        total_t += nverts // 3

    root = bpy.data.objects.new("ELEGANT_SHIP", None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 25
    coll.objects.link(root)
    for ob in list(coll.objects):
        if ob is not root:
            ob.parent = root

    _add_cabin_fronts(coll, root, cabins)
    hull_rooms = _add_hull_cabins(coll, root, hull_plates, hull_windows)
    rooms = _add_decks(coll, root)
    _add_porthole_storey(coll, root)
    _add_glass_frames(coll, root)
    _add_lights(coll, root, rooms, cabins, hull_rooms)
    _add_interior_lights(coll, root)

    return {"verts": total_v, "tris": total_t, "objects": len(set(M.tolist()))}


def add_environment() -> None:
    scene = bpy.context.scene
    env = bpy.data.collections.new("Environment")
    scene.collection.children.link(env)

    bpy.ops.mesh.primitive_plane_add(size=50000, location=(0, 0, -0.18))
    water = bpy.context.object
    water.name = "Sea"
    water.data.name = "Sea"
    for c in water.users_collection:
        c.objects.unlink(water)
    env.objects.link(water)

    mat = bpy.data.materials.new("Sea_Water")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.008, 0.045, 0.075, 1)
    bsdf.inputs["Roughness"].default_value = 0.14
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["IOR"].default_value = 1.333
    bsdf.inputs["Specular IOR Level"].default_value = 0.55
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.9
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Roughness"].default_value = 0.55
    noise.location = (-500, -200)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.30
    bump.inputs["Distance"].default_value = 1.5
    bump.location = (-260, -200)
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    water.data.materials.append(mat)

    world = bpy.data.worlds.new("Sea_Sky")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.72, 0.83, 0.93, 1.0)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (0.045, 0.14, 0.34, 1.0)
    mid = ramp.color_ramp.elements.new(0.35)
    mid.color = (0.16, 0.35, 0.62, 1.0)
    mapr = nt.nodes.new("ShaderNodeMapRange")
    mapr.inputs["From Min"].default_value = -0.04
    mapr.inputs["From Max"].default_value = 0.55
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.0
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(coord.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mapr.inputs["Value"])
    nt.links.new(mapr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 6.5
    sun_data.angle = math.radians(1.2)
    sun_data.color = (1.0, 0.88, 0.74)
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.rotation_euler = Vector((0.85, 0.50, -0.55)).to_track_quat("-Z", "Y").to_euler()
    env.objects.link(sun)

    fill_data = bpy.data.lights.new("Sky_Fill", "SUN")
    fill_data.energy = 0.8
    fill_data.angle = math.radians(25)
    fill_data.color = (0.62, 0.76, 1.0)
    fill = bpy.data.objects.new("Sky_Fill", fill_data)
    fill.rotation_euler = Vector((-0.7, -0.4, -0.35)).to_track_quat("-Z", "Y").to_euler()
    env.objects.link(fill)


def add_cameras() -> None:
    scene = bpy.context.scene
    coll = bpy.data.collections.new("Cameras")
    scene.collection.children.link(coll)

    def camera(name, loc, target, lens, ortho=None):
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.clip_start = 5.0
        cd.clip_end = 30000.0
        if ortho:
            cd.type = "ORTHO"
            cd.ortho_scale = ortho
        ob = bpy.data.objects.new(name, cd)
        ob.location = Vector(loc)
        ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        coll.objects.link(ob)
        return ob

    overview = camera("CAM_Overview", (-720, -720, 340), (0, 0, 24), 45)
    camera("CAM_Hero", (-390, -390, 165), (0, 0, 20), 55)
    camera("CAM_Side", (0, -790, 30), (0, 0, 30), 70)
    camera("CAM_Aerial", (-160, -350, 320), (0, 0, 14), 50)
    camera("CAM_Bow", (-350, -210, 60), (-140, 0, 22), 60)
    scene.camera = overview


def setup_render() -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -0.10
    scene.render.film_transparent = False
    try:
        scene.eevee.use_raytracing = True
        scene.eevee.ray_tracing_method = "SCREEN"
        scene.eevee.use_shadows = True
        scene.eevee.use_fast_gi = True
    except AttributeError:
        pass


def render_views() -> None:
    scene = bpy.context.scene
    os.makedirs(OUT, exist_ok=True)
    for cam_name, filename in [
        ("CAM_Hero", "hero.png"),
        ("CAM_Side", "side.png"),
        ("CAM_Aerial", "aerial.png"),
        ("CAM_Bow", "bow.png"),
    ]:
        scene.camera = bpy.data.objects[cam_name]
        scene.render.filepath = os.path.join(OUT, filename)
        bpy.ops.render.render(write_still=True)
        print(f"[ship] rendered {filename}")


def frame_viewport() -> None:
    """Save a 3/4 overview in every 3D viewport so the file opens on the
    whole ship instead of a default close-up inside the model."""
    direction = Vector((-1.0, -1.0, 0.55)).normalized()
    rotation = direction.to_track_quat("Z", "Y")
    count = 0
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type != "VIEW_3D":
                    continue
                r3d = space.region_3d
                r3d.view_location = (0.0, 0.0, 28.0)
                r3d.view_distance = 760.0
                r3d.view_rotation = rotation
                r3d.view_perspective = "PERSP"
                space.clip_start = 1.0
                space.clip_end = 30000.0
                count += 1
    print(f"[ship] viewport framed: {count} 3D views at 760 m")


def main() -> None:
    clear_scene()
    stats = build_ship()
    add_environment()
    skip = bpy.data.collections["Ship_Light_Skip"]
    skip.objects.link(bpy.data.objects["Sea"])
    for item in skip.collection_objects:
        item.light_linking.link_state = "EXCLUDE"
    add_cameras()
    setup_render()
    print(f"[ship] geometry: {stats['verts']} verts, {stats['tris']} tris, "
          f"{stats['objects']} material objects")
    frame_viewport()
    os.makedirs(OUT, exist_ok=True)
    blend = os.path.join(OUT, "elegant_ship.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    print(f"[ship] saved {blend}")
    if RENDER:
        render_views()


if __name__ == "__main__":
    main()
