# Progress

## 2026-08-15 — main — make the materials actually visible on open

User reported the model still looked flat grey-white. Cause was not the
materials: Blender opens every 3D viewport in SOLID shading, which ignores
materials and draws a flat default grey. Confirmed by reading the saved file —
all viewports were SOLID except the Shading workspace.

First attempt was to set `space.shading.type = 'RENDERED'` inside the
`--background` build and save. That silently does nothing: viewport state is only
written back when a real UI exists, and it also reset the Shading workspace's
own MATERIAL mode to SOLID. Reverted it.

Changes:
- new `open_in_blender.py` — runs inside a GUI session, sets every 3D viewport to
  RENDERED with scene world and lights, extends clip_end to 4000 (a 160 m tower
  clips at the default), and frames the building. Falls back to a timer retry if
  no UI exists yet.
- new `view.sh` — one-line wrapper: `./view.sh`.
- `README.md` — a "Viewing it in Blender" section explaining the Z-key shading
  menu and why this cannot be baked into the .blend headlessly.

Verification:
- `sh -n view.sh` and an ast parse of open_in_blender.py both clean.
- Ran `blender --background out/highrise_house.blend --python open_in_blender.py`:
  reports "set 1 viewport(s) to RENDERED", no errors — so the script is safe in
  both GUI and headless contexts.
- Could not verify the GUI appearance itself; that needs the user to look.

Remaining issues:
- Whether the materials look right on screen is still unconfirmed by me.

## 2026-08-15 — main — materials: warm stone walls, green transmissive glass

User asked how to give the glass a real glass feel, with pale grey / beige walls
and a faint green transmissive glass.

Engine: Cycles. Blender 5.2 does NOT list CYCLES in the engine enum (only
BLENDER_EEVEE) but assigning it works and renders correctly — verified with a
test render before committing to it. Cycles is what gives real refraction.

Changes:
- new `materials.py` — palette in linear RGB (sRGB values in a colour socket
  render washed out), wall / concrete / metal / dark / ground / glass builders, a
  sky world, and one shared sun direction so the lamp and sky cannot drift apart.
- `build_house.py` — imports materials, replaces the six inline `make_material`
  calls, `RENDER_ENGINE`/`WALL_COLOR`/`GLASS_TINT`/`CYCLES_SAMPLES` knobs at the
  top, Cycles bounce settings (transmission 12 — the default 4 clips overlapping
  panes to black), AgX view transform.
- `render_views.py` — optional samples override argument.
- `README.md` — a Materials section documenting the three findings below.

Since images cannot be viewed in-session, the look was tuned by measuring
rendered pixels. Three real problems were found this way, none of which were
material-parameter issues:

1. The sun lit the wrong side. Rotation Z=-120 deg put the light coming from
   (-0.62, +0.36) — north-west — while every camera sits at +X/-Y looking at the
   south and east facades. The whole visible building was in shade under blue
   skylight, so the warm wall measured r-b = -0.106. Measured the emission vector
   for candidate azimuths rather than guessing; 38 deg puts the sun at
   (+0.44, -0.57, +0.69), the south-east. Wall brightness went 0.248 -> 0.529.
2. The Nishita sky was too blue. Isolated the material on a bare plane: warm
   under a neutral world (r-b = +0.081), cold under the sky (-0.162). So the wall
   colour was right and the lighting was wrong. Desaturated the skylight to 0.28
   and mixed 35% warm; wall now measures +0.020 on the real building.
3. Glass at transmission 1.0 rendered near-black — 0.101 brightness against a
   0.59 wall, i.e. a smoked panel. Found by ray-casting per pixel to mask only
   glass-hit pixels; a whole-frame average had hidden it, since it was dominated
   by spandrel. Transmission 0.75 + specular 0.75 + 0.06 emission brings glass to
   0.512 with green bias +0.108.

Verification:
- Build clean; per-surface measured values glass 0.404/0.512/0.470 (g-r +0.108),
  wall 0.601/0.594/0.577 (warm +0.020), metal and concrete plausible.
- Material properties read back from the saved .blend: engine CYCLES, 128 samples,
  transmission_bounces 12, AgX, sky world with TEX_SKY, glass trans 1.00->0.75
  IOR 1.52, spandrel base (0.635,0.590,0.500).
- `verify_house.py`: 59/59 still passing — geometry untouched by this change.
- 4 views re-rendered in Cycles, 48 s total.

