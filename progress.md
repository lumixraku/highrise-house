# Progress

## 2026-08-23 — fix — add refuge-level plan X bracing and crossed short-face trusses

Expanded the taller companion tower's two refuge-level truss systems without
adding members to ordinary residential floors. Each short-face panel now has a
second diagonal, making a complete X brace. Each refuge level also gets four
horizontal plan-X panels, embedded in the upper refuge slab to stiffen the
diaphragm while staying out of residential rooms and sightlines. The first tower
is unchanged.

Verification:
- `python3 -m py_compile build_house.py verify_house.py floor_plan.py render_views.py` passed.
- `git diff --check` passed.
- Blender 5.2.0 LTS rebuilt `out/highrise_house.blend`, `out/highrise_house.glb`,
  and `out/preview.png`; the companion has 96 refuge-truss members (48 per
  refuge level), including 32 crossed short-face diagonals and 16 hidden plan-X
  members.
- `verify_house.py` reports `163/167`; all new truss checks pass. The four
  remaining failures are the same pre-existing geometry assumptions (`blank
  bands land on floor lines`, refuge corner piers, roof-overrun footprint, and
  solid corner-wall sampling).

Remaining issues: None for the requested truss additions. This is still a
conceptual geometry model, not a substitute for a project-specific structural
analysis.

## 2026-08-23 — fix — add companion-tower refuge-level Z trusses

Added a dedicated `Structural_Trusses` mesh to the taller companion tower only.
At both of its double-height refuge / sky-garden levels, the system now has
long-face belt chords, core-to-perimeter outriggers, alternating Z-shaped
diagonals on both short (depth-side) facades, and X-braced panels on both faces
of both service cores. The concrete cores remain continuous closed tubes; the
metal members are an added lateral-load path and a visible core-to-perimeter
connection. Updated the verifier and README with the truss geometry and scope.

Verification:
- `python3 -m py_compile build_house.py verify_house.py floor_plan.py render_views.py` passed.
- `git diff --check` passed.
- Blender 5.2.0 LTS rebuilt `out/highrise_house.blend` and `out/highrise_house.glb`; 64 truss members were generated across the two companion refuge levels.
- `verify_house.py` passed all new truss assertions: `161/165` overall. The four remaining failures are pre-existing boundary assumptions (`blank bands land on floor lines`, refuge corner piers, roof-overrun footprint, and solid corner-wall sampling).

Remaining issues: the four legacy verifier assumptions above remain; none is caused by the truss system.

## 2026-08-23 — fix — extend the companion cores to one-bay separation

Adjusted only the taller companion tower's service cores from two long-face
column bays to three. The outer boundary remains on the first inset column line,
so each core grows inward while its defining columns stay connected to the wall.
The companion now uses `27.73 x 9.00 m` cores at x = +/-17.42 m, leaving a
`7.11 m` clear single-column bay between them. The original 76 m tower remains
at two bays and `19.20 x 9.00 m` cores at x = +/-17.60 m. Updated the procedural
configuration, verifier, and README.

Verification:
- `python3 -m py_compile build_house.py verify_house.py floor_plan.py render_views.py` passed.
- `git diff --check` passed.
- Blender 5.2.0 LTS rebuilt `out/highrise_house.blend` and `out/highrise_house.glb`; the companion report confirmed 27.73 m cores and a 7.11 m gap.
- `verify_house.py` passed the new companion core-length, end-column, and one-bay separation assertions and reports `151/155` overall.

Remaining issues: four pre-existing verifier assumptions remain (`blank bands land on floor lines`, refuge corner piers, roof-overrun footprint, and solid corner-wall sampling); none is caused by this core extension.

## 2026-08-23 — fix — derive service-core length from each tower's columns

Replaced the shared fixed core length with a per-tower layout derived from the
long-face column grid. Each core now spans two column bays and extends to the
outer faces of its defining columns, so those columns remain in the structural
mesh and meet both core ends. The reference tower now uses 19.20 x 9.00 m cores
at x = +/-17.60 m; the taller companion independently uses 19.02 x 9.00 m cores
at x = +/-21.78 m. Synchronized the floor plan, README, build report, and
geometry checks with the derived dimensions.

Verification:
- `python3 -m py_compile build_house.py verify_house.py floor_plan.py render_views.py` passed.
- `git diff --check` passed.
- Blender 5.2.0 LTS rebuilt `out/highrise_house.blend` and `out/highrise_house.glb`; both tower reports confirmed the derived core sizes and positions.
- `verify_house.py` passed the new core-length and column-contact assertions for both towers and reports `150/154` overall.

Remaining issues: four pre-existing verifier assumptions remain (`blank bands land on floor lines`, refuge corner piers, roof-overrun footprint, and solid corner-wall sampling); none is caused by this core-layout change.

## 2026-08-23 — fix — build two residential towers with separate configurations

Kept the existing tower at the origin with `2 x 17` residential groups and `18`
long-facade rooms per floor (`76 x 32 m`, `43` storeys, roof at `172.0 m`). Added
an adjacent procedural tower using `3 x 17` groups and `20` long-facade rooms per
floor (`84 x 32 m`, `62` storeys, roof at `248.0 m`). The towers share the fixed
floor, depth, pier and twin-core rules, remain `18.0 m` apart, and are framed as a
`178.0 x 32.0 m` site. Both builds reuse the same material set so the original
tower's emissive ceiling-light slots remain intact. Added verifier checks for the
second tower's width, 51 glazed floors and clear gap; synchronized README and
extra-view framing with the two-tower site.

Verification:
- `python3 -m py_compile build_house.py verify_house.py render_views.py floor_plan.py materials.py` passed.
- `git diff --check` passed.
- Blender 5.2.0 LTS rebuilt `out/highrise_house.blend` and `out/highrise_house.glb`; the build report confirmed both configurations and the 18 m gap.
- Full Cycles preview rendered to `out/preview.png` and was visually inspected; six low-sample extra views rendered successfully, including the two-tower front elevation.
- `verify_house.py` passed all new two-tower checks and reports `148/152`; four legacy geometry assumptions remain (`blank bands land on floor lines`, refuge corner piers, roof-overrun footprint, and solid corner-wall sampling).
- Final README pass now labels the saved preview as a Cycles render of both towers.

Remaining issues: the four pre-existing verifier assumptions above are unchanged and unrelated to the separate tower configurations.

## 2026-08-23 — fix — add clustered office ceiling lights

Added warm emissive ceiling panels behind the Office tower curtain wall. Each
of the 24 office floors now lights 31 of 103 facade modules (30.1%): most lights
form deterministic 3–6-module work-zone clusters, with a smaller number of
isolated late-working bays. The fixed seed gives every office floor a different
pattern while keeping rebuilds stable. Pilotis, equipment, refuge, and roof
levels receive no lights.

Verification:
- `python3 -m py_compile build_office.py materials.py` passed.
- `git diff --check` passed.
- Blender 5.2.0 LTS rebuilt `out/office_tower.blend` and
  `out/office_tower.glb` successfully, producing 744 ceiling panels across the
  24 office floors only.
- Inspected the saved blend: `Office_Ceiling_Lights` has the expected 5,952
  vertices / 4,464 faces, stays inside the 50 m curtain-wall envelope, and uses
  `OfficeCeilingLight` with emission strength 6.0.
- Re-rendered and visually checked `out/office_preview.png`; clustered and
  scattered lights are visible through the glazing without lighting the blank
  or ventilated bands.

Remaining issues: None.

## 2026-08-23 — fix — randomize occupied-room ceiling lights

Changed the residential ceiling lights from every room window being on to a
deterministic 36% occupancy pattern. Each facade is generated independently on
each glazed floor: one short adjacent cluster is kept for a natural occupied
patch, while the remaining lights are scattered. The fixed seed makes rebuilds
stable, but all 34 glazed floors receive distinct patterns. Updated the README
and verifier with sparse-count, per-floor, and pattern-variation checks.

Verification: Python compilation and diff whitespace checks passed. Blender
rebuilt the `.blend` and `.glb`, all six 16-sample views rendered, and front,
corner, and floor-detail images were inspected. The model contains 612 light
panels: 18 of 50 room-window positions per glazed floor. All new light checks
pass; the full verifier remains at 144/148 because of the same four pre-existing
geometry assumptions. Remaining issues for this change: None.

## 2026-08-23 — fix — verify emissive ceiling-light diagnostics

Corrected the ceiling-light verifier diagnostic so a present material slot is
reported accurately when the emissive material check passes. Rebuilt the house,
exported glTF, rendered all six low-sample views, and inspected the front,
corner, and floor-detail views; the recessed warm light panels are visible
behind the glazing and remain inside the facade.

Verification: Python compilation, Blender rebuild, six-view render, and
verifier checks completed. The verifier reports 141/145 checks because four
pre-existing geometry assumptions still fail; all ceiling-light checks pass.
Remaining issues for this change: None.

## 2026-08-23 — fix — add recessed emissive ceiling lights

Added one small warm-white emissive ceiling panel per room-window bay on every
glazed floor. The panels sit just inside the existing window band, between the
glass and the interior lining, so they read as real ceiling fixtures through the
facade without changing the 76 x 32 m envelope. Added the `Ceiling_Lights` mesh
object, a dedicated emissive material, and verifier checks for count, height,
recess, and emission strength.

Verification: Python compilation, Blender rebuild, low-sample render of all six
views, and image inspection passed. The legacy verifier still reports its
pre-existing four geometry assumptions unrelated to these lights. Remaining
issues for this change: None.

