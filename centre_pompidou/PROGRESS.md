# Centre Pompidou — Progress

## 2026-09-06 — main — clear all interior floor structure

Removed the remaining interior transfer beams and exposed diagonal trusses
from floors 2 through 7. The glazed floor plates are now completely free of
interior columns and structural members; the only vertical structural members
retained are the thick exposed perimeter frame columns outside the facade.

Verification:
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- Blender regenerated the `.blend`, perspective preview, front elevation, and
  short-side elevation successfully.
- `verify_pompidou.py` pass; all 45 checks passed, including no interior
  trusses and the existing column-free checks.
- `git diff --check` pass.

Remaining issues: None. The model now has no generated interior structural
columns or trusses; only the exterior frame columns remain.

## 2026-09-06 — main — remove thin facade columns from open floors

Removed the repeated thin vertical curtain-wall and end-facade mullions that
made the open lower level read as a forest of columns. The exterior structural
columns and diagonal frame remain the only vertical load-bearing elements; the
facade retains transparent glazing and horizontal transoms without introducing
interior columns.

Verification:
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- Blender regenerated the `.blend`, perspective preview, front elevation, and
  short-side elevation successfully.
- `verify_pompidou.py` pass; all 45 checks passed, including the no-thin-column
  check and the existing column-free interior checks.
- `git diff --check` pass.

Remaining issues: None. The open level now retains only the exterior structural
frame; browser screenshot inspection was unavailable, but Blender renders were
successfully generated.

## 2026-09-06 — main — remove redundant escalator cantilevers

Removed the redundant `Escalator_Extended_Cantilever` support grid that was
visually intruding into the perimeter balcony zone. The balcony elevation is
kept at its existing near-floor datum; only the unnecessary support objects
and their obsolete count assertion were removed. The actual exposed facade
frame and short-side trusses remain in place.

Verification:
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- Blender regenerated the `.blend`, perspective preview, front elevation, and
  short-side elevation successfully.
- `verify_pompidou.py` pass; all 44 checks passed, including the absence of
  redundant escalator cantilevers and the balcony clearance check.
- `git diff --check` pass.

Remaining issues: None known. Chrome visual review was unavailable because the
browser inspection call timed out; the three Blender renders were generated.

## 2026-09-06 — main — raise balcony decks below facade frame supports

Raised every upper-floor perimeter balcony deck by 0.60 m relative to the
floor datum. This puts the walking surface below the floor-level facade-frame
supports and removes the previous visual conflict where the supports appeared
to occupy the balcony path. Balcony depth, four-sided continuity, railings,
and the existing escalator and service alignment are unchanged.

Verification:
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- Blender regenerated the `.blend`, perspective preview, front elevation, and
  short-side elevation successfully.
- Render review confirms the balcony walking surface is below the horizontal
  facade-frame supports.
- `verify_pompidou.py` pass; all 45 checks passed, including the new
  below-balcony support clearance check.
- `git diff --check` pass.

Remaining issues: None for the requested balcony/support vertical relationship.

## 2026-09-06 — main — complete end trusses and mirrored facade services

Added exposed structural frames to both short elevations. Each end now has six
vertical frame lines, floor-aligned horizontal members, and diagonal braces
across five bays on every upper storey, matching the structural rhythm of the
two long facades while preserving the open ground floor.

Mirrored the full blue, green, yellow, and red external service system onto the
opposite long elevation. Vertical stacks, roof bends, and floor-level outward
branches now use the same coordinates and offsets on both sides. Existing
escalator cantilevers remain symmetrically aligned with the two facade routes.

Verification:
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- Blender regenerated the `.blend`, perspective preview, front elevation, and
  short-side elevation successfully.
- Short-side render review confirms diagonal end trusses on the glazed facade;
  perspective and end views confirm paired colored services on both long sides.
- `verify_pompidou.py` pass; all 44 checks passed, including 60 short-facade
  braces and mirrored colored service stacks.
- `git diff --check` pass.

Remaining issues: None for the requested end trusses and facade symmetry.

## 2026-09-06 — main — mirror escalators across the two long facades

