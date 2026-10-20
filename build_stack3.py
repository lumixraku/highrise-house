"""Build Stack 3: a third-generation study of MVRDV's The Stack proposal.

The first two generations (build_the_stack.py, build_stack2.py) read the tower
as a glass slab in a chunky square frame cage. This generation goes back to the
published elevation and section sheets in the MVRDV gallery and models the thing
that actually gives the building its identity: the stack of neighbourhoods, each
with its own facade language, reading as horizontal strata.

Client direction for this generation sets the envelope: about 350 m tall, a
little over 100 m wide and only 36 m deep, so the mass is a very flat slab. The
model uses a 108 x 36 m plan; the client later asked for a completely flat roof,
so the stack stops at the apartment band and the tower tops out at 334 m
(335.6 m to the parapet). That is a 3.09 : 1 wide elevation - exactly the ratio
of the published orthographic elevation sheet (321 : 992 px) - while keeping the
36 m depth.

Three bands, bottom to top, each with its own facade system, separated by metal
cornices - these are the "stack":

    Lattice     0 - 190   one bold external frame, three bays by three tiers,
                          an X brace in every cell over glass; warm hall below,
                          cool floors above
    Plaza      190 - 220  planted arcade of branching tree columns
    Apart.     220 - 334  semi-transparent glazed bays in a staggered block
                          grid, 4 m courses, the frame itself is the window

The tower stops at a completely flat roof at 334 m: one deck and a parapet, no
stepped crown, no terraces above the apartment band.

The shallow plan is what makes the strata legible: with only 36 m of depth the
long faces stay almost flat and the bands read as continuous horizontal ribbons,
while the short faces show the same sequence compressed into a narrow slice.
The two service cores stand on the long axis, so the glazed bands read as
occupied floors rather than a hollow box.

The competition entry has no as-built drawings. Dimensions, band order and
facade treatments are inferred from the published elevation, section and model
photography; the model is an interpretation, not a survey.
"""

import argparse
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import materials


OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
BLEND_PATH = os.path.join(OUT_DIR, "the_stack3.blend")
PREFIX = "Stack3_"

# ---------------------------------------------------------------------------
# Frozen envelope and program
# ---------------------------------------------------------------------------
ROOF = 302.0              # flat roof deck; the stepped crown is gone
PARAPET_H = 1.2
HEIGHT = ROOF + 0.4 + PARAPET_H    # 335.6 to the top of the parapet
WIDTH = 108.0
DEPTH = 36.0
HALF_W, HALF_D = WIDTH / 2.0, DEPTH / 2.0

STOREY = 4.0            # apartment storey (and the block module)
STOREY_LOW = 5.0        # base / diagrid / plaza storey: 5 m, fewer floors


def floor_levels():
    """Floor plates: 5 m storeys below the apartments, 4 m within them."""
    return ([z for z in range(5, 186, 5)]
            + [z for z in range(188, 301, 4)])
BAY = 3.6               # facade mullion module on the glazed bands

BANDS = (
    ("Lattice", 0.0, 158.0),
    ("Plaza", 158.0, 188.0),
    ("Apartments", 188.0, 302.0),
)
BAND = {name: (z0, z1) for name, z0, z1 in BANDS}

FACES = ("S", "N", "W", "E")
LONG_FACES = ("S", "N")
VIEW_NAMES = ("preview", "elevation", "side", "base", "detail")


def face_half(face):
    return HALF_W if face in LONG_FACES else HALF_D


def fp(face, u, z, out=0.0):
    """World point on a facade: u runs along the face, out runs outward."""
    if face == "S":
        return Vector((u, -HALF_D - out, z))
    if face == "N":
        return Vector((u, HALF_D + out, z))
    if face == "W":
        return Vector((-HALF_W - out, u, z))
    return Vector((HALF_W + out, u, z))


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
_CUBE_V = ((-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5),
           (-0.5, 0.5, -0.5), (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5),
           (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5))
_CUBE_F = ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
           (2, 3, 7, 6), (3, 0, 4, 7))