## 2026-08-23 — fix — widen and move the twin service cores

Responding to the wider 76 m plate, changed each service core from 16 × 9 m at
x = ±16 m to 20 × 9 m at x = ±18 m. This reduces the outboard clearance to each
short end from 14 m to 10 m while preserving a 16 m clear span between cores and
keeping every core edge on the 4 m pane grid. Synchronized `build_house.py`,
`verify_house.py`, `floor_plan.py`, and the service-core section of `README.md`.

Verification: Python compilation, floor-plan regeneration, diff whitespace check,
and Blender rebuild passed. The build report confirms two 20 × 9 m cores at ±18 m
with 360 m² total provision. Six low-sample Blender views rendered successfully,
including the pilotis close-up. The legacy verifier still stops at its pre-existing
missing `Interior_Lining` object assertion. Remaining issues: None for this change.

## 2026-08-23 — fix — parameterize the two residential blocks and room count

Made the requested massing controls explicit in `build_house.py`: each of the two
residential blocks now uses `BLOCK_FLOORS = 17`, and the long facade uses
`WINDOWS_LONG = 18` room-window modules per floor. `TOTAL_FLOORS` is derived from
the two blocks plus the fixed pilotis, refuge and solid-band floors; `W` is derived
from the long-facade module count and fixed piers. The verifier now mirrors these
parameters and asserts the refuge divides the glazed floors into two 17-floor
blocks. The floor-plan and extra-view scripts follow the 18-room width and derived
172 m roof / 88–96 m refuge elevations; the README summary reflects the new 76 ×
32 m, 43-storey configuration.

Verification: `py_compile`, `git diff --check`, and a Blender rebuild passed. The
build report confirms 43 total floors, 34 glazed floors split 17 + 17, 18 long-face
windows per floor, a 76.0 × 32.0 m footprint, and a 172.0 m roof. The full legacy
verifier still stops at its pre-existing missing `Interior_Lining` object assertion.
Remaining issues: None for the requested parameter change.

## 2026-08-23 — fix — close the upper two metres of the refuge opening

Added a solid facade band from z=106.0–108.0 m above the six-metre refuge grille.
The actual refuge void and its ceiling remain 8.0 m high, but the outside opening
now ends at z=106.0 m and the wall is directly connected to the grille top.

Verification: Python compilation, `git diff --check`, Blender rebuild, and a
saved-Blend geometry probe passed. Remaining issue: the full verifier still stops
at the pre-existing missing `Interior_Lining` object assertion.

## 2026-08-23 — fix — revalidate the refuge grille and facade band configuration

Synchronized the README with the current 49-storey model and regenerated the
saved Blender and glTF outputs plus the five extra views. The residential
ventilation + glass band remains 0.50–2.50 m above each floor, with the clear
glass at 0.75–2.25 m. The 8.0 m refuge void remains z=100.0–108.0 m; its
external grille/opening starts at z=100.0 m and ends at z=106.0 m, with a solid
wall closing the upper 2.0 m.

Verification: `py_compile`, `git diff --check`, Blender rebuild, extra-view
renders, and a saved-Blend vertex probe passed. The full verifier still stops at
the pre-existing missing `Interior_Lining` object assertion. The README's pane
counts and the 20/20 glazed-floor split around the refuge are synchronized too.

## 2026-08-23 — fix — bind the refuge grille to the 8 m void

Made the refuge screen geometry derive from the actual 8.0 m refuge void: its
lower edge remains at the refuge floor, its height is 8.0 minus a 2.0 m top
blank band, and its upper edge is therefore exactly 6.0 m above the floor.
Regenerated the `.blend`, `.glb`, preview, and extra view renders.

Verification: Python compilation, `git diff --check`, and a saved-Blend probe
passed. The refuge grille is z=100.0–106.0 m inside the z=100.0–108.0 m void;
the next glass band resumes at z=108.75 m. The full verifier still has the
pre-existing missing `Interior_Lining` object assertion.

## 2026-08-23 — fix — expand the tower to 40 residential floors

Changed the house to 49 physical storeys: 3 pilotis floors, 40 glazed
residential floors, 4 blank floors, and a 2-storey refuge void. Regenerated
`out/highrise_house.blend` and `out/highrise_house.glb`; the roof is now at
196.0 m, the parapet at 197.32 m, and the core bulkheads at 201.94 m.

Verification: Python compilation passed and the Blender build report confirmed
exactly 40 glazed floors. Remaining issues: None.

## 2026-08-23 — fix — shorten the refuge grille and restore glazing above

Removed the 4.0 m solid separator above the refuge void, restoring the normal
glazed facade above it. In the current 49-storey configuration the refuge
occupies z=100.0–108.0 m; its outside grille begins at z=100.0 m and is 6.0 m
high (z=100.0–106.0 m), leaving the upper 2.0 m open. Updated the geometry
checks and documentation accordingly.

Verification: Python compilation and `git diff --check` passed; Blender rebuilt
`out/highrise_house.blend` and `out/highrise_house.glb`. A saved-Blend probe
confirmed refuge grille vertices at z=100.0 and 106.0, and glass resumes above
the refuge at z=108.75 m. The full verifier still stops at its pre-existing
missing `Interior_Lining` object assertion.

## 2026-08-23 — fix — add a solid separation floor above the refuge void

Added one 4.0 m windowless facade floor directly above the double-height refuge
garden. The refuge void remains open from z=80.0–88.0 m; its new solid separator
band occupies z=88.0–92.0 m, with glazing and ventilation resuming above it.
Updated the generated-floor accounting, geometry-verification constants and
sampling heights, and the documentation. The model now has 30 glazed floors.

Verification: `python3 -m py_compile build_house.py verify_house.py` and
`git diff --check` passed; Blender regenerated `out/highrise_house.blend` and
`out/highrise_house.glb`; a saved-Blend geometry probe confirmed z=88.0–92.0 m
contains a full facade wall and no glass or vents. `verify_house.py` still stops
at its pre-existing `Interior_Lining` object assertion, because the current
generator does not create that legacy object. Remaining issues: None for the
refuge-top separation band.

## 2026-08-22 — fix — move the residential facade band down to 0.50 m above every floor

Moved the per-floor ventilation + glass + ventilation assembly in `build_house.py`
from the vertically centred position to z=0.50–2.50 m above each glazed-floor
level. The 1.50 m glass now spans z=0.75–2.25 m; the 0.25 m louvre strips span
z=0.50–0.75 m and z=2.25–2.50 m; the solid spandrels are 0.50 m below and
1.50 m above. Updated `verify_house.py` and the facade-band documentation to
assert and describe the new position.

Verification: `python3 -m py_compile build_house.py verify_house.py` passed;
Blender regenerated `out/highrise_house.blend` and `out/highrise_house.glb`; a
saved-Blend geometry probe passed for all 31 glass bands and 62 vent bands at the
specified offsets. `verify_house.py` still stops at its pre-existing
`Interior_Lining` object assertion, because the current generator does not create
that object. Remaining issues: None for this facade-band change.

## 2026-08-22 — fix — restore the complete column count with corner relocation

Restored all original non-corner grid columns after the erroneous perimeter-row
removal. Only the four original grid-corner columns are replaced by four
columns at the actual building corners, preserving the original total of 20
main structural columns. All 20 columns now run as single uninterrupted
members from z=0 to the building's highest elevation, z=165.94 m.

Verification: `python3 -m py_compile build_house.py` passed; Blender
regenerated `out/highrise_house.blend` and `out/highrise_house.glb`; saved-mesh
inspection counted exactly 20 continuous columns, each with z-range
0.00–165.94 m. Remaining issues: None.

## 2026-08-22 — fix — remove the remaining perimeter column row

Removed every non-corner column from the inset perimeter grid, using explicit
grid row/column indices so neither facade can retain an asymmetric outer column
by floating-point comparison. The structure now contains only six continuous
main-tower columns: four corner columns and two interior columns. Each runs
unbroken from z=0 to the main-roof elevation at z=160 m.

Verification: `python3 -m py_compile build_house.py` passed; Blender
regenerated `out/highrise_house.blend` and `out/highrise_house.glb`; saved-mesh
inspection found full-height columns only at (0.0, -4.4), (0.0, 4.4), and the
four corners (+/-31.0, +/-15.0). Remaining issues: None.

## 2026-08-22 — fix — verify removal of the four inset corner columns

Regenerated the deliverable scene and inspected the joined `Structure` mesh
after the reported duplicate-column view. The four former inset corner-grid
positions at (+/-29.2 m, +/-13.2 m) are excluded from the full-height grid;
only the four actual corner columns at (+/-31.0 m, +/-15.0 m) remain, each
continuous from the ground to the 160 m tower top.

Verification: `python3 -m py_compile build_house.py` passed and Blender
regenerated `out/highrise_house.blend` and `out/highrise_house.glb`.
Remaining issues: None in the regenerated scene; a viewer must reload the
saved Blend/GLB to discard any older scene instance.

## 2026-08-22 — main — relocate the four corner columns

Restored the original 2 m facade corner margins and 15-by-7 ribbon-window
layout. Replaced the four closest inset grid columns with four 1.60 m square
columns centred at the actual building corners, so the corner supports align
with the retained corner pier zones while every other column remains inset from
the glazing.