Remaining issues:
- The look is verified numerically, never visually. The measurements say warm
  walls and bright green-tinted glass, but whether it looks good is the user's
  call.
- Glass brightness partly comes from a 0.06 emission standing in for lit
  interiors. If the user wants strict physical accuracy, model lit floor plates
  behind the glazing instead.

## 2026-08-15 — main — whole-metre footprint: 76 x 32 m

User asked why the dimensions had decimals, pointing out that 30 panes x 2 m plus
two 8 m piers should simply be 76 m, and restated that W/D must be derived from
the pane counts rather than the other way round. They were right: the decimals
were mine. The old code added each mullion's width to the facade length
(N panes + (N+1) x 0.09), injecting 2.79 m into the width and 0.72 m into the
depth. Depth had also dropped to 22.72 m, below the 30 m minimum they wanted.

Changes:
- `build_house.py` — mullions are now cover caps centred on each pane joint:
  they overlap the panes they join and add NO facade length. `opening_for(n)` is
  simply `n * PANE_W`, `PANE_PITCH` is `PANE_W`, and the caps are placed at exact
  multiples of the pane width from the opening edge (including one on each edge,
  against the pier). Short facade 7 -> 12 panes. Result: W = 30 x 2 + 2 x 8 = 76 m,
  D = 12 x 2 + 2 x 4 = 32 m, both exact. Added an assert that the footprint lands
  on whole metres. Removed the DEPTH_TARGET / derived-MULLION_W approach tried
  first, which hit 31 m depth but left the width at 78.5833 m.
- `verify_house.py` — 55 -> 59 checks. Mullion-length assumptions removed; added
  whole-metre footprint, footprint == panes + piers with no leftover, depth >= 30 m,
  and clear internal depth >= 30 m.
- `render_views.py` — W/D updated to 76/32.
- `README.md` — pane section rewritten around the cap detail, with a note on why
  the earlier version produced 78.79 x 30.72 m.

Verification:
- Build clean under Blender 5.2.0 LTS; 8 objects, 37776 vertices.
- `verify_house.py`: 59/59 passed — W=76.0000, D=32.0000 m exactly, clear internal
  depth 31.40 m, 31 caps -> 30 panes long / 13 -> 12 short, measured pane
  2.0000 x 1.50 m and pitch 2.0000 m on both faces, piers 8/4 m, long-facade
  margins all 8.00 m, blank bands unchanged.
- 4 views re-rendered.

Remaining issues:
- Images still not viewable in-session; verified geometrically, not by eye.

## 2026-08-15 — main — even 8 m frame on the long facade, 4 m piers on the short

User wanted the long (wide) facade to read with a uniform 8 m blank margin on all
four sides: keep its 8 m piers, drop the short-facade piers to 4 m, and grow the
bottom blank band from 1 floor to 2 (8 m) to match the top.

Changes:
- `build_house.py` — split `CORNER_PIER` into `PIER_LONG = 8.0` and
  `PIER_SHORT = 4.0`. `D` now derives from `PIER_SHORT`, giving 22.72 m (was
  30.72 m). `corner_piers()` builds an asymmetric L: an 8 m leg along the wide
  facade, a 4 m leg along the narrow. Added `SOLID_BASE_TARGET = 8.0` alongside
  the existing top target, both rounded to whole floors, so the base band is now
  2 floors (12.0 -> 20.0 m). Report prints the four long-facade margins.
- `verify_house.py` — same split. The corner-overlap region is now asymmetric
  (PIER_LONG in X, PIER_SHORT in Y) or it would have missed pieces. 54 -> 55
  checks; added an explicit assertion that the long facade's left/right, below
  and above margins are all exactly 8 m.
- `render_views.py` — D updated to 22.72, cameras nudged for the slimmer plan.
- `README.md` — replaced the "Blank bands" section with "An even 8 m frame on the
  long facade", including a diagram; noted the column grid is now 9 x 3.

Verification:
- Build clean under Blender 5.2.0 LTS; 8 objects, 35072 vertices.
- `verify_house.py`: 55/55 passed — footprint 78.790 x 22.720 m, piers measured
  8.000 m long / 4.000 m short, long-facade margins left/right 8.00, below 8.00,
  above 8.00 m, glazed floors now 2..34 (33 of 37), lowest glass at 21.250 m
  (above the 20.0 m band). Pane still exactly 2.0000 x 1.50 m both directions.
