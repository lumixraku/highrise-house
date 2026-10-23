# Abeno Harukas — Progress

## 2026-09-05 — main — correct Abeno Harukas plan proportions

Reworked the three tower tiers from near-square footprints into long, thin bar
volumes based on the latest user-provided massing references. The lower, middle,
and upper tiers now measure approximately 72 x 40 m, 68 x 32 m, and 64 x 24 m,
with progressively shallower plans and northward offsets while retaining the
continuous east edge and the 80 m / 195 m vertical transitions. The grounded
annex was widened and repositioned to preserve the broad low-rise base. Added
verification checks for tier aspect ratios, decreasing depth, and plan offset.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `blender --background --factory-startup --python build_abeno_harukas.py` pass;
  regenerated the Blender scene and perspective, front, side, and silhouette
  review renders.
- `blender --background --factory-startup --python verify_abeno_harukas.py -- out/abeno_harukas.blend`
  pass; all 15 scene, section, and plan-proportion checks passed.
- Visually reviewed all four renders; the front view exposes the long facade,
  while the side view confirms the substantially thinner stepped depths.
- `git diff --check` pass.

Remaining issues: Exact plan dimensions and offsets remain approximate because
the available public diagrams and reference images do not provide a complete
dimension chain.

## 2026-09-05 — main — use published section as Abeno Harukas silhouette test

Reworked the tower again using the user-provided elevation/program and
structural-section references as the primary silhouette constraint. The tower
now uses a continuous east edge with west-side tier setbacks, section-derived
height bands at 0–80 m, 80–195 m, and 195–300 m, a grounded low annex, and
explicit facade recess markers. Added a black-on-white orthographic elevation
test render so the massing can be judged independently from glass, lighting,
and facade mullions.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `blender --background --factory-startup --python build_abeno_harukas.py` pass;
  generated the perspective, front, side, and
  `out/abeno_harukas_elevation_test.png` renders.
- `blender --background --factory-startup --python verify_abeno_harukas.py -- out/abeno_harukas.blend`
  pass; all 13 scene and section-constraint checks passed.
- `git diff --check` pass.

Remaining issues: The black silhouette now follows the selected section test,
but the model still needs a direct image-overlay comparison against the exact
elevation crop to tune the annex length, terrace/recess widths, and crown
details. The public section is schematic and does not provide a complete
dimension chain.

## 2026-09-05 — main — recalibrate Abeno Harukas massing and review views

Reworked the Abeno Harukas approximation after rejecting the first three-box
interpretation. The procedural scene now uses a broad 0–28 m podium, a separate
lower west wing, a narrower lower/middle/upper tower sequence, larger image-
calibrated transfer zones, and explicit front and side orthographic review
cameras. The plan dimensions remain labelled as approximate because no
dimensioned public plan was found.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `blender --background --factory-startup --python build_abeno_harukas.py` pass;
  generated `out/abeno_harukas_preview.png`,
  `out/abeno_harukas_front.png`, and `out/abeno_harukas_side.png`.
- `blender --background --factory-startup --python verify_abeno_harukas.py -- out/abeno_harukas.blend`
  pass; all 11 structural/documentation checks passed.
- `git diff --check` pass.
- Visually reviewed the perspective, front, and side renders against the saved
  elevation and building-photo references.

Remaining issues: The model still approximates the real facade zoning,
observatory crown, terrace depth, and perspective-specific offsets. The current
checks prove scene construction constraints only; they do not prove survey
accuracy or image similarity.

## 2026-09-05 — main — build approximate Abeno Harukas model

Added `build_abeno_harukas.py` and `verify_abeno_harukas.py` for a procedural,
editable reconstruction of Abeno Harukas. The scene uses the documented 300 m
height and 60 floors, three offset facade volumes, two exposed megatruss zones,
two setback sky gardens, curtain-wall mullions, a central core, and a top
observatory cap. Width and depth remain explicitly labelled as estimates based
on public imagery and the published 2,400 m2 office standard floor because no
complete dimensioned public plan was found.

The preview lighting and camera were adjusted for clearer facade separation and
side elevation readability. The result is an architectural approximation, not
a survey-grade or construction-grade BIM model.

Verification:
- `blender --background --factory-startup --python build_abeno_harukas.py`
  completed and generated `out/abeno_harukas.blend` plus its preview render.