class Part:
    """Accumulates primitives into a single mesh object for one material.

    One Part per band and role keeps the outliner readable while keeping the
    object count low enough that EEVEE stays fast at 350 m scale.
    """

    def __init__(self, name, mat, col):
        self.name = PREFIX + name
        self.mat = mat
        self.col = col
        self.bm = bmesh.new()
        self.boxes = 0

    # -- primitives -------------------------------------------------------
    def _cube(self, matrix):
        verts = [self.bm.verts.new(matrix @ Vector(v)) for v in _CUBE_V]
        for face in _CUBE_F:
            self.bm.faces.new([verts[i] for i in face])
        self.boxes += 1

    def box(self, center, size):
        m = Matrix.Translation(Vector(center)) @ Matrix.Diagonal(
            Vector((size[0], size[1], size[2], 1.0)))
        self._cube(m)

    def face_box(self, face, u0, u1, z0, z1, out=0.0, thick=0.1):
        """A slab parallel to a facade plane, occupying [out, out + thick]."""
        if u1 <= u0 or z1 <= z0:
            return
        cu, cz = (u0 + u1) / 2.0, (z0 + z1) / 2.0
        p = fp(face, cu, cz, out + thick / 2.0)
        if face in LONG_FACES:
            size = (u1 - u0, thick, z1 - z0)
        else:
            size = (thick, u1 - u0, z1 - z0)
        self.box(p, size)

    def prism(self, p0, p1, width, height, up=(0, 0, 1)):
        """A member from p0 to p1 with a rectangular cross-section."""
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        length = d.length
        if length < 1e-6:
            return
        z = d / length
        up = Vector(up)
        x = up.cross(z)
        if x.length < 1e-6:
            x = Vector((1, 0, 0)).cross(z)
        x.normalize()
        y = z.cross(x)
        m = Matrix((
            (x.x * width, y.x * height, z.x * length, (p0.x + p1.x) / 2),
            (x.y * width, y.y * height, z.y * length, (p0.y + p1.y) / 2),
            (x.z * width, y.z * height, z.z * length, (p0.z + p1.z) / 2),
            (0, 0, 0, 1),
        ))
        self._cube(m)

    def bar(self, p0, p1, width, depth):
        """A diagonal member lying in a vertical facade plane."""
        self.prism(p0, p1, width, depth, up=(0, 0, 1))

    def cyl(self, p0, p1, r0, r1, seg=8):
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        length = d.length
        if length < 1e-6:
            return
        z = d / length
        up = Vector((0, 0, 1)) if abs(z.z) < 0.95 else Vector((1, 0, 0))
        x = up.cross(z).normalized()
        y = z.cross(x)
        m = Matrix(((x.x, y.x, z.x, 0), (x.y, y.y, z.y, 0),
                    (x.z, y.z, z.z, 0), (0, 0, 0, 1)))
        m.translation = (p0 + p1) / 2.0
        bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False,
                              segments=seg, radius1=r0, radius2=r1,
                              depth=length, matrix=m)
        self.boxes += 1

    def face_disc(self, face, u, z, r, out0, out1, seg=20):
        self.cyl(fp(face, u, z, out0), fp(face, u, z, out1), r, r, seg)

    def sphere(self, center, radius, subdiv=1):
        m = Matrix.Translation(Vector(center))
        try:
            bmesh.ops.create_icosphere(self.bm, subdivisions=subdiv,
                                       radius=radius, matrix=m)
        except TypeError:                     # very old bmesh signature
            bmesh.ops.create_icosphere(self.bm, subdivisions=subdiv,
                                       diameter=radius, matrix=m)
        self.boxes += 1

    # -- output -----------------------------------------------------------
    def finish(self):
        if not self.bm.faces:
            self.bm.free()
            return None
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        mesh = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        mesh.materials.append(self.mat)
        obj = bpy.data.objects.new(self.name, mesh)
        self.col.objects.link(obj)
        return obj


def sub_collection(parent, name):
    col = bpy.data.collections.new(name)
    parent.children.link(col)
    return col


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------
def block_material(name, color):
    """Large-format masonry: a warm flat tone with a soft grain, no courses.

    The one-storey reading comes from the geometry (block joints, staggered
    tones), so the material must not add a fine brick pattern of its own.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for node in list(nt.nodes):
        nt.nodes.remove(node)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (520, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (260, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    coord = nt.nodes.new("ShaderNodeTexCoord")
    coord.location = (-700, 0)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.location = (-500, 0)
    noise.inputs["Scale"].default_value = 1.6
    noise.inputs["Detail"].default_value = 5.0
    nt.links.new(coord.outputs["Object"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-280, 0)
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (0.84, 0.84, 0.84, 1.0)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.location = (0, 0)
    mix.blend_type = "MULTIPLY"
    mix.inputs["Fac"].default_value = 0.55
    mix.inputs["Color1"].default_value = (*color, 1.0)
    nt.links.new(ramp.outputs["Color"], mix.inputs["Color2"])
    nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.84
    bsdf.inputs["Specular IOR Level"].default_value = 0.24
    return mat


def make_unlit(name, color):
    """A flat emission surface: the model's floor must not take light or cast
    shadow, so it never darkens or blocks the studio lights."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for node in list(nt.nodes):
        nt.nodes.remove(node)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (300, 0)
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.location = (80, 0)
    emit.inputs["Color"].default_value = (*color, 1.0)
    emit.inputs["Strength"].default_value = 1.0
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def build_materials(night=False):
    glow = 6.0 if not night else 3.0
    return {
        "glass": materials.make_glass(
            "Stack3_Glass", engine="BLENDER_EEVEE", tint=(0.26, 0.33, 0.36)),
        "glass_deep": materials.make_glass(
            "Stack3_Glass_Deep", engine="BLENDER_EEVEE", tint=(0.085, 0.100, 0.110)),
        "glass_warm": materials.make_glass(
            "Stack3_Glass_Warm", engine="BLENDER_EEVEE",
            tint=(0.34, 0.34, 0.30)),
        "glass_dark": materials.make_glass(
            "Stack3_Glass_Dark", engine="BLENDER_EEVEE",
            tint=(0.045, 0.050, 0.055)),
        "pane_a": materials.make_glass(
            "Stack3_Pane_A", engine="BLENDER_EEVEE", tint=(0.46, 0.51, 0.53)),
        "pane_b": materials.make_glass(
            "Stack3_Pane_B", engine="BLENDER_EEVEE", tint=(0.54, 0.58, 0.59)),
        "pane_c": materials.make_glass(
            "Stack3_Pane_C", engine="BLENDER_EEVEE", tint=(0.38, 0.44, 0.47)),
        "block_a": block_material("Stack3_Block_A", (0.105, 0.090, 0.076)),
        "block_b": block_material("Stack3_Block_B", (0.120, 0.103, 0.086)),
        "block_c": block_material("Stack3_Block_C", (0.094, 0.081, 0.069)),
        "block_d": block_material("Stack3_Block_D", (0.138, 0.119, 0.100)),
        "silver": materials.make_metal("Stack3_Silver", color=(0.66, 0.67, 0.68)),
        "mesh": materials.make_metal("Stack3_Aluminium", color=(0.47, 0.48, 0.48)),
        "stone": materials.make_wall("Stack3_Stone", color=(0.46, 0.45, 0.42)),
        "concrete": materials.make_concrete("Stack3_Concrete", color=(0.40, 0.40, 0.39)),
        "slate": materials.make_concrete("Stack3_Slate", color=(0.022, 0.024, 0.027)),
        "black": materials.make_concrete("Stack3_Black", color=(0.020, 0.021, 0.024)),
        "slab": materials.make_concrete("Stack3_Slab", color=(0.34, 0.35, 0.35)),
        "slab_dark": materials.make_concrete("Stack3_Slab_Dark",
                                             color=(0.008, 0.008, 0.009)),
        "panel_dark": materials.make_wall("Stack3_Panel_Dark",
                                          color=(0.085, 0.088, 0.092)),
        "core": materials.make_concrete("Stack3_Core", color=(0.10, 0.11, 0.12)),
        "ground": make_unlit("Stack3_Ground", (0.055, 0.055, 0.058)),
        "plaza": make_unlit("Stack3_Plaza", (0.085, 0.085, 0.082)),
        "lawn": materials.make_wall("Stack3_Lawn", color=(0.11, 0.24, 0.09)),
        "foliage": materials.make_foliage("Stack3_Foliage",
                                          color=(0.075, 0.22, 0.085)),
        "trunk": materials.make_trunk("Stack3_Trunk"),
        "circle": materials.make_wall("Stack3_Circle", color=(0.155, 0.030, 0.024)),
        "glow": materials.make_ceiling_light(
            "Stack3_Glow", (1.0, 0.70, 0.38), 3.2 if not night else 2.0),
        "glow_warm": materials.make_ceiling_light(
            "Stack3_Glow_Warm", (1.0, 0.62, 0.30), 10.0 if not night else 5.0),
        "light_day": materials.make_ceiling_light(
            "Stack3_Light_Daylight", materials.CEILING_LIGHT_DAYLIGHT, 9.0),
        "light_dim": materials.make_ceiling_light(
            "Stack3_Light_Dim", (0.72, 0.82, 0.95), 3.2),
        "light_glow": materials.make_ceiling_light(
            "Stack3_Light_Glow", (1.0, 0.66, 0.38), 2.2),
        "light_warm": materials.make_ceiling_light(
            "Stack3_Light_Warm", (1.0, 0.55, 0.25), 7.5),
        "glow_cool": materials.make_ceiling_light(
            "Stack3_Glow_Cool", (0.66, 0.78, 0.95), glow * 0.8),
    }


