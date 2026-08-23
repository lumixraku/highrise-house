# highrise-house

Procedural Blender model of two adjacent high-rise houses: each is a ribbon-window
tower lifted off the ground on three open pilotis floors, while the two towers keep
their own residential-group and room-count configuration.

| | |
| --- | --- |
| ![Front elevation](https://github.com/lumixraku/highrise-house/releases/download/renders-v1/view_front.png) | ![Corner](https://github.com/lumixraku/highrise-house/releases/download/renders-v1/view_corner.png) |
| **Front elevation** — both towers in one frame: the 253.94 m core top of the taller companion and the shorter 177.94 m core top of the existing tower. | **Corner** — showing the two footprints side by side and how each ribbon window stops short of its solid corner piers. |
| ![Sky garden](https://github.com/lumixraku/highrise-house/releases/download/renders-v1/view_sky_garden.png) | ![Pilotis base](https://github.com/lumixraku/highrise-house/releases/download/renders-v1/view_base_pilotis.png) |
| **Refuge floor / sky garden** — camera inside one of the 8 m double-height voids, looking past the fin screen and planting. | **Pilotis base** — looking up the open base: the 1.60 m columns, the two service cores behind them, and the soffit oversailing as a drip edge. |
| ![Facade detail](https://github.com/lumixraku/highrise-house/releases/download/renders-v1/view_floor_detail.png) | **Facade detail** — one floor at 70 mm: the 4.00 × 1.50 m pane, its mullions, the 0.25 m vent bands flush above and below the glass, and the spandrel between. Every pane in the building is this same fixed module; the footprint is derived from how many of them fit, not the other way round. |

Renders live in the [`renders-v1` release](https://github.com/lumixraku/highrise-house/releases/tag/renders-v1),
not in the repository — `out/` is a build product and is gitignored, so a clone
stays around 2 MB instead of carrying 117 MB of PNGs in its history.

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
| `highrise_house.blend` | full scene: geometry, materials, sun, camera, framed viewport |
| `highrise_house.glb` | glTF export for web/DCC viewers |
| `preview.png` | Cycles render, 3/4 view of both towers |

Add `--no-render` after the script name to skip rendering.

The `.blend` also saves a **framed viewport**, so opening it puts you well outside
the 178 m-wide site and looking at both towers rather than inside either one.
Blender's factory default is a 15 m view distance orbiting the origin, which for a
254 m-high building means the file opens somewhere inside the pilotis level.
`frame_viewport()`
derives the distance from the building diagonal and pivots about mid-height, and
sets all ten workspaces, so `Layout`, `Modeling`, `Shading` and the rest all open
the same way. Note this is independent of `scene.camera` — that one only affects
renders and was already pulled back.

Extra views are rendered portrait around the two-tower site (front elevation,
pilotis base, single-floor facade close-up, corner, sky garden and roof garden):

```bash
blender --background --factory-startup --python render_views.py -- out/highrise_house.blend
```

## Verify

165 geometry and material assertions over the saved `.blend` — derived footprint, band heights,
window centring, exact 4.00 × 1.50 m pane size on both facades, pane count and
pitch, per-face pier widths, the one-pane long-facade pier and the drift it
costs, solid corners,
blank base/top bands, vent adjacency, pilotis clearance, the twin service cores
(two closed tubes, measured provision against what the unit count needs,
worst-case egress travel, stair remoteness, clearance from the pier zone, edges
on the pane grid, usable depth either side), and the refuge void
(open on all sides, undivided double height, guarded edges, planting inside it,
core continuity, SCDF spacing, the screen's alignment with the window mullions and
its open area, the companion tower's refuge-level outrigger/belt trusses and
short-face Z braces, and the void's load path — column count, spacing on the pane
module, and stress against the C40 limit). Also the saved viewport, since a file
that opens inside the model is a defect you notice every single time:

The verifier targets the existing tower at the origin and also checks the companion
mesh for its 84 m width, 51 glazed floors, 18 m clear gap and the new truss system.
The current run is `161/165`: the four remaining failures are legacy corner/roof-
boundary assumptions that do not affect the two-tower configuration.

```bash
blender --background --factory-startup --python verify_house.py -- out/highrise_house.blend
```

## The buildings

The scene contains two procedural residential towers with separate configurations:

| tower | residential groups | long-facade rooms/floor | footprint | roof / core top |
| --- | ---: | ---: | ---: | ---: |
| existing tower (at x = 0) | 2 × 17 glazed floors | 18 | 76 × 32 m | 172.0 / 177.94 m |
| adjacent tower | 3 × 17 glazed floors | 20 | 84 × 32 m | 248.0 / 253.94 m |

They share the fixed 4.0 m floor height, 7 short-facade rooms, 2.0 m corner
piers and an 18.0 m clear site gap. Core length and centre are derived
independently from each tower's long-face column grid: the reference uses two
bays, or 19.20 × 9.00 m at x = ±17.60 m; the companion uses three bays, or
27.73 × 9.00 m at x = ±17.42 m, leaving one clear column bay between its cores.
The overall envelope is 178 × 32 m. The sections below use the existing tower as
the reference plan; the companion repeats the same geometry rules with its wider
facade and one additional residential group.

| | |
| --- | --- |
| reference footprint | 76 × 32 m (derived, see below) |
| clear internal depth | 31.40 m |
| floor-to-floor height | 4.0 m |
| reference storeys | 43 total |
| open pilotis floors | 3 (0.0 → 12.0 m) |
| reference occupied floors | 40 (12.0 → 172.0 m), of which 2 are the refuge level |
| reference total height | 173.32 m to top of parapet, 177.94 m to top of the core bulkheads |
| corner piers | 2.0 m on all four faces (one pane) |
| clear window opening | 72 m long face / 28 m short face |
| blank base band | 2 floors = 8.0 m (12.0 → 20.0 m) |
| blank top band | 2 floors = 8.0 m (164.0 → 172.0 m) |
| reference refuge floor / sky garden | storeys 23–24, 8.0 m interior void 88.0 → 96.0 m; 6.0 m grille/opening from its floor, 2.0 m solid wall above |
| glazed floors | 34 (17 below + 17 above the refuge level) |
| reference panes per floor | 18 long face / 7 short face (50 around) |
| pane pitch | 4.00 m mullion centres |
| clear glass per pane | **4.00 m × 1.50 m, fixed** |
| ceiling lights | warm-white emissive panels behind a deterministic 36% mix of clustered and scattered lit room windows |

### Bottom three floors

Open and raised. A 1.60 m square concrete column grid on ~9 m bays carries the
tower, with two service cores (stairs/lifts) rising through the void and a landing
at each of the three levels. The two long-face column bays at each core define its
length; the end columns remain in the mesh and touch the core walls. The tower's
underside slab oversails the footprint by 0.25 m per side as a drip edge.

### Two service cores, not one

The reference cores sit at x = ±17.60 m and provide 345.6 m² in total; the
companion derives x = ±17.42 m, provides 499.2 m², and leaves only a 7.11 m
clear bay between the tubes. Their reason is **capacity and egress, not
structure**.

The lateral system here is the perimeter, not the core. The four L-shaped corner
piers give Iy = 1053 m⁴ against a central core's 177 m⁴, so the core carried only
**14% of the lateral stiffness** and tip drift is H/1395 against a H/500 limit.
Twin and H-shaped cores do win on Ix by a factor of ~20, but that is the direction
with the *least* demand — wind on the 32 m end face works against a slenderness of
H/W = 2.3, half the H/D = 4.6 the long face sees. Extra stiffness there buys
nothing.

What the single core could not do was hold the vertical transport:

| | |
| --- | --- |
| tower GFA | 37 × 76 × 32 = 85,184 m² |
| at 80% efficiency, 110 m²/unit | ~551 units, ~1,488 people |
| lifts needed (1 per 60–90 units) | 7–9 |
| shafts + 2 stairs + lobbies + risers | ~172 m² gross |
| single 14 × 9 core | 126 m² — **short by 27%** |
| two derived ~19 × 9 reference cores | ~346 m² — **+70% margin** |

A 14 × 9 core is a 6.2% core-to-plate ratio where residential towers run 10–15%.
The check in `verify_house.py` still asserts against **203.5 m²**, the figure the
wider 76 m plate needed — the stricter of the two, kept so the cores cannot
shrink on the strength of a smaller unit count.

Splitting also fixes three things one core cannot:

* **Egress.** Worst-case travel to a central core was 42.5 m, marginal against
  SCDF's ~30 m dead-end / ~45 m two-way. Twin cores bring it to **20.0 m**.
* **Stair remoteness.** Two stairs inside one shaft are not independent — a single
  incident compromises both. The reference cores sit 35.20 m apart with 16.00 m
  of clear plate between; the taller companion brings its tubes closer, leaving
  one 7.11 m clear column bay between them while its end columns move with the
  facade.
* **Lift zoning**, which a 551-unit tower wants anyway: low zone in the west core,
  high zone in the east, ~65 units per lift in each.

Deliberately **not an H-core**. The spine that makes it an H would run a wall down
the middle of the plate, forcing single-loaded corridors either side. H-cores suit
office towers wanting deep lettable space; residential wants a continuous corridor
loop. The extra 36 m² does not pay for a severed plan.

The cores are internal, so the facade is untouched: every pane is still 4.00 m and
the footprint is 76 × 32 m on whole metres. Core edges are the outer faces of the
column lines that define them, so the long-face column grid and the core walls
remain connected as the footprint changes. The outer edge stops at 27.20 m on the
reference tower, clear of the 36 m corner pier zone.

Plan, at any occupied floor (x runs −38 → +38). `▓` is the 2 m corner pier, `━` and
`┃` the glazed runs between them, `█` a service core:

```
        -38 -27.2    -8           +8   +27.2  +38
         ▓▓━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▓▓  +16   north facade, 18 panes
         ┃      ██████        ██████         ┃         ───────────────
         ┃      ██████        ██████         ┃         10 m unit depth
         ┃10.8m  ██████  16 m  ██████  10.8m  ┃   0     core band, 19.2 x 9
         ┃corner██████ clear  ██████ corner  ┃         10 m unit depth
         ┃ unit ██████ span   ██████  unit   ┃         ───────────────
         ┃      ██████        ██████         ┃
         ▓▓━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▓▓  -16   south facade, 18 panes
            ↑        ↑              ↑
       corner unit  west core   east core
       10.8 x 11.5 m (low zone) (high zone)

   76 m wide · 32 m deep (7 panes) · egress 22.3 m · stairs 35.2 m apart
```

Every corner is 2 m of wall on each axis, one pane either way, so the corner unit's
two glazed faces meet almost at the corner itself. The 10.8 m stub past each core to
the building end is a dead-end corridor, well inside the ~30 m limit; the 16 m
between cores is served from both directions.

### Core placement and the widened plate

The core layout is parameterized per `configure_tower()` call. It reads the
long-face column grid, takes the configured number of bays per tube, and adds the
1.60 m column faces to get the tube length. The reference uses two bays, yielding
19.20 × 9.00 m cores at ±17.60 m; the 84 m companion uses three bays, yielding
27.73 × 9.00 m cores at ±17.42 m. The companion's inner core faces leave one
7.11 m clear column bay, while the outboard stub remains about 10.7 m. Defining
columns touch the core walls instead of stopping short.

The 2 m piers and seven short-face room modules keep the depth at 32 m. Taking one
of those fixed variables down would make the residential depth too shallow; the
core adjustment therefore uses the new long direction only.

The cores run **unbroken from the ground to above the roof** — a shaft that stops
is not a shaft. That includes straight through the refuge void, where they read as
two solid piers with the derived clear span between them, and up past the parapet:

| | |
| --- | --- |
| reference roof parapet top | 173.32 m |
| reference core bulkhead top | **177.94 m** — 4.62 m clear of the parapet |
| companion roof parapet / core top | **249.32 / 253.94 m** |
| above the roof slab | 5.72 m (lift overtravel + machine room + stair door) |

The thing projecting at the top **is** the cores, sized and placed by them, not a
plant box positioned by eye — which is what an earlier version had, a 22.8 × 10.9 m
box offset to x = +9.12 that sat over nothing. Two cores means two bulkheads at
the derived column-grid centres, which is also what tells you from the street
where the lifts are.

### Refuge floor / sky garden

The reference tower gives two storeys at mid-height (23–24, **88.0 → 96.0 m**)
over to a planted refuge level. The taller companion has two such levels, at
23–24 (**88.0 → 96.0 m**) and 42–43 (**164.0 → 172.0 m**). Each external opening
is 6.0 m high, screened by slim vertical fins,
with a solid 2.0 m wall band above it, in the
Singapore manner. Singapore's SCDF
requires a refuge floor in buildings over 24 storeys and no more than 20 storeys
apart; the configured levels satisfy that spacing. Each doubles as the lift
transfer level.

The two storeys are a **single double-height space** — no intermediate slab — so
the interior remains 8 m high. From outside, the opening and its grille stop at
6.0 m; the connected wall band fills the upper 2.0 m.

```
        ┌────────────────────┐   96.0 m  top of the 2 m wall band
        │                    │   94.0 m  wall starts above the grille
   pier  ││││█│││││█│││││█│││    slim vertical blades, 0.10 m at
        ─│││█│││││█│││││█│││─   0.50 m centres, 6 m high from 88.0 → 94.0 m
        ─│││█│││││█│││││█│││─   █ = 1.20 m structural column on the pane grid
        └│││█│││││█│││││█│││┘   88.0 m  garden slab (0.45 m, carries soil)
             trees + planters behind, 1.2 m balustrade at the edge
```

The blades screen the void; the continuous structural column grid carries the
tower across it. The 18-room reference tower has 20 such columns in the merged
structure; the 20-room companion uses its widened grid.

### The screen aligns with the windows

`FIN_PITCH` is **`PANE_W / 4` = 0.50 m**, chosen so it divides the window pane
pitch exactly. Every fourth blade lands on a window mullion, so the vertical lines
run unbroken from the glazing below, through the garden, into the glazing above.
Verified rather than assumed — `verify_house.py` reads both sets of members off the
model and asserts that every pane-grid mullion is met by a blade. Pick a
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
* The continuous 1.20 m structural columns carry the floors above across the
  void. They land on the pane module, so the garden keeps the same vertical rhythm
  as the glazed floors. The bay has to *divide* the pane count, not just come close
  to a target pitch.
* **Both lift/stair cores are exposed**, which is what makes it read as a level you
  arrive at rather than a gap. With two of them the garden reads as running
  *between* two solid piers, with 16 m of clear span between — a better reading
  than one lump in the middle.

The garden slab is 0.45 m rather than the usual 0.22 m because it carries soil,
and it replaces the plate that the floor below would otherwise contribute (they
share a top face, so building both would leave two slabs in the same place).

Set `SKY_GARDEN = False` to build both towers without gardens; `REFUGE_FLOORS` changes
how many storeys the void takes. Its position is derived — centred in the *glazed*
part of the tower, not the tower as a whole, so the blank bands don't push it
off-centre — and asserts fail the build if it lands on a blank band or breaks the
20-storey spacing rule.

### The blank bands, and what frames the long facade

Four of the reference tower's 40 occupied floors carry no openings at all — two at the bottom
(12.0 → 20.0 m) and two at the top (164.0 → 172.0 m), 8 m each. The piers left
and right are 2 m, one pane, so the frame is deliberately asymmetric: heavy top
and bottom, nearly open at the ends.

```
        8.0 m blank (2 floors)
      ┌─────────────────────────┐
 2.0  │   17 floors of          │  2.0
 pier │   18-pane windows       │  pier
      ├─────────────────────────┤
      │   sky garden (2)        │
      ├─────────────────────────┤
 2.0  │   17 floors of          │  2.0
 pier │   18-pane windows       │  pier
      └─────────────────────────┘
        8.0 m blank (2 floors)
```

The horizontal bands read as the building's cap and base; the ends stay open so the
corner apartments turn the corner onto their second aspect. 34 glazed floors in all:
17 above the garden, 17 below it.

Both bands are specified as target heights (`SOLID_BASE_TARGET`,
`SOLID_TOP_TARGET`) and rounded to whole floors, so a break always lands on a
floor line instead of cutting a window in half. At a 4 m floor height each is
exactly 2 floors.

The short facade uses the same 2.0 m pier, leaving 28 m of window in a 32 m face.
The companion's long facade expands from 18 to 20 room modules (80 m of clear
opening in the same 84 m envelope); its depth remains 32 m.
Getting there took two extra panes rather than a narrower building: `D` sets the
unit depth either side of the cores, and thinning the pier alone would have dropped
that depth to 8.0 m, under the 9 m a residential plan needs.

### Facade band layout

Each *glazed* floor repeats the same section, measured up from its floor level:

```
4.00 ┬───────────────────────────────  next floor
     │  1.50  solid spandrel
2.50 ├───────────────────────────────
     │  0.25  ventilation louvres
2.25 ├───────────────────────────────
     │
     │  1.50  window
     │
0.75 ├───────────────────────────────
     │  0.25  ventilation louvres
0.50 ├───────────────────────────────
     │  0.50  solid spandrel
0.00 ┴───────────────────────────────  floor level
```

`0.50 + 0.25 + 1.50 + 0.25 + 1.50 = 4.00 m`. The combined ventilation and
glass band starts 0.50 m above every floor, and the two vent strips remain flush
against the window.

The window and both vent strips run the width of every facade but stop short of
each corner, so all four corners stay solid wall: 2.0 m on both axes
(`PIER_LONG`, `PIER_SHORT`), one pane either way. The piers are L-shaped in plan —
a leg along each facade meeting at the corner — and fill the whole
vent + window + vent zone. Clear openings are 72 m on the reference tower's long
faces and 80 m on the companion's; both have 28 m on the short ones.

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

The pane is fixed at exactly **4.00 m × 1.50 m** of clear glass, on every facade.
The footprint is not an input — it is the pane count plus the piers, nothing else:

```
reference W = 18 panes x 4.00 + 2 x 2.00 pier = 76 m
companion W = 20 panes x 4.00 + 2 x 2.00 pier = 84 m
both towers D = 7 panes x 4.00 + 2 x 2.00 pier = 32 m
pane pitch = 4.00 m (identical on all four facades)
```

Mullions are 0.09 m **cover caps centred on each pane joint**: they overlap the
two panes they join rather than displacing them, so they consume no facade
length. (They are 0.14 m deep, but that depth runs *inward* from the flush face —
see above.) That is what keeps the arithmetic clean — 18 panes of 4 m is exactly
72 m of opening, and the footprint lands on whole metres. (An earlier version
added each mullion's width to the facade, which pushed the dimensions to
78.79 × 30.72 m; the caps fixed that.)

The reference tower has 50 panes per floor on 34 glazed floors; the companion has
54 panes per floor on 51 glazed floors. To resize a tower, change its
`configure_tower(groups, windows_long)` call (or the shared `WINDOWS_SHORT` / pier
widths) — never `W`/`D`, which are derived. Adding one pane to a long facade widens
that tower by exactly 4 m.

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

Each tower is generated from boxes and joined into the base facade/structure
objects (the saved scene contains the two sets with Blender's `.001` suffixes),
with one additional truss mesh on the taller companion, so the scene stays light
for a 178 m-wide site:

`Facade_Spandrels` · `Windows_Glass` · `Interior_Lining` · `Ceiling_Lights` · `Window_Mullions` ·
`Vent_Louvres` · `Vent_Shadowboxes` · `Sky_Garden_Grille` ·
`Sky_Garden_Planting` · `Sky_Garden_Trunks` · `Floor_Plates` · `Structure` ·
`Structural_Trusses` ·
`Ground`

## Changing the design

The shared `BLOCK_FLOORS = 17` sets the height of each residential group. `main()`
then calls `configure_tower(2, 18, core_column_bays=2)` for the existing tower and
`configure_tower(3, 20, core_column_bays=3)` for the companion. `TOTAL_FLOORS`,
`W` and `D` are derived from those group and pane counts (do not set them directly).
The column grid, core lengths, roof bulkheads and camera all derive from each
footprint, and the camera frames the combined site envelope.
Note that
`verify_house.py` carries its own copy of `W`, `D` and the floor counts — update it
to match, or its assertions will test the old dimensions. The five vertical bands
place the vent + glass + vent zone from 0.50 m to 2.50 m above each floor; an
`assert` fails the build if the bands stop summing to `H`.

The taller companion adds a dedicated `Structural_Trusses` mesh. At each of its
two double-height refuge levels, horizontal outrigger rails run from both cores
to the long-face belt, and a light single-diagonal panel pattern wraps around all
four refuge-level facades. Each core's long wall still gets an X-braced panel,
while four additional X panels are embedded in the upper refuge slab in plan so
they reinforce the diaphragm without crossing any ordinary residential window
band or sightline. The concrete cores remain continuous closed tubes; the metal
trusses are an added lateral-load path and a visible expression of the
core-to-perimeter connection.