- `blender --background --factory-startup --python verify_abeno_harukas.py --
  out/abeno_harukas.blend` completed with `All 7 checks passed`.
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` and
  `git diff --check` pass.
- Visually reviewed the updated 900 x 1400 preview against the collected
  Pinterest and structural-reference screenshots.

Remaining issues: The public evidence does not support exact plan dimensions;
the current approximation still simplifies the reference's terraces, gardens,
and observatory crown.

## 2026-09-08 — main — taper Abeno Harukas tower plans

Updated the Abeno Harukas generator so the three main tower tiers use lightly
trapezoidal footprints: the south edge remains 71 m while the east/west edges
slope inward toward each tier's north edge. North and south truss spans now use
their corresponding footprint widths, and the scene metadata and verification
checks describe and enforce the tapered plan instead of a rectangular massing.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `git diff --check` pass.
- Blender 5.2.0 build with `-- --views preview plan --samples 16` pass; both
  renders and the editable `.blend` were saved under `out/`.
- `verify_abeno_harukas.py` pass; all 16 checks passed, including the new
  tapered-plan check.

Remaining issues: Render files are generated successfully but were not visually
opened in this session because `out/` is ignored by the workspace file reader.

## 2026-09-08 — main — rebuild Abeno Harukas body-first

Replaced the previous Abeno Harukas generator with a clean body-first model.
The new generator has only the three primary stacked tower bodies, each built
from one four-corner trapezoidal prism. The south edges stay aligned at Y=-40,
the east/west edges slope inward northward, and the tier depths are 80 m, 59 m,
and 29 m with level breaks at 80 m and 195 m. Schematic facade mullions are
included; complex core, trusses, and interior systems are intentionally deferred.
The verification script was rewritten around these massing constraints.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `git diff --check` pass.
- Blender 5.2 body build with `-- --no-render` pass; 343 objects generated.
- `verify_abeno_harukas.py` pass; all 16 checks passed.
- Blender rendered `preview`, `plan`, and `north` views successfully.

Remaining issues: None for the body-first scope. Core, truss, and detailed facade
systems remain intentionally out of scope for this pass.

## 2026-09-08 — main — skew the middle tower body

Adjusted only the Middle body footprint. Its north edge now shifts 3 m east
while the south edge stays aligned with the other tower bodies, making the two
long side edges visibly asymmetric: the west/left edge carries the stronger
slope and the east/right edge stays closer to the upper body's side. This is
implemented in the footprint vertices and not as a camera or object rotation.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `git diff --check` pass.
- Blender rebuild with `-- --no-render` pass.
- `verify_abeno_harukas.py` pass; all 18 checks passed, including asymmetric
  middle-edge slope checks.
- Blender rendered `preview`, `plan`, and `north` successfully.

Remaining issues: None for the requested middle-body plan correction.

## 2026-09-08 — main — reconnect the three Harukas masses horizontally

Replaced the vertically stacked tier massing with the user's sketch layout:
three volumes of different heights (Low 80 m, Middle 195 m, High 300 m) all
stand on the same ground plane and connect horizontally south to north,
sharing their full connecting edges. Each volume is a different quadrilateral
plan defined in MASSES; the long side edges tilt inward toward the high
volume. The middle volume's east side extends outward — its SE corner
(36, -11) is the composition's outermost point — while its west edge stays
collinear with the high volume's west edge. The ground prism is the exact
octagonal union of the three plans. Added a sun light and node-based world
background so EEVEE review renders are visible (previous renders were
effectively black), and re-aimed the preview camera from the southeast with
full framing. verify_abeno_harukas.py now hard-checks every plan corner,
the shared connecting edges, the ground union, and the middle-volume
asymmetry.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `git diff --check` pass.
- Blender 5.2.0 full build pass; 564 objects; preview/plan/north renders
  saved and visually inspected: plan matches the sketch (three connected
  quadrilaterals, east bulge at the middle volume, near-straight west side),
  preview shows the 80/195/300 m steps rising south to north, and the north
  elevation shows the east bulge with the west side flush.
- `verify_abeno_harukas.py` pass; all 20 checks passed.

Remaining issues: None for the massing scope. Facade grids remain schematic;
core and truss systems are still out of scope for this pass.

## 2026-09-08 — main — slope the Harukas roofs in Z

Follow-up to the horizontal reconnection: the long top edges now tilt in Z.
Each volume's roof is a single plane with constant dz/dx (west/east top
heights: Low 90/70, Middle 215/175, High 300/284), so all three masses have
sloped roofs with different gradients. The middle volume's west side rises
toward the high volume's top while its east side drops away, matching the
requested "one side near, one side far" relationship; the plan geometry
(east bulge, collinear west edges, shared connecting edges) is unchanged.
Facade mullions follow the sloped tops, transoms stop below the lowest top
edge, and each sloped top edge gets a cap beam. The verifier now checks
every roof corner height, the three distinct slopes, and the middle/high
top-height relationship.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `git diff --check` pass.
- Blender 5.2.0 full build pass; 540 objects; preview and north renders
  visually inspected: all three roofs visibly slope along X, with the middle
  roof falling from 215 m (west) to 175 m (east).
- `verify_abeno_harukas.py` pass; all 23 checks passed.

Remaining issues: None for the massing scope. Facade grids remain schematic;
core and truss systems are still out of scope for this pass.

## 2026-09-08 — main — slant the Harukas connecting edges in plan

Corrected the tilt axis after user feedback: the tilt belongs to the plan
(the long connecting edges lean along the north-south direction, as drawn in
the user's sketch), not to the roof heights. Reverted the sloped roofs; all
three masses again have flat roofs at 80/195/300 m. The footprints are now
three irregular quadrilaterals exactly like the sketch: the low/middle
dividing edge drops toward the east while the middle/high dividing edge
climbs toward the east (opposite slants), the low south edge and high north
edge stay straight east-west, and the middle volume's SE corner (36, -15)
remains the composition's outermost point to the east with its west side
approaching the high volume. Ground octagon, cameras, and lighting
unchanged. The verifier now hard-checks the slanted connecting edges, the
opposite slant directions, the straight outer short edges, and flat roofs.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `git diff --check` pass.
- Blender 5.2.0 full build pass; 564 objects; plan and preview renders
  visually inspected: the plan matches the sketch (two slanted dividing
  lines with opposite slants, east bulge at the middle volume, kinked west
  silhouette), and the preview shows the three flat-roofed masses stepping
  80/195/300 m south to north.
- `verify_abeno_harukas.py` pass; all 22 checks passed.

Remaining issues: None for the massing scope. Facade grids remain schematic;
core and truss systems are still out of scope for this pass.

## 2026-09-08 — main — open the Harukas scene outside the building

The saved .blend's initial 3D viewport now starts on an exterior orbit that
reconstructs the preview camera's eye position (140, -285, 130) looking at
the massing centre, instead of Blender's factory default view near the
origin — which sat inside the 300 m high volume every time the file was
opened. Render cameras were already outside; the verifier now checks both
the render cameras and the saved initial viewport eye stay clear of the
building envelope.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `git diff --check` pass.
- Blender rebuild with `-- --no-render` pass; build log shows no missing
  viewport warning.
- `verify_abeno_harukas.py` pass; all 24 checks passed, including the two
  new exterior-viewpoint checks.

Remaining issues: None.

## 2026-09-08 — main — reduce Harukas plan tilts to under 3 degrees

Reduced every plan tilt to match the user's sketch, where edges lean about
3 degrees or less. The previous middle-volume east edge leaned ~22 degrees;
now all twelve mass edges stay within ~2.7 degrees of their dominant axis:
connecting edges tilt 2.5/2.6 degrees, the middle east edge 2.7 degrees
(its SE corner at (34, -14) remains the composition's subtle outermost
point), and the remaining side edges 1.0-2.2 degrees. Footprints widened
slightly (south edge 66 m) so the geometry stays close to the sketch's
proportions. The verifier now checks every plan edge tilt against the
3-degree limit, along with the existing shared-edge, bulge, and flat-roof
checks. Cameras, ground, and viewport unchanged.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `git diff --check` pass.
- Blender 5.2.0 full build pass; 564 objects; plan render visually inspected:
  both dividing lines show the gentle opposite slants from the sketch.
- `verify_abeno_harukas.py` pass; all 27 checks passed, including per-mass
  "plan tilts within 3 degrees".

Remaining issues: None.

## 2026-09-08 — main — widen the Harukas masses by 10 m

Widened all three masses by 10 m along X (the wide faces): east and west
sides each move 5 m outward, so the straight south/north edges go from 66 m
to 76 m wide. All side-edge leans keep their previous metre offsets, and the
longer connecting edges now tilt slightly less (2.2-2.7 degrees, still under
the 3-degree limit). The middle volume's SE corner (39, -14) remains the
composition's outermost eastern point and its west side still approaches the
high volume's west edge. Cameras and framing unchanged.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `git diff --check` pass.
- Blender 5.2.0 full build pass; 564 objects; plan and preview renders
  visually inspected with the wider proportions.
- `verify_abeno_harukas.py` pass; all 27 checks passed.

Remaining issues: None.

## 2026-09-08 — main — widen the Harukas masses to 86 m

Widened the composition from 78 m to 86 m overall so the width matches the
86 m depth, per the user's request. Both sides move 4 m outward about the
central axis; every short side edge keeps its exact previous lean (1.0-1.5 m
offsets, 1.0-2.7 degrees), and the longer connecting edges now tilt about
2.0 degrees — everything stays under the 3-degree limit. The middle volume's
SE corner (43, -14) remains the outermost eastern point. The verifier now
also hard-checks that overall width and depth are both 86 m.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `git diff --check` pass.
- Blender 5.2.0 full build pass; 564 objects; plan render visually inspected:
  square 86 x 86 m composition with the subtle slanted dividing lines intact.
- `verify_abeno_harukas.py` pass; all 28 checks passed.

Remaining issues: None.

## 2026-09-08 — main — add recessed open truss bands

Added Abeno Harukas-style belt trusses at the visible base of each of the
three sections: z 0-15 m (Low), 80-95 m (Middle, above the low roof), and
195-210 m (High, above the middle roof). Per the user's correction, the
truss zone carries no glazing — the glass body splits below/above the band —
and the truss is recessed inside the glass outline with a dark backing wall
further inboard so the zone does not read as hollow. Each face has seven
complete upward chevrons (14 diagonals with both feet on the lower chord,
eight boundary posts) plus top/bottom chords, per the trident reference.
Facade grids skip the band zone.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `git diff --check` pass.
- Blender 5.2.0 full build pass; 885 objects; preview render visually
  inspected: three dark recessed truss bands with visible chevron zigzag at
  the three step levels.
- `verify_abeno_harukas.py` pass; all 45 checks passed, including per-mass
  chevron counts, band spans, no-glazing-in-band, and recessed-truss checks.

Remaining issues: None for this scope.

## 2026-09-08 — main — base truss band on all three volumes

Reworked the truss layout per user feedback: removed the floating elevated
bands at 80-95/195-210 m and instead every volume carries the same open
truss band at the ground level (z 0-15 m), so the truss runs continuously
through the one-storey base of all three connected masses. Chevron density
now follows face width at a ~12 m spacing (`TRUSS_SPACING`): the long
south/north faces keep seven groups while the short east/west faces get 2-3
groups, matching the front-face density instead of forcing seven everywhere.
The band keeps the recessed no-glazing treatment (inset truss + dark
backing). Preview camera target lowered to keep the base band in frame.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `git diff --check` pass.
- Blender 5.2.0 full build pass; 735 objects; preview and base close-up
  renders visually inspected: continuous ground-level truss band with the
  chevron rhythm on the front faces and sparser side faces.
- `verify_abeno_harukas.py` pass; all 43 checks passed, including
  per-face density counts and "truss band sits at the ground level" for all
  three masses.

Remaining issues: None for this scope.

## 2026-09-08 — main — two two-storey step truss bands only

Per user feedback: removed the ground-level truss band entirely (glass now
stands on the ground for all three masses) and slimmed the bands from 15 m
(three storeys) to 10 m (two storeys). The remaining bands sit just below
the low/middle rooflines at z 70-80 and z 185-195 m, each running through
the two adjoining volumes (Low+Middle, Middle+High). Recessed no-glazing
band treatment and ~12 m chevron density unchanged.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `git diff --check` pass.
- Blender 5.2.0 full build pass; 970 objects; preview render visually
  inspected: exactly two two-storey truss bands at the step levels.
- `verify_abeno_harukas.py` pass; all 58 checks passed, including
  "no truss band at the ground level" and "truss bands span two storeys".

Remaining issues: None for this scope.

## 2026-09-08 — main — steepen the Harukas dividing edges slightly

Increased the slant of the two long connecting edges as requested: the
low/middle edge now tilts about 3.0 degrees (dy 3.0 -> 4.5 m over 86 m) and
the middle/high edge about 2.75 degrees (dy 3.0 -> 4.0 m). Dividing-edge
centres stayed fixed so the overall 86 x 86 m envelope is unchanged, and
every short side edge keeps its previous 1.0-1.5 m lean. All plan tilts
remain within the 3-degree cap.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `git diff --check` pass.
- Blender 5.2.0 full build pass; 970 objects; plan render visually
  inspected: both dividing lines now read as clearly slanted but gentle.
- `verify_abeno_harukas.py` pass; all 58 checks passed.

Remaining issues: None.

## 2026-09-08 — main — widen the middle Harukas volume northward

Per user feedback, the middle volume's short side edges now lean outward
going north (about 3.5 degrees, exceeding the general 3-degree plan-tilt
cap): its north face reaches 89.5 m, the composition's widest line, while
its south face stays at 86 m shared with the low volume. The middle NE
corner (45, 18.5) is now the outermost eastern point; the high volume eases
back to 88.5 m at its north face so its own side edges stay within 3
degrees. Overall depth remains 86 m. The verifier's tilt check keeps the
3-degree cap everywhere except the middle volume's two side edges (5-degree
cap), and now checks the middle volume's outward widening directly.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `git diff --check` pass.
- Blender 5.2.0 full build pass; 970 objects; plan render visually
  inspected: middle volume visibly widens toward the high volume.
- `verify_abeno_harukas.py` pass; all 59 checks passed.

Remaining issues: None.

## 2026-09-08 — main — widen the middle volume at its low-side face

Corrected the extension direction: the widening belongs at the face where
the middle volume joins the lowest volume, not at its north side. The
low/middle connecting edge (now 88 m, spanning -44..+44) is the
composition's widest line, and both the low and middle volumes flare outward
toward it; the middle volume narrows past it toward the high volume. All
plan tilts stay within 3 degrees (no more 5-degree exemption). Total depth
86 m. The verifier now checks that the middle volume is widest at its
low-side face and that the width peaks at the low/middle junction.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py` pass.
- `git diff --check` pass.
- Blender 5.2.0 full build pass; 970 objects; plan render visually
  inspected: the low/middle junction is the widest line, with the middle
  volume flaring toward it.
