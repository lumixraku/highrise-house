# highrise-house

Procedural Blender model of a high-rise house: a ribbon-window tower lifted off the
ground on three open pilotis floors.

| | |
| --- | --- |
| ![Front elevation](out/view_front.png) | ![Corner](out/view_corner.png) |
| **Front elevation** — the full 161 m from 440 m out, 42 mm. The blank 8 m bands top and bottom, and the refuge void at mid-height. | **Corner** — 38 mm from above the halfway point, showing how the ribbon window stops short of the solid corner piers. |
| ![Sky garden](out/view_sky_garden.png) | ![Pilotis base](out/view_base_pilotis.png) |
| **Refuge floor / sky garden** — 58 mm, camera inside the void and slightly below it, looking up into the 8 m double height past the fin screen and the planting. | **Pilotis base** — 32 mm looking up the open base: the 1.60 m columns, the service core behind them, and the soffit oversailing as a drip edge. |
| ![Facade detail](out/view_floor_detail.png) | **Facade detail** — one floor at 70 mm: the 2.00 × 1.50 m pane, its mullions, the 0.30 m vent bands flush above and below the glass, and the spandrel between. Every pane in the building is this same fixed module; the footprint is derived from how many of them fit, not the other way round. |

## Build

Requires Blender 5.x on `PATH` (developed against Blender 5.2.0 LTS). Renders
with Cycles — note that Blender 5.2 does not list `CYCLES` in the engine enum but
does render with it when set, so `RENDER_ENGINE = "CYCLES"` works.

```bash
blender --background --factory-startup --python build_house.py
```

Writes into `out/`:

| file | contents |
| --- | --- |
| `highrise_house.blend` | full scene: geometry, materials, sun, camera |
| `highrise_house.glb` | glTF export for web/DCC viewers |
| `preview.png` | EEVEE render, 3/4 view |

Add `--no-render` after the script name to skip rendering.

Extra views, rendered portrait since the tower is 160 m tall (front elevation,
pilotis base, single-floor facade close-up, corner, sky garden):

```bash
blender --background --factory-startup --python render_views.py -- out/highrise_house.blend
```

## Verify

105 geometry and material assertions over the saved `.blend` — derived footprint, band heights,
window centring, exact 2.00 × 1.50 m pane size on both facades, pane count and
pitch, per-face pier widths, the even 8 m long-facade margin, solid corners,
blank base/top bands, vent adjacency, pilotis clearance, and the refuge void
(open on all sides, undivided double height, guarded edges, planting inside it,
core continuity, SCDF spacing, the screen's alignment with the window mullions and
its open area, and the void's load path — column count, spacing on the pane
module, and stress against the C40 limit):

```bash
blender --background --factory-startup --python verify_house.py -- out/highrise_house.blend
```

## The building

| | |
| --- | --- |
| footprint | 76 × 32 m (derived, see below) |
| clear internal depth | 31.40 m |
| floor-to-floor height | 4.0 m |
| storeys | 40 total |
| open pilotis floors | 3 (0.0 → 12.0 m) |
| occupied floors | 37 (12.0 → 160.0 m), of which 2 are the refuge level |
| total height | 161.32 m to top of parapet |
| corner piers | 8.0 m on long faces / 4.0 m on short faces |
| clear window opening | 60 m long face / 24 m short face |
| blank base band | 2 floors = 8.0 m (12.0 → 20.0 m) |
| blank top band | 2 floors = 8.0 m (152.0 → 160.0 m) |
| refuge floor / sky garden | storeys 21–22, screened void 80.0 → 88.0 m (79.8% open) |
| glazed floors | 31 |
| panes per floor | 30 long face / 12 short face (84 around) |
| pane pitch | 2.00 m mullion centres |
| clear glass per pane | **2.00 m × 1.50 m, fixed** |

### Bottom three floors

Open and raised. A 9 × 4 grid of 1.60 m square concrete columns on ~9 m bays
carries the tower, with a 14.0 × 9.0 m service core (stairs/lifts) rising through
the void and a landing at each of the three levels. Columns that would clash with
the core are omitted. The tower's underside slab oversails the footprint by 0.25 m
per side as a drip edge.

### Refuge floor / sky garden