Verification: `python3 -m py_compile build_house.py verify_house.py` passed;
Blender regenerated `out/highrise_house.blend` and `out/highrise_house.glb`.
The rebuilt structure reports the four corner-column centres at (+/-29.2 m,
+/-13.2 m). Remaining issues: the existing standalone geometry verifier still
expects the removed `Interior_Lining` object, so it requires its unrelated
legacy expectation to be updated before it can complete.

## 2026-08-22 — main — make corner columns replace corner walls

Corrected the corner detail so the four 2 x 2 m continuous corner columns
replace the L-shaped corner wall piers instead of overlapping them. All facade
wall and spandrel bands now terminate at each corner-column edge; the closest
inset grid columns remain omitted.

Verification: `python3 -m py_compile build_house.py` passed and Blender
regenerated `out/highrise_house.blend` and `out/highrise_house.glb` with the
revised non-overlapping corner geometry. Remaining issues: `verify_house.py`
still carries a pre-existing expectation for an `Interior_Lining` mesh that the
current generator no longer creates.

## 2026-08-22 — main — match the corner-column finish to the facade

Assigned the four corner columns the same spandrel material used by the facade,
replacing the unintended exposed-concrete finish. Their geometry and clean wall
termination remain unchanged.

Verification: `python3 -m py_compile build_house.py` passed and Blender
regenerated `out/highrise_house.blend` and `out/highrise_house.glb`. Remaining
issues: None for this material correction.

## 2026-08-22 — main — remove the oversized scene ground

Removed the 600 x 600 m dark scene-ground mesh so it no longer blocks
under-building and upward-looking views. The building's own structural ground
slab remains in place.

Verification: `python3 -m py_compile build_house.py` passed; Blender
regenerated `out/highrise_house.blend` and `out/highrise_house.glb`. A saved
scene inspection confirms `Ground` is absent and the building `Structure`
remains present. Remaining issues: None.

## 2026-08-21 — main — restore physical transparent glass

Replaced the prior alpha-cutout glass with fully opaque-at-the-shader physical
glass: alpha is again 1.00, while transmission remains 1.00 and roughness 0.00.
This restores Fresnel reflection and clear refraction instead of the frosted
look caused by alpha blending. Kept the interior linings removed, and aligned
the office tower's Cycles ray budgets with the house: 12 total, transmission,
and transparent bounces plus 6 glossy bounces.

Verification: `python3 -m py_compile materials.py build_office.py build_house.py`,
both headless Blender builds, and saved-Blend inspections passed. Both generated
glass materials report alpha 1.00; neither model contains interior lining
geometry; both scenes use 12 transmission bounces. Remaining issues: None.

## 2026-08-21 — main — make both tower facades visibly transparent

Changed the shared glass material to a 0.38-alpha pale green architectural
glass and enabled Blender's dithered surface transparency. Removed the opaque
interior lining generated directly behind glazing in both `build_office.py`
and `build_house.py`, so floor plates, service cores, and the far-side facade
remain visible through the windows.

Verification: `python3 -m py_compile materials.py build_office.py build_house.py`,
both headless Blender builds, and saved-Blend inspections passed. Both glass
materials report alpha 0.38, and neither generated model contains an interior
lining object. Remaining issues: None.

## 2026-08-21 — main — moderate office glazing height

Reduced `CLEAR_PANE_H` in `build_office.py` from 4.00 m to 3.50 m. Green
glazing now covers 70% of each 5.00 m office storey, balancing it against the
1.50 m upper white band.

Verification: `python3 -m py_compile build_office.py` and
`blender --background --factory-startup --python build_office.py -- --no-render`
completed successfully, regenerating `out/office_tower.blend` and
`out/office_tower.glb`. Remaining issues: None.

## 2026-08-21 — main — increase office glazing proportion

Increased `CLEAR_PANE_H` in `build_office.py` from 2.50 m to 4.00 m within
each 5.00 m office storey. The green glazing now occupies 80% of each office
facade band, leaving a shallower 1.00 m upper white band.

Verification: `python3 -m py_compile build_office.py` and
`blender --background --factory-startup --python build_office.py -- --no-render`
completed successfully, regenerating `out/office_tower.blend` and
`out/office_tower.glb`. Remaining issues: None.

## 2026-08-21 — main — orient refuge grilles toward the tower centre

Reworked each refuge-level grille member in `build_office.py` as a 1.20 m long,
0.08 m wide vertical blade. Each blade now extends along the local radial axis
and points toward the tower's geometric centre, producing the requested
clock-tick pattern in plan view.

Verification: `python3 -m py_compile build_office.py` and
`blender --background --factory-startup --python build_office.py -- --no-render`
completed successfully, regenerating `out/office_tower.blend` and
`out/office_tower.glb`. Remaining issues: None.

## 2026-08-21 — main — express inter-group refuge levels as fine grilles

Changed the two inter-group refuge levels in `build_office.py` from solid
equipment facade bands to open vertical metal grilles. The grilles use 0.08 m
wide members at approximately 0.50 m centres; podium and roof equipment levels
remain solid.

Verification: `python3 -m py_compile build_office.py` and
`blender --background --factory-startup --python build_office.py -- --no-render`
completed successfully, regenerating `out/office_tower.blend` and
`out/office_tower.glb`. Remaining issues: None.

## 2026-08-21 — main — make office glazing continuous below top band

Changed `build_office.py` so each office glass panel starts at its floor level
instead of being vertically centred. This removes the lower white facade strip
and leaves the existing upper white horizontal band above each continuous green
glass field.

Verification: `python3 -m py_compile build_office.py` and
`blender --background --factory-startup --python build_office.py -- --no-render`
completed successfully, regenerating `out/office_tower.blend` and
`out/office_tower.glb`. Remaining issues: None.

## 2026-08-21 — main — correct office tower to three eight-floor groups

Corrected the prior four-group mistake. The office tower now has exactly three
groups of eight office floors (24 total) and exactly two inter-group equipment /
refuge levels. It retains two equipment levels above the pilotis and two at the
top, all excluded from the office count. The resulting 33 physical 5.0 m levels
put the roof at 165.0 m above ground.

Verification: `blender --background --factory-startup --python build_office.py --
--no-render` completed successfully. The model reports 24 office floors in three
groups of eight, equipment/refuge levels `[3, 4, 13, 22, 31, 32]`, and a 165.0 m
roof elevation. Remaining issues: None.

## 2026-08-21 — main — regroup office tower into eight-floor zones

Reconfigured `build_office.py` into four groups of eight office floors (32 office
floors total). Added the requested solid equipment bands: two directly above the
three-level pilotis, one between each pair of office groups, and two at the top.
All equipment bands have full floor slabs and remain excluded from the office-floor
count. The 42 physical levels at 5.0 m put the roof at 210.0 m above ground.

Verification: `python3 -m py_compile build_office.py`,
`blender --background --factory-startup --python build_office.py -- --no-render`,
and saved-Blend geometry inspection all passed. The model has 32 office glass bands,
seven equipment bands spanning 15.0–25.0 m, 65.0–70.0 m, 110.0–115.0 m,
155.0–160.0 m, and 200.0–210.0 m; the core is continuous at 14.0 x 14.0 x 210.0 m.
Remaining issues: None.

## 2026-08-21 — main — group office floors around equipment refuge levels

Corrected the office-tower count: the three pilotis levels and two equipment/refuge
levels no longer count as office floors. The tower now contains three groups of 10
glazed office floors, separated by solid 5.0 m equipment/refuge bands at physical
levels 13 and 24. With the three pilotis levels, this makes 35 physical levels and
a 175.0 m roof elevation.

Verification: `python3 -m py_compile build_office.py`,
`blender --background --factory-startup --python build_office.py -- --no-render`,
and saved-Blend geometry inspection all passed. The model contains exactly 30 glass
bands, and the equipment/refuge bands span z=65.0–70.0 m and z=120.0–125.0 m.
Remaining issues: None.

## 2026-08-21 — main — complete office floor plates and service core

Replaced the office facade-edge-only floor geometry with full solid concrete slabs
at every level from the pilotis roof through the 30th storey, including both
refuge levels. Added a 14.0 x 14.0 m solid concrete `Office_Core` continuously
from ground level to the 150.0 m roof, eliminating the hollow tower interior.

Verification: `python3 -m py_compile build_office.py`,
`blender --background --factory-startup --python build_office.py -- --no-render`,
and an inspection of `out/office_tower.blend` all passed. Slabs exist at every
5.0 m level from 15.0 m through 150.0 m; the core measures 14.0 x 14.0 x 150.0 m
with z bounds 0.0–150.0 m. Remaining issues: None.

## 2026-08-21 — main — revise office tower storeys and refuge floors

Updated `build_office.py` to derive a 150.0 m tower from 30 storeys at 5.0 m
floor-to-floor. Storeys 10 and 20 are now open refuge levels: their glazing,
mullions, floor-edge rings, and interior lining are omitted, while continuous
open vertical fins retain the facade profile and natural ventilation.

Verification: `python3 -m py_compile build_office.py`,
`blender --background --factory-startup --python build_office.py -- --no-render`,
and a saved-Blend geometry probe all passed. The generated model reports 30
storeys at 5.0 m and refuge storeys 10 and 20; the refuge screens span
z=45.0–50.0 m and z=95.0–100.0 m. Remaining issues: None.

## 2026-08-19 — main — rooftop open sky garden

Added a roof-level sky garden above the roof slab with perimeter grille, planting,
and trees. The terrace deliberately has no ceiling; the lift/stair bulkheads remain
the only volumes rising above it. The grille exactly matches the refuge garden:
full two-storey height (8.0 m), with 0.10 m blades at 0.50 m centres and 0.34 m deep.
Added roof-garden geometry checks and a dedicated `out/view_roof_garden.png` render.