# ---------------------------------------------------------------------------
# Site and structure
# ---------------------------------------------------------------------------
def tree(trunks, leaves, x, y, z, height, radius=None):
    """A simple site tree: a tapered trunk and one canopy blob."""
    radius = radius if radius else height * 0.42
    trunks.cyl((x, y, z), (x, y, z + height * 0.62), 0.18, 0.10, 6)
    leaves.sphere((x, y, z + height * 0.78), radius)


def build_site(mats, cols, rng):
    p = Part("Site_Ground", mats["ground"], cols["Site"])
    p.box((0, 0, -0.2), (190, 135, 0.4))
    ground = p.finish()
    p = Part("Site_Plaza", mats["plaza"], cols["Site"])
    p.box((0, 0, 0.03), (136, 62, 0.06))
    plaza = p.finish()
    # The floor must not block or swallow the studio lights.
    for obj in (ground, plaza):
        if obj is not None:
            obj.visible_shadow = False
            obj.visible_diffuse = False

    trunks = Part("Site_Trees_Trunks", mats["trunk"], cols["Site"])
    leaves = Part("Site_Trees", mats["foliage"], cols["Site"])
    for x in range(-48, 49, 12):
        for y in (-30.0, 30.0):
            tree(trunks, leaves, x + rng.uniform(-1.0, 1.0), y,
                 rng.uniform(6.0, 9.0), rng.uniform(2.4, 3.2))
    trunks.finish()
    leaves.finish()


def build_floors(mats, cols):
    p = Part("Structure_Floors", mats["slab_dark"], cols["Structure"])
    for z in floor_levels():
        if z <= ROOF - 0.6:
            p.box((0, 0, z - 0.175), (WIDTH - 4.8, DEPTH - 4.8, 0.35))
    floors = p.finish()
    if floors is not None:
        # Floors neither take light nor block it, so the interior lights carry
        # up and down the whole shaft instead of pooling on one plate.
        floors.visible_shadow = False
        floors.visible_diffuse = False

    # Transfer slabs on the band lines read through the glazed bands as the
    # same thick floor the truss-less bands sit on.
    p = Part("Structure_Transfer_Slabs", mats["slab_dark"], cols["Structure"])
    for name, z0, z1 in BANDS[1:-1]:
        p.box((0, 0, z0 - 0.35), (WIDTH - 0.8, DEPTH - 0.8, 0.7))
    transfers = p.finish()
    if transfers is not None:
        transfers.visible_shadow = False
        transfers.visible_diffuse = False

    p = Part("Structure_Cores", mats["core"], cols["Structure"])
    for sx in (-1, 1):
        p.box((sx * 26.0, 0, ROOF / 2), (16.0, 14.0, ROOF))
    p.finish()


def build_cornices(mats, cols):
    """The horizontal bands that make the stack read as a stack."""
    p = Part("Envelope_Cornices", mats["silver"], cols["Structure"])
    for name, z0, z1 in BANDS[1:]:
        for face in FACES:
            half = face_half(face)
            p.face_box(face, -half, half, z0 - 0.30, z0 + 0.30, -0.55, 0.70)
    p.finish()

    # Crisp metal corner posts, flush with the envelope.
    p = Part("Envelope_Corners", mats["silver"], cols["Structure"])
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.box((sx * (HALF_W - 0.45), sy * (HALF_D - 0.45), ROOF / 2),
                  (1.1, 1.1, ROOF))
    p.finish()


