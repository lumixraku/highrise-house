"""Materials for the high-rise house.

Kept separate from build_house.py so the look can be tuned without touching
geometry. Two engines are supported and they need different glass:

* Cycles — real refraction. Transmission on a thin solid pane, low roughness,
  a faint green tint. This is the one that looks like glass.
* EEVEE  — no true refraction unless raytracing is on. Uses transmission plus a
  raised specular so the pane still reads as glazing.

The tint is applied to BOTH base colour and transmission so the green shows in
reflection as well as through the pane; glass that is only tinted in
transmission reads grey when you see it against a bright sky.
"""

import bpy

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
# Linear RGB. sRGB values were converted with c/12.92 for c <= 0.04045 else
# ((c + 0.055) / 1.055) ** 2.4 — putting sRGB numbers straight into a Blender
# colour socket gives a washed-out result.

WARM_STONE = (0.635, 0.590, 0.500)      # pale sand / beige, the default wall
COOL_STONE = (0.610, 0.615, 0.600)      # pale grey alternative
CONCRETE_GREY = (0.430, 0.430, 0.415)   # structure, slightly darker
# Architectural glass tint. Kept bright — a dark base colour on a transmissive
# pane reads as a smoked panel, not glazing. The green has to be clearly above
# red and blue to survive the sky's blue reflection.
GLASS_GREEN = (0.560, 0.880, 0.700)
MULLION_METAL = (0.155, 0.160, 0.165)   # dark anodised
GROUND_GREY = (0.115, 0.120, 0.110)


def _bsdf(mat):
    return mat.node_tree.nodes["Principled BSDF"]


def _set(bsdf, name, value):
    """Set a socket if this Blender version has it, ignore it otherwise."""
    if name in bsdf.inputs:
        bsdf.inputs[name].default_value = value
        return True
    return False


def _new(name):
    mat = bpy.data.materials.get(name)
    if mat:
        bpy.data.materials.remove(mat)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    return mat


# ---------------------------------------------------------------------------
# Opaque surfaces
# ---------------------------------------------------------------------------

def make_wall(name="Spandrel", color=WARM_STONE):
    """Matte architectural stone/render. No sheen — walls should not compete
    with the glass for highlights."""
    mat = _new(name)
    b = _bsdf(mat)
    _set(b, "Base Color", (*color, 1.0))
    _set(b, "Roughness", 0.72)
    _set(b, "Metallic", 0.0)
    # A trace of sheen keeps large flat walls from looking like paper.
    _set(b, "Specular IOR Level", 0.28)
    return mat


def make_concrete(name="Concrete", color=CONCRETE_GREY):
    mat = _new(name)
    b = _bsdf(mat)
    _set(b, "Base Color", (*color, 1.0))
    _set(b, "Roughness", 0.85)
    _set(b, "Specular IOR Level", 0.2)
    return mat


def make_metal(name="LouvreMetal", color=MULLION_METAL):
    """Dark anodised aluminium for louvres and mullion caps. Not mirror-smooth:
    brushed metal reads better at this scale."""
    mat = _new(name)
    b = _bsdf(mat)
    _set(b, "Base Color", (*color, 1.0))
    _set(b, "Metallic", 0.85)
    _set(b, "Roughness", 0.38)
    return mat


def make_dark(name="Shadowbox", color=(0.012, 0.013, 0.014)):
    mat = _new(name)
    b = _bsdf(mat)
    _set(b, "Base Color", (*color, 1.0))
    _set(b, "Roughness", 0.92)
    _set(b, "Specular IOR Level", 0.1)
    return mat


def make_ground(name="Ground", color=GROUND_GREY):
    mat = _new(name)
    b = _bsdf(mat)
    _set(b, "Base Color", (*color, 1.0))
    _set(b, "Roughness", 0.88)
    return mat


# ---------------------------------------------------------------------------
# Glass
# ---------------------------------------------------------------------------

def make_glass(name="Glass", engine="CYCLES", tint=GLASS_GREEN):
    """Tinted architectural glazing.

    Cycles: transmission 1.0 with IOR 1.52 (soda-lime glass) and roughness 0.02
    — not 0.0, since a dead-flat pane reflects the sky as a hard mirror and reads
    as plastic. Thin-walled is left OFF because the panes are modelled with real
    thickness (GLASS_T), so light should refract through both faces.

    EEVEE: same tint, but transmission there is a screen-space approximation.
    Raised specular compensates so the pane still reflects the sky.
    """
    mat = _new(name)
    b = _bsdf(mat)

    _set(b, "Base Color", (*tint, 1.0))
    _set(b, "Metallic", 0.0)
    _set(b, "IOR", 1.52)

    if engine == "CYCLES":
        # Partial transmission, not 1.0. A fully transmissive pane over an unlit
        # interior renders near-black (measured 0.10 against a 0.59 wall), which
        # reads as a smoked panel. Holding some of the weight back leaves a
        # reflective sky component, which is what makes real curtain wall bright.
        _set(b, "Transmission Weight", 0.75)
        _set(b, "Roughness", 0.02)
        # In Blender 5.x the Principled BSDF has no separate transmission colour
        # socket: Base Color tints both the reflection and what passes through.
        # Raising the specular level strengthens the sky reflection further.
        _set(b, "Specular IOR Level", 0.75)
        # A faint glow stands in for lit floors behind the glass, so the panes
        # never fall to pure black in shadow.
        _set(b, "Emission Color", (*tint, 1.0))
        _set(b, "Emission Strength", 0.06)
    else:
        _set(b, "Transmission Weight", 0.92)
        _set(b, "Roughness", 0.04)
        _set(b, "Specular IOR Level", 0.6)
        mat.blend_method = "BLEND"
        mat.use_backface_culling = False
        if hasattr(mat, "use_screen_refraction"):
            mat.use_screen_refraction = True
        if hasattr(mat, "use_raytrace_refraction"):
            mat.use_raytrace_refraction = True

    return mat