- `verify_abeno_harukas.py` pass; all 58 checks passed.

Remaining issues: None.

## 2026-09-09 — main — add the Harukas linked-void service core

Added the service core to the body-first model, following the published
linked-void scheme recorded in AGENTS.md (user confirmed scope: core
structure only, floor slabs with shaft/atrium openings deferred). Per
volume, in its own `Harukas_Core` collection: four 8x8 m lower corner
service zones (z 0-80 m, every volume, placed on the 5 m inset plan
corners via `quad_inset`); for the middle and high volumes a braced steel
spine (20x12 m, z 80-195 m) with surface X-bracing on both faces (4 tiers
x 2 bays), a west eco-void strip outlined by four slim columns plus
base/top ring beams, and three east lift shafts; for the high volume an
upper atrium frame (26x15 m columns plus ring beams at z 195/300 m).
Horizontal transfer ties connect the corner zones to the spine base at
z 80 m and the spine top corners to the atrium columns at z 195 m. Added
a `core` render view (new `Harukas_Core_Camera`) that hides the facade
collections only during its render, leaving the saved model fully visible;
`core` is now in the default `--views` list and skipped under
`--blockout`. Fixed one layout bug found by the verifier: the eco-void
frame's east columns overlapped the spine west face, so the void now
stands 0.6 m clear of the spine.