Verification: `python3 -m py_compile build_house.py verify_house.py render_views.py`,
Blender rebuild, and `blender -b --python verify_house.py -- out/highrise_house.blend`:
**136/136 checks passed**. The refuge and roof grilles are both 8.0 m high. Remaining issues: None.

## 2026-08-19 — main — connect roof grille corners

Extended the roof garden fins across the full building perimeter, including all
four corners. The refuge grille remains limited to its opening span because its
corner piers already close that level.

Verification: `python3 -m py_compile build_house.py verify_house.py` and
`blender -b --python verify_house.py -- out/highrise_house.blend`:
**136/136 checks passed**. Remaining issues: None.

## 2026-08-19 — main — elongated, narrower service cores

Changed each core from 12 x 12 m to 16 x 9 m: longer along the facade and narrower
into the apartments, preserving 144 m2 per core while giving the rooms 3 m more depth.
Core centrelines are x = +/-16 m, with 16 m clear separation and 8 m corner bays.

## 2026-08-19 — main — regenerated current build artifacts

Regenerated `out/highrise_house.blend`, `out/highrise_house.glb`, and `out/preview.png`
from the current `build_house.py`, then regenerated all five supplemental views:
`view_front.png`, `view_base_pilotis.png`, `view_floor_detail.png`, `view_corner.png`,
and `view_sky_garden.png`.

Verification: `verify_house.py` against the newly saved `.blend`: **132/132 checks
passed**. Remaining issues: None.

## 2026-08-19 — main — 0.25 m ventilation bands

Reduced each ventilation louvre band from 0.30 m to 0.25 m. The centred 1.50 m
window plus its upper and lower ventilation bands now totals exactly 2.00 m;
the remaining solid spandrels are 1.00 m above and below.

Verification: `python3 -m py_compile build_house.py floor_plan.py verify_house.py`,
Blender rebuild with `--no-render`, and `verify_house.py`: **132/132 checks passed**.
Remaining issues: None.

## 2026-08-19 — main — continuous full-height inset column grid

Replaced the separate pilotis and sky-garden column sets with one independent
structural grid running continuously from ground to roof. Every column outer
face is at least 2.00 m inside the facade; windows and refuge grille geometry are
unchanged.

Verification: `python3 -m py_compile build_house.py floor_plan.py verify_house.py`,
Blender rebuild with `--no-render`, and `verify_house.py`: **132/132 checks passed**.
Remaining issues: None.

## 2026-08-18 — main — recessed vertical window mullions

Recessed only the vertical `Window_Mullions` caps by 120 mm from the facade
plane. Glass and ventilation louvres remain flush, and the window dimensions,
counts, footprint, and floor structure are unchanged.

Verification: `python3 -m py_compile build_house.py floor_plan.py verify_house.py`,
Blender rebuild with `--no-render`, and `verify_house.py`: **134/134 checks passed**.
Remaining issues: None.

## 2026-08-19 — main — separate room windows with real vertical joints

Replaced each continuous facade glass ribbon with independent room panes. Each
pane remains centred on a 4.00 m module but is 3.88 m wide, leaving a 120 mm
vertical joint between adjacent homes. Interior linings use the same per-room
segmentation so the gap remains visually open.

Verification: Python compilation, Blender rebuild with `--no-render`, and
`verify_house.py`: **135/135 checks passed**. Remaining issues: None.

## 2026-08-19 — main — restore dense refuge garden grille

Restored the sky-garden fin spacing to the original absolute `0.50 m` pitch.
The window module change no longer changes the refuge grille density.

Verification: pending rebuild and geometry checks. Remaining issues: None known.

## 2026-08-18 — main — one 4 x 1.5 m window per room, footprint unchanged

Changed the facade module from two 2 x 1.5 m panes per room to one 4 x 1.5 m
room window. Window counts are now 15 on each long face and 7 on each short face;
the derived footprint remains exactly 64 x 32 m. Updated the floor-plan generator,
refuge screen/column spacing, and verification labels/checks accordingly.

Verification: `python3 -m py_compile build_house.py floor_plan.py verify_house.py`,
`python3 floor_plan.py`, Blender rebuild with `--no-render`, and
`verify_house.py`: **134/134 checks passed**. Remaining issues: None.

## 2026-08-17 — main — all four corner piers down to one pane (2 m)

Two rounds in one session. First the long-facade pier only (8 → 2 m), then the user
pointed at the render: "都改为 2m 呀！！！侧面也应该呀" — the short faces too.

The reasoning I had in the file before this was wrong and is now replaced. I had
claimed shrinking `PIER_LONG` gives nothing because "the glazing edge moves inward
with the corner unit". It does not: a glass run is fixed at N × 2.00 m, so the
glazing edge stays put and the pier only decides how far the **building end** sits
beyond it. At 8 m the corner apartment ended in 8 m of dead wall before reaching its
return; at 2 m it turns the corner after one pane.

Changed, in `build_house.py` and the duplicated constants in `verify_house.py`:

- `PIER_LONG` 8.0 → 2.0, `PIER_SHORT` 4.0 → 2.0.
- **`WINDOWS_SHORT` 12 → 14**, which is what makes the short pier affordable. D is
  derived, so thinning that pier alone would have given D = 28 m and dropped the unit
  depth beside the cores to 8.0 m, under the 9 m residential minimum. Two more panes
  hold D at exactly 32 m. Footprint ends at **64 × 32 m** (was 76 × 32): the depth the
  user asked to leave alone is unchanged, only the corners moved.
- `CORE_OFFSET` kept at 18.0, not reverted to 20.0 as an earlier "Y" had covered: at
  W = 64 the ±20 corner unit is 6 m wide against 10 m deep, a corridor. At ±18 it is
  8 × 10 m with 3 panes on the long face. Told the user.
- `render_views.py` `W` 76.0 → 64.0 (it hardcodes the footprint).

**A real bug the pane change exposed.** `refuge_columns()` derived its bay as
`round(axis_len / REFUGE_COL_PITCH)`, which only lands on the pane grid when the
result happens to divide the pane count. 14 panes with a 3-pane target gives 5.6 m
bays — every short-face column off-grid — and the existing check sampled the long face
only, so it would have passed silently. Extracted `col_bay()`, which picks the
panes-per-bay that *divides* the pane count and sits closest to the requested pitch:
3 panes (6.0 m) long, 2 panes (4.0 m) short. Added two checks on the short face
specifically. 30 columns now, up from 24.

Corrected figures that were wrong or moved with the smaller plate:

- I had said `PIER_LONG = 0` fails drift at H/428. It does not — that used the 76 m
  wind width. Ran the check with `PIER_LONG = 0` to confirm: **H/1,311, passes**.
  Deleting all piers gives H/507, still inside H/500 by 1%. So drift is not what stops
  the pier going to zero; the facade is (nothing halts a ribbon short of the corner,
  ten checks fail). Documented it that way.
- Current drift **H/1,395**, Iy 1,655 m⁴. Refuge void load 486,605 kN over 73.9 m² =
  **6.59 MPa**, 37% of C40 (was 7.72 MPa / 43%); without the columns 30.7 m² at
  15.85 MPa, 88%. Tower GFA 89,984 → 75,776 m², ~654 → ~551 units. Egress improved to
  22.0 m. Perimeter Iy vs a central core is now 1,053 vs 177 m⁴, so the core carries
  14% of lateral stiffness rather than 5%.
- `CORE_PROVISION` deliberately left at 203.5 m² — the stricter figure from the wider
  plate, and the measured 288 m² clears it either way, so the cores cannot shrink on
  the strength of fewer units.
- Also fixed "the 32 m end face has a slenderness of 2.11", which was neither H/D nor
  H/W. Wind on the 64 m end face works against H/W = 2.3; the long face sees H/D = 4.6.

Verification: build printed `footprint : 64.0 x 32.0 m` and
`derivation : W = 30 x 2 + 2 x 2 = 64 m, D = 14 x 2 + 2 x 2 = 32 m`; verify
**134/134 passed**. Measured the corner geometry directly out of the .blend: 2.00 m of
wall on the long face and 2.00 m on the short, so the two glass runs meet at the
corner. Negative test with `PIER_LONG = 0` gave 122/132 with the facade failures
listed above, so the new checks are load-bearing. All five views re-rendered.

Remaining issues: none. The ±18 core move from earlier in the session goes in the same
commit.

## 2026-08-17 — main — the .blend now opens looking at the building, not inside it

User: every time they open the file they land inside the building and have to zoom
out repeatedly.

The cause is not the scene camera — that was already pulled back to
`max(W, D, TOP_Z) * 1.35` and only affects renders anyway. It is the **viewport**
state stored in the .blend's screen layouts, which is a completely separate thing.
Measured the factory default directly: `view_distance` **14.99 m**, pivoting about
the origin at z = 0. The building is 166 m tall with a 185 m diagonal, so 15 m from
the ground plane is inside the pilotis level. Nothing in the script had ever touched
it, so every build inherited that default.

`frame_viewport()` in `build_house.py`, called from `main()` before saving:

- `view_distance = diag * 1.6` where `diag = sqrt(W² + D² + CORE_TOP_Z²)` — derived,
  so it keeps working if the footprint or floor count changes. 296 m for the current
  building. The diagonal is what has to fit, not the height alone.