Two storeys at mid-height (21–22, **80.0 → 88.0 m**) are given over to a planted
refuge level, unglazed on all four sides and screened by slim vertical fins, in the
Singapore manner. Singapore's SCDF
requires a refuge floor in buildings over 24 storeys and no more than 20 storeys
apart; at storey 21 of 40 there are 21 below and 19 above, so one level satisfies
the rule. It doubles as the lift transfer level.

The two storeys are a **single double-height space** — no intermediate slab — so
the void reads as one 8 m opening rather than two stacked floors. It is screened,
not hollowed out: leaving it fully open reads as a bite taken out of the tower.

```
        ┌│││█│││││█│││││█│││┐   88.0 m  ceiling = plate of the floor above
   pier  ││││█│││││█│││││█│││    121 slim vertical blades, 0.10 m at
        ─│││█│││││█│││││█│││─   0.50 m centres, full 8 m height
        ─│││█│││││█│││││█│││─   █ = 1.20 m structural column, 6.0 m centres
        └│││█│││││█│││││█│││┘   80.0 m  garden slab (0.45 m, carries soil)
             trees + planters behind, 1.2 m balustrade at the edge
```

The blades screen the void; the columns marked █ are what carry the tower across
it. 24 of them in all — 9 on each long face, 3 on each short face.

### The screen aligns with the windows

`FIN_PITCH` is **`PANE_W / 4` = 0.50 m**, chosen so it divides the window pane
pitch exactly. Every fourth blade lands on a window mullion, so the vertical lines
run unbroken from the glazing below, through the garden, into the glazing above.
Verified rather than assumed — `verify_house.py` reads both sets of members off the
model and asserts that all **31 mullions are met by a blade** (31 of 121). Pick a
pitch that does not divide 2.0 m and the refuge level reads as a foreign object
inserted into the tower.

It stays a filter, not a wall: **79.8%** of the long face is open, and the gaps are
real voids, so the level ventilates as a refuge floor must. Confirmed by
ray-casting — a ray between two blades leaves the building with 0 hits, one aimed
at a blade is blocked.

`GRILLE_STYLE` switches the treatment. Both pass all assertions:

| | |
| --- | --- |
| `"FINS"` | 0.10 m vertical blades at 0.50 m centres, 0.34 m deep. Default. Fine-grained; transparent head-on, closing up at a raking angle. |
| `"GRID"` | 2.0 m square openings in 0.34 m members — after 432 Park Avenue. Heavier, and the horizontals read as four stacked bands rather than one tall void. |

The grille is a screen and nothing more — a 0.10 m blade carries no load. The
floors above cross the void on 24 dedicated columns behind it (see below).

What holds the elevation together where the facade stops:

* **Corner piers continue through the void**, so the building line turns the
  corners exactly as it does on a glazed floor.
* **A 1.2 m balustrade** runs between the piers on all four sides, on the same
  clear opening the windows use, so the vertical rhythm is unbroken.
* **24 structural columns**, 1.20 m square, carry the 18 floors above across the
  void. Without them the load lands on the corner piers and core alone: 26.6 m²
  of concrete under 513638 kN, which is 19.3 MPa and over the limit for C40. With
  them the path is 61.2 m² at 9.45 MPa — a 52% utilisation, matching the pilotis
  columns below. They sit at `PANE_W * 3` = 6.0 m centres, so every column lands
  on a mullion line and the facade's vertical rhythm runs through the garden.
* **The lift/stair core is exposed**, which is what makes it read as a level you
  arrive at rather than a gap.

The garden slab is 0.45 m rather than the usual 0.22 m because it carries soil,
and it replaces the plate that the floor below would otherwise contribute (they
share a top face, so building both would leave two slabs in the same place).

Set `SKY_GARDEN = False` to build the tower without it; `REFUGE_FLOORS` changes
how many storeys the void takes. Its position is derived — centred in the *glazed*
part of the tower, not the tower as a whole, so the blank bands don't push it
off-centre — and asserts fail the build if it lands on a blank band or breaks the
20-storey spacing rule.

### An even 8 m frame on the long facade

Four of the 37 occupied floors carry no openings at all — two at the bottom
(12.0 → 20.0 m) and two at the top (152.0 → 160.0 m), 8 m each. Together with the
8 m piers left and right, the window field on the long facade sits inside an even
**8 m blank margin on all four sides**:

```
        8.0 m blank (2 floors)
      ┌───────────────────────┐
 8.0  │   16 floors of        │  8.0
 pier │   30-pane windows     │  pier
      ├───────────────────────┤
      │   sky garden (2)      │
      ├───────────────────────┤
 8.0  │   15 floors of        │  8.0
 pier │   30-pane windows     │  pier
      └───────────────────────┘
        8.0 m blank (2 floors)
```

31 glazed floors in all: 16 above the garden, 15 below it.

Both bands are specified as target heights (`SOLID_BASE_TARGET`,
`SOLID_TOP_TARGET`) and rounded to whole floors, so a break always lands on a
floor line instead of cutting a window in half. At a 4 m floor height each is
exactly 2 floors.

The short facade uses a narrower 4.0 m pier (`PIER_SHORT`), leaving 24 m of window
in a 32 m face. At 8 m it would be mostly wall.

### Facade band layout

Each *glazed* floor repeats the same section, measured up from its floor level:

```
4.00 ┬───────────────────────────────  next floor
     │  0.95  solid spandrel
3.05 ├───────────────────────────────
     │  0.30  ventilation louvres
2.75 ├───────────────────────────────
     │
     │  1.50  window          ← centre at 2.00 m = mid-floor
     │
1.25 ├───────────────────────────────
     │  0.30  ventilation louvres
0.95 ├───────────────────────────────
     │  0.95  solid spandrel
0.00 ┴───────────────────────────────  floor level
```

`0.95 + 0.30 + 1.50 + 0.30 + 0.95 = 4.00 m`, so the window sits exactly
vertically centred and the two vent strips are flush against it.

The window and both vent strips run the width of every facade but stop short of
each corner, so all four corners stay solid wall: 8.0 m on the long faces
(`PIER_LONG`) and 4.0 m on the short ones (`PIER_SHORT`). The piers are L-shaped
in plan — a long leg along the wide facade, a shorter one along the narrow — and
fill the whole vent + window + vent zone. Clear openings are 60 m on the long
faces and 24 m on the short ones.

### Flush glazing — one facade plane

`GLASS_INSET = 0.0` and `VENT_INSET = 0.0`: the glass, its mullion caps and the
louvre slats all finish on the **same plane as the wall**, with no reveal and no
sill. Setting glass back from the wall face leaves a strip of opening side wall
around each pane, and that strip is precisely what reads as a window sill — at
0.09 m it was clearly visible.

Depth still comes from what sits *behind* the plane, not in front of it: the
louvres are tilted 30° over a dark shadowbox 0.10 m back, and the interior lining
is set back `INTERIOR_SETBACK` = 0.85 m so pane and lining move against each other
as the view shifts.

One subtlety in the geometry: a tilted slat sweeps deeper than half its own
thickness, so the louvre offset is keyed to its *rotated* extent
(`slat_depth/2·cos θ + slat_t/2·sin θ`). Keying it to `slat_depth / 2` would push
the slat corners 1.4 mm through the wall plane once the inset reached zero.

Four assertions hold this: the outer face of glass, mullions and louvres each
measured against the wall plane within 2 mm, plus one that nothing stands proud of
it. They are not decorative — reverting `GLASS_INSET` to 0.09 fails two of them
with a reported `+90.0 mm`.

### The window is the module — the footprint follows from it

The pane is fixed at exactly **2.00 m × 1.50 m** of clear glass, on every facade.
The footprint is not an input — it is the pane count plus the piers, nothing else:

```
W = 30 panes x 2.00 + 2 x 8.00 pier = 76 m
D = 12 panes x 2.00 + 2 x 4.00 pier = 32 m
pane pitch = 2.00 m (identical on all four facades)
```

Mullions are 0.09 m **cover caps centred on each pane joint**: they overlap the
two panes they join rather than displacing them, so they consume no facade
length. (They are 0.14 m deep, but that depth runs *inward* from the flush face —
see above.) That is what keeps the arithmetic clean — 30 panes of 2 m is exactly
60 m of opening, and the footprint lands on whole metres. (An earlier version
added each mullion's width to the facade, which pushed the dimensions to
78.79 × 30.72 m; the caps fixed that.)

84 panes per floor, on 31 glazed floors. To resize the building, change
`WINDOWS_LONG` / `WINDOWS_SHORT` (or the pier widths) — never `W`/`D`, which are
derived. Adding one pane to a facade widens the building by exactly 2 m.