# ---------------------------------------------------------------------------
# Band 1: one big X lattice over the whole lower block
# ---------------------------------------------------------------------------
def build_lattice(mats, cols, rng):
    """The lower 190 m is one facade: a bold external frame three bays wide by
    three tiers tall, with an X brace in every cell and glass behind it.

    This follows the reference tower the client pointed at - three crosses per
    row, three rows - and replaces the earlier glazed base plus diagrid split.
    """
    z0, z1 = BAND["Lattice"]
    col = cols["Lattice"]
    bays, tiers = 6, 5
    inset = 0.62
    tier_h = (z1 - z0) / tiers

    glass = Part("Lattice_Glass", mats["glass_deep"], col)
    for face in FACES:
        half = face_half(face)
        glass.face_box(face, -half, half, z0 + 0.2, z1 - 0.2, -0.75, 0.14)
    glass.finish()

    # The pane frame: 200 mm wide flat bars, one full storey tall between the
    # horizontals, so every pane sits inside a 200 mm border - the flat strip
    # frame the client asked for, after Stack 2.
    mull = Part("Lattice_Mullions", mats["silver"], col)
    for face in FACES:
        half = face_half(face)
        n = max(8, int(round(2 * half / 1.45)))
        step = 2 * half / n
        for i in range(n + 1):
            u = -half + i * step
            mull.face_box(face, u - 0.10, u + 0.10, z0, z1, -0.50, 0.08)
    mull.finish()

    trans = Part("Lattice_Transoms", mats["silver"], col)
    for face in FACES:
        half = face_half(face)
        for z in [z0] + [lev for lev in floor_levels() if z0 < lev <= z1]:
            lo = 0.0 if z <= z0 else z - 0.10
            hi = 0.20 if z <= z0 else z + 0.10
            trans.face_box(face, -half, half, lo, hi, -0.50, 0.08)
    trans.finish()

    # A real curtain wall behind the big frame: narrow vertical panes between
    # thin mullions, with a white spandrel band on every floor - the office
    # glazing in the reference the client sent.
    # The floor line is the slab edge itself - no added white band.
    band = Part("Lattice_Slab_Edges", mats["slate"], col)
    for face in FACES:
        half = face_half(face)
        base_top = z0 + inset + 2 * ((z1 - z0) - 2 * inset) / tiers
        for z in [0.0] + [lev for lev in floor_levels()
                          if lev < base_top - 0.5]:
            lo = 0.0 if z <= 0.0 else z - 0.32
            hi = 0.40 if z <= 0.0 else z + 0.08
            band.face_box(face, -half, half, lo, hi, -0.56, 0.26)
    band.finish()

    frame = Part("Lattice_Frame", mats["silver"], col)
    for face in FACES:
        half = face_half(face)
        hw = half - inset
        n = bays if face in LONG_FACES else 2
        base_top = z0 + inset + 2 * ((z1 - z0) - 2 * inset) / tiers
        for i in range(n + 1):
            u = -hw + i * 2 * hw / n
            top = z1 if i in (0, n) else base_top
            frame.face_box(face, u - inset, u + inset, z0, top, -0.34, 0.60)
    frame.finish()

    brace = Part("Lattice_Braces", mats["silver"], col)
    for face in FACES:
        half = face_half(face)
        hw = half - inset
        n = bays if face in LONG_FACES else 2
        du = 2 * hw / n
        dz = ((z1 - z0) - 2 * inset) / tiers
        for i in range(n):
            for j in range(2, tiers):
                u0 = -hw + i * du
                u1 = u0 + du
                za = z0 + inset + j * dz
                zb = za + dz
                brace.bar(fp(face, u0, za, -0.05), fp(face, u1, zb, -0.05),
                          0.66, 0.95)
                brace.bar(fp(face, u0, zb, -0.05), fp(face, u1, za, -0.05),
                          0.66, 0.95)
    brace.finish()

    # The bottom two tiers carry no X: each cell becomes a big thick-framed
    # square/rectangle of glass, two rows of six, closing the base.
    rails = Part("Lattice_Base_Rails", mats["silver"], col)
    for face in FACES:
        half = face_half(face)
        rail_h = 0.62
        for j in (0, 1, 2):
            z = z0 + inset + j * ((z1 - z0) - 2 * inset) / tiers
            rails.face_box(face, -half, half, z - rail_h, z + rail_h,
                           -0.34, 0.60)
    rails.finish()

    # Warm hall below, cool floors above; one strip per 5 m storey.
    # The same room lights as the apartments: one long strip per room, cool or
    # warm, on every floor - the house language for all interior lighting.
    cool = Part("Lattice_Lights_Cool", mats["light_day"], col)
    warm = Part("Lattice_Lights_Warm", mats["light_warm"], col)
    for face in FACES:
        half = face_half(face)
        hw = half - inset
        n = bays if face in LONG_FACES else 2
        du = 2 * hw / n
        for z in floor_levels():
            if 1.0 < z <= z1:
                for i in range(n):
                    if rng.random() < 0.35:      # dark rooms keep it from
                        continue                 # reading as a line of light
                    u0 = -hw + i * du
                    part = cool if rng.random() < 0.5 else warm
                    for depth in (1.2, 2.8):
                        ceiling_strip(part, face, u0 + 0.8, u0 + du - 0.8,
                                      z - 0.52, depth, rng, frac=(0.22, 0.45))
    cool.finish()
    warm.finish()


# ---------------------------------------------------------------------------
# Bands 3 and 6: planted arcades
# ---------------------------------------------------------------------------
def tree_column(part, face, u, z_base, z_top, rng):
    h = z_top - z_base
    trunk_top = z_base + 0.46 * h
    part.cyl(fp(face, u, z_base, -0.42), fp(face, u, trunk_top, -0.42),
             0.46, 0.30, 8)
    branches = ((-2.2, 0.80), (2.2, 0.80), (-0.9, 0.99),
                (0.9, 0.99), (0.0, 1.02))
    for du, frac in branches:
        p0 = fp(face, u, trunk_top - 0.8, -0.42)
        p1 = fp(face, u + du * rng.uniform(0.9, 1.1),
                z_base + frac * h, -0.42)
        part.cyl(p0, p1, 0.21, 0.09, 6)
        mid = p0.lerp(p1, 0.52)
        p2 = fp(face, u + du * 1.25, z_base + min(1.02, frac + 0.10) * h,
                -0.42)
        part.cyl(mid, p2, 0.09, 0.04, 5)


