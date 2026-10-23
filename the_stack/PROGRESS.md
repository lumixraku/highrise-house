# The Stack — Progress

## 2026-09-12 — main — wind slots snapped to the facade grid

Client review: the wind slots should line up with the apartment-band cells.

- Added `BAND_BAY` (the apartment band's mullion spacing, `WIDTH / round(WIDTH
  / 7)` = 7.1875 m) and sized `WIND_TUNNELS` from it: each slot is two bays
  wide (14.375 m) and ten apartment storeys tall (40 m), centred on mullion
  positions and storey levels. The lining walls now land on the mullions and
  the opening edges meet the horizontal slab bars exactly.

Verification:
- `python3 -m py_compile build_the_stack.py verify_the_stack.py` pass.
- Blender rebuilt `out/the_stack.blend` (7483 objects) and re-rendered preview,
  elevation and section; the wind slots now read as two clean grid bays.
- `verify_the_stack.py` pass; 34 checks.
- `git diff --check` pass.

Remaining issues: None known.

## 2026-09-12 — main — connected apartment-band grid, one slab bar per floor

Client review: the band read as a broken brick bond — the staggered running
bond left the frame lines unconnected. Every floor should carry a continuous
horizontal bar (the slab edge) and the grid should be joined.

- `band_brick` rebuilt as one connected grid instead of a running bond. Course
  boundaries now come from `storey_levels()`, so each horizontal `Brick_Bed`
  bar lines up with a real floor plate; vertical `Brick_Joint` mullions are on
  a regular 7 m grid and run unbroken through every floor (only split around
  the wind slots). The staggered panes, random pane widths and the feature bay
  were removed.

Verification:
- `python3 -m py_compile build_the_stack.py verify_the_stack.py` pass.
- Blender rebuilt `out/the_stack.blend` (7434 objects) and re-rendered preview,
  elevation and section; the upper band now reads as a connected glass-and-frame
  grid with a slab bar at every floor.
- `verify_the_stack.py` pass; 34 checks.
- `git diff --check` pass.

Remaining issues: None known.

## 2026-09-12 — main — readable apartment-band frame

Client review: the apartment band's frame was a hairline (0.12-0.14 m beams),
invisible from a distance. The frame should occupy real width.

- `band_brick` bed and joint members are now flat panels, not round beams:
  `bed_w = 0.8` m horizontal bands and `joint_w = 0.7` m vertical mullions,
  laid in the same running bond over the dark glass skin.

Verification:
- `python3 -m py_compile build_the_stack.py verify_the_stack.py` pass.
- Blender rebuilt `out/the_stack.blend` (8195 objects) and re-rendered preview,
  elevation and section; the upper band now reads as a brick-like glass-and-
  frame grid from both close and distance.
- `verify_the_stack.py` pass; 34 checks.
- `git diff --check` pass.

Remaining issues: None known.

## 2026-09-12 — main — apartment band is glazing and frame, not a white wall

Client review: the top band showed a lot of solid white wall between the panes.
The design is glass with a large frame, so no masonry should show.

- `band_brick` no longer builds a masonry backing. `Brick_Back` became
  `Brick_Glass`, a continuous dark glass skin (new `Stack_Glass_Dark`), and the
  panes and feature bay now use the same dark glass instead of opaque
  `window_dark`/`brick` fills. The only light elements left are the white
  `Brick_Bed`/`Brick_Joint` frame lines, which still lay the running bond.
- Removed the now-unused `window_dark` material.

Verification:
- `python3 -m py_compile build_the_stack.py verify_the_stack.py` pass.
- Blender rebuilt `out/the_stack.blend` (8195 objects) and re-rendered preview,
  elevation and section; a close render of the upper band shows dark glass with
  the white frame and no white wall.
- `verify_the_stack.py` pass; 34 checks, including new `apartment band is
  glazed` (`Brick_Glass` present, `Brick_Back` absent).
- `git diff --check` pass.

Remaining issues: None known.

## 2026-09-12 — main — 14 mall floors with plates, tall wind slots, 346.8 m

Client review: the mall base was too tall and its floors were not visible, and
the two wind openings in the apartment band were too small.

- Mall reduced from 16 to 14 floors (`MALL_FLOORS=14`), so `LEVEL_BASE=70`,
  `LEVEL_APARTMENT=220`, `LEVEL_ROOF=344`. The client chose to cap the total at
  ≤350 m, so `HEIGHT` is now 346.8 m (14x5 + 30x5 + 31x4 = 344 m, plus a 2.8 m
  roof) over 75 floors. Band boundaries moved down 10 m to 100/120/160/175/200.
- `add_interior` now lays one ring of mall plates per retail storey around a
  central atrium (`MALL_VOID_X/Y`), so all 14 mall floors read through the
  glass while the escalator still climbs the void. The escalator was shortened
  to fit the atrium (x -28..28, z 3..64) with its return flight and landings.
- `WIND_TUNNELS` changed from 13 m squares to 16 x 44 m vertical slots at z 258
  and 308, so wind openings are much larger and read as tall strips; the lining
  builder, the brick-band hole cut and the slab splits all follow the new
  (x, z, width, height) tuples.
- Scene metadata adds `model_height_m`; `published_height_m` stays 356.8 m as
  the published figure.

Verification:
- `python3 -m py_compile build_the_stack.py verify_the_stack.py` pass.
- Blender rebuilt `out/the_stack.blend` (8188 objects) and re-rendered preview,
  elevation and section; close renders show 14 mall plates with the atrium
  escalator, and two tall vertical wind slots in the upper band.
- `verify_the_stack.py` pass; 33 checks, including new `model height recorded`,
  `mall storey plates` and `wind slots are vertical`.
- `git diff --check` pass.

Remaining issues: None known.

## 2026-09-12 — main — explicit storey program (77 floors, 5/5/4 m)

The facade read as 100-plus floors because floor plates were laid every 4.4 m
and the apartment band carried thin 3 m courses with no relation to storeys.
Replaced that with an explicit program: 5 m mall, 5 m offices, 4 m apartments.

- New storey constants: `MALL_FLOORS=16`, `OFFICE_FLOORS=30`,
  `APARTMENT_FLOORS=31` at `MALL_H=OFFICE_H=5.0` and `APARTMENT_H=4.0`. That is
  77 floors and 354 m, with a 2.8 m roof structure under the unchanged 356.8 m
  top. `storey_levels()` returns every floor level.
- Band boundaries now sit on the storey grid: `LEVEL_BASE=80`,
  `LEVEL_APARTMENT=230`, `LEVEL_ROOF=354`, and the intermediate boundaries
  snapped to 110/130/170/185/210 m.
- `add_interior` lays one slab per storey from the first office floor to the
  top (mall stays an open glazed atrium), and the core transfer ties moved to
  the new boundaries.
- `band_brick` now uses one course per apartment storey, so the masonry band
  reads as 31 floors instead of an indeterminate stack of lines.
- Scene metadata records `floor_count`, per-zone floor counts and
  `storey_heights_m`.

Verification:
- `python3 -m py_compile build_the_stack.py verify_the_stack.py` pass.
- Blender rebuilt `out/the_stack.blend` (8201 objects) and re-rendered preview,
  elevation and section; the elevation shows one masonry course per apartment
  floor.
- `verify_the_stack.py` pass; 31 checks, including new `storey program
  recorded` and `storey heights recorded`.
- `git diff --check` pass.

Remaining issues: None known.

## 2026-09-12 — main — transparent base hall with a long escalator

The base read as a solid glowing wall: an emissive `Base_Glow` panel sat just
inside each face and opaque `Base_Spandrel` bands covered the glass, so no
interior showed. Rebuilt the base as the reference model shows it — a pure
transparent glass curtain wall over one full-height hall, with the structure
inside reading through the panes.

- `band_base` now lays a single clear pane (`Stack_Glass_Clear`, a new
  near-white glass) per face with a fine white mullion/transom frame and no
  spandrels. The unused `base_spandrel` and `glass_warm` materials were removed.
- New `base_interior`: one very long escalator climbing the full hall (two
  close side beams, handrails, 25 short treads), a return flight with landings,
  a white stair block at the foot, warm glow on the floor and ceiling, and
  three warm area lights inside.
- `add_interior` skips floor plates below `LEVEL_BASE`, so the base is an open
  81 m hall rather than a stack of storeys.

Verification:
- `python3 -m py_compile build_the_stack.py verify_the_stack.py` pass.
- Blender rebuilt `out/the_stack.blend` (8630 objects) and re-rendered preview,
  elevation and section; a close render of the base shows the transparent glass
  with the escalator, treads and stair block lit warmly inside.
- `verify_the_stack.py` pass; 29 checks, including new `open base hall` and
  `long escalator in base`.
- `git diff --check` pass.

Remaining issues: None known.

## 2026-09-12 — main — switch-diagram woodland that runs to the band top

The candelabra trees still had branches that stopped in mid-air. The facade
model instead reads like a railway switch diagram: one trunk forks, and every
resulting line runs all the way to the top of the block. Rewrote `forest_tree`
as a binary merge tree: a thick trunk rises to a fork, then each level pairs up
into parents with smooth `arc_beam` curves, and all 2^depth lines terminate
exactly at the band top. Depth is two or three levels, chosen per tree, with
jittered tips.

Verification:
- `python3 -m py_compile build_the_stack.py verify_the_stack.py` pass.
- Blender rebuilt `out/the_stack.blend` (8821 objects) and re-rendered the
  preview, elevation and section; a straight-on render of the upper garden band
  shows the forks all reaching the top edge with nothing broken in between.
- `verify_the_stack.py` pass; all 27 checks passed.
- `git diff --check` pass.

Remaining issues: None known.

## 2026-09-12 — main — thicker candelabra woodland on the garden bands

The garden-band trees read as thin straight lines. The facade model actually
draws them as thick members whose forks sweep in smooth arcs, like the arms of
an old candelabra. Added an `arc_beam` helper that traces a quadratic Bezier as
a chain of short beams, and rewrote `forest_tree` to use it: a 0.8 m-thick
trunk carrying thick arms that leave almost level and curve upward, with lower
arms reaching further out, each arm sprouting a sub-arm. Each tree now varies
its height and takes three to five branch levels so the row is not uniform.

Verification:
- `python3 -m py_compile build_the_stack.py verify_the_stack.py` pass.
- Blender rebuilt `out/the_stack.blend` (11709 objects) and re-rendered the
  preview, elevation and section; a straight-on render of the upper garden band
  shows the thick curved woodland over the glazing.
- `verify_the_stack.py` pass; all 27 checks passed.
- `git diff --check` pass.

Remaining issues: None known.

## 2026-09-12 — main — metal line-drawing woodland on the garden bands

The two sky-garden bands had a few 3D trees on the facade. The facade model
shows the exterior skin of these bands is instead a white-steel line drawing of
a wood: stylised tree outlines fixed to the outside of the glazing. Rebuilt
`band_garden` around a new `forest_tree` helper that draws each tree as a trunk
with five pairs of branches, every branch carrying a twig, in thin white steel
at the facade plane. The old 3D trees are kept but reduced and recessed behind
the glass so the glazing still reads as a garden.

Verification:
- `python3 -m py_compile build_the_stack.py verify_the_stack.py` pass.
- Blender rebuilt `out/the_stack.blend` (8113 objects) and re-rendered the
  preview, elevation and section; a straight-on render of the upper garden band
  shows the white line woodland over the glazing.
- `verify_the_stack.py` pass; all 27 checks passed.
- `git diff --check` pass.

Remaining issues: None known.

## 2026-09-12 — main — 40 m depth and two wind tunnels

Widened the short side from the drawing's 34 m to 40 m, per the client's load
concern; the override and its reason are stored in the scene metadata
(`depth_override_m`, `depth_override_note`) so the deviation from the elevation
sheet stays explicit. Added the two square wind tunnels the model photo shows
in the upper apartment band: 13 m square openings at (x -16, z 305) and
(x 10, z 268), running the full 40 m depth so they pierce both long faces and
let wind through. Each tunnel gets a concrete box lining that stands 0.2 m
proud of the facade, the masonry backing and courses are cut around the
openings, and the floor plates are split so the tunnels stay clear. The long
feature pane now sits between the two tunnels so it survives on every face.

Verification:
- `python3 -m py_compile build_the_stack.py verify_the_stack.py` pass.
- Blender rebuilt `out/the_stack.blend` (5237 objects) and re-rendered the
  preview, elevation and section; a straight-on front render shows the two
  openings reading through to the sky, and a straight-on east render shows the
  short faces are unpierced.
- `verify_the_stack.py` pass; all 27 checks passed, including the new
  "wind tunnels" check and the 40 m depth check.
- `git diff --check` pass.

Remaining issues: None known.

## 2026-09-12 — main — long brick-like glazing and real z-fighting fix

Two separate problems in the upper apartment band. First the band was a solid
masonry wall with short punched windows, not the long glazing the reference
calls for; it is now a running bond of long horizontal glass panes (median
aspect above 2:1) over a recessed masonry backing, with one longer feature pane
across whole courses at the band's centre. Second, the "z-fighting" was a depth
precision problem, not coincident geometry: the preview cameras had the default
0.1 m near plane, which at a 600 m view distance leaves only ~0.2 m of usable
depth resolution, so the 0.06 m window-to-wall offset flickered. Set every
camera's clip start to 5 m (clip end 3000 m) and the viewport's clip start too,
and pushed the shallowest facade offsets apart as well (porthole discs 0.10 to
0.24, fin backs to -0.10, masonry backing to -0.30, crown inset to WIDTH-1.0).

Verification:
- `python3 -m py_compile build_the_stack.py verify_the_stack.py` pass.
- Blender rebuilt `out/the_stack.blend` (5090 objects) and re-rendered the
  preview, elevation and section; a low grazing-angle render and a 600 m
  zoomed render show the long courses with no depth flicker.
- `verify_the_stack.py` pass; all 26 checks passed, including the new
  "upper glazing is long" check and the updated masonry-band marker.
- `git diff --check` pass.

Remaining issues: The measured depth is still 34 m pending the user's call on
whether to deviate from the elevation sheet.

## 2026-09-12 — main — frame the saved viewport on the whole building

Opening `out/the_stack.blend` started inside the tower because the generator
never set the 3D viewport. Added `frame_viewport`, which points every saved
VIEW_3D area at the same exterior orbit as the preview camera (pivot at
(0, 0, 175), distance ~656 m, perspective, lens 55, clip end 6000), so the file
opens showing the complete building without zooming out.

Verification:
- `python3 -m py_compile build_the_stack.py verify_the_stack.py` pass.
- Blender rebuilt `out/the_stack.blend` (4243 objects); reopening it reports
  every VIEW_3D at distance ~656 m on the exterior.
- `verify_the_stack.py` pass; all 25 checks passed, including the new
  "viewport framed on building" check.
- `git diff --check` pass.

Remaining issues: None known.

## 2026-09-12 — main — re-measure depth, flat top, horizontal glazing

Re-measured the envelope on the orthographic elevation sheet with a lower
threshold: front elevation 321 px wide, side elevation 94 px wide, both 992 px
tall against the published 356.8 m. That is 115.5 x 33.8 m, so the depth moved
from 33 to 34 m; the axonometric and model photos are perspective views and
cannot override this reading. Reworked the facade to match the reference band
order (base, portholes, trees, diagrid, louvre with the eye, fins, trees,
masonry) and made the top a single flat plane instead of stepped setbacks: the
masonry band now runs to 356.8 m over a solid crown that keeps the cores flush.
The masonry glazing is now a horizontal ~3:1 ribbon instead of square panes.

Verification:
- `python3 -m py_compile build_the_stack.py verify_the_stack.py` pass.
- Blender rebuilt `out/the_stack.blend` (4243 objects) and re-rendered the
  preview, elevation and section; the top is flat, the cores are enclosed, and
  the upper glazing reads as horizontal ribbons.
- `verify_the_stack.py` pass; all 24 checks passed, including the new flat-top
  and depth checks.
- `git diff --check` pass.

Remaining issues: The measured depth is 34 m; if a deeper slab is wanted it is a
deliberate deviation from the elevation sheet and must be confirmed.

## 2026-09-12 — main — make The Stack cores flush with the top

The reference drawings show no protruding cores: the service cores finish flush
with the building's top surface. Replaced the open stepped roof (which left the
two cores standing above the roofline) with a solid stepped masonry crown that
fills the footprint and covers the core area up to 356.8 m, topped by the
planted City Plaza deck at the top surface. The cores and crown are now flush,
so nothing protrudes above the building line.

Verification:
- `python3 -m py_compile build_the_stack.py verify_the_stack.py` pass.
- Blender rebuilt `out/the_stack.blend` (3816 objects) and re-rendered the
  preview, elevation and section; no cores are visible above the roof.
- `verify_the_stack.py` pass; all 24 checks passed, including new checks that
  the crown reaches 356.8 m and that no core exceeds the top surface.
- `git diff --check` pass.

Remaining issues: None known for the exterior.

## 2026-09-12 — main — fix The Stack facade Z-fighting

Removed the coplanar faces that made the facade shimmer. Each facade element now
occupies a distinct outward depth on a fixed ladder (backing wall, glass,
windows, spandrels, mullions, slats, diagrid, louvres, fins) instead of sharing a
plane. The short east/west faces are also inset by 0.02 m at the corners and sit
0.02 m further out than the long faces, so the two faces meeting at a corner no
longer coincide. The ground slab top dropped below z=0 and the roof slab and
roof steps were nudged off the apartment band top, removing the remaining
coincident horizontal planes.

Verification:
- `python3 -m py_compile build_the_stack.py verify_the_stack.py` pass.
- Blender rebuilt `out/the_stack.blend` (3825 objects) and re-rendered the
  preview, elevation and section; the straight-on elevation shows clean bands
  with no striping.
- `verify_the_stack.py` pass; all 21 checks passed.
- `git diff --check` pass.

Remaining issues: None known for the exterior.

## 2026-09-12 — main — rebuild The Stack exterior as stacked neighbourhood bands

Reviewed all eleven MVRDV gallery images (renders 01-07, aerial, axo, model,
section, neighbourhoods, plazas, elevation/section sheet). The exterior was
wrong: the earlier model was a plain glazed box, while the proposal is a slender
slab whose facade is a vertical stack of differently detailed horizontal bands.
Rebuilt `build_the_stack.py` around that band language, wrapping all four faces:

- warm glazed retail base with visible diagonal escalators and floor spandrels
- dark porthole band with scattered circular windows
- vertical slat band
- diamond diagrid band
- planted sky-garden band (trees behind glazing)
- louvre band with the central diamond "eye"
- tall vertical-fin band
- masonry apartment band with a punched-window grid
- stepped, planted City Plaza roof

Envelope re-measured from the elevation sheet with pixel analysis (front 319 px,
side 92 px, height 992 px) confirming 115 x 33 x 356.8 m, so the massing stayed
and only the facade changed. Floor slabs now stop at the roof band so the City
Plaza no longer exposes stacked plates. Interior remains schematic (two cores
and transfer links).

Verification:
- `python3 -m py_compile build_the_stack.py verify_the_stack.py` pass.
- Blender rebuilt `out/the_stack.blend` (3873 objects) and re-rendered
  `out/the_stack_preview.png`, `out/the_stack_elevation.png` and
  `out/the_stack_section.png`; the three views show the band sequence on the
  long and short faces.
- `verify_the_stack.py` pass; all 21 checks passed, including each facade band,
  band wrapping on four faces, and the image-scaled width/depth.
- `git diff --check` pass.

Remaining issues: Facade bands are an image-led interpretation of the model and
renders, not as-built detail. Interior fit-out is still schematic.

## 2026-09-12 — main — build The Stack (MVRDV 2018 competition)

Added a standalone generator and verifier for MVRDV's The Stack competition
proposal (`build_the_stack.py`, `verify_the_stack.py`). The envelope was
measured from the orthographic elevation sheet in the MVRDV gallery: about
319 px wide, 89 px deep and 992 px tall against the published 356.8 m height,
giving 114.8 x 32.0 m, rounded to 115 x 32 m (replacing the earlier guessed
100 x 22 m). The model stacks 76 storeys with four planted sky plazas, a porous
retail base, a performance block, public escalators, and two separated service
cores with transfer links along the long axis.

Verification:
- `python3 -m py_compile build_the_stack.py verify_the_stack.py` pass.
- Blender rebuilt `out/the_stack.blend` (6927 objects) and rendered
  `out/the_stack_preview.png`, `out/the_stack_elevation.png` and
  `out/the_stack_section.png`; all three show the complete long, thin slab.
- `verify_the_stack.py` pass; all 14 checks passed, including the
  image-scaled width/depth and the 3.5-3.7 thin-slab proportion.
- `git diff --check -- build_the_stack.py verify_the_stack.py` pass.

Remaining issues: None. Dimensions are an image-led approximation, not as-built.