## Viewing it in Blender

```bash
./view.sh
```

Opening the `.blend` by hand shows a **flat grey-white building** — that is not the
materials failing. Blender starts every 3D viewport in `SOLID` shading, which
ignores materials entirely. To see the real look, put the cursor in the 3D view and
press `Z`, then pick:

* **Material Preview** — EEVEE, fast, approximate glass
* **Rendered** — the scene engine (Cycles), the only mode where the glass refracts
  correctly

or click the fourth (rightmost) of the four sphere icons at the top right of the
viewport. `./view.sh` just does this for you at startup via `open_in_blender.py`.

This cannot be baked into the `.blend` from a `--background` build: viewport state
is only written back to file when a real UI exists, so setting it headlessly is
silently discarded.

## Materials

All materials live in `materials.py`, separate from the geometry, so the look can
be tuned without rebuilding the model logic. Colours are **linear RGB**, not sRGB —
putting sRGB values straight into a Blender colour socket renders washed out.

| | |
| --- | --- |
| walls | warm pale stone, matte (roughness 0.72), `WALL_COLOR` |
| glass | pale green tint, transmission 1.0, IOR 1.52, roughness 0.0, no emission |
| interior lining | matte warm grey 0.85 m behind the glass, self-illuminated 0.75 |
| mullions / louvres | dark anodised metal, roughness 0.38 |
| structure | grey concrete, roughness 0.85 |
| foliage | dark matte green, 12% transmission for backlit leaves |

Foliage is far darker than intuition suggests — a leaf reflects roughly 15–20% in
green and much less in red and blue, so a bright green renders as plastic turf.
`PLANT_GREEN` is deliberately dark, with a little transmission because the
planting is backlit against an open void.

### Keeping the glass clear, not frosted

Three separate settings each turn smooth glass into ground glass, and they add
up quietly — an earlier version had all three at once and the panes looked
sandblasted:

* **Transmission below 1.0.** The leftover weight is a *diffuse* lobe using the
  base colour, and a diffuse lobe on a window is exactly what frosted glass is.
* **Roughness above ~0.01.** Architectural glazing is float glass, optically
  flat. Even 0.02 scatters visibly at this distance.
* **Emission on the glass.** A glow is uniform across the pane, so it washes out
  the reflections and reads as a milky film.

Plus one that is not a material setting at all: Cycles' **Filter Glossy**
(`blur_glossy`) deliberately blurs glossy and refractive rays to cut noise. At
1.0 it frosts perfectly smooth glass on its own, whatever the material says. It
is held at 0 and the noise is paid for in samples instead.

`verify_house.py` asserts all four, since they are easy to reintroduce while
tuning.

The catch with fully clear glass is that it shows whatever is behind it — over
an empty tower that is the far facade and then the sky, so the panes lose all
depth and read as gaps. Hence `Interior_Lining`: a matte surface 0.85 m behind
the glazing, standing in for lit floors. Because it sits *behind* the pane it
shifts against the sky reflection as the view moves, which is the cue that reads
as glass. That is also what replaced the emission that used to be on the glass —
same brightness, but with depth.

Three things mattered more than the material parameters, each found by measuring
rendered pixels rather than by eye:

**The sun has to light the faces the camera sees.** All cameras sit at +X/−Y
looking at the south and east facades, so the sun must come from the south-east.
An earlier azimuth put it north-west, leaving every visible surface in shade lit
only by blue skylight — the warm walls rendered cold and the glass had no glints.
`SUN_ELEV_DEG` / `SUN_AZIM_DEG` in `materials.py` are the measured-correct values.

**A physical sky is too blue for a matte wall.** A raw Nishita sky dragged the
beige wall from `r−b = +0.08` under neutral light to `−0.16` — cold, regardless of
its own colour, because a diffuse surface integrates skylight over the whole
hemisphere. The world shader desaturates the sky to 0.28 and mixes 35% warm tone,
which keeps a readable sky in the glass reflections while letting surfaces show
their real colour.

**Fully transmissive glass needs something behind it, not less transmission.**
Clear glass over an unlit interior renders near-black, and the tempting fix —
pulling transmission back and adding a glow — is what frosted the panes. The
right fix is geometric: put a lit lining behind the glazing and leave the glass
alone.