def build_garden_band(name, mats, cols, tree_pitch, rng):
    """A planted arcade: recessed glazing, a colonnade of branching columns on
    the facade line, planting behind it, and a lit interior wall.

    Every tree, planter and foliage clump is kept inside the envelope: the
    colonnade is inset 3.2 m from each corner and the branch spread is capped, so
    a corner column never throws a bough past the slab edge.
    """
    z0, z1 = BAND[name]
    col = cols[name]
    margin = 3.2

    def spots(face):
        half = face_half(face)
        bays = max(3, int(round((2 * half - 2 * margin) / tree_pitch)))
        step = (2 * half - 2 * margin) / bays
        return [-half + margin + i * step for i in range(bays + 1)]

    glass = Part(f"{name}_Glass", mats["glass_warm"], col)
    for face in FACES:
        half = face_half(face)
        glass.face_box(face, -half, half, z0 + 0.2, z1 - 0.7, -2.5, 0.16)
    glass.finish()

    fascia = Part(f"{name}_Fascia", mats["concrete"], col)
    for face in FACES:
        half = face_half(face)
        fascia.face_box(face, -half, half, z0, z0 + 0.9, -0.50, 0.55)
        fascia.face_box(face, -half, half, z1 - 1.7, z1, -0.50, 0.55)
    fascia.finish()

    trees = Part(f"{name}_Trees", mats["concrete"], col)
    for face in FACES:
        for u in spots(face):
            tree_column(trees, face, u, z0 + 0.35, z1 - 0.9, rng)
    trees.finish()

    planters = Part(f"{name}_Planters", mats["stone"], col)
    for face in FACES:
        long_face = face in LONG_FACES
        for u in spots(face):
            base = fp(face, u, z0, -1.0)
            planters.box((base.x, base.y, z0 + 0.75),
                         (2.4 if long_face else 1.9,
                          1.9 if long_face else 2.4, 1.5))
    planters.finish()

    leaves = Part(f"{name}_Foliage", mats["foliage"], col)
    for face in FACES:
        half = face_half(face)
        for u in spots(face):
            uc = max(-half + 2.4, min(half - 2.4, u + rng.uniform(-0.5, 0.5)))
            for k in range(3):
                p = fp(face, uc, z0 + 4.6 + k * 2.6, -2.4)
                leaves.sphere((p.x, p.y, p.z), rng.uniform(1.9, 2.3))
    leaves.finish()

    hedge = Part(f"{name}_Hedge", mats["foliage"], col)
    for face in FACES:
        half = face_half(face)
        hedge.face_box(face, -half, half, z0 + 0.7, z0 + 2.0, -1.3, 1.2)
    hedge.finish()

    rail = Part(f"{name}_Balustrade", mats["silver"], col)
    for face in FACES:
        half = face_half(face)
        rail.face_box(face, -half, half, z0 + 1.15, z0 + 1.25, -0.02, 0.14)
    rail.finish()

    cool = Part(f"{name}_Light_Cool", mats["light_day"], col)
    warm = Part(f"{name}_Light_Warm", mats["light_warm"], col)
    for face in FACES:
        half = face_half(face)
        n = 4
        du = 2 * half / n
        for z in floor_levels():
            if z0 + 1.0 < z <= z1:
                for i in range(n):
                    u0 = -half + i * du
                    part = cool if rng.random() < 0.5 else warm
                    for depth in (1.4, 3.0):
                        ceiling_strip(part, face, u0 + 0.8, u0 + du - 0.8,
                                      z - 0.52, depth, rng)
    cool.finish()
    warm.finish()


# ---------------------------------------------------------------------------
# Band 4: office fins
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Band 5: hotel diamond lattice
# ---------------------------------------------------------------------------
# Band 7: one-storey masonry blocks in a running bond
# ---------------------------------------------------------------------------
# The top band is not a fine brick texture: every visible block is one 4 m
# storey, laid in a half-bond running course, so the facade reads as staggered
# rooms. Windows are punched inside a block, so no opening ever crosses a joint.
BLOCK_H = 4.0
BLOCK_L = 10.8
BLOCK_JOINT = 0.25


def storey_lights(part, face, half, z, inset=2.0, depths=(1.5,), width=0.50):
    """Continuous ceiling strips across one storey, seen through the glass."""
    span = 2 * half - 2 * inset
    for depth in depths:
        p = fp(face, 0.0, z, -depth)
        if face in LONG_FACES:
            part.box((p.x, p.y, z), (span, width, 0.07))
        else:
            part.box((p.x, p.y, z), (width, span, 0.07))


def ceiling_strip(part, face, u0, u1, z, depth, rng, frac=(0.5, 0.85)):
    """A thin ceiling fixture inside one room, seen through the glazing."""
    length = (u1 - u0) * rng.uniform(*frac)
    cu = (u0 + u1) / 2 + rng.uniform(-0.4, 0.4)
    p = fp(face, cu, z, -depth)
    if face in LONG_FACES:
        part.box((p.x, p.y, z), (length, 0.45, 0.07))
    else:
        part.box((p.x, p.y, z), (0.45, length, 0.07))