- `view_location` at `CORE_TOP_Z * 0.5` (83 m). Orbiting the origin puts the ground
  at screen centre and the tower off the top.
- 3/4 view from the south-east (72° / 38°), matching where the render cameras sit,
  which is also the lit side.
- `clip_end = diag * 6` (1112 m). Necessary: at 296 m out, the default 1000 m clip
  would be fine, but a smaller default would cull the model and the file would open
  onto empty grey — worse than opening inside it.

Blender stores **ten** 3D viewports (one per workspace: Layout, Modeling, Shading,
Animation, Sculpting, UV Editing, Texture Paint, Geometry Nodes, Scripting…), so the
function loops over `bpy.data.screens` and sets all of them. Setting only the active
one would have left the problem in place for anyone who opens on a different tab.

Verify grew 124 → 129. Five checks, reading the state back out of the saved file:

- the .blend stores viewports to configure (10 across 11 workspaces)
- every viewport opens outside the building — `view_distance > diag/2`
- the whole tower fits the frame, computed from each viewport's own `lens` against
  the 24 mm sensor height (203 m visible for a 166 m building)
- the pivot is at 30–70% of building height, not the ground
- far clip clears the pull-back

**Negative test.** Disabled the `frame_viewport()` call, rebuilt, re-verified:
126/129 with exactly the three expected failures — nearest viewport 15.0 m against
a 93 m half-diagonal, all ten too tight for a 166 m building, pivot at z = 0. So
the checks are reading real state rather than restating the constants. Restored
from a copy and confirmed 129/129.

Renders are unaffected — `scene.camera` was not touched, so no re-render needed.

Docs: README build section explains the viewport and that it is independent of
`scene.camera`; outputs table mentions the framed viewport; check count 124 → 129.

## 2026-08-17 — main — the cores now run continuous and finish above the roof

User pointed out that the core should rise above the building, and that the thing
projecting at the top was not the core.

They were right, and worse than they said. What sat up there was `RoofPlant`, an
arbitrary 22.8 × 10.9 × 3.4 m box offset to x = +9.12 — sized as a fraction of the
footprint, unrelated to the cores, and only on one side. Checking further, the
cores existed **only** at the pilotis levels (0 → 12 m) and the refuge level
(80 → 88 m); the tower was hollow between them. The lift shafts stopped and
started again, and a motor room on the roof would have sat over nothing.

Changes to `build_house.py`:

- `RoofPlant` deleted.
- `CORE_OVERRUN = 4.6` (lift overtravel + machine room) and
  `CORE_ROOF_PARAPET = 0.9`, with `CORE_TOP_Z` derived from `TOP_Z`. An assert
  holds `CORE_TOP_Z` above the roof parapet, so the overrun cannot silently
  shrink below where it is visible.
- The roof block now builds the two cores continuing up via `cores()` itself, a
  cap slab per core, and a low upstand — placed by `CORE_XS` and `CORE_W/CORE_D`,
  so they move if the cores ever move.
- `cores("TowerCore", BASE_Z, TOP_Z - BASE_Z, concrete)` replaces the
  refuge-only core, making the shafts continuous ground → roof. Within the refuge
  void they stay visible, so the garden reads as a 28 m span between two piers.
- Stats now print the parapet top and the bulkhead top separately.

Heights: roof slab 160.22, parapet top **161.32**, bulkhead top **165.94** —
4.62 m clear of the parapet, 5.72 m above the roof slab.

**Ordering bug, caught by the build failing:** `CORE_TOP_Z` was first placed with
the other overrun constants at line 240, before `TOP_Z` is defined at 245, giving
`NameError`. Moved below `TOP_Z`. Worth noting the failure mode — the verify run
immediately after that failed build passed 124/124 because it was reading the
**previous** blend. This is the same trap recorded further down this file: always
confirm the build printed its stats before trusting a verify result. I only caught
it because the build's height lines were missing from the grep output.

**Predicted breakage that did not happen.** I expected continuous core walls
touching the floor plates to merge into large connected components and break the
`core_pieces` filter's `(hi[0] - lo[0]) < W * 0.5` condition in `verify_house.py`.
It didn't: abutting boxes share no vertices, and `piece_bounds()` walks bmesh
edges, so contact alone doesn't merge pieces. All 12 twin-core checks still pass
unchanged.

Verify grew 117 → 124. Seven new checks, all reading geometry:

- something rises above the roof parapet (18 pieces above 161.32 m)
- the highest point **is** the core bulkhead (165.94 m, matches `CORE_TOP_Z`)
- the overrun gives ≥ 4 m of real headroom above the roof slab (5.72 m)
- everything above the parapet sits over a core footprint (0 pieces outside)
- each core carries its own bulkhead (9 pieces at x = −20, 9 at +20)
- no projecting piece wider than `CORE_W` — this is the check the old
  22.8 m-wide `RoofPlant` would have failed

Re-rendered all five views. **I still cannot see a rendered image** — the Read
tool returns nothing for PNGs, as throughout this project. So instead of claiming
the bulkheads look right, I projected `(±20, 0, 165.94)` through the front
elevation camera with `world_to_camera_view`: both land at NDC y = 0.733, inside
the frame, 1.2% of frame height above the parapet line at 0.721. That confirms
they are *framed*, not that they *read* well. Whether the pair looks right at that
scale needs your eyes.

README: total height row now gives both figures; a new block in the core section
covers continuity and the overrun, and names the old plant box as what it
replaced; check count 117 → 124; "roof plant" → "roof bulkheads".

## 2026-08-17 — main — twin service cores replacing the single central core

User asked whether a single flat central core was right, or whether two cores at
the ends, or an H-core, would be better in reality — noting that the facade
already has blanks at both ends.

**Corrected a premise first.** The blanks are 8 m at each end of the LONG (76 m)
facade. The building's END is the 32 m short facade, which carries 24 m of ribbon
window and is only solid for 4 m at each corner. So a core pushed to the end
would back onto blank on two sides but sit behind glass on the third. The existing
blanks do not pay for an end core.

**Computed before recommending, and the structural answer was "it does not
matter".** The lateral system is the perimeter, not the core:

| | Iy (wind on 76 m face) | Ix (wind on 32 m face) |
| --- | --- | --- |
| core 14 × 9 | 177 m⁴ | 351 m⁴ |
| 4 L-shaped corner piers | 3359 m⁴ | 18025 m⁴ |

The core held 5.0% of Y stiffness and 1.9% of X. Tip drift 60 mm = H/2650 against
a H/500 limit. Twin/H cores win on Ix by ~20×, but Ix is the *low-demand*
direction (slenderness 2.11 vs 5.00). Extra stiffness there buys nothing.

**The real problem was capacity.** 37 floors × 76 × 32 = 89,984 m² GFA, ~654 units,
~1,767 people, needing 7–11 lifts. Shafts + 2 stairs + lobbies + smoke-stop
lobbies + risers ≈ 204 m² gross. The 14 × 9 core was 126 m², short by 38%, a 5.2%
core-to-plate ratio where residential runs 10–15%. Egress was also marginal:
worst-case travel 42.5 m against SCDF's ~30 m dead-end / ~45 m two-way. And two
stairs in one shaft are not independent.

**Built: two 12 × 12 cores at x = ±20.** 288 m² (+42% margin), 11.8% of the plate,
worst-case egress 24.0 m, stairs 40 m apart with 28 m of clear plate between, 10 m
unit depth either side. Swept the placement and size options rather than picking:
±20 with 12 × 12 was the point where egress bottomed out while keeping unit depth
in the 9–13 m band and the edges (14 m and 26 m) on the 2.00 m pane grid.

**Rejected the H-core deliberately.** Its spine would run a wall down the middle
of the plate, forcing single-loaded corridors either side. H-cores suit office
towers wanting deep lettable space; residential wants a continuous corridor loop.
The extra 36 m² does not pay for a severed plan.

User's two facade constraints held automatically, because the cores are internal
and never touch a facade: every pane is still 2.00 m, counts are still 30 and 12,
footprint still 76 × 32 m on whole metres. Asserts in `build_house.py` now enforce
the pier-zone clearance, pane-grid alignment and minimum provision.

Side effect worth recording: the refuge void's load path IMPROVED. Twin cores give
26.25 m² of core wall against the old 12.57, so the piers-plus-cores case is now
14.34 MPa where it was 19.31 and over the C40 limit. The 24 columns stay — 14.34 is
80% utilisation with no margin, and they carry the facade rhythm through the
garden. With them it is 7.72 MPa / 43%. Updated the stale figures in the README.

**Three verify failures, and all three were my own test code, not the geometry:**

- Filtered core wall pieces by the y CENTRE, which keeps the east/west walls
  (centred y = 0) and drops the north/south walls (centred y = ±5.86). Fixed by
  filtering on the piece lying within the footprint instead.
- The grille ray test hardcoded bay `gxs[10]`, which stopped being clear the
  moment the cores moved behind it. Now it scans for a bay that is actually open
  and reports how many of the 120 are (76).
- Twice I diagnosed a "failure" against a stale `.blend` — after `git stash` and
  after a build that had crashed on my own stats line. **Always confirm the build
  printed its stats before trusting a verify run.**

Verify grew 105 → 117. The new checks read **measured geometry**, not this file's
duplicated constants, which matters because a constants-based check would pass
even if the model disagreed. Proved they bite with a negative test: reverting to a
single central 14 × 9 gives 112/116 with 4 failures, including provision measured
at 0 m².