Reworked the exposed circulation so there is exactly one continuous escalator
tube on each long elevation. The negative-Y facade now carries the left-to-
right ascending route, while the positive-Y facade carries the mirrored
right-to-left ascending route. The two routes no longer sit side-by-side on
one facade, giving both ends of the building a direct vertical circulation
option.

Updated the cantilever supports to serve both long facades symmetrically, with
one full support line per facade. Existing four-sided balconies and the
4.25 m glass-to-frame clear zone are retained.

Verification:
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- Blender regenerated the `.blend`, perspective preview, front elevation, and
  short-side elevation successfully.
- Render review confirms one escalator route at each long-side edge, with
  opposite horizontal directions and mirrored placement.
- `verify_pompidou.py` pass; all 41 checks passed after updating the route and
  support expectations.
- `git diff --check` pass.

Remaining issues: None for the requested mirrored two-facade escalator layout.

## 2026-09-06 — main — add wraparound balcony bands between glazing and frame

Added a continuous four-sided balcony band at every upper floor level. Each
level now has four balcony slabs extending 4.0 m outside the glass volume,
with steel perimeter railings on all four elevations. The exposed frame was
moved outward so the glass-to-frame clear zone is 4.25 m, leaving the balcony
as a usable circulation and maintenance zone between the curtain wall and the
main truss.

Verification:
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- Blender regenerated the `.blend`, perspective preview, front elevation, and
  short-side elevation successfully.
- Render review confirms the wraparound balcony slabs and railings are visible
  around the glazed volume without changing the open ground floor.
- `verify_pompidou.py` pass; all 41 checks passed, including seven balcony
  levels, 28 balcony slab segments, perimeter railings, and at least 4.0 m
  glass-to-frame clearance.
- `git diff --check` pass.

Remaining issues: None for the requested wraparound balcony geometry.

## 2026-09-06 — main — add short-side elevation render

Added a dedicated orthographic short-side elevation render to the Pompidou
build script at `out/centre_pompidou_side.png`. The view makes the new end-wall
glazing directly inspectable, including its reflective blue glass, full-height
vertical mullions, horizontal transoms, and the external escalator edge.

Verification:
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- Blender regenerated the `.blend`, perspective preview, front elevation, and
  short-side elevation successfully.
- Short-side render visually reviewed: the end facade is fully glazed and the
  panel grid is clearly visible.
- `verify_pompidou.py` pass; all 38 checks passed.
- `git diff --check` pass.

Remaining issues: None for the requested visual inspection step.

## 2026-09-06 — main — restore short-side glazing and remove interior columns

Added transparent reflective curtain-wall panels to both short end elevations,
with dedicated mullions and transoms, so the building is glazed on all four
sides instead of only along the long facades. The glass uses the same smooth,
high-transmission reflective material as the long elevations.

Removed the interior structural column grid, service-core shafts, lift shafts,
lift doors, guide rails, and lift cars. The interior is now column-free and the
load-bearing diagonal frame remains external, consistent with the intended
Pompidou-like open-plan reading. The previously added interior diagonal trusses
remain as exposed non-column members behind the transparent envelope.

Verification:
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- Regenerated `out/centre_pompidou.blend`, perspective preview, and front
  elevation with Blender 5.2.
- `verify_pompidou.py` pass; all 38 checks passed, including 60 short-side
  glass panels, no interior columns, no internal service or lift shafts, and
  the existing transparent-glass and escalator checks.
- Visually reviewed both renders; the short end facade is glazed and the model
  no longer contains the previously visible interior pillar/shaft objects.
- `git diff --check` pass.

Remaining issues: None for the requested side glazing and column removal.

## 2026-09-06 — main — open ground floor and reflective transparent glazing

Removed the opaque interior shadow shell and omitted the first-storey curtain
wall panels and lights, leaving the 10 m ground storey visually open. Reworked
both facade and escalator glazing as smooth reflective glass rather than a
frosted or grainy surface: roughness is now 0.02, transmission is 0.90, and the
facade retains enough blue tint and opacity to catch reflections while exposing
the structure and lit interior behind it.