- 4 views re-rendered, framing re-checked by projection.

Remaining issues:
- Images still not viewable in-session; verified geometrically, not by eye.

## 2026-08-15 — main — fix the pane at 2.00 x 1.50 m, derive the footprint

User wants the window to be exactly 2.0 x 1.5 m, 30 panes on the wide face,
piers widened from 4 m to 8 m, and the footprint widened to suit in both
directions. So the dependency is inverted: the pane is now the fixed module and
W/D are computed from it.

Changes:
- `build_house.py` — `W`/`D` are no longer inputs. Added `PANE_W = 2.00`,
  `WINDOWS_LONG = 30`, `WINDOWS_SHORT = 7`, `CORNER_PIER` 4.0 -> 8.0, and
  `opening_for(n) = n * PANE_W + (n + 1) * MULLION_W`. Footprint follows:
  W = 62.79 + 16 = 78.79 m, D = 14.72 + 16 = 30.72 m. Pane pitch is a single
  2.09 m on all four facades (previously the short face had its own stretched
  pitch). Two asserts confirm panes + mullions sum to each opening exactly.
  Chose 7 panes for the short face as the value nearest the old 30 m depth.
- `verify_house.py` — same inversion; W/D derived from the module, not literals.
  51 -> 54 checks: added exact 2.00 x 1.50 m pane size, short-face panes also
  exactly 2.00 m, identical pitch on long and short facades, and piers measuring
  8 m. Footprint checks now state the derivation in their labels.
- `render_views.py` — W/D updated to 78.79/30.72 (used to place the detail
  camera) and the overview cameras pulled back for the larger footprint.
- `README.md` — rewrote the pane section as "the window is the module"; noted
  the column grid is now 9 x 4 (was 8 x 4), which followed automatically.

One assertion was relaxed rather than the design changed: "window is the majority
of each facade" now reads "openings are a meaningful share". With 8 m piers the
30.72 m short face is 16 m of wall against a 14.72 m opening, i.e. 47.9% open —
mostly wall. That is the direct consequence of the requested 8 m piers, so the
check was made to state it instead of failing on it. Flagging in case the short
face reads too closed.

Verification:
- Build clean under Blender 5.2.0 LTS; 8 objects, 36144 vertices.
- `verify_house.py`: 54/54 passed — footprint 78.790 x 30.720 m, 31 mullions ->
  30 panes long / 8 -> 7 short, measured clear glass exactly 2.0000 x 1.50 m on
  both faces, pitch 2.0900 m identical both ways, piers 8.00 m all round, opening
  62.7900 m = 30 x 2.0 + 31 x 0.09. Earlier invariants hold (window centred at
  2.00 m, 0.30 m vents flush, blank base floor, 8 m blank top band).
- 4 views re-rendered; framing re-checked by camera projection, all in frame.

Remaining issues:
- Images still not viewable in-session; verified geometrically, not by eye.

## 2026-08-15 — main — 30 panes per long facade

User asked for 30 windows across the wide facade and what that makes each pane.
Answer: 1.9737 m clear glass, on a 2.0637 m mullion pitch.

Changes:
- `build_house.py` — replaced `MULLION_SPACING` (a target spacing) with
  `WINDOWS_LONG = 30` (an exact count). Derived `PANE_GLASS_LONG`,
  `PANE_PITCH`, and `WINDOWS_SHORT` (11 panes at the same pitch) with an assert
  guarding against a count too high to fit. `mullions()` now places
  `WINDOWS_LONG + 1` mullions from the derived pitch. Report prints pane counts,
  pitch and clear glass width.
- Fixed a real geometry bug found by the new checks: the end mullions were
  centred on the opening edge, so half of each was buried in the corner pier.
  They are now inset half a mullion width, and the opening resolves exactly as
  30 x 1.9737 + 31 x 0.09 = 62.000 m.
- `verify_house.py` — 44 → 51 checks. Counts mullions per facade at one floor and
  derives the pane count from them, asserting 30 / 11 panes, even spacing, the
  2.0637 m pitch, 1.9737 m clear glass, end mullions flush inside the opening,
  and that panes + mullions sum to the opening exactly.
- `README.md` gained a "Pane division" section with the arithmetic.