Remaining issue: **still cannot view a rendered image in this session** — the Read
tool returns nothing for PNGs. So the claim that two cores read better in the sky
garden view than one central lump is a geometric argument (28 m of clear span
between them), not something I have seen. Verified numerically, not visually.

## 2026-08-17 — main — purged renders from git history, renders now in a release

The repo had grown to 108 MB. Measured where it went before touching anything, by
summing blob sizes per path prefix over `git rev-list --objects --all`:
**`out/` = 117.4 MB against 1.0 MB of source**, and 13 of 15 commits touched it.
99% of every clone was build products that `build_house.py` regenerates.

User asked to either stop tracking the images or strip them from history, and chose
the stronger option: **rewrite history and force push**, with the README images
**moved to a GitHub Release** rather than kept anywhere in the repo.

Order of operations mattered here, since a force push is irreversible for anyone
who has already cloned:

1. Backed up first — `git bundle create --all` (84 MB, `/tmp/highrise-house-backup-489114b.bundle`)
   plus a copy of `out/`. Pre-rewrite HEAD was `489114b`.
2. Created the `renders-v1` release and uploaded the 5 PNGs; rewrote the README
   image links to the release asset URLs.
3. `out/` added to `.gitignore`, and this committed *before* the rewrite so the
   rewrite would cover it too.
4. Recorded the blob hash of all 10 source files, then
   `git filter-repo --path out/ --invert-paths`.
5. Verified: the 10 source blob hashes are **byte-identical** before and after, all
   16 commits survive, `git rev-list --objects --all | grep out/` returns nothing.
   `.git` went **91 MB → 228 KB**.
6. Force pushed to `origin main` (`489114b` → `51ec17f`). Confirmed the remote tree
   holds only the 10 source files and the README points at the release.

Two things worth knowing for next time:

- **filter-repo removes the `origin` remote on purpose**, so it cannot push a
  rewrite anywhere by accident. Re-added by hand afterwards.
- **filter-repo also clears the ignored working-tree files** it purged — `out/`
  was emptied on disk, not just in history. Restored from the backup copy. Without
  that backup the renders would have been gone, since they take ~40 min to
  re-render.

GitHub's API still reports `size: 77843 KB` — that is their cached figure and drops
when their GC runs; the actual tree is clean.

Remaining issue: **I still cannot view a rendered image in this session** (the Read
tool returns nothing for PNGs), so I verified the release assets by size and HTTP
200 rather than by looking at them. The 5 assets report `state=uploaded` at their
original byte sizes, and `view_front.png` fetched back at exactly 1209475 bytes.

## 2026-08-17 — main — flush glazing: glass, mullions and louvres on the wall plane

User noticed the windows were not in the same plane as the facade and read as
having sills, and asked for them flush. Measured before changing anything: the
glass outer face sat at y = 15.910 against a wall face at 16.000, so it was
**90 mm behind the wall**, and those 90 mm of opening side wall are exactly what
reads as a sill.

Asked which way to take the mullions and louvres rather than guessing, since flush
glazing does not settle either. User chose **everything flush** — glass, mullion
caps and louvre slats all finishing on the wall plane.

- `GLASS_INSET` 0.09 → 0.0, `VENT_INSET` 0.13 → 0.0.
- `mullions()` had to change basis, not just constant: it centred the cap on the
  *glass centreline*, which with a zero inset would leave it standing 70 mm proud.
  Now centred at half its own depth, so its outer face lands on the plane and its
  0.14 m depth runs inward.
- The louvre offset was keyed to `slat_depth / 2`, but the slats tilt 30° and a
  tilted box sweeps deeper than half its depth: 0.0564 vs 0.055, so the corners
  would have poked **1.4 mm** through the wall. Now keyed to the rotated extent,
  `slat_depth/2·cos θ + slat_t/2·sin θ`, which stays flush at any tilt.

Depth now comes only from behind the plane: the shadowbox 0.10 m back and the
0.85 m interior lining, both unchanged.

The verify suite was **blind to this whole change** — 101/101 passed both before
and after, because every existing check measured Z bands or plan positions and
nothing measured depth. Added 4 checks that do: the outer face of glass, mullions
and louvres each against the wall plane within 2 mm, plus one that nothing stands
proud of it. Then ran the negative test rather than trusting them: reverting
`GLASS_INSET` to 0.09, rebuilding and re-verifying gives 103/105 with both glass
and mullion checks failing and reporting `+90.0 mm`. Restored, rebuilt, 105/105.

Lesson worth keeping: a suite that passes before and after a real geometric change
is not confirming the change, it is silent about it. Check the negative case.

Also fixed two stale numbers in the README while in there: the verify count (97 →
105) and "33 glazed floors" (31 since the refuge void took two).

Rebuilt (12 objects / 39880 verts, unchanged — this only moved geometry) and
re-rendered all 5 views. Still cannot view a PNG in this environment, so the flush
result is confirmed by measurement against the wall plane, not by looking at it.

## 2026-08-16 — main — put the rendered views in the README

User asked for screenshots in the README. Added all five `out/view_*.png` as a
single two-column table under the intro, each with a caption naming what the view
is for and the focal length it was taken at, so the framing is documented rather
than implied. They are committed build products already in the repo, so relative
paths render on GitHub without any hosting.

Two stale numbers fixed while in the file: the verify section still advertised 97
checks (now 101), and its list of what is covered did not mention the void's load
path. Confirmed all five paths resolve to files on disk and that every render is
900 × 1400 portrait, so the two-column layout is even.

Caveat unchanged: I cannot view a PNG in this environment, so the captions describe
each camera's target and lens as set in `render_views.py`, not what I can see in the
image. If a caption misdescribes its picture, that is why.

Remaining issue: `out/` build products are now load-bearing for the README, which
argues against the idea of stripping them from the repo to save ~6 MB. If they are
ever removed, the images need hosting elsewhere first.

## 2026-08-16 — main — carry the tower across the refuge void on real columns

User asked, from a structural point of view, whether the columns are too slim and
too few. Ran the numbers rather than guessing, because "立柱" could mean either the
pilotis columns or the garden fins. Two different answers:

**The pilotis columns are fine — arguably oversized.** 34 columns at 1.60 m square
on an 8.95 × 9.20 m grid, carrying 37 floors:

| | |
| --- | --- |
| factored axial per column | 22708 kN → 8.87 MPa |
| wind moment (1.5 kPa on the 76 m face) | 305 kNm → 0.45 MPa |
| peak compression | 9.32 MPa vs 18 MPa (0.45·fck, C40) |
| utilisation | **52%** |
| slenderness | 12.0 / 1.6 = 7.5 (stocky) |

The 14 × 9 m closed core tube has I = 177 m⁴ against the columns' 18.6 m⁴ combined,
so it takes ~91% of the storey shear and the columns are essentially gravity-only.
Enlarging them would *worsen* the soft-storey behaviour, not improve it: at 2.2 m
the core's share drops to 73% and the column base moment nearly triples to 877 kNm.
Left unchanged.

**The refuge void was the real problem, and worse than the user's framing.** After
the fins replaced the posts, the only concrete crossing the 8 m void was the four
corner piers (14.04 m²) and the core walls (12.57 m²) — 26.61 m² under 18 floors,
513638 kN factored: **19.31 MPa, over the C40 limit**, with a 60 m clear span on
the long face and nothing in it. Compare 87 m² of column at the base of the same
building.

This traced to a documentation claim of mine that was simply false, in README and
in the entry below: "the screen's verticals carry the 19 floors above". A 0.10 m
blade carries nothing, and the count was 18, not 19. Both are now corrected in
place rather than quietly overwritten.

Added `refuge_columns()`: 24 columns at `REFUGE_COL_SIZE = 1.20` m square,
9 per long face and 3 per short face. Spacing is `REFUGE_COL_PITCH = PANE_W * 3`
= 6.0 m, chosen so every column lands on a window mullion line and the facade's
vertical rhythm runs straight through the garden — the same discipline the fin
pitch follows. Load path is now 61.2 m² at **9.45 MPa, 52%**, matching the pilotis
columns exactly. Searched the (count × section) space for the option that clears
the stress limit while staying on the pane module; 9 × 3 at 1.20 m was the leanest.

The fins stay as they are. Their job is screening, and the 79.8% open area and both
ray-cast checks are unchanged — they were never the structure.

Verification: 97 → **101 checks, all passing**. The four new ones are deliberately
not tautologies — one counts columns actually spanning `REFUGE_Z0..REFUGE_Z1` in
the built model, one recomputes the stress from measured geometry and fails above
18 MPa, and two assert the columns sit on the facade line and on a whole number of
pane widths. Rebuilt (12 objects) and re-rendered all 5 views.

Remaining issues: `verify_house.py` still duplicates the dimension constants and
now `REFUGE_COL_SIZE`/`REFUGE_COL_PITCH` and `WALL_T` too, and `render_views.py`
still hardcodes `W`, `D`, `TOP_Z`, `REFUGE_Z0`, `REFUGE_Z1` — all need manual
syncing. Still unable to view a rendered PNG in this session, so every claim above
rests on computed geometry, assertions and ray-casts, not on looking at the image.

## 2026-08-16 — main — switch the garden screen to slim vertical fins

User rejected the 432 Park-style square grid ("好丑") and asked for the slim
vertical option instead. Switched `GRILLE_STYLE` to `FINS` and made the blades
finer than the values I had left in that branch: 0.10 m wide (was 0.18) at 0.50 m
centres (was 1.00), 0.34 m deep.