Verification:
- Standalone layout math check: every core piece clears its plan edges by
  at least 0.8 m; z 195 transfer-tie lengths sane.
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  pass.
- `git diff --check` pass.
- Blender 5.2.0 full build pass; 1103 objects; core render visually
  inspected: corner zones, braced spine with west void frame and east
  lift banks, transfer ties, and the atrium frame all read correctly;
  preview render inspected for no facade regression.
- `verify_abeno_harukas.py` pass; all 94 checks passed (35 new core
  checks: facade clearance, zone z-ranges, inset-corner placement, spine
  bracing count, void/lift bank sides, transfer-tie endpoints, saved
  collection visibility).

Remaining issues: None for this scope. Floor slabs with core/atrium
openings (`core_floor`/`core_openings`) remain deferred by user choice.

## 2026-09-09 — main — add floor slabs with core/atrium openings

Added floor plates to the Harukas model. One 0.3 m slab per 5 m storey,
top flush with the storey level, outline inset 0.3 m from the plan quad
(`quad_inset`). Slabs skip levels whose thickness would touch a
solid-backed truss band (5 cm clearance), so counts are Low 13, Middle 33,
High 54. Each slab is a holed 2D curve extruded to thickness
(`core_floor`): `core_openings` cuts actual holes where the core passes —
four corner service zones in the lower zone (every volume), spine +
eco-void + three lift shafts in the middle zone (middle/high), and the
atrium void in the upper zone (high). Openings grow 5 cm so slab edges
never touch core walls (no coplanar faces). Slabs live in the
`Harukas_Floors` collection; the `core` render view now hides both facade
and floor collections, restoring them right after. The verifier's
`world_points` now evaluates curve objects to meshes.

Verification:
- Empirical Blender check: 2D curve `extrude` spans +/-half symmetric
  around the curve plane; nested poly splines tessellate as real holes.
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  pass.
- Blender 5.2.0 full build pass; 1203 objects; preview render visually
  inspected: storey lines read through the glass, core faintly visible,
  truss bands unchanged; core render unchanged (floors hidden).
- `verify_abeno_harukas.py` pass; all 110 checks passed (16 new floor
  checks: counts follow storeys and skip bands, tops flush with storey
  levels, slabs inside the plan, outline/opening corners cut, openings
  kept clear, floor collection visible in the saved model).

Remaining issues: None.

## 2026-09-09 — main — continue the Harukas service core to the roof

The user noted the top volume's core read as hollow. The upper atrium
frame is intentional (the linked-void hotel section), but the building
still needed vertical circulation to the observatory level. Added a slim
8x12 m concrete upper service core (z 195-300 m, high volume only),
standing just east of the atrium (`UPPER_CORE_DX = ATRIUM_W/2 + 1 + W/2`)
and stacking over the middle-zone lift banks, so the lifts continue to
the roof. Upper-zone floor slabs now cut a matching opening beside the
atrium hole.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  pass.
- Blender 5.2.0 full build pass; 1204 objects; core render visually
  inspected: the white upper core rises beside the atrium frame and tops
  out flush at the 300 m roofline.
- `verify_abeno_harukas.py` pass; all 113 checks passed (3 new: upper
  core z-range, east of the atrium, stacking over the lift banks; middle
  zone slabs already covered by the opening checks).

Remaining issues: None.

## 2026-09-10 — main — Harukas truss layout per the published void-structure figure