Added 204 interior diagonal truss members across the upper six storeys at two
depth planes. These now remain visible through the transparent envelope and do
not obstruct the open ground level.

Verification:
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- Regenerated `out/centre_pompidou.blend`, perspective preview, and front
  elevation with Blender 5.2.
- `verify_pompidou.py` pass; all 38 checks passed, including open ground-floor
  glazing, removal of the opaque shell, reflective/transmissive glass values,
  and 204 visible interior truss members.
- Visually reviewed both renders; the facade is now smooth, reflective, and
  transparent enough to reveal the orange interior lighting and inner trusses.
- `git diff --check` pass.

Remaining issues: None for the requested glass, ground-floor opening, and
interior-truss changes.

## 2026-09-06 — main — lengthen facade and flatten paired escalators

Expanded the building from 166 m to 216 m by adding four structural bays and
updating the corresponding facade, frame, cantilever, standoff, plaza, and
camera extents. Re-spaced the seven landing centres so each floor-to-floor
flight has substantially more horizontal run. The two exposed X-shaped routes
now stay at or below 30 degrees instead of reading as steep 45–60 degree
flights; the current run is approximately 30 m between landing centres with
12 m landings.

Verification:
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- Regenerated `out/centre_pompidou.blend`, the perspective preview, and the
  orthographic front elevation with Blender 5.2.
- `verify_pompidou.py` pass; all 34 checks passed, including the 216 m facade,
  10 m storeys, 70 m overall height, 204 tight-to-building braces, twelve
  flights, and the explicit at-or-below-30-degree slope check.
- Visually reviewed both regenerated renders; the longer facade provides a
  gentler, more elegant escalator posture while retaining the exposed tubes and
  the facade-mounted truss frame.
- `git diff --check` pass.

Remaining issues: None for the requested length and escalator-slope adjustment.
The scene remains a proportional architectural study rather than survey-grade
BIM geometry.

## 2026-09-06 — main — add mirrored X escalators on extended cantilevers

Changed the single diagonal caterpillar into two separate, mirrored escalator
routes. The original route now rises from the lower left toward the upper right;
the added route rises from the lower right toward the upper left, producing a
paired X-shaped circulation system across the exposed facade. Each route has
six floor-to-floor flights, seven landings, a continuous glazed weather tube,
individual treads, balustrades, handrails, and enclosure hoops.

Kept the diagonal truss wall tight against the building and left both escalator
tubes exposed outside it. The existing cylindrical horizontal supports now
extend 13.8 m outward from the facade frame, far enough to carry both escalator
routes without introducing a second outer truss wall or enclosing support cage.

Verification:
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- Regenerated `out/centre_pompidou.blend`, the perspective preview, and the
  orthographic front elevation with Blender 5.2.
- `verify_pompidou.py` pass; all 32 checks passed for twelve flights, two
  opposite-direction routes, fourteen landings, two continuous glass tubes,
  doubled tread and enclosure counts, absence of an outer truss cage, and 112
  extended cylindrical cantilevers.
- Visually reviewed `out/centre_pompidou_front.png` and
  `out/centre_pompidou_preview.png`; the paired routes form a clear X in the
  front view, remain separated in depth in perspective, and stay outside the
  facade-mounted diagonal trusses.
- `git diff --check` pass.

Remaining issues: None for this requested X-shaped circulation adjustment.
The scene remains a proportional architectural study rather than survey-grade
BIM geometry.

## 2026-09-06 — main — match the Pompidou caterpillar reference

Reworked the west-façade circulation against a photographic reference instead
of continuing the unsupported stacked-zigzag interpretation. The caterpillar is
now six successive, same-direction floor-to-floor escalator flights stepping
diagonally across the façade, with seven short intermediate landing tubes. Each
flight has a cylindrical glazed enclosure with closely spaced white hoops,
individual treads, glass balustrades, and a red handrail.

Verification:
- Captured and reviewed `out/pompidou_reference_selected.png` from the current
  browser session as the comparison reference.
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- Regenerated `out/centre_pompidou.blend`, the perspective preview, and the
  orthographic front view with Blender 5.2.
