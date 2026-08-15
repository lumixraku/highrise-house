# highrise-house

Procedural Blender model of a high-rise house: a ribbon-window tower lifted off the
ground on three open pilotis floors.

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
pilotis base, single-floor facade close-up, corner):

```bash
blender --background --factory-startup --python render_views.py -- out/highrise_house.blend
```

## Verify

59 geometry assertions over the saved `.blend` — derived footprint, band heights,
window centring, exact 2.00 × 1.50 m pane size on both facades, pane count and
pitch, per-face pier widths, the even 8 m long-facade margin, solid corners,
blank base/top bands, vent adjacency, pilotis clearance:

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
| occupied floors | 37 (12.0 → 160.0 m) |
| total height | 161.32 m to top of parapet |
| corner piers | 8.0 m on long faces / 4.0 m on short faces |
| clear window opening | 60 m long face / 24 m short face |
| blank base band | 2 floors = 8.0 m (12.0 → 20.0 m) |
| blank top band | 2 floors = 8.0 m (152.0 → 160.0 m) |
| glazed floors | 33 |
| panes per floor | 30 long face / 12 short face (84 around) |
| pane pitch | 2.00 m mullion centres |
| clear glass per pane | **2.00 m × 1.50 m, fixed** |

### Bottom three floors

Open and raised. A 9 × 4 grid of 1.60 m square concrete columns on ~9 m bays
carries the tower, with a 14.0 × 9.0 m service core (stairs/lifts) rising through
the void and a landing at each of the three levels. Columns that would clash with
the core are omitted. The tower's underside slab oversails the footprint by 0.25 m
per side as a drip edge.

### An even 8 m frame on the long facade

Four of the 37 occupied floors carry no openings at all — two at the bottom
(12.0 → 20.0 m) and two at the top (152.0 → 160.0 m), 8 m each. Together with the
8 m piers left and right, the window field on the long facade sits inside an even
**8 m blank margin on all four sides**:

```
        8.0 m blank (2 floors)
      ┌───────────────────────┐
 8.0  │   33 floors of        │  8.0
 pier │   30-pane windows     │  pier
      └───────────────────────┘
        8.0 m blank (2 floors)
```

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

Glazing is inset 0.09 m from the
outer wall face; the louvres sit deeper at 0.13 m, tilted 30°, over a dark
shadowbox so the openings read as depth rather than holes.

### The window is the module — the footprint follows from it

The pane is fixed at exactly **2.00 m × 1.50 m** of clear glass, on every facade.
The footprint is not an input — it is the pane count plus the piers, nothing else:

```
W = 30 panes x 2.00 + 2 x 8.00 pier = 76 m
D = 12 panes x 2.00 + 2 x 4.00 pier = 32 m
pane pitch = 2.00 m (identical on all four facades)
```

Mullions are 0.09 m **cover caps centred on each pane joint**: they overlap the
two panes they join and sit proud of the glass line, so they consume no facade
length. That is what keeps the arithmetic clean — 30 panes of 2 m is exactly
60 m of opening, and the footprint lands on whole metres. (An earlier version
added each mullion's width to the facade, which pushed the dimensions to
78.79 × 30.72 m; the caps fixed that.)

84 panes per floor, on 33 glazed floors. To resize the building, change
`WINDOWS_LONG` / `WINDOWS_SHORT` (or the pier widths) — never `W`/`D`, which are
derived. Adding one pane to a facade widens the building by exactly 2 m.

## Materials

All materials live in `materials.py`, separate from the geometry, so the look can
be tuned without rebuilding the model logic. Colours are **linear RGB**, not sRGB —
putting sRGB values straight into a Blender colour socket renders washed out.

| | |
| --- | --- |
| walls | warm pale stone, matte (roughness 0.72), `WALL_COLOR` |
| glass | faint green, transmission 0.75, IOR 1.52, roughness 0.02 |
| mullions / louvres | dark anodised metal, roughness 0.38 |
| structure | grey concrete, roughness 0.85 |

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

**Fully transmissive glass over an unlit interior renders black.** At
transmission 1.0 the panes measured 0.10 brightness against a 0.59 wall — a smoked
panel, not glazing. Holding transmission at 0.75, raising specular to 0.75 and
adding a 0.06 emission (standing in for lit floors) brings the panes to 0.51 with
a clear green bias, which is what makes real curtain wall look bright.

Measured on the final build, per surface:

| surface | R | G | B | green bias |
| --- | --- | --- | --- | --- |
| glass | 0.404 | 0.512 | 0.470 | +0.108 |
| wall | 0.601 | 0.594 | 0.577 | −0.006 (warm) |

To try the pale grey wall instead of beige, set
`WALL_COLOR = materials.COOL_STONE` in `build_house.py`.

## Geometry organisation

Everything is generated from boxes and joined into eight objects, so the scene
stays light (~35k vertices at 40 storeys):

`Facade_Spandrels` · `Windows_Glass` · `Window_Mullions` · `Vent_Louvres` ·
`Vent_Shadowboxes` · `Floor_Plates` · `Structure` · `Ground`

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