The user provided the published structural figures (saved as
`docs/images/harukas_truss_void_structure_fig4.png` with floor labels
15F / 25,26F / 31,32F / 37F, and `docs/images/harukas_truss_floors_fig7.png`
with the floor axis showing the 56-57F top band). Positions were measured
from the figures by pixel analysis and iterated against renders with the
user. Final truss scheme, all bands two 5 m storeys tall:

- Belt bands just below the low/middle roofs (z 70-80, 185-195 m) and one
  near the tower top (z 275-285 m, floors 56-57, below the 58-60F
  observatory), each wrapping every volume tall enough to carry it
  (`TRUSS_BAND_TOPS`).
- Two staggered mid-office trusses each wrapping a single volume only —
  z 120-130 (floors 25-26) on the middle volume, z 150-160 (floors
  31-32) on the high volume (`TRUSS_BAND_TOPS_PARTIAL`); unlike the belt
  bands they do not run through the adjoining volume. `mass_bands` and
  `floor_levels` now take the mass name.
- Bands are open 3D lattices, not solid boxes: the dark backing prism was
  removed and each band now gets a uniform interior web grid in both plan
  directions at the facade chevron spacing, clipped to the inset plan
  (`truss_interior`/`truss_line`/`quad_clip`), so the bands read as hollow
  frameworks as in the figure.

Verify script mirrors the layout, gains staggered-partial/top-band checks
and per-band open-lattice checks (no solid backing, interior webs span
the zone and stay inside the plan); the roofline check now reads the
truss top chords (half chord width tolerance) since the backing no longer
caps the low/middle roofs. AGENTS.md truss bullets and the `truss_zones`
scene custom property updated.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 full build pass; 2285 objects; preview/north renders
  visually inspected with the user: five truss zones at z 70-80 /
  120-130 / 150-160 / 185-195 / 275-285 m, the mid-office pair staggered
  on separate volumes, all bands hollow lattices.
- `verify_abeno_harukas.py` pass; all 143 checks passed.

Remaining issues: None.

## 2026-09-10 — main — vertical truss walls and chunkier truss posts

The user pointed at the published section figure and a building photo:
trusses also run in the vertical direction (the hanging-truss masts
between the belt bands), and the truss posts were too thin. Changes:

- Truss boundary posts thickened 0.45 -> 0.9 m (`TRUSS_POST_W`, ~2.5x
  the diagonals, matching the figures' chunky columns); truss recess
  deepened (`TRUSS_INSET` 0.025 -> 0.04) so the thicker posts and the
  interior web members stay inside the glass line on the narrowest faces.
- Added the missing vertical trusses: the upper atrium frame's east/west
  flank walls are now X-braced in two-storey cells from the middle-roof
  band up to the top band (z 195-285 m, `ATRIUM_BRACE_TIERS` = 9, high
  volume only); the crown floors above the top band stay unbraced, per
  the figure. The braced middle spine (z 80-195 m) already covered the
  middle-zone vertical truss.
- Verify script: new check that the atrium flank braces span z 195-285 m
  (36 members); `ATRIUM_BRACE_TOP`/`ATRIUM_BRACE_TIERS` mirrored.
- AGENTS.md core bullet and the build header/SOURCES text updated.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 full build pass; preview/north/core renders visually
  inspected: bands read as chunky hollow frameworks, and the core view
  shows the vertical X-braced walls flanking the atrium up to the top
  band.
- `verify_abeno_harukas.py` pass; all 144 checks passed (1 new: atrium
  flank bracing count and z-range).

Remaining issues: the figure also shows vertical braced walls flanking
the department-store void in the lowest zone (z 0-80 m); our model keeps
the published four corner service zones there instead — left as-is
pending user direction.

## 2026-09-10 — main — facade hanging-truss masts between the belt bands

The user asked for the vertical trusses from the published section figure
to be drawn: vertical hanging-truss masts connecting the horizontal belt
truss bands. The figure (and the building photo) show them running on the
facade between band levels, so they are modelled as facade strips rather
than hidden interior walls. Measured positions from the section figure:

- Low zone: two masts flanking the department-store void, z 0-70 m
  (up to the 15F belt band), at y ≈ -29.5 and -18.
- Middle zone: two masts near the middle/high junction, z 80-185 m
  (from the 15F band to the 37F band), at y ≈ +5.2 and +15.2.
- Tower zone: the interior X-braced atrium flank walls (added in the
  previous round) already cover z 195-285 m.

Each mast is a planar truss standing just proud of the glass line
(`MAST_PROUD` = 0.3 m, so it reads on the facade): two chunky 0.9 m posts
(matching the thickened band posts) with X diagonals and rungs in
two-storey cells (`facade_mast`/`facade_masts`, driven by the
`FACADE_MASTS` list, placed on both the east and west faces of the
volume). AGENTS.md documents the scheme.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 full build pass; preview render visually inspected: the
  vertical X-braced strips now connect the belt bands on the side
  facades, matching the section figure.
- `verify_abeno_harukas.py` pass; all 160 checks passed (16 new: per-mast
  member counts, z-ranges, and standing proud of the glass line).

Remaining issues: None.

## 2026-09-10 — main — correct facade mast: one strip, middle volume, zigzag

The user corrected the facade hanging trusses against a clearer building
photo and the section figure: the vertical truss is a single strip on the
middle volume only (not two per zone, nothing on the low volume), and its
diagonals form zigzag (Warren) triangles, not stacked X braces. Changes:

- `FACADE_MASTS` reduced to one entry: middle volume, y ≈ +11 (near the
  middle/high junction), z 80-185 m, one strip on each of the east and
  west faces; `MAST_WIDTH` 6 -> 9 m per the section's measured width.
- `facade_mast` diagonals changed from stacked X braces to zigzag
  triangles (one diagonal per two-storey cell, alternating direction),
  matching the section figure.
- Verify script mirrors the list and the member count (2 x cells + 3 per
  mast). AGENTS.md mast bullet updated.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 build pass; preview render inspected: one zigzag vertical
  strip on each side face of the middle volume, connecting the 15F and
  37F belt bands; low block facade clean.
- `verify_abeno_harukas.py` pass; all 148 checks passed.

Remaining issues: None.

## 2026-09-10 — main — facade mast cells are stacked pyramids

The user corrected the facade mast pattern against the zoomed section
figure: the vertical truss is built from upward-pointing pyramid (A-frame)
cells stacked vertically — each cell's two diagonals run from the bottom
corners to an apex at the top centre, with a rung at every joint — not
zigzag Warren triangles and not stacked X braces. `facade_mast` rewritten
accordingly (members per mast: 2 posts + cells+1 rungs + 2 x cells
diagonals); verify count mirrored (3 x cells + 3); AGENTS.md updated.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  pass.
- Blender 5.2.0 build pass; preview render inspected: the mast shows
  stacked upward triangles between the 15F and 37F belt bands.
- `verify_abeno_harukas.py` pass; all 148 checks passed.

Remaining issues: None.

## 2026-09-10 — main — truss bands recessed behind a continuous curtain wall

The user pointed out from the building photo: only the asymmetric facade
mast is exposed; all the horizontal truss bands sit inside the outer
curtain-wall glass. The glass body no longer splits around the bands:
each volume is one continuous full-height glass prism with the facade
grid running through, and the open truss lattices sit recessed behind the
glass (`TRUSS_INSET`), reading through it. The facade mast stays proud of
the glass line, so it alone reads as exposed structure. `glass_spans`
removed (orphaned). Verify: the "glass clears every truss band" check
became "curtain wall runs continuous past the truss bands" (single prism,
z 0 to roof); the recessed-inside-the-glass-line check now guards the
band placement behind the glass. AGENTS.md updated.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 build pass; preview render inspected: continuous glass
  with the truss bands visible through it, and only the vertical mast
  exposed on the facade.
- `verify_abeno_harukas.py` pass; all 148 checks passed.

Remaining issues: None.

## 2026-09-10 — main — staggered trusses exposed and one storey tall

The user corrected the truss glazing from the floor-axis figure: the two
staggered mid-office trusses are exposed (no curtain-wall wrapping), the
belt bands stay wrapped by the continuous glass; and the truss heights
differ — belt bands two storeys, the staggered trusses smaller. Changes:

- `mass_bands` now returns (z0, z1, exposed) triples; the staggered
  mid-office trusses are one storey (`TRUSS_BAND_H_PARTIAL` = 5 m:
  z 125-130 on the middle volume, z 155-160 on the high volume) and
  exposed, while the belt bands stay two storeys behind the glass.
- `glass_spans` reintroduced: the curtain wall splits only around the
  exposed staggered trusses (each volume's glass is one or two prisms;
  the belt bands keep their glazing).
- Verify mirrors: wrap/expose check per volume (glass spans cover the
  belt bands, clear the exposed ones), band-height check (belt 10 m,
  staggered 5 m), staggered band positions updated. AGENTS.md updated.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 build pass; preview render inspected: belt bands read
  through the continuous glass, the one-storey staggered trusses and the
  facade mast stand exposed.
- `verify_abeno_harukas.py` pass; all 148 checks passed.

Remaining issues: None.

## 2026-09-10 — main — facade masts recessed within the envelope

The user corrected that no truss may protrude beyond the building's
outer surface: the facade masts stood proud of the glass line
(`MAST_PROUD` = +0.3 m). They are now recessed at `TRUSS_INSET` like the
truss bands (the photo shows a flush curtain wall over the mast zone);
`MAST_PROUD` removed. Mast ends are clamped to the face extent so the
west-face mast stays clear of the shorter tilted edge's corner. Verify:
"stands proud" check became "stays inside the glass line" (all mast
points inside the plan). AGENTS.md updated.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 build pass; preview render inspected: flat curtain wall,
  nothing protrudes; the mast reads faintly through the glass and the
  exposed staggered trusses stay in their unglazed bands.
- `verify_abeno_harukas.py` pass; all 148 checks passed.

Remaining issues: None.

## 2026-09-10 — main — hollow truss rings: interior web grid removed

The user compared a close-up of our bands with the reference band photo:
the reference is a clean hollow ring of perimeter chevron trusses
(see-through to the far face), while our bands had a dense interior web
grid reading as a forest of columns. Removed `truss_interior` (and its
now-orphaned `truss_line`/`quad_clip` helpers); each band is again just
the four perimeter chevron faces around an open interior. Verify dropped
the web checks and keeps a guard that no `TrussWeb` objects or solid
backing reappear. AGENTS.md updated.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 build pass; preview render inspected: bands read as
  clean hollow chevron rings, no interior forest.
- `verify_abeno_harukas.py` pass; all 132 checks passed.

Remaining issues: None.

## 2026-09-10 — main — declutter the band short faces

The user found the band short faces still messy: extra columns. Two
causes fixed:

- The facade mast (z 80-185 m) crossed the exposed 25-26F band on the
  side faces, doubling members there. Masts now split around the exposed
  bands they meet — segments end at the band chords (`facade_masts` takes
  the band list and cuts the z-range).
- Adjacent truss faces each built a post at the shared corner, giving
  doubled corner posts; `truss_face` now skips the k=0 post — the
  previous face's last post stands at the shared corner.

Also added the floor plate at each band's bottom level (`floor_levels`
keeps slabs at z0 of a band), so truss rings stand on a plate as in the
reference band photo. Verify mirrors: post count is now sum(groups) per
band, mast member counts account for the split segments. AGENTS.md
updated.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 build pass; band close-up renders (oblique and straight
  short-face views) inspected: no mast members inside the band, single
  shared corner posts, band stands on its floor plate.
- `verify_abeno_harukas.py` pass; all 132 checks passed.

Remaining issues: None.

## 2026-09-10 — main — truss posts doubled in width