Note on a false failure chased during this: "panes are evenly spaced" kept failing
with a spread exactly equal to whatever rounding I applied when collecting mullion
centres (1 mm, then 0.1 mm). The model was uniform throughout; the check was
quantising its own input. Fixed by deduping coincident centres by proximity
instead of rounding. Real spread is 0.000004 m.

Verification:
- Build clean under Blender 5.2.0 LTS; 8 objects, 38272 vertices.
- `verify_house.py`: 51/51 passed — 31 mullions -> 30 panes on the long face,
  12 -> 11 on the short, pitch 2.0637 m measured, clear glass 1.9737 m measured,
  end mullions at +/-30.9550 m as expected, spacing spread 4 microns. All earlier
  invariants hold.
- 4 views re-rendered.

Remaining issues:
- Images still not viewable in-session; verified geometrically, not by eye.

## 2026-08-15 — main — blank base floor and 8 m blank top band

User wanted no windows on the floor meeting the pilotis zone (looked
uncoordinated), plus roughly 8 m of blank wall at the top.

Changes:
- `build_house.py` — added `SOLID_BASE_FLOORS = 1` and `SOLID_TOP_TARGET = 8.0`
  with `SOLID_TOP_FLOORS = round(target / H)` = 2 floors. Rounding to whole
  floors keeps the break on a floor line instead of cutting a window in half.
  The per-floor loop now takes a `blank_floors` set; those floors get a
  full-storey-height solid `ring()` and a floor plate, and skip the window,
  vents, mullions and corner piers. Report prints both bands and the glazed count.
- `verify_house.py` — 39 → 44 checks. Counts that assumed every occupied floor
  is glazed now use `GLAZED_FLOORS` (glass Z levels, vent Z levels, glazing start
  height); floor plates still expect all 37, since blank floors keep theirs. New
  assertions: no window on the transition floor, bottom band solid up to 16 m, no
  glass above 152 m, top band measures exactly 8 m, blank bands aligned to the
  storey grid. The corner-zone sample floor is now derived from `FIRST_GLAZED`
  with an assert, rather than a hardcoded index that could land on a blank floor.
- `README.md` updated with a "Blank bands" section.

