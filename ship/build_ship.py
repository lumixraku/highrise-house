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
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shared"))
from materials import make_glass  # noqa: E402

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
    z = T[:, :, 2]
    for li, level in enumerate(DECK_LEVELS):
        # A slab is the floor of the storey above it and the ceiling of the
        # one below, so it is bounded by walls from just under the level up
        # through the next storey.  Stacking cuts closes door/window gaps a
        # single cut would leak through; the short reach below closes the
        # SKP's open-topped bow wedge (its walls stop at z=15).
        above = DECK_LEVELS[li + 1] if li + 1 < len(DECK_LEVELS) else level + 3.0
        wall = np.zeros((ny, nx), bool)
        for cut in np.arange(level - 0.6, above - 0.1, 0.4):
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
        existing = horiz & (np.abs(z.mean(1) - level) < 0.3)
        deck &= ~_raster_tris(T[existing], x0, y0, nx, ny)
        if pool_cells is not None and pool_z[0] - 0.5 < level < pool_z[1] + 3.0:
            deck &= ~_dilate(pool_cells, 1)
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
    T, UV, M = _fix_coplanar(T, UV, M)
    T = T - np.array(
        [SHIP_CENTER[0], SHIP_CENTER[1], SHIP_WATERLINE], dtype=np.float64
    )

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

    _add_decks(coll, root)
    _add_glass_frames(coll, root)

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