**A pale green needs two measurements, not one.** Only what passes *through* the
pane is tinted; the sky reflection is not, and at these viewing angles the
reflection carries most of the brightness — and it is blue. So the tint has to
fight the sky, and tracking "how green" alone walks straight into yellow or cyan.
Watch both:

* **green bias** = G − (R+B)/2 — how green
* **warm bias** = R − B — green vs *yellow*-green vs cyan

| tint | green bias | warm bias | |
| --- | --- | --- | --- |
| `(0.88, 0.965, 0.92)` | +0.010 | −0.008 | too weak: B 0.456 beat G 0.448, reads blue-grey |
| `(0.88, 0.965, 0.70)` | +0.025 | **+0.012** | **yellow-green** — red high + blue low *is* yellow |
| `(0.74, 0.965, 0.86)` | +0.026 | −0.056 | cyan: B caught up with G |
| `(0.72, 0.965, 0.76)` | +0.035 | −0.039 | **in use** — G clearly leads, R under B, no yellow |

All three channels matter: G highest by a clear margin, R lowest, B in between.
To adjust — raise all three for paler, lower red for greener, raise blue if it
looks yellow, lower blue if it looks cyan.

**Transparency is mostly a property of the lining, not the glass.** Once
transmission is 1.0 and roughness 0.0 there is nothing left to make the material
clearer — what remains is whether there is anything legible on the far side.
Where the lining falls dark the pane goes opaque and heavy regardless. Lifting it
to emission 0.75 cut the share of glass pixels below 0.25 luminance from 3.6% to
0.8%. Going brighter still (emission 1.0) starts to overpower the sky reflection
and the panes drift toward "glowing panel".

The lining's *colour* matters for the same reason — at that brightness it is
plainly visible through clear glass, so its cast lands on every pane. A warm grey
lining tints the whole facade yellow on its own, which was half of why the
windows read as olive. `INTERIOR_LINING` is kept neutral-to-cool so the green
tint can read as green.

Measured over glass pixels only (found by ray-casting the camera through each
pixel — whole-frame averages are useless, since spandrel covers most of the
facade and drowns the panes out):

| surface | R | G | B | mean luminance | local stdev |
| --- | --- | --- | --- | --- | --- |
| glass | 0.500 | 0.554 | 0.539 | 0.541 | 0.080 |
| wall | 0.598 | 0.592 | 0.574 | 0.592 | 0.020 |

The **stdev** column is the frosted test, and the only one that catches it
numerically: a rough or partly-diffuse pane averages its surroundings, so
neighbouring pixels converge and local contrast collapses toward the wall's.
Clear glass holds sharp sky-reflection, mullion and lining detail — here it runs
**≈4× the matte wall's local contrast**, at roughly 0.9× the wall's brightness.
`measure_glass.py` reports all of this:

```bash
blender --background --factory-startup --python measure_glass.py -- out/highrise_house.blend
```

To try the pale grey wall instead of beige, set
`WALL_COLOR = materials.COOL_STONE` in `build_house.py`.

## Geometry organisation

Everything is generated from boxes and joined into twelve objects, so the scene
stays light (~40k vertices at 40 storeys):

`Facade_Spandrels` · `Windows_Glass` · `Interior_Lining` · `Window_Mullions` ·
`Vent_Louvres` · `Vent_Shadowboxes` · `Sky_Garden_Grille` ·
`Sky_Garden_Planting` · `Sky_Garden_Trunks` · `Floor_Plates` · `Structure` ·
`Ground`

## Changing the design

All parameters sit at the top of `build_house.py`. `PANE_W` and the pane counts
set the footprint (`W`/`D` are derived — don't set them directly),
`TOTAL_FLOORS` the storey count and `PILOTIS_FLOORS` how many of those are open
(`TOWER_FLOORS` is the remainder). The column grid, roof plant and camera all
derive from the footprint, so changing the pane counts keeps the model coherent.
Note that
`verify_house.py` carries its own copy of `W`, `D` and the floor counts — update it
to match, or its assertions will test the old dimensions. The five vertical bands are derived
from `H`, `WIN_H` and `VENT_H` — `SPANDREL_H` is computed as
`(H - WIN_H - 2 * VENT_H) / 2`, which keeps the window centred for any floor
height, and an `assert` fails the build if the bands stop summing to `H`.