def make_glass_variant(name, engine, tint, roughness=None):
    """A glass with a different tint — for trying alternatives side by side."""
    mat = make_glass(name=name, engine=engine, tint=tint)
    if roughness is not None:
        _set(_bsdf(mat), "Roughness", roughness)
    return mat


# ---------------------------------------------------------------------------
# Environment — glass needs something to reflect
# ---------------------------------------------------------------------------

# Sun position, defined ONCE so the sky texture and the sun lamp agree.
# All cameras sit at +X / -Y and look at the south and east facades, so the sun
# has to come from the south-east or those faces render in shade.
SUN_ELEV_DEG = 46.0      # sun lamp X rotation
SUN_AZIM_DEG = 38.0      # sun lamp Z rotation
# Measured, not guessed: a sun at (46, 0, 38) emits along (-0.44, +0.57, -0.69),
# so the light ARRIVES FROM (+0.44, -0.57, +0.69) — the south-east, which is
# where every camera stands. (The previous -120 deg put it at (-0.62, +0.36),
# the north-west, leaving every visible facade in shade.)
SKY_SUN_ELEVATION = 0.80     # radians, for the Sky texture (~46 deg)
SKY_SUN_ROTATION = 0.66      # radians, matching the azimuth above


def make_sky_world(name="Sky", strength=1.0):
    """A physical sky as the world background.

    This matters more than any glass parameter: a pane in an empty world has
    nothing to reflect and always looks flat. The Sky Texture gives a gradient
    plus a sun disc for the glass to pick up.
    """
    world = bpy.data.worlds.get(name)
    if world:
        bpy.data.worlds.remove(world)
    world = bpy.data.worlds.new(name)
    world.use_nodes = True

    nt = world.node_tree
    nt.nodes.clear()
    bg = nt.nodes.new("ShaderNodeBackground")
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg.inputs["Strength"].default_value = strength

    try:
        sky = nt.nodes.new("ShaderNodeTexSky")
        sky.sky_type = "NISHITA"
        sky.sun_elevation = SKY_SUN_ELEVATION
        sky.sun_rotation = SKY_SUN_ROTATION
        sky.altitude = 60.0             # a tower sees a slightly paler horizon
        if hasattr(sky, "sun_intensity"):
            sky.sun_intensity = 0.6     # keep the disc from blowing out glass

        # A raw Nishita sky is intensely blue, and a matte wall integrates that
        # blue over the whole hemisphere: measured, it drags the warm beige from
        # r-b = +0.08 to -0.16, i.e. the wall renders cold regardless of its own
        # colour. Desaturating the skylight and nudging it warm keeps the sky
        # readable in the glass reflections while letting the surfaces show their
        # actual colour.
        hsv = nt.nodes.new("ShaderNodeHueSaturation")
        hsv.inputs["Saturation"].default_value = 0.28
        hsv.inputs["Value"].default_value = 1.0
        nt.links.new(sky.outputs["Color"], hsv.inputs["Color"])

        warm = nt.nodes.new("ShaderNodeMixRGB")
        warm.blend_type = "MIX"
        warm.inputs["Fac"].default_value = 0.35
        warm.inputs["Color2"].default_value = (1.0, 0.92, 0.80, 1.0)
        nt.links.new(hsv.outputs["Color"], warm.inputs["Color1"])
        nt.links.new(warm.outputs["Color"], bg.inputs["Color"])
    except Exception:
        # Fall back to a flat, already-muted sky colour.
        bg.inputs["Color"].default_value = (0.42, 0.48, 0.58, 1.0)

    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return world


# ---------------------------------------------------------------------------
# One call to build the whole set
# ---------------------------------------------------------------------------

def build_all(engine="CYCLES", wall_color=WARM_STONE, glass_tint=GLASS_GREEN):
    """Returns the dict of materials build_house.py expects."""
    return {
        "concrete": make_concrete(),
        "spandrel": make_wall(color=wall_color),
        "glass": make_glass(engine=engine, tint=glass_tint),
        "metal": make_metal(),
        "dark": make_dark(),
        "ground": make_ground(),
    }