- `verify_pompidou.py` pass; all 21 checks passed for six ascending flights,
  seven landings, six cylindrical flight tubes, seven landing tubes, and the
  façade-spanning diagonal chain.
- Visually compared `out/centre_pompidou_front.png` and
  `out/centre_pompidou_preview.png` against the captured reference. The overall
  circulation topology and cylindrical ribbed enclosure now follow the real
  caterpillar rather than the prior alternating stack.
- `git diff --check` pass.

Additional calibration in this pass uses the Centre Pompidou's official published
dimensions: 166 m length, 60 m width, 42 m height, and six occupied plateaux
within the seven-level superstructure. The escalator chain now spans the widened
façade, uses seven evenly spaced landings, and has hoops at approximately 2 m
intervals on both flights and landings. The official Centre Pompidou page also
confirms that the caterpillar is the main diagonal outdoor path serving all
levels and that the circulation systems are externally exposed.

Verification after calibration:
- `blender --background --factory-startup --python build_pompidou.py` pass;
  regenerated the `.blend`, perspective preview, and a dedicated orthographic
  front elevation.
- `blender --background out/centre_pompidou.blend --python
  verify_pompidou.py -- out/centre_pompidou.blend` pass; all 25 checks passed.
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- `git diff --check` pass.

Remaining issues: This is still a proportional architectural study, not a
survey-grade BIM. The photographic reference is perspective-only and does not
provide the exact caterpillar tube diameter, support-node spacing, or hidden
connection dimensions.

## 2026-09-06 — main — lengthen caterpillar landing platforms

Adjusted the caterpillar so each intermediate landing is a substantial glazed
horizontal tube rather than a short connector. Landing length is now 9.4 m,
with full-length tube geometry and hoops at roughly 2 m spacing. Flight tube
and landing tube lengths are checked to remain comparable, matching the supplied
reference detail.

Verification:
- `blender --background --factory-startup --python build_pompidou.py` pass;
  regenerated the `.blend`, perspective preview, and orthographic front view.
- `verify_pompidou.py` passes all 27 checks for the seven-storey model,
  upper-six-storey bracing, and comparable landing/flight tube length checks.
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- `git diff --check` pass.

Remaining issues: None beyond the documented proportional-study limitations.

## 2026-09-06 — main — correct oversized Pompidou escalator flights

Corrected the escalator scale after the previous zigzag used nearly the full
98 m facade width for every floor-to-floor flight. The seven landing centres now
alternate across a compact 15.5 m span, producing six approximately 13.7 m long
flights at about 29 degrees. Reduced the landing length to 4.5 m and adjusted the
tread count to 35 per flight while retaining separate balustrades, handrails,
platforms, and glazed enclosures.

Verification:
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- Regenerated `out/centre_pompidou.blend` and
  `out/centre_pompidou_preview.png` with Blender 5.2.
- `verify_pompidou.py` pass; all 24 checks passed, including explicit limits for
  11-15 m flight length, 25-35 degree slope, and under-20 m landing span.
- Regenerated and visually reviewed `out/centre_pompidou_front.png` and the
  perspective preview; both show a compact six-flight vertical circulation stack.
- `git diff --check` pass.

Remaining issues: Exact escalator and landing dimensions remain reference-based
rather than survey-derived. None for the oversized-flight defect.

## 2026-09-06 — main — correct Pompidou escalator zigzag

Replaced the incorrect seven-flight, one-way diagonal escalator with six
independent floor-to-floor flights connecting seven landings. Successive flights
now reverse direction between fixed left and right landing ends, producing the
required front-elevation zigzag. Each flight retains individual treads, glass
balustrades, red handrails, and its own framed glass enclosure.

Verification:
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- `blender --background --factory-startup --python build_pompidou.py -- --no-render`
  pass; regenerated `out/centre_pompidou.blend` and the perspective preview.
- `blender --background out/centre_pompidou.blend --python verify_pompidou.py -- out/centre_pompidou.blend`
  pass; all 21 checks passed, including exact flight count, tread count,
  alternating flight directions, and alternating landing ends.
