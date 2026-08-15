# highrise-house

Procedural Blender model of a high-rise house: a ribbon-window tower lifted off the
ground on three open pilotis floors.

## Build

Requires Blender 5.x on `PATH` (developed against Blender 5.2.0 LTS).

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

44 geometry assertions over the saved `.blend` — footprint, band heights, window
centring, per-facade opening widths, solid corners, blank base/top bands, vent
adjacency, pilotis clearance:

```bash
blender --background --factory-startup --python verify_house.py -- out/highrise_house.blend
```

## The building

| | |
| --- | --- |
| footprint | 70.0 × 30.0 m |
| floor-to-floor height | 4.0 m |
| storeys | 40 total |
| open pilotis floors | 3 (0.0 → 12.0 m) |
| occupied floors | 37 (12.0 → 160.0 m) |
| total height | 161.32 m to top of parapet |
| corner piers | 4.0 m solid at each facade end |
| clear window opening | 62.0 m long face / 22.0 m short face |
| blank base floor | 1 (12.0 → 16.0 m) |
| blank top band | 2 floors = 8.0 m (152.0 → 160.0 m) |
| glazed floors | 34 |

### Bottom three floors

Open and raised. An 8 × 4 grid of 1.60 m square concrete columns on ~9 m bays
carries the tower, with a 14.0 × 9.0 m service core (stairs/lifts) rising through
the void and a landing at each of the three levels. Columns that would clash with
the core are omitted. The tower's underside slab oversails the footprint by 0.25 m
per side as a drip edge.

### Blank bands

Three of the 37 occupied floors carry no openings at all:

* the first floor above the pilotis (12.0 → 16.0 m), so the tower meets the open
  base against solid wall rather than glass;
* the top two floors (152.0 → 160.0 m), giving an 8 m blank band under the roof.

The top band is specified as a target height (`SOLID_TOP_TARGET = 8.0`) and
rounded to whole floors, so the break always lands on a floor line instead of
cutting a window in half. At a 4 m floor height that is exactly 2 floors.

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

The window and both vent strips run the width of every facade but stop 4.0 m
short of each corner (`CORNER_PIER`), so all four corners stay solid wall. The
piers are L-shaped in plan — one leg along each facade — and fill the whole
vent + window + vent zone. Clear openings are 62.0 m on the long faces and
22.0 m on the short ones, identical treatment on all four sides.

Glazing is inset 0.09 m from the
outer wall face; the louvres sit deeper at 0.13 m, tilted 30°, over a dark
shadowbox so the openings read as depth rather than holes. Mullions divide the
glass at roughly 2.6 m centres.

## Geometry organisation

Everything is generated from boxes and joined into eight objects, so the scene
stays light (~35k vertices at 40 storeys):

`Facade_Spandrels` · `Windows_Glass` · `Window_Mullions` · `Vent_Louvres` ·
`Vent_Shadowboxes` · `Floor_Plates` · `Structure` · `Ground`

## Changing the design

All parameters sit at the top of `build_house.py`. `W`/`D` set the footprint,
`TOTAL_FLOORS` the storey count and `PILOTIS_FLOORS` how many of those are open
(`TOWER_FLOORS` is the remainder). The column grid, roof plant and camera all
derive from the footprint, so changing `W`/`D` keeps the model coherent. Note that
`verify_house.py` carries its own copy of `W`, `D` and the floor counts — update it
to match, or its assertions will test the old dimensions. The five vertical bands are derived
from `H`, `WIN_H` and `VENT_H` — `SPANDREL_H` is computed as
`(H - WIN_H - 2 * VENT_H) / 2`, which keeps the window centred for any floor
height, and an `assert` fails the build if the bands stop summing to `H`.