def build_apartments(mats, cols, rng):
    """The top band is a semi-transparent glazed skin in a staggered block grid.

    There are no punched windows and no wall behind the glass: every block is one
    4 m storey of glass with a floor slab at its base, and the room interiors are
    read through the panes as scattered ceiling lights - some cool, some warm,
    many switched off - the same device the earlier Stack studies use.
    """
    z0, z1 = BAND["Apartments"]
    col = cols["Apartments"]
    attic = 2.0
    top = z1 - attic
    courses = int(round((top - z0) / BLOCK_H))
    tones = ("pane_a", "pane_b", "pane_c")

    for face in FACES:
        half = face_half(face)
        panes = {t: Part(f"Apartment_Glass_{face}_{t[-1]}", mats[t], col)
                 for t in tones}
        frame = Part(f"Apartment_Frame_{face}", mats["silver"], col)
        cool = Part(f"Apartment_Light_Cool_{face}", mats["light_day"], col)
        warm = Part(f"Apartment_Light_Warm_{face}", mats["light_warm"], col)

        last = None
        for j in range(courses):
            za = z0 + j * BLOCK_H
            zb = za + BLOCK_H
            offset = 0.0 if j % 2 == 0 else BLOCK_L / 2
            a = -half - offset
            while a < half - 0.5:
                b = a + BLOCK_L
                aa, bb = max(a, -half), min(b, half)
                if bb - aa > 1.5:
                    tone = rng.choice([t for t in tones if t != last])
                    last = tone
                    panes[tone].face_box(face, aa + 0.02, bb - 0.02,
                                         za + 0.13, zb - 0.13, -0.12, 0.06)
                    part = cool if rng.random() < 0.45 else warm
                    for depth in (1.2, 2.8):
                        ceiling_strip(part, face, aa + 0.7, bb - 0.7,
                                      zb - 0.52, depth, rng)
                if -half + 0.3 < b < half - 0.3:
                    frame.face_box(face, b - 0.12, b + 0.12,
                                   za + 0.12, zb - 0.12, -0.16, 0.28)
                a = b
            frame.face_box(face, -half, half, zb - 0.12, zb + 0.12,
                           -0.16, 0.28)

        for part in panes.values():
            part.finish()
        frame.finish()
        cool.finish()
        warm.finish()

    # A two-metre metal fascia closes the grid at the roof.
    cap = Part("Apartment_Topband", mats["mesh"], col)
    for face in FACES:
        half = face_half(face)
        cap.face_box(face, -half, half, top, z1, -0.16, 0.28)
    cap.finish()


# ---------------------------------------------------------------------------
# Roof
# ---------------------------------------------------------------------------
def rect_minus(rect, hole):
    """Split rect (x0, x1, y0, y1) around hole into up to four rectangles."""
    x0, x1, y0, y1 = rect
    hx0, hx1, hy0, hy1 = hole
    out = []
    if hx0 > x0:
        out.append((x0, min(hx0, x1), y0, y1))
    if hx1 < x1:
        out.append((max(hx1, x0), x1, y0, y1))
    ix0, ix1 = max(x0, hx0), min(x1, hx1)
    if ix1 > ix0:
        if hy0 > y0:
            out.append((ix0, ix1, y0, min(hy0, y1)))
        if hy1 < y1:
            out.append((ix0, ix1, max(hy1, y0), y1))
    return [r for r in out if r[1] - r[0] > 0.2 and r[3] - r[2] > 0.2]


def build_roof(mats, cols):
    """A completely flat roof: one deck slab and a parapet, nothing above it."""
    col = cols["Roof"]
    deck = Part("Roof_Deck", mats["stone"], col)
    deck.box((0, 0, ROOF + 0.20), (WIDTH, DEPTH, 0.40))
    deck.finish()

    parapet = Part("Roof_Parapet", mats["silver"], col)
    for face in FACES:
        half = face_half(face)
        parapet.face_box(face, -half, half, ROOF + 0.40,
                         ROOF + 0.40 + PARAPET_H, -0.55, 0.55)
    parapet.finish()


# ---------------------------------------------------------------------------
# Interior glow behind the glazed bands
# ---------------------------------------------------------------------------
# Cameras, lighting, render
# ---------------------------------------------------------------------------
def _basis(direction):
    d = Vector(direction).normalized()
    fwd = -d
    up = Vector((0, 0, 1))
    if abs(fwd.dot(up)) > 0.995:
        up = Vector((0, 1, 0))
    z = -fwd
    y = (up - z * up.dot(z)).normalized()
    x = y.cross(z).normalized()
    return d, fwd, x, y, z


def _bbox_points():
    return [Vector((x, y, z)) for x in (-HALF_W, HALF_W)
            for y in (-HALF_D, HALF_D) for z in (0.0, HEIGHT)]


def fit_distance(direction, target, lens, res, margin=1.14):
    """Projection-driven camera fit: solve distance so the bbox fills the frame.

    Never estimate this from the AABB extents: at a 3/4 view the projected
    range has nothing to do with dx, dy and dz.
    """
    d, fwd, x, y, z = _basis(direction)
    tan_h = 18.0 / lens
    tan_v = tan_h * res[1] / float(res[0])
    wanted = 1.0 / margin
    dist = 900.0
    pts = _bbox_points()
    target = Vector(target)
    for _ in range(80):
        cam = target + d * dist
        k = 0.0
        for p in pts:
            v = p - cam
            dep = max(v.dot(fwd), 1e-3)
            k = max(k, abs(v.dot(x)) / (dep * tan_h),
                    abs(v.dot(y)) / (dep * tan_v))
        dist *= (k / wanted) ** 0.9
    return dist


def make_camera(name, location, target, lens, ortho_scale=None, res=(900, 1200)):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.clip_start, data.clip_end = 4.0, 4000.0
    if ortho_scale:
        data.type = "ORTHO"
        data.ortho_scale = ortho_scale
        data.sensor_fit = "VERTICAL"
    else:
        # 36 mm across the image width, so the fit maths and the render agree
        # on a portrait frame (AUTO would fit the 36 mm to the long edge).
        data.sensor_fit = "HORIZONTAL"
    cam = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = location
    cam.rotation_euler = (Vector(target) - Vector(location)).to_track_quat(
        "-Z", "Y").to_euler()
    return cam


def ndc_worst(cam, res):
    bpy.context.view_layer.update()
    mw = cam.matrix_world
    origin = mw.translation
    x = mw.col[0].to_3d().normalized()
    y = mw.col[1].to_3d().normalized()
    fwd = -mw.col[2].to_3d().normalized()
    if cam.data.type == "ORTHO":
        w = cam.data.ortho_scale
        if res[1] >= res[0]:
            half_y, half_x = w / 2.0, w / 2.0 * res[0] / res[1]
        else:
            half_x, half_y = w / 2.0, w / 2.0 * res[1] / res[0]
        worst = 0.0
        for p in _bbox_points():
            v = p - origin
            worst = max(worst, abs(v.dot(x)) / half_x, abs(v.dot(y)) / half_y)
        return worst
    tan_h = 18.0 / cam.data.lens
    tan_v = tan_h * res[1] / float(res[0])
    worst = 0.0
    for p in _bbox_points():
        v = p - origin
        dep = max(v.dot(fwd), 1e-3)
        worst = max(worst, abs(v.dot(x)) / (dep * tan_h),
                    abs(v.dot(y)) / (dep * tan_v))
    return worst