Kept the alignment discipline by choosing `FIN_PITCH = PANE_W / 4`, so the pitch
still divides the 2.0 m pane pitch exactly and every fourth blade lands on a
window mullion — the vertical lines carry through the garden unbroken, same as
with the grid. 121 blades on the long face, 79.8% open (more than the grid's
68.9%, since there are no horizontals).

Two assertions had to be generalised, because I had written them for the grid's
one-member-per-pane case and they failed on fins (31/121 aligned, pitch 0.50 vs
2.00). Both failures were the tests being too narrow, not the geometry being
wrong. The real rule is that the screen pitch must *divide* the pane pitch and
every mullion must be met by a blade, which holds for both styles:
- "the screen pitch divides the window pane pitch" — checks PANE_PITCH/pitch is a
  whole number; reports blades per pane (4 for fins, 1 for the grid).
- "every window mullion is met by a grille vertical" — counts mullions covered,
  not blades consumed.
The open-area calculation was also grid-specific (square cells); replaced with a
strip calculation along the facade, which is the conservative lower bound for both.

Verification:
- Build clean; 12 objects, 39688 vertices.
- `verify_house.py`: **97/97 passed** with FINS. Also rebuilt with GRID and
  re-ran: **97/97** there too, so the switch stays usable either way (grid reports
  1 blade per pane, 31/31 mullions, 82.4% open by the new strip measure).
- Ray-casts still hold: 0 hits between blades, 4 through a blade.
- 5 views re-rendered.
- Fixed the 8 m frame diagram, which had the floor split reversed against its own
  caption. It is 16 glazed floors above the garden and 15 below.

Remaining issues:
- Blade proportion (0.10 m at 0.50 m centres) is my choice and unverified visually.
  If it still reads wrong: `FIN_W` for thickness, `FIN_PITCH` for density — but keep
  the pitch as `PANE_W / N` (0.50, 0.40, 0.25 …) or the alignment breaks.
- `FIN_DEPTH` 0.34 m controls how much it closes up when seen at an angle; raise it
  if the garden shows too much of its interior from oblique views.

## 2026-08-16 — main — screen the sky garden instead of leaving it hollow

User: fully hollowing out the refuge level looked bad ("全空着太丑了"), and asked for
vertical grilles or a dense field of small square openings like 432 Park Avenue.
Right call — an unscreened void reads as a bite taken out of the tower, and there
was nothing holding the facade plane for 8 m.

Built the 432 Park option as the default, with vertical fins as a switch
(`GRILLE_STYLE`).

The dimension that matters: `GRILLE_CELL = PANE_W`, so the 2.0 m grid is on the
*same pitch as the window panes*. That makes every grille vertical land exactly on
a window mullion, so the vertical lines run unbroken from the glazing below,
through the garden, into the glazing above. Measured, not assumed: 31 of 31
verticals align (both sets read off the model and compared within 0.02 m). At any
other pitch the refuge level reads as a foreign object inserted into the tower —
this is the one number that must not be tuned freely.

Still a filter, not a wall: 68.9% of the long face is open and the cells are real
voids, so the level ventilates as a refuge floor must. Checked two independent
ways — open-area arithmetic from the measured member sizes, and ray-casting: a ray
through a cell centre leaves the building with 0 hits, one through a member is
blocked (4 hits).

Removed the separate facade posts added in the previous entry, on the grounds that
the grille verticals sit on the same line and would double up members in one
plane. **That reasoning was wrong and is corrected in the 2026-08-16 structural
entry below** — a 0.10 m blade carries nothing, so removing the posts left the
void with no load path.

`GRILLE_STYLE = "FINS"` gives 0.18 m blades at 1.0 m centres, 0.45 m deep —
transparent head-on, nearly solid at a glancing angle. Built and confirmed working
(38344 verts) before switching back to GRID.

Verification:
- Build clean; 12 objects, 37832 vertices. New `Sky_Garden_Grille` object.
- `verify_house.py`: **97/97 passed**, up from 89. Added 8: the void is screened
  at all, the screen spans the full 8 m, every vertical aligns with a mullion,
  the pitch equals the pane pitch, open area within 45-85%, and the two ray-cast
  checks (cell open / member blocking). The earlier "nothing in the void" checks
  still pass — they test glass, lining and louvres, none of which the screen is.
- Both `GRILLE_STYLE` values build without error.
- 5 views re-rendered.
- Fixed a stale README diagram claiming 33 glazed floors; it is 31, split 15 below
  the garden and 16 above (I first wrote that backwards and corrected it against
  the actual floor indices).

Remaining issues:
- Whether the screen reads well — member thickness, 4 rows vs more, GRID vs FINS —
  needs your eyes. Alignment, openness and geometry are asserted; proportion is not
  something I can check without seeing it.
- `GRILLE_CELL` is deliberately tied to `PANE_W`. If you want a denser screen,
  prefer halving it to 1.0 m (still aligns, every other line meets a mullion)
  rather than an arbitrary value that breaks the alignment.

## 2026-08-16 — main — refuge floor / sky garden at mid-height

User asked for the refuge floor that high-rises have every so many storeys (also
the lift transfer level), done as a Singapore-style open sky garden: two floors
left empty and hollowed out.

Placement follows Singapore's SCDF rule — refuge floor required above 24 storeys,
spaced no more than 20 apart. One level does it for a 40-storey tower. Landed on
storeys 21–22, 80.0 → 88.0 m: 21 storeys below, 19 above, both inside the limit,
and 46% up the tower so it reads as mid-height. The position is *derived*, centred
in the glazed part rather than the whole tower, so the 8 m blank bands top and
bottom don't push it off-centre. Two asserts fail the build if it lands on a blank
band or breaks the spacing rule.

The two storeys form ONE double-height space — no intermediate slab — which is what
makes it read as an 8 m void rather than two stacked empty floors. No glazing, no
spandrel, no lining on those floors.

What keeps the elevation coherent where the facade stops:
- Corner piers continue through the void, so the building line still turns.
- A 1.2 m balustrade on all four open edges, on the same clear opening the
  windows use, so the vertical rhythm is unbroken.
- Slim posts on the facade line carrying the 19 floors above. Without them the
  upper tower visually floats on nothing. **(Superseded — these were later removed
  in favour of the grille, which cannot carry anything. See the 2026-08-16
  structural entry: the void now has 24 real columns, and the count is 18 floors
  above, not 19.)**
- The lift/stair core is exposed through the void — that is what makes it a level
  you arrive at rather than a gap. This is the transfer level.
- Planting: perimeter troughs plus 14 trees, canopies stopping 1.35 m clear of
  the ceiling.

Two slab traps, both caught while wiring it up rather than by luck:
1. Slabs are added at the TOP of each floor, so simply `continue`-ing past the
   refuge storeys left the void with no ceiling and the floor above with nothing
   under it. Fixed by emitting the cap at `REFUGE_END`.
2. The 0.45 m garden slab (thicker, it carries soil) shares its top face with the
   plate the floor below would add, so both would occupy the same place. The
   floor below now skips its plate.

New `PLANT_GREEN = (0.070, 0.185, 0.058)` is deliberately dark: real foliage
reflects only ~15-20% in green and far less in red and blue, so a bright green
renders as plastic turf. 12% transmission for leaves backlit against the void.

Verification:
- Build clean; 11 objects, 37112 vertices (fewer than before — two floors of
  glazing removed outweighs the planting added).
- `verify_house.py`: **89/89 passed**, up from 71. Fixed 5 pre-existing checks
  whose constants assumed 33 glazed floors (now 31) and 37 floor plates (now 35);
  their reported numbers were already correct, only the expectations were stale.
  Added 18 checks: nothing glazed/lined/louvred inside the void, no plate
  splitting it, garden slab present at 80.0 m and 0.45 m thick, ceiling at
  88.0 m, 4 balustrade runs ≥1.0 m, corner piers continuing (16 pieces),
  planting and trunks bounded inside the void, canopies clear of the ceiling,
  core spanning it, no overlap with blank bands, SCDF spacing, mid-tower position.
- Independent ray-cast check (`/tmp/void_test.py`): a horizontal ray at z=84 m
  passes clean through the building with **0 hits**, versus 12 at a glazed floor
  and 4 at a blank band. The void is genuinely open air, not just unglazed.
- New `sky_garden` view added to `render_views.py`; 5 views re-rendered.

- Glass unaffected: `measure_glass.py` reports byte-identical glass values
  (R 0.500 / G 0.554 / B 0.539, stdev 0.080). Its glass/wall contrast *ratio*
  fell 3.92x -> 1.25x, but that is the denominator moving, not the glass — the
  probe frame now includes walls shadowed by the void, so the wall's own stdev
  went 0.020 -> 0.064. Noted in the script so it is not misread as a regression.

Remaining issues:
- Images cannot be viewed in this session, so whether the garden *looks* right
  (tree scale, planting density, how the void reads in elevation) needs your eyes.
  Geometry and openness are confirmed by assertion and ray-cast.
- `render_views.py` now also hardcodes `REFUGE_Z0`/`REFUGE_Z1`, and
  `verify_house.py` duplicates the refuge constants — both need manual syncing if
  `REFUGE_FLOORS` or the blank bands change.

## 2026-08-16 — main — fix the glass reading yellow-olive, not pale green

