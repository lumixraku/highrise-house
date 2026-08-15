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

Extra views (front elevation, pilotis base, single-floor facade close-up):

```bash
blender --background --factory-startup --python render_views.py -- out/highrise_house.blend
```

## Verify

29 geometry assertions over the saved `.blend` — band heights, window centring,
full-width spans, vent adjacency, pilotis clearance:

```bash
blender --background --factory-startup --python verify_house.py -- out/highrise_house.blend
```

## The building

| | |
| --- | --- |
| footprint | 20.0 × 14.0 m |
| floor-to-floor height | 4.0 m |
| open pilotis floors | 3 (0.0 → 12.0 m) |
| occupied floors | 12 (12.0 → 60.0 m) |
| total height | 62.60 m to top of parapet |

### Bottom three floors

Open and raised. Six 0.85 m square concrete columns carry the tower, with a
5.0 × 4.2 m service core (stairs/lifts) rising through the void and a landing at
each of the three levels. The tower's underside slab oversails the footprint by
0.25 m per side as a drip edge.

### Facade band layout

Each occupied floor repeats the same section, measured up from its floor level:

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

The window and both vent strips run the full width of every facade and wrap all
four corners, reading as continuous ribbons. Glazing is inset 0.09 m from the
outer wall face; the louvres sit deeper at 0.13 m, tilted 30°, over a dark
shadowbox so the openings read as depth rather than holes. Mullions divide the
glass at roughly 2.6 m centres.

## Geometry organisation

Everything is generated from boxes and joined into eight objects, so the scene
stays light (~6.4k vertices):

`Facade_Spandrels` · `Windows_Glass` · `Window_Mullions` · `Vent_Louvres` ·
`Vent_Shadowboxes` · `Floor_Plates` · `Structure` · `Ground`

## Changing the design

All parameters sit at the top of `build_house.py`. `W`/`D` set the footprint,
`PILOTIS_FLOORS`/`TOWER_FLOORS` the counts. The five vertical bands are derived
from `H`, `WIN_H` and `VENT_H` — `SPANDREL_H` is computed as
`(H - WIN_H - 2 * VENT_H) / 2`, which keeps the window centred for any floor
height, and an `assert` fails the build if the bands stop summing to `H`.