Verification:
- Build clean under Blender 5.2.0 LTS; 8 objects, 32832 vertices (down from
  35568 — three floors' worth of openings replaced by plain wall).
- `verify_house.py`: 44/44 passed — glazed floors are indices 1..34 (34 of 37),
  lowest glass at 17.250 m (above the 16.0 m blank base), highest at 150.750 m
  (below the 152.0 m blank top), top band exactly 2 x 4.0 = 8.0 m. All earlier
  invariants hold: window 1.50 m centred at 2.00 m, 0.30 m vents flush, 4.000 m
  corner piers on all four faces, 0 glass/louvre/mullion pieces in corner zones.
- 4 views re-rendered; floor_detail targets z=58 m, which is still a glazed floor.

Remaining issues:
- Images still not viewable in-session; verified geometrically, not by eye.

## 2026-08-15 — main — stop the ribbon short of the corners

User wanted the window to not wrap the corners: 4 m of solid wall at both ends
of every facade, same on all four sides.

Changes:
- `build_house.py` — added `CORNER_PIER = 4.0` with `OPEN_W`/`OPEN_D` derived
  (62.0 / 22.0 m clear opening) and an assert guarding against a pier too wide
  for the footprint. `glass_ring()` now builds four separate panes sized to the
  opening instead of a wrapping ribbon. New `corner_piers()` places an L-shaped
  wall at each corner (two legs, the second shortened by WALL_T so they meet
  without overlap) filling the whole vent+window+vent zone. `vent_strip()` and
  `mullions()` constrained to the opening; mullion loop now includes both ends
  so the glass is framed where it meets a pier.
- `verify_house.py` — 31 → 39 checks. Added `piece_bounds()` (connected-component
  bboxes) and `facade_span()` (per-facade extent), then new assertions: per-face
  opening widths, equal pier width on all four faces, and no glass/louvre/mullion
  overlapping any corner zone while wall geometry does.
- `README.md` updated.

Two bugs found in my own verification code while doing this, both fixed:
- `world_bounds()` on the joined glass object measures the overall bbox, so the
  E/W panes pinned the X extent at ~70 m regardless of the N/S pane length —
  the "stops short of corners" check could never pass. Replaced with per-facade
  vertex selection.
- The first corner test counted vertices inside a z-slice. A box spanning the
  slice has no vertices in it, so "no glass in corners" passed vacuously and
  "wall present in corners" failed on geometry that was actually there.
  Replaced with bbox-overlap testing per connected piece.

Verification:
- Build clean under Blender 5.2.0 LTS; 8 objects, 35568 vertices.
- `verify_house.py`: 39/39 passed — opening 62.000 m long face / 22.000 m short
  face, pier 4.000 m on all four faces, 0 glass/louvre/mullion pieces in any
  corner zone, 8 wall pieces present there (L-leg x 2 per corner x 4 corners),
  window still 88.6% of the long face and 73.3% of the short face. All earlier
  invariants still hold (1.50 m window centred at 2.00 m, 0.30 m vents flush).
- 4 views re-rendered.

Remaining issues:
- Images still not viewable in-session; verified geometrically, not by eye.

## 2026-08-15 — main — scale up to 70 x 30 m, 40 storeys

User asked for a larger building. Read 40 as the total storey count: 3 pilotis
floors + 37 occupied, 160.0 m to roof, 161.32 m to top of parapet.

Changes:
- `build_house.py` — `W` 20→70, `D` 14→30, added `TOTAL_FLOORS = 40` with
  `TOWER_FLOORS` derived from it. Replaced the three hardcoded column X
  positions with `col_grid()`, which spaces columns across any span at ~9 m
  bays; columns clashing with the core are skipped. Column size 0.85→1.60 m and
  core 5.0 × 4.2 → 14.0 × 9.0 m for the increased load. Roof plant, ground slab,
  ground plane and camera now derive from the footprint instead of fixed values.
- `verify_house.py` — constants updated to the new scale, plus 2 new checks
  asserting the footprint really is 70 × 30 m (29 → 31 checks).
- `render_views.py` — portrait 900 × 1400 frames (a 160 m tower crops badly in
  landscape), repositioned all cameras, added a `corner` view.
- `README.md` updated; noted that verify_house.py duplicates the dimensions.

Verification:
- Build clean under Blender 5.2.0 LTS; 8 objects, 34976 vertices.
- `verify_house.py`: 31/31 passed — footprint 70.000 × 30.000 m, 37 window bands
  all 1.50 m and centred at 2.00 m of a 4.00 m floor, glazing spans 99.7% of X
  and 100% of Y, all vent bands 0.30 m flush above/below each window, no facade
  geometry below 12.0 m, structure -0.30 → 163.60 m.
- Framing checked numerically by projecting model bounds through each camera
  (world_to_camera_view): front/base/corner fully inside 0..1 in both axes,
  floor_detail intentionally fills the frame. 5 renders written, ~1.3 MB each.

Remaining issues:
- Still could not view images in-session; renders verified by projection maths
  and file size, not by eye.

## 2026-08-15 — main

Initial repo: procedural Blender high-rise house generator.

Changes:
- `build_house.py` — generates the model. 20 × 14 m footprint, 4.0 m floor
  height, 3 open pilotis floors (columns + service core) carrying 12 occupied
  floors, 62.60 m to top of parapet. Per floor: 0.95 m spandrel / 0.30 m vent /
  1.50 m window / 0.30 m vent / 0.95 m spandrel, so the window is centred at
  mid-floor. Window and vent strips wrap all four facades at full width. Saves
  `.blend`, `.glb` and an EEVEE render into `out/`.
- `verify_house.py` — 29 geometry assertions over the saved `.blend`.
- `render_views.py` — front elevation, pilotis base, floor close-up.
- `README.md`, `.gitignore`.

Verification:
- Build ran clean under Blender 5.2.0 LTS; 8 objects, 6408 vertices.
- `verify_house.py`: 29/29 checks passed — every window 1.50 m and centred
  (offset 2.00 m in a 4.00 m floor), 12 window bands, glazing spans 99.1% of X
  and 100% of Y, all vent bands 0.30 m and flush above/below each window, no
  facade geometry below 12.0 m, structure from -0.30 m to 62.60 m.
- 4 renders written, all ~1.2 MB non-blank PNGs.

Remaining issues:
- Image files could not be viewed inside this session, so the renders were
  confirmed by geometry assertions and file-size checks rather than by eye.
  Worth a visual look at `out/preview.png` and `out/view_base_pilotis.png`.
