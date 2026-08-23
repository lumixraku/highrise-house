"""Materials for the high-rise house.

Kept separate from build_house.py so the look can be tuned without touching
geometry. Two engines are supported and they need different glass:

* Cycles — real refraction. Transmission on a thin solid pane, low roughness,
  and a neutral base colour. This is the one that looks like glass.
* EEVEE  — no true refraction unless raytracing is on. Uses transmission plus a
  raised specular so the pane still reads as glazing.

The default is neutral clear glass: the IOR supplies the physical reflection,
while the interior lining and ceiling fixtures provide visible depth behind the
pane. A legacy green tint remains available as an explicit override.
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
# Architectural glass tint: a PALE, slightly COOL green.
#
# Getting here took three wrong turns, and the lesson each time was that one
# number cannot describe a colour. Watch TWO measurements on the rendered panes:
#   green bias = G - (R+B)/2   how green
#   warm bias  = R - B         green vs yellow-green vs cyan
#
#   (0.88, 0.965, 0.92)  green +0.010  warm -0.008   too weak: reads blue-grey,
#                                                    since B (0.456) beat G (0.448)
#   (0.88, 0.965, 0.70)  green +0.025  warm +0.012   YELLOW-green: red high plus
#                                                    blue low IS yellow, and a weak
#                                                    green bias cannot mask it
#   (0.74, 0.965, 0.86)  green +0.026  warm -0.056   cyan: B caught up with G
#   (0.72, 0.965, 0.76)  green +0.035  warm -0.039   <- this. G clearly leads both,
#                                                    R stays under B, no yellow
#
# So all three channels matter: G highest by a clear margin, R lowest, B in
# between. Only what passes THROUGH the pane is tinted — the sky reflection is
# not, and it is blue and carries most of the brightness — which is why the tint
# has to fight the sky rather than just be "a light green".
#
# To adjust: raise all three together for paler; lower red for greener; if it
# looks yellow raise blue, if it looks cyan lower blue.
GLASS_GREEN = (0.720, 0.965, 0.760)
# Neutral clear architectural glazing. With a white base colour, the visible
# reflection comes from the physical IOR rather than a colour cast.
GLASS_CLEAR = (1.000, 1.000, 1.000)
# Lit floors, seen through the glazing. Deliberately NEUTRAL-to-cool: the lining
# is bright and clearly visible through clear glass, so a warm grey here tints
# every pane yellow on its own — it was half of why the windows read as olive.
INTERIOR_LINING = (0.630, 0.650, 0.655)
# Small warm-white ceiling fixtures. They are deliberately warmer and brighter
# than the neutral interior lining so occupied rooms read through the glazing.
CEILING_LIGHT = (1.000, 0.550, 0.250)
MULLION_METAL = (0.155, 0.160, 0.165)   # dark anodised
GROUND_GREY = (0.115, 0.120, 0.110)
# Sky-garden planting. Foliage is much darker than it looks to the eye — a leaf
# reflects roughly 15-20% in green and far less in red and blue, so a bright
# green here renders as plastic turf.
PLANT_GREEN = (0.070, 0.185, 0.058)
PLANT_TRUNK = (0.085, 0.062, 0.044)


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


def make_foliage(name="Foliage", color=PLANT_GREEN):
    """Planting in the sky garden.

    Matte and dark. Real foliage is far darker than intuition suggests, and a
    little translucency matters at this scale: leaves are backlit against an open
    void, which is what stops a planter reading as a solid green block.
    """
    mat = _new(name)
    b = _bsdf(mat)
    _set(b, "Base Color", (*color, 1.0))
    _set(b, "Roughness", 0.68)
    _set(b, "Specular IOR Level", 0.22)
    # Thin, backlit leaves pass some light through.
    _set(b, "Transmission Weight", 0.12)
    _set(b, "IOR", 1.42)
    return mat


def make_trunk(name="Trunk", color=PLANT_TRUNK):
    mat = _new(name)
    b = _bsdf(mat)
    _set(b, "Base Color", (*color, 1.0))
    _set(b, "Roughness", 0.86)
    _set(b, "Specular IOR Level", 0.15)
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

def make_glass(name="Glass", engine="CYCLES", tint=GLASS_CLEAR):
    """Neutral clear architectural glazing — smooth, fully transmissive.

    Everything here is aimed at ONE thing: no frosted look. Three separate
    settings can each make glass read as ground/etched glass, and the earlier
    version had all three:

    * Transmission below 1.0. The leftover weight is a *diffuse* lobe using the
      base colour, and a diffuse lobe on a window IS frosted glass. Anything
      under ~0.98 shows it. Held at 1.0.
    * Roughness above ~0.01. Real architectural glass is float glass, optically
      flat; 0.02 already scatters visibly at 100 m. Held at 0.0.
    * Emission. A glow is uniform across the pane, so it flattens out the
      reflections and reads as a milky film. Removed — the interior lining
      (make_interior) supplies the brightness instead, and it does so with
      depth, since it sits behind the glass rather than on it.

    Also note Cycles' Filter Glossy: it deliberately blurs glossy/refractive
    rays to cut noise, and at 1.0 it frosts the panes on its own. build_house.py
    keeps it at 0.

    Thin-walled stays OFF: the panes have real thickness (GLASS_T) and should
    refract through both faces.

    EEVEE: transmission there is a screen-space approximation, so raytraced
    refraction is requested where available.
    """
    mat = _new(name)
    b = _bsdf(mat)

    _set(b, "Base Color", (*tint, 1.0))
    _set(b, "Metallic", 0.0)
    _set(b, "IOR", 1.52)                    # soda-lime float glass
    # Keep the material fully opaque at the shader level. In Cycles, physical
    # transparency comes from transmission; lowering Alpha creates a cutout-like
    # mix that weakens reflection and makes the facade look frosted.
    _set(b, "Alpha", 1.0)

    if engine == "CYCLES":
        _set(b, "Transmission Weight", 1.0)
        _set(b, "Roughness", 0.0)
        # Neutral: at 0.5 the reflection strength comes purely from the IOR
        # above. Pushing it higher adds non-physical mirror on top, which reads
        # as a hard reflective skin rather than something you can see through.
        _set(b, "Specular IOR Level", 0.5)
        _set(b, "Emission Strength", 0.0)
        # Blender 5.x has no separate transmission-colour socket: Base Color
        # tints both the reflection and what passes through, once per surface
        # crossing. A pane is two surfaces, and looking through the building
        # crosses two panes — so the tint is applied up to four times and must
        # stay close to white. This is what made the old 0.56 red render at
        # 0.56**4 = 0.10, i.e. the "black glass" that the partial transmission
        # was working around.
    else:
        _set(b, "Transmission Weight", 1.0)
        _set(b, "Roughness", 0.0)
        _set(b, "Specular IOR Level", 0.5)
        mat.blend_method = "BLEND"
        mat.use_backface_culling = False
        if hasattr(mat, "use_screen_refraction"):
            mat.use_screen_refraction = True
        if hasattr(mat, "use_raytrace_refraction"):
            mat.use_raytrace_refraction = True

    return mat


def make_interior(name="Interior", color=INTERIOR_LINING):
    """What you see THROUGH the glass.

    Clear glass over an empty tower shows whatever is behind it — which, at
    window height, is the far facade and then the sky, so the panes lose all
    depth. A lining set back from the glazing gives the light something to land
    on: it reads as lit floors, and because it sits behind the pane it moves
    against the sky reflection as the view changes, which is exactly the cue
    that says "glass" rather than "tinted panel".

    Matte, and slightly darker than the facade so the glazing still registers as
    an opening.

    Brightness here is what "transparent" actually looks like. Glass reads as see-
    through only if there is something legible on the far side; where the lining
    falls dark the pane goes opaque and heavy no matter how clear the material is.
    Measured share of glass pixels below 0.25 luminance as the lining was lifted:

        (0.52,0.50,0.47) emit 0.35   3.6% dark   luminance 0.438
        (0.66,0.65,0.62) emit 0.75   0.8% dark   luminance 0.542   <- brightness
        (0.70,0.69,0.67) emit 1.00   0.5% dark   luminance 0.582

    Its COLOUR matters as much as its brightness, for the same reason: at this
    brightness the lining is plainly visible through the glass, so its cast lands
    on every pane. The warm greys above pulled the glazing toward olive. Kept
    neutral-to-cool so it remains legible through neutral clear glass.

    Stopping at 0.75 is deliberate: past it the emission starts to overpower the
    sky reflection (local contrast climbed 0.079 -> 0.088), and the pane drifts
    from "glass with lit rooms behind it" toward "glowing panel".
    """
    mat = _new(name)
    b = _bsdf(mat)
    _set(b, "Base Color", (*color, 1.0))
    _set(b, "Roughness", 0.80)
    _set(b, "Specular IOR Level", 0.15)
    # Self-illumination stands in for lit floors — on the lining, well behind the
    # glass, so it never flattens the pane the way emission on the glass did.
    _set(b, "Emission Color", (*color, 1.0))
    _set(b, "Emission Strength", 0.75)
    return mat


def make_ceiling_light(name="CeilingLight", color=CEILING_LIGHT):
    """Warm emissive panels mounted just inside the top of each window bay."""
    mat = _new(name)
    b = _bsdf(mat)
    _set(b, "Base Color", (*color, 1.0))
    _set(b, "Roughness", 0.25)
    _set(b, "Specular IOR Level", 0.1)
    _set(b, "Emission Color", (*color, 1.0))
    _set(b, "Emission Strength", 6.0)
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

def build_all(engine="CYCLES", wall_color=WARM_STONE, glass_tint=GLASS_CLEAR):
    """Returns the dict of materials build_house.py expects."""
    return {
        "concrete": make_concrete(),
        "spandrel": make_wall(color=wall_color),
        "glass": make_glass(engine=engine, tint=glass_tint),
        "interior": make_interior(),
        "ceiling_light": make_ceiling_light(),
        "foliage": make_foliage(),
        "trunk": make_trunk(),
        "metal": make_metal(),
        "dark": make_dark(),
        "ground": make_ground(),
    }