The user asked for the truss posts to be at least twice as thick.
`TRUSS_POST_W` 0.9 -> 1.8 m (band boundary posts and the facade mast
posts). `TRUSS_INSET` 0.04 -> 0.07 so the chunkier posts still stay
inside the facade line on the narrowest faces. Diagonals and chords
unchanged.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 build pass; band close-up renders inspected: posts read
  as chunky columns, recessed within the envelope.
- `verify_abeno_harukas.py` pass; all 132 checks passed.

Remaining issues: None.

## 2026-09-10 — main — thicker diagonals, white truss steel

The user asked for the diagonals to be thickened too and all truss
members to be white: `TRUSS_DIAG_W` 0.35 -> 0.70 m (posts had just gone
0.9 -> 1.8 m); new `Harukas_Truss_White` material (white-painted steel,
per the reference photos) applied to the band trusses and facade masts —
the facade mullions/transoms keep their own material. Verify unchanged
(no width/material checks); member counts unaffected.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 build pass; preview and band close-up renders inspected:
  white chunky trusses reading through the glass.
- `verify_abeno_harukas.py` pass; all 132 checks passed.

Remaining issues: None.

## 2026-09-10 — main — mast snapped to the belt truss grid

The user noted the vertical mast should read as a vertical extension of
the main (belt) trusses, but its posts sat off-grid. The mast is now
exactly one chevron bay wide and snapped to the face's chevron grid
(`facade_masts` computes the bay from the target y), so its posts
continue the belt bands' posts above and below. `MAST_WIDTH` removed
(width follows the bay). Verify unchanged (member counts and inside-the
-glass-line checks still pass).

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 build pass; mast close-up render inspected: the mast
  posts continue the band posts at the chevron boundaries.
- `verify_abeno_harukas.py` pass; all 132 checks passed.

Remaining issues: None.

## 2026-09-10 — main — belt bands resized to 1.5x the staggered trusses

The user noted the figure's proportions: the belt bands and the staggered
mid-office trusses differ by 1.5x in height, not 2x. `TRUSS_BAND_H`
10.0 -> 7.5 m (band tops unchanged: 80/195/285 m, so the bands are now
z 72.5-80 / 187.5-195 / 277.5-285). The facade mast and the atrium flank
bracing still run band-to-band: mast z 80-187.5, atrium bracing
`ATRIUM_BRACE_TOP` 285 -> 277.5 (stops at the top band's lower edge).
Verify mirrors constants and the explicit band z-range checks; slab
levels follow automatically. AGENTS.md and the module docstrings updated.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 full build pass; preview/north renders inspected: belt
  bands read at 1.5x the staggered trusses' height.
- `verify_abeno_harukas.py` pass; all 132 checks passed.

Remaining issues: None.

## 2026-09-10 — main — facade mast only on the wider east side

The user noted the vertical truss should extend down only from the side
with three chevron groups: the middle volume's east face (33 m, three
groups) keeps the mast, while the narrower west face (25 m, two groups)
gets none. `facade_masts` now builds the E face only; verify drops the
W-side mast checks and gains an absence check (`_Mast_W_` must not
exist). AGENTS.md updated.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 build pass; preview render inspected: single mast on the
  east face, west face clean.
- `verify_abeno_harukas.py` pass; all 131 checks passed.

Remaining issues: None.

## 2026-09-10 — main — west mast on the high volume's west face

The user clarified the mast rule: on each side of the composition the
mast runs on the wider side face (the one with three chevron groups).
East side: the middle volume's east face (kept). West side: the mast
belongs to the high volume's west face (31.6 m, three groups), not the
middle volume's narrower west face (25 m, two groups). `FACADE_MASTS`
entries now carry the face ("Middle"/E, "High"/W); the High mast
splits around the high volume's exposed 31-32F band (z 155-160) like the
Middle mast does at 25-26F. Verify mirrors the new tuple shape and the
absence check (no mast on Middle's west face, High's east face, or the
low volume). AGENTS.md updated.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 build pass; west-side render inspected: the mast reads
  through the glass on the high volume's west face at the junction.
- `verify_abeno_harukas.py` pass; all 133 checks passed.

Remaining issues: None.

## 2026-09-10 — main — mast aligned to the band grid exactly