def setup_scene(args):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    try:
        scene.eevee.taa_render_samples = args.samples
        scene.eevee.use_raytracing = True
    except AttributeError:
        pass
    scene.render.resolution_x, scene.render.resolution_y = 900, 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.look = "AgX - High Contrast"
    scene.render.film_transparent = False

    # A dusk sky: the published model photography is shot against a dark
    # ground, and a dark sky is also what makes the glazing read as glass
    # rather than as a mirror of a bright overcast dome.
    world = bpy.data.worlds.new("Stack3_Dusk")
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    bg.inputs["Color"].default_value = (0.040, 0.048, 0.062, 1.0)
    bg.inputs["Strength"].default_value = 1.1
    scene.world = world

    # Studio lighting: five big area lights around the tower plus one low fill.
    # The brief is a model shot - the whole elevation lit, no single hard sun.
    studio = (
        ("Key_W",   (-390, -410, 300), (0, 0, 185), 120, 3200000,
         (1.00, 0.96, 0.90)),
        ("Fill_E",  (420, -350, 165), (0, 0, 150), 130, 2400000,
         (0.92, 0.96, 1.00)),
        ("Back_N",  (-90, 440, 300), (0, 0, 220), 140, 2500000,
         (0.95, 0.97, 1.00)),
        ("Side_E",  (470, 160, 360), (0, 0, 240), 110, 2000000,
         (1.00, 0.98, 0.95)),
        ("Top",     (40, -80, 680), (0, 0, 310), 150, 2200000,
         (1.00, 1.00, 1.00)),
        ("Low_Fill", (-430, -150, 45), (0, 0, 95), 90, 1000000,
         (1.00, 0.95, 0.88)),
    )
    # Simulated interior lighting: a few dozen point lights scattered through
    # the volume stand in for the thousands of fixtures, at random plan
    # positions and heights, so the tower reads like a real building at night
    # rather than a lit column.
    rng_lights = random.Random(20261020)
    for i in range(48):
        z = rng_lights.uniform(6.0, ROOF - 8.0)
        x = rng_lights.uniform(-46.0, 46.0)
        y = rng_lights.uniform(-14.0, 14.0)
        data = bpy.data.lights.new(f"Stack3_Interior_{i:02d}", "POINT")
        data.energy = rng_lights.uniform(35000.0, 95000.0)
        data.shadow_soft_size = rng_lights.uniform(3.5, 7.0)
        data.use_shadow = False       # glow only; keeps EEVEE's shadow budget
        data.color = ((1.0, 0.80, 0.58) if rng_lights.random() < 0.55
                      else (0.88, 0.93, 1.0))
        obj = bpy.data.objects.new(f"Stack3_Interior_{i:02d}", data)
        obj.location = (x, y, z)
        scene.collection.objects.link(obj)

    for name, loc, target, size, energy, color in studio:
        data = bpy.data.lights.new(f"Stack3_{name}", "AREA")
        data.shape = "DISK"
        data.size = size
        data.energy = energy
        data.color = color
        # A mirror-smooth curtain wall turns each studio light into a hard disc
        # on the glass; the studio rig lights the building only.
        data.specular_factor = 0.0
        obj = bpy.data.objects.new(f"Stack3_{name}", data)
        obj.location = loc
        obj.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat(
            "-Z", "Y").to_euler()
        scene.collection.objects.link(obj)

    cams = {}
    # Preview: the published model shot, a mild upward 3/4 from the south-east.
    res = (900, 1200)
    direction = (0.62, -1.0, -0.11)
    target = (0, 0, 176.0)
    dist = fit_distance(direction, target, 55.0, res, margin=1.06)
    d = Vector(direction).normalized()
    cams["preview"] = make_camera("Stack3_Cam_preview", Vector(target) + d * dist,
                                  target, 55.0, res=res)

    cams["elevation"] = make_camera(
        "Stack3_Cam_elevation", (0, -700, HEIGHT / 2), (0, 0, HEIGHT / 2),
        55.0, ortho_scale=HEIGHT * 1.06, res=(640, 1200))

    direction = (1.0, -0.5, -0.06)
    target = (0, 0, 176.0)
    dist = fit_distance(direction, target, 55.0, res, margin=1.06)
    d = Vector(direction).normalized()
    cams["side"] = make_camera("Stack3_Cam_side", Vector(target) + d * dist,
                               target, 55.0, res=res)

    cams["base"] = make_camera("Stack3_Cam_base", (-104, -138, 5.0), (0, 0, 46.0),
                               32.0, res=(1200, 900))
    cams["detail"] = make_camera("Stack3_Cam_detail", (72, -168, 250.0),
                                 (4, 0, 278.0), 90.0, res=(1200, 900))

    scene.camera = cams["preview"]
    return cams


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def set_saved_view(target=(0.0, 0.0, 185.0), direction=(0.62, -1.0, 0.03),
                   distance=200.0):
    """Bake a default 3D view into the .blend, outside the building.

    A headless build has no window, but the screen/area datablocks still exist,
    and their region_3d values are saved with the file, so the view survives
    reopening it in the GUI.
    """
    d = Vector(direction).normalized()
    pivot = Vector(target)
    eye = pivot + d * distance
    rotation = (pivot - eye).to_track_quat("-Z", "Y")
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type != "VIEW_3D" or space.region_3d is None:
                    continue
                r3 = space.region_3d
                r3.view_perspective = "PERSP"
                r3.view_location = pivot
                r3.view_distance = distance
                r3.view_rotation = rotation
                # Do not touch the viewport lens: the saved view keeps the
                # user's normal lens so nothing is distorted.
                space.shading.type = "MATERIAL"
                # Material Preview uses Blender's bundled studio HDRIs; the
                # third world sphere is forest.exr, the house default.
                space.shading.use_scene_world = False
                space.shading.studio_light = "forest.exr"
                space.shading.use_scene_lights = True
                space.clip_end = 4000.0