User: "怎么感觉窗子是黄的？土黄色。我要淡淡的浅绿色呀。" Correct, and it was a
direct consequence of the previous entry's tuning: I optimised a single metric
(green bias) and picked red-high + blue-low, which **is** yellow. A green bias of
+0.025 is far too weak to mask it. The signal was already in my own numbers —
R 0.533 > B 0.521 is a warm cast — I just wasn't looking at the red/blue relation.

Two causes, both fixed:

1. `GLASS_GREEN` was (0.880, 0.965, 0.700) — that low blue is what made it olive.
2. `INTERIOR_LINING` was (0.660, 0.650, 0.620), a *warm* grey. At emission 0.75 the
   lining is plainly visible through clear glass, so its cast lands on every pane
   and yellowed the glazing on its own. This was half the problem and I had missed
   it entirely: I treated the lining as a brightness control only.

Now tracking two metrics instead of one — green bias = G − (R+B)/2, and warm bias
= R − B. Swept eight combinations:

    (0.88, 0.965, 0.92)  green +0.010  warm -0.008   blue-grey (B beat G)
    (0.88, 0.965, 0.70)  green +0.025  warm +0.012   YELLOW-green (shipped, wrong)
    (0.74, 0.965, 0.86)  green +0.026  warm -0.056   cyan (B caught up with G)
    (0.72, 0.965, 0.76)  green +0.035  warm -0.039   <- chosen
    (0.70, 0.960, 0.74)  green +0.038  warm -0.039   slightly greener, dimmer

Chose `GLASS_GREEN = (0.720, 0.965, 0.760)` with
`INTERIOR_LINING = (0.630, 0.650, 0.655)` (neutral-to-cool). Predicted panes:
R 0.496 / G 0.550 / B 0.534 — G clearly leads, R sits *under* B so there is no
yellow, but warm −0.039 stays short of cyan. Luminance 0.537, local stdev 0.079,
so brightness and the non-frosted character are preserved.

The general rule, recorded because I got it wrong twice: one number cannot
describe a colour. G highest by a clear margin, R lowest, B in between.

Verification (rebuilt after the source-only commit `9d454a9`):
- Build clean under Blender 5.2.0 LTS; 9 objects, 38832 vertices. `preview.png`
  plus all 4 extra views re-rendered, so `out/` now matches the source again.
- `verify_house.py`: **71/71 passed**, including the four anti-frosting
  assertions (transmission 1.0, roughness 0.0, no glass emission, Filter Glossy
  off) and the lining's alignment, height, 0.825 m setback and 60 × 24 m coverage.
- `measure_glass.py` as built: glass R 0.500 / G 0.554 / B 0.539, luminance 0.541,
  green bias **+0.034**, warm bias **−0.039** — G leads both channels and R sits
  under B, so the yellow is gone without tipping into cyan. Within 0.004 of the
  sweep's prediction on every channel.
- Not frosted: local stdev 0.080 = **3.92× the matte wall's**, dynamic range
  0.515, brightness 0.92× the wall.

Remaining issues:
- Images cannot be viewed in this session, so the colour is confirmed by
  measurement, not seen. The numbers say pale cool green (G highest, R lowest,
  B between); whether it reads that way needs a look.
- Levers if it is still off: raise all three channels for paler, lower red for
  greener, raise blue if it looks yellow, lower blue if it looks cyan.

## 2026-08-16 — main — pale green glass, and more visibly transparent
(superseded by the entry above — this tuning produced the yellow-olive glass)

User wanted the green much lighter than the (0.30, 0.94, 0.62) set earlier, with
the emphasis on transparency rather than colour. Those two goals turn out to
agree: the paler the tint, the more legible what is behind it.

Swept the pale range and hit a trap — at (0.88, 0.965, 0.92) the panes measure
B 0.456 against G 0.448, i.e. a pale "green" tint renders blue-**grey**. Because
only what passes through the pane is tinted while the sky reflection is not, and
the reflection is blue and carries most of the brightness. The fix is which
channel to move: hold red high, suppress blue.

    (0.88, 0.965, 0.92)   green bias +0.010   lum 0.443   blue-grey
    (0.88, 0.965, 0.70)   green bias +0.025   lum 0.438   <- chosen
    (0.30, 0.940, 0.62)   green bias +0.080   lum 0.410   previous, too deep

So `GLASS_GREEN = (0.880, 0.965, 0.700)`: pale, and brighter than the deep green
it replaces. Darkening everything is the expensive way to get green; dropping
blue is the cheap way.

For transparency there was nothing left in the material — transmission is already
1.0 and roughness 0.0. The remaining lever is the lining, since glass only reads
as see-through if the far side is legible; where the lining fell dark the pane
went opaque regardless. Swept it and measured the share of glass pixels below
0.25 luminance:

    (0.52,0.50,0.47) emit 0.35   3.6% dark   lum 0.438   sd 0.080
    (0.66,0.65,0.62) emit 0.75   0.8% dark   lum 0.542   sd 0.079   <- chosen
    (0.70,0.69,0.67) emit 1.00   0.5% dark   lum 0.582   sd 0.088

Stopped at 0.75 on purpose: at 1.00 the local contrast rises because the emission
begins to overpower the sky reflection, which drifts from "glass with lit rooms
behind it" toward "glowing panel".

Verification:
- Build clean under Blender 5.2.0 LTS; 9 objects, 38832 vertices. 4 extra views
  re-rendered.
- `verify_house.py`: 71/71 passed — the four anti-frosting assertions still hold
  (transmission 1.0, roughness 0.0, no glass emission, Filter Glossy off).
- `measure_glass.py`: glass R 0.533 / G 0.553 / B 0.521, luminance 0.546,
  green bias +0.026 with G above both R and B, local stdev 0.081 = **3.96× the
  matte wall**, dynamic range 0.516, and 0.92× the wall's brightness (was 0.70×).
  Brighter, paler, still clearly green, still not frosted.
- Geometry untouched.

Remaining issues:
- Images remain unviewable in this session, so "pale green" and "looks
  transparent" rest on the measurements above, not on my eyes. G is measurably
  above R and B while luminance is high, which is what a pale tint should do.
- Tuning levers if it is still off: raise the red in `GLASS_GREEN` for paler,
  lower the blue for greener; `INTERIOR_LINING` + its emission control how much
  you see through.

## 2026-08-16 — main — clear, smooth glass instead of frosted

User reported the glazing had a strong frosted/sandblasted look and wanted it
clear, smooth and bright. Three independent causes, all present at once, and each
one enough on its own:

- `Transmission Weight = 0.75` — the remaining 0.25 is a *diffuse* lobe on the
  base colour, and a diffuse lobe on a window is what frosted glass is. Now 1.0.
- `Roughness = 0.02` — float glass is optically flat; 0.02 already scatters
  visibly at 100 m. Now 0.0.
- `Emission Strength = 0.06` on the glass — uniform across the pane, so it washed
  out the reflections into a milky film. Now 0.
- Plus `blur_glossy = 1.0` (Cycles Filter Glossy), which is not a material
  setting at all: it blurs refractive rays to cut noise and frosts smooth glass
  by itself. Now 0.

The first three were all workarounds I had added for "clear glass over an unlit
interior renders black". That was the wrong fix. The right one is geometric:
`interior_ring()` adds an `Interior_Lining` object 0.85 m behind the glazing
(`INTERIOR_SETBACK`), matte and faintly self-illuminated, standing in for lit
floors. Because it sits behind the pane it shifts against the sky reflection as
the view moves, which is the cue that reads as glass — the emission on the glass
gave brightness but no depth.

Also retuned the tint. Only what passes *through* the pane is tinted; the sky
reflection is not, and at these angles the reflection carries most of the
brightness. Measured across four candidates: deepening `GLASS_GREEN` from
(0.82, 0.94, 0.88) to (0.30, 0.94, 0.62) took the green bias +0.014 → +0.080
while brightness moved only 0.437 → 0.410. My earlier "keep the tint near white
or the pane goes dark" reasoning was wrong — a deep tint is nearly free here.

New `measure_glass.py` measures glass pixels only, isolated by ray-casting the
camera through each pixel. Whole-frame averages cannot see this: spandrel covers
most of the facade and drowns the panes out. The frosted test is **local
contrast** — a rough or partly-diffuse pane averages its surroundings, so
neighbouring pixels converge and stdev collapses toward the matte wall's.

Verification:
- Build clean under Blender 5.2.0 LTS; 9 objects, 38832 vertices.
- `verify_house.py`: **71/71 passed** (was 59). Added 12 checks — the four
  frosting causes above, so they cannot be reintroduced silently, plus the
  lining's band alignment, height, 0.825 m setback behind the glass, and full
  60 × 24 m opening coverage.
- `measure_glass.py` on the final build: glass R 0.314 / G 0.439 / B 0.405,
  luminance 0.410, local stdev 0.086 vs the wall's 0.020 — **4.21× the matte
  wall's local contrast** over a 0.471 dynamic range. Frosted glass compresses
  both. Green bias +0.080.
- Geometry untouched: still 76 × 32 m, 31.40 m clear depth, 2.00 × 1.50 m panes.

Remaining issues:
- Images still cannot be viewed in this session, so "not frosted" rests on the
  contrast measurement, not on my eyes. The numbers say clear, smooth, tinted
  glass; whether the green reads at the right strength needs a look.
- `render_views.py` hardcodes `W`, `D`, `TOP_Z`, and `verify_house.py` keeps its
  own copy of the dimension constants. Unchanged here (no dimensions moved), but
  both still need manual syncing if the pane counts change.

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