The west mast was off-grid: `facade_masts` computed the chevron group
count from the inset quad's edge length while the band trusses use the
raw face width (e.g. the high volume's west face: 3 groups vs 2), so the
mast posts missed the band posts. The mast now snaps with the band
trusses' own group count and `edge_point` inset — its posts are exactly
the band posts' positions continued vertically. AGENTS.md updated.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 build pass; west-side close-up render inspected: the
  mast posts land exactly on the band posts at the 37F junction.
- `verify_abeno_harukas.py` pass; all 133 checks passed.

Remaining issues: None.

## 2026-09-10 — main — shift the massing: 3 storeys from the base to the tower

The user asked to take 3 storeys off the base and add 3 to the top
volume — net zero on the total height, the composition just shifts. New
massing (`MASSES` plans unchanged): Low 80 -> 65 m, Middle 195 -> 180 m,
High stays 300 m (it dropped 15 m with the base, then regained 15 m on
top). Everything tied to the volume heights moved with it:

- Belt band tops follow the rooflines: z 65/180/285 m (bands
  57.5-65 / 172.5-180 / 277.5-285); the staggered mid-office trusses keep
  their positions (z 125-130 / 155-160).
- Core zones follow the volume boundaries: corner zones z 0-65, spine
  zone z 65-180, atrium zone z 180-300; transfer ties at z 65/180.
- Facade masts run from the low band's top to the middle band's bottom
  (z 65-172.5).
- Verify mirrors all shifted constants; the building's documented height
  stays 300 m.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 full build pass; preview/north renders inspected: the
  base is 3 storeys lower, the middle roofline 3 storeys lower, the tower
  top unchanged.
- `verify_abeno_harukas.py` pass; all 133 checks passed.

Remaining issues: None.

## 2026-09-11 — main — continuous white curtain-wall frame

The user found the curtain wall read differently on the long and short
faces: the dark vertical mullion crossed the white truss band on the long
face while the short face lost its frame there. The frame is now one
continuous white member on every face, per the facade reference photo.

- `facade_grid` is now called once per volume over the full height
  (0 → `height`) instead of per glass span, so the vertical mullions no
  longer break where the glass splits around the exposed staggered
  trusses; long and short faces read identically.
- The frame uses a new white-painted aluminium material
  (`Harukas_Facade_Frame`, 0.92/0.92/0.90 — the same white as the truss
  steel) in place of the dark schematic mullion metal.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 build pass; preview, north and corner close-up renders
  inspected: the white frame is continuous bottom to top on all four
  faces, long and short alike.
- `verify_abeno_harukas.py`: 3 checks fail, all unrelated to this change
  and present in the working tree before it — the concurrent widened
  middle plan leaves the Low/Middle north edges at 8 chevron groups
  (checks still expect 7) and the `middle east side extends outward`
  check still expects the old corner x.

Remaining issues: the 3 unrelated verify failures above, from the
in-flight middle-plan widening.

## 2026-09-11 — main — middle volume flares to 5 degrees

Widened the middle volume's two side edges to about 5 degrees of outward
flare toward its low-side face, eliminating the previous ~3-degree cap
for this volume. The high-side connecting edge (shared with the high
volume) is unchanged; the low-side connecting edge widens with the
flare, so the old fixed 88 m width limit is removed — the shared
low/middle edge is now about 90.2 m. Low and middle still share the full
widened edge, overall depth stays 86 m, and the middle volume keeps its
outermost SE corner.

Truss chevrons now derive their group count from each face's width at
the fixed ~12 m `TRUSS_SPACING` (counts may change as a face widens; the
span does not). The widened north/south faces therefore move from 7 to
8 groups, so the old hardcoded "seven groups" check was replaced with a
span-based one.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 full build pass; preview, plan and north renders
  inspected: the middle volume visibly widens toward the low side.
- `verify_abeno_harukas.py` pass; all 133 checks passed, including new
  `Middle side edges flare outward at 5 degrees`,
  `Middle connecting edges retain shallow plan tilt`, and
  `chevron groups follow the fixed span`.

Remaining issues: None. The 3 prior "in-flight widening" failures are
resolved.

## 2026-09-11 — main — interior roller blinds on every glass module

Added interior curtains to the Abeno Harukas masses, following the Office
reference (`make_frosted_glass_film`). One thin frosted panel per
curtain-wall module (`MULLION_SPACING` = 1.25 m grid) sits behind each
storey's vision glass on all four faces, hung `CURTAIN_GAP` = 10 cm inside
the glass line, for every storey that has a floor slab. Three discrete
states — rolled up (no panel), half down, fully down — are distributed in
exactly balanced counts from a fixed `CURTAIN_SEED` and shuffled, so all
panes are covered with an even mix. All panels merge into one
`Harukas_Curtains` object in the `Harukas_Curtains` collection, which the
`core` review view hides alongside the facades and floors.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 build pass (897 objects); preview, plan and north renders
  inspected: frosted blinds read through the glazing in a mixed pattern.
- `verify_abeno_harukas.py` pass; all 137 checks passed, including the new
  "a curtain pane for every glass module and floored storey", "three
  curtain states, all present and balanced", "curtain panels hang just
  inside the facade (5-12 cm)" and "curtains use the frosted roller-blind
  material".

Remaining issues: None. Curtain geometry is schematic (flat per-module
panel), not an as-built blind detail.

## 2026-09-11 — main — ceiling strip lights ring the core

Added ceiling lighting to the Abeno Harukas masses, following the house
reference. `LIGHT_RING_SETBACKS` = 2/5/8 m inside the glass line define
three concentric rings per floor; each ring edge carries one long thin
strip fixture (`append_strip`, `LIGHT_STRIP_W` = 0.35, `LIGHT_STRIP_H` =
0.10), shortened by `LIGHT_STRIP_CORNER_GAP` = 9.5 m at each corner so it
clears the lower corner service zones. Every floor with a slab gets rings.

A fixed `LIGHT_SEED` gives each strip a stable state — off, or lit
daylight/warm at `LIGHT_ON_RATIO` = 0.5 — merged into
`Harukas_Ceiling_Lights_{Daylight,Warm,Off}` in the new `Harukas_Lights`
collection, which the `core` review view hides alongside the facades,
curtains and floors. Each object carries its `strip_count`.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 build pass (900 objects); preview, plan and north renders
  inspected: bright horizontal light bands read through the glazing in a
  mixed lit/off pattern.
- `verify_abeno_harukas.py` pass; all 140 checks passed, including
  "ceiling strip lights ring the core on every floor", "some ceiling
  lights are lit and some are off", and "ceiling lights stay inside the
  plan and clear of the core".

Remaining issues: None. Light rings are schematic strip fixtures, not
as-built luminaire layouts.

## 2026-09-11 — main — even ceiling light coverage over the whole plate

The user found the three perimeter rings left the middle of each floor
plate (away from both the facade and the core) dark. Reworked
`build_ceiling_lights` from rings to an even row grid: `LIGHT_ROW_PITCH` =
3 m rows of long thin fixtures run along the plan's long axis across the
whole ceiling of every floor with a slab. Each row is clipped against the
plan (`line_span_in_quad`) and around the modelled core openings
(`subtract_intervals`), keeping `LIGHT_EDGE_CLEAR` = 0.6 m off the facade
and the core, so every part of the plate gets lights while the rows still
wrap the core. The seeded lit/off/warm mix and the three merged
`Harukas_Ceiling_Lights_{Daylight,Warm,Off}` objects are unchanged.

Verification:
- `python3 -m py_compile build_abeno_harukas.py verify_abeno_harukas.py`
  and `git diff --check` pass.
- Blender 5.2.0 build pass (900 objects); preview, plan and north renders
  inspected: light rows now spread across the full plate with no dark
  band between the facade and the core.
- `verify_abeno_harukas.py` pass; all 140 checks passed, including the
  mirrored strip-count check and "ceiling lights stay inside the plan and
  clear of the core".

Remaining issues: None. Light rows are schematic strip fixtures, not
as-built luminaire layouts.