- Rendered and visually reviewed `out/centre_pompidou_front.png`; the six flights
  alternate cleanly between seven level-aligned end platforms.

Remaining issues: The building dimensions and escalator proportions are based on
available references rather than survey data. Previously added interior cores,
lift shafts, columns, floor assemblies, and roof plant remain generalized and
should not be treated as authoritative BIM geometry.

## 2026-09-06 — main — expand Pompidou to BIM-like component detail

Expanded the model beyond the exterior escalator work into separable
architectural, structural, vertical-transport, facade, and MEP components. The
scene now includes 112 segmented interior columns, floor transfer beams, two
full-height service cores with per-floor elevator doors and roof headrooms,
seven distinct lift shafts with cars and guide rails, modular raised floors,
suspended ceiling grids, distributed colored service racks, panelized curtain
wall glazing, sill flashings, and 196 facade-to-frame standoffs. Existing exposed
structure, seven escalator flights, platforms, enclosure glass, and coded service
risers remain individually editable.

Verification:
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- `blender --background --factory-startup --python build_pompidou.py` pass in
  2m23s; regenerated `out/centre_pompidou.blend` and the preview render.
- `blender --background --factory-startup --python verify_pompidou.py -- out/centre_pompidou.blend`
  pass; all 19 component-count and scene checks passed.
- Visually reviewed the regenerated render for facade panelization, internal
  depth, core headrooms, external circulation, and MEP readability.
- `git diff --check` pass.

Remaining issues: This is now BIM-like in component separation and model
granularity, but it is not authoritative construction BIM: published survey
geometry, manufacturer families, connection schedules, fire strategy, and
asset parameters were not supplied.

## 2026-09-06 — main — detail Pompidou escalators and glazing

Rebuilt the exterior circulation as seven separate storey-height escalator
flights instead of continuous cylindrical tubes. Every flight now has individual
metal treads, sloping belts, red handrails, transparent glass balustrades, a
segmented glazed weather enclosure, enclosure ribs, and a distinct horizontal
landing between levels. Increased the building to seven occupied levels and
reworked both long facades as semi-transparent curtain walls with dense vertical
mullions and floor-level transoms.

Verification:
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- `blender --background --factory-startup --python build_pompidou.py` pass;
  regenerated `out/centre_pompidou.blend` and the preview render.
- `blender --background --factory-startup --python verify_pompidou.py -- out/centre_pompidou.blend`
  pass; all 13 checks passed, including exact checks for seven flights, seven
  horizontal landings, 133 treads, segmented enclosure glass, and facade glass.
- Visually reviewed the final render; each floor-to-floor escalator and landing
  is now separately legible through the transparent enclosure.
- `git diff --check` pass.

Remaining issues: The reconstruction remains an architectural visualization,
not a survey-accurate BIM model. Interior galleries and building services are
more detailed but still generalized from the real building.

## 2026-09-05 — main — build Centre Pompidou model

Added a standalone procedural Blender reconstruction of the Centre Pompidou.
The editable scene includes the six-storey exhibition volume, exposed white
external frame and diagonal bracing, roof ties and gerberette-like cantilevers,
the front glass escalator snake, and the building's blue, green, yellow, and red
external service systems. Added a plaza, roof plant, interior floor plates and
lighting, presentation materials, camera, and a separate structural verifier.

Verification:
- `python3 -m py_compile build_pompidou.py verify_pompidou.py` pass.
- `blender --background --factory-startup --python build_pompidou.py` pass;
  generated `out/centre_pompidou.blend` and
  `out/centre_pompidou_preview.png`.
- `blender --background --factory-startup --python verify_pompidou.py -- out/centre_pompidou.blend`
  pass; all 9 scene checks passed.
- Visually reviewed the final 1400 x 900 render for framing, readable structure,
  exterior services, and circulation tube.
- `git diff --check` pass.

Remaining issues: The model is a stylized architectural reconstruction rather
than a survey-accurate BIM model; facade pipe routing and gerberette geometry
are simplified.
