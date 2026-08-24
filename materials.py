"""Materials for the high-rise house.

Kept separate from build_house.py so the look can be tuned without touching
geometry. Two engines are supported and they need different glass:

* Cycles — real refraction. Transmission on a thin solid pane, low roughness,
  and a neutral base colour. This is the one that looks like glass.
* EEVEE  — Fresnel-blended preview glass. It does not need ray tracing, keeps
  the discrete room fixtures visible, and retains an environment reflection.

The default is neutral clear glass: the IOR supplies the physical reflection,
while discrete ceiling fixtures make occupied rooms visible behind the pane. A
legacy green tint remains available as an explicit override.
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
# Ceiling fixture temperatures. The values are intentionally distinct under AgX:
# daylight is cool white and warm is domestic tungsten-white, not amber signage.
CEILING_LIGHT_DAYLIGHT = (0.600, 0.780, 1.000)
CEILING_LIGHT_WARM = (1.000, 0.420, 0.150)
CEILING_LIGHT_STRENGTH = 100.0
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
      reflections and reads as a milky film. Occupied rooms instead use discrete
      ceiling fixtures at varied depths behind the glass.

    Also note Cycles' Filter Glossy: it deliberately blurs glossy/refractive
    rays to cut noise, and at 1.0 it frosts the panes on its own. build_house.py
    keeps it at 0.

    Thin-walled stays OFF: the panes have real thickness (GLASS_T) and should
    refract through both faces.

    EEVEE: mix a transparent surface with an opaque reflection lobe by Fresnel.
    The blend keeps rooms legible straight on, while reflecting the environment
    more strongly at a shallow angle. Drawing only the front surface prevents
    the pane's real thickness from being composited twice in Material Preview.
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
        output = mat.node_tree.nodes.get("Material Output")
        # The stored Principled node above remains the physical glass definition.
        # EEVEE's real-time view uses this dedicated reflection lobe instead:
        # alpha blending is what lets a non-ray-traced viewport see the fixtures,
        # and Fresnel puts a convincing reflected sky back on the pane.
        reflect = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        reflect.name = "Preview Glass Reflection"
        reflect.label = "Preview Glass Reflection"
        _set(reflect, "Base Color", (*tint, 1.0))
        _set(reflect, "Metallic", 0.0)
        _set(reflect, "Roughness", 0.035)
        _set(reflect, "IOR", 1.52)
        _set(reflect, "Specular IOR Level", 0.5)
        _set(reflect, "Transmission Weight", 0.0)

        transparent = mat.node_tree.nodes.new("ShaderNodeBsdfTransparent")
        fresnel = mat.node_tree.nodes.new("ShaderNodeFresnel")
        fresnel.inputs["IOR"].default_value = 1.52
        reflection_mix = mat.node_tree.nodes.new("ShaderNodeMixShader")
        reflection_mix.name = "Preview Glass Fresnel"
        reflection_mix.label = "Preview Glass Fresnel"
        # Keep a modest reflection at every angle so the facade reads as glass,
        # but cap it well below a mirror. A limited 14%..40% response is more
        # useful in Material Preview than a physical 0%..100% Fresnel curve:
        # rooms remain visible from an upward-looking view without the lower
        # facade turning into an indistinguishable open hole.
        reflection_range = mat.node_tree.nodes.new("ShaderNodeMapRange")
        reflection_range.name = "Preview Glass Reflection Range"
        reflection_range.label = "Preview Glass Reflection Range (14%–40%)"
        reflection_range.clamp = True
        reflection_range.inputs["From Min"].default_value = 0.0
        reflection_range.inputs["From Max"].default_value = 1.0
        reflection_range.inputs["To Min"].default_value = 0.14
        reflection_range.inputs["To Max"].default_value = 0.40

        links = mat.node_tree.links
        for link in list(output.inputs["Surface"].links):
            links.remove(link)
        links.new(fresnel.outputs["Fac"], reflection_range.inputs["Value"])
        links.new(reflection_range.outputs["Result"], reflection_mix.inputs[0])
        links.new(transparent.outputs[0], reflection_mix.inputs[1])
        links.new(reflect.outputs[0], reflection_mix.inputs[2])
        links.new(reflection_mix.outputs[0], output.inputs["Surface"])

        mat.blend_method = "BLEND"
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "BLENDED"
        mat.use_backface_culling = False
        if hasattr(mat, "use_transparency_overlap"):
            mat.use_transparency_overlap = False
        if hasattr(mat, "show_transparent_back"):
            mat.show_transparent_back = False
        if hasattr(mat, "use_screen_refraction"):
            mat.use_screen_refraction = False
        if hasattr(mat, "use_raytrace_refraction"):
            mat.use_raytrace_refraction = False

    return mat


def make_ceiling_light(name="CeilingLight", color=CEILING_LIGHT_WARM,
                       strength=CEILING_LIGHT_STRENGTH):
    """Emissive ceiling panel; zero strength keeps a switched-off fixture."""
    mat = _new(name)
    b = _bsdf(mat)
    _set(b, "Base Color", (*color, 1.0))
    _set(b, "Roughness", 0.25)
    _set(b, "Specular IOR Level", 0.1)
    _set(b, "Emission Color", (*color, 1.0))
    _set(b, "Emission Strength", strength)
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
        "ceiling_light_daylight": make_ceiling_light(
            "CeilingLight_Daylight", CEILING_LIGHT_DAYLIGHT),
        "ceiling_light_warm": make_ceiling_light(
            "CeilingLight_Warm", CEILING_LIGHT_WARM),
        "ceiling_light_off": make_ceiling_light(
            "CeilingLight_Off", (0.055, 0.045, 0.035), 0.0),
        "foliage": make_foliage(),
        "trunk": make_trunk(),
        "metal": make_metal(),
        "dark": make_dark(),
        "ground": make_ground(),
    }