def build(args):
    random.seed(20261019)
    rng = random.Random(20261019)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    root = bpy.data.collections.new("STACK3")
    scene.collection.children.link(root)
    names = ("Site", "Structure", "Lattice", "Plaza", "Apartments",
             "Roof", "Lighting")
    cols = {name: sub_collection(root, "STACK3_" + name) for name in names}

    mats = build_materials(args.night)

    build_site(mats, cols, rng)
    build_floors(mats, cols)
    build_cornices(mats, cols)
    build_lattice(mats, cols, rng)
    build_garden_band("Plaza", mats, cols, 11.8, rng)
    build_apartments(mats, cols, rng)
    build_roof(mats, cols)

    cams = setup_scene(args)

    scene["design"] = "MVRDV The Stack (competition proposal)"
    scene["reference_urls"] = ("https://mvrdv.com/projects/340/the-stack; "
                               "?photo=16062; ?photo=16063; ?photo=16064")
    scene["model_width_m"] = WIDTH
    scene["model_depth_m"] = DEPTH
    scene["model_height_m"] = ROOF
    scene["parapet_top_m"] = HEIGHT
    scene["envelope_note"] = (
        "Client direction: a little over 100 m wide, 36 m deep, originally "
        "about 350 m tall. The stepped crown was dropped at the client's "
        "request, so the roof is flat at 334 m and the tower is 335.6 m to the "
        "parapet.")
    scene["bands"] = ", ".join(f"{n} {z0:g}-{z1:g}" for n, z0, z1 in BANDS)
    scene["band_count"] = len(BANDS)
    scene["band_order"] = "lattice, plaza, apartments"
    scene["storey_height_m"] = STOREY
    scene["facade_module_m"] = (f"mullion {BAY}; lower block 3 x 3 X-braced "
                                f"cells over 0-190 m")
    scene["apartment_module_m"] = (f"{BLOCK_L:g} x {BLOCK_H:g} glazed bay, "
                                   f"half-bond offset")
    scene["apartment_reading"] = ("each bay is one 4 m storey of semi-transparent "
                                  "glazing; the staggered frame draws the window "
                                  "pattern, no punched openings, and the rooms "
                                  "read through scattered ceiling lights")
    scene["structural_scheme"] = (
        "Shallow slab, two long-axis service cores, four-storey transfer "
        "slabs on every band line, facade carried by per-band systems.")
    scene["approximation_note"] = (
        "Competition proposal; dimensions, band order and facade treatments "
        "inferred from MVRDV elevation, section and model imagery. Not a "
        "measured survey; interior cores are schematic.")
    scene["reference_photo_bands"] = (
        "elevation reads: glass base with X bracing, black band with round "
        "openings, planted arcade, fin band, diamond lattice, planted arcade, "
        "one-storey masonry blocks in a running bond, flat roof")
    scene["render_engine"] = "EEVEE"
    scene["camera_note"] = "preview 3/4 from the south-east, mild upward tilt"
    scene["roof"] = ("completely flat: one deck slab at 334 m, parapet to "
                     "335.6 m, nothing above the apartment band")
    scene["facade_relief_m"] = 0.24
    scene["facade_relief_note"] = (
        "Deepest projection past the 108 x 36 m slab edge; every fin, lattice "
        "bar, brace and tree sits inside this relief band.")
    scene["lighting"] = ("dusk sky, low sun, warm interior bands; the model "
                         "photography in the MVRDV gallery is shot on a dark "
                         "ground, and the dark sky keeps the glass dark")

    # The saved viewport view: outside the slab, about 200 m out, so opening
    # the file never starts inside the building. Set on every screen so the
    # next workspace switch keeps the same vantage.
    set_saved_view()

    os.makedirs(OUT_DIR, exist_ok=True)
    for name, cam in cams.items():
        scene.camera = cam
        if name in ("base", "detail"):
            print(f"CAMERA {name}: close-up, whole-building NDC not applicable")
            continue
        res = (900, 1200) if name == "preview" else (640, 1200) if name == "elevation" else (900, 1200)
        print(f"CAMERA {name}: worst NDC {ndc_worst(cam, res):.3f}")

    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)

    if not args.no_render:
        suffix = "_night" if args.night else ""
        for view in args.views:
            scene.camera = cams[view]
            if view in ("preview", "side", "elevation"):
                scene.render.resolution_x, scene.render.resolution_y = 900, 1200
            else:
                scene.render.resolution_x, scene.render.resolution_y = 1200, 900
            scene.render.filepath = os.path.join(
                OUT_DIR, f"the_stack3_{view}{suffix}.png")
            bpy.ops.render.render(write_still=True)

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    tris = sum(len(o.data.polygons) for o in meshes)
    xs, ys, zs = [], [], []
    for o in meshes:
        for corner in o.bound_box:
            v = o.matrix_world @ Vector(corner)
            xs.append(v.x)
            ys.append(v.y)
            zs.append(v.z)
    print(f"OBJECTS {len(bpy.data.objects)}  MESHES {len(meshes)}  FACES {tris}")
    print(f"BBOX x {min(xs):.2f}..{max(xs):.2f}  y {min(ys):.2f}..{max(ys):.2f}"
          f"  z {min(zs):.2f}..{max(zs):.2f}")
    print(f"Saved editable model: {BLEND_PATH}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("--night", action="store_true")
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--views", nargs="+", default=list(VIEW_NAMES))
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    build(args)


if __name__ == "__main__":
    main()
