# Office Tower — Progress

## 2026-08-26 — fix — restore visible Office radial ceiling lights

Branch: `main`.

Kept the Office lighting as 32 radial fan strips per office floor, with three
independent segments and the existing deterministic on/off pattern. Increased
the panel width and thickness slightly and moved the saved camera/viewport
closer so the lighting remains legible through the EEVEE facade instead of
disappearing at overview scale. The glass remains the existing EEVEE 50/50
reflection/transmission material, and the three curtain states remain exactly
balanced.

Verification:
- Blender rebuilt `out/office_tower.blend`, `out/office_tower.glb`, and
  `out/office_preview.png` with EEVEE.
- Build output confirms 2,304 total light segments (`1,452` on / `852` off),
  plus 824 rolled-up, 824 half-down, and 824 fully-down curtain states.
- Close EEVEE render visibly confirms the radial three-segment light bands;
  `python3 -m py_compile build_office.py materials.py` passed.

Remaining issues: None.

## 2026-08-26 — fix — use three equally distributed random curtain states

Branch: `main`.

Replaced the continuous random curtain height with exactly three discrete
states: rolled up (`0%` coverage), half down (`50%`), and fully down (`100%`).
The state list is shuffled with the existing deterministic curtain seed, while
the total window count is divided exactly equally so the 2,472 windows contain
824 of each state. Rolled-up windows intentionally have no visible curtain
panel; the other two states keep the existing opaque grey-white panel.

Verification:
- Blender rebuilt `out/office_tower.blend`, `out/office_tower.glb`, and
  `out/office_preview.png` with EEVEE.
- Build output confirms `824 / 824 / 824` for rolled-up, half-down, and
  fully-down states, with 1,648 visible curtain panels across 2,472 windows.
- `python3 -m py_compile build_office.py materials.py` and `git diff --check`
  passed.

Remaining issues: None.

## 2026-08-26 — fix — restore the solid upper quarter of Office storeys

Branch: `main`.

Changed the Office clear glazing from 3.50 m to 3.75 m in the 5.00 m storey,
so glass occupies exactly 75% of each office level. Added a continuous
grey-white `Office_Spandrel_*` solid wall band from the glass head to the next
floor plate, and shortened mullions to the glass height. Curtains now start
exactly at the glass head and descend from there; their grey-white material is
fully opaque (`Alpha = 1`, `Transmission Weight = 0`) so interior light strips
cannot show through them.

Verification:
- Blender rebuilt `out/office_tower.blend`, `out/office_tower.glb`, and
  `out/office_preview.png` with EEVEE.
- Close EEVEE render confirms the continuous upper wall bands and no light
  leakage through the opaque curtain panels.
- `python3 -m py_compile build_office.py materials.py` and `git diff --check`
  passed.

Remaining issues: None.

## 2026-08-26 — fix — separate Office curtains from the glass surface

Branch: `main`.

Moved each top-down curtain 12 cm into the room from the inner glass surface
and gave it 1 cm of physical thickness. This keeps the panel close to the
glazing while removing the near-coplanar depth overlap that caused Z-fighting
and made Material Preview lose the curtain. Increased the frosted panel colour
to a readable light grey-green; the material remains high-roughness and EEVEE
`DITHERED` so it visibly blocks the interior instead of being depth-sorted
away.

Verification:
- Blender rebuilt `out/office_tower.blend`, `out/office_tower.glb`, and
  `out/office_preview.png` with EEVEE.
- Saved-Blend inspection confirms 2,472 glass panels and 2,472 curtain panels;
  the measured inner-surface separation is `0.121 m`, and the first curtain's
  top is above its random bottom edge (`28.470 m` to `26.512 m`).
- `python3 -m py_compile build_office.py materials.py` and `git diff --check`
  passed.

Remaining issues: None.

## 2026-08-26 — fix — make top-down Office curtains visibly frosted in EEVEE

Branch: `main`.

Kept every Office curtain anchored at the top of its pane with a deterministic
random drop toward the bottom. Increased the muted frosted-panel colour from
dark green to a light grey-green and raised the low transmission weight so the
curtains remain readable against the glass reflections and interior lighting.
The material remains opaque at the EEVEE surface level with high roughness and
DITHERED rendering; this is required because a transparent curtain behind the
50/50 transparent/reflection glass is otherwise lost by EEVEE depth sorting.

Verification:
- Diagnostic EEVEE close renders confirm the panels are visible across the
  window grid and start at the top edge rather than rising from the sill.
- `python3 -m py_compile build_office.py materials.py` and `git diff --check`
  passed after the source change.

Remaining issues: None.

## 2026-08-26 — fix — give every Office window a random curtain drop

Branch: `main`.

Reworked the Office curtain logic so an open state no longer removes the
curtain. Every office window now receives one frosted, semi-transparent panel
anchored at the top of the glazing, with a deterministic random drop between
18% and 100% of the clear window height. This creates varied vertical coverage
while ensuring every window still has an interior curtain. The frosted material
also uses an explicit transparent/high-roughness shader mix so it visibly
obscures the interior behind the clear facade glass.

Verification:
- Blender 5.2.0 LTS rebuilt `out/office_tower.blend`, `out/office_tower.glb`, and
  `out/office_preview.png` with EEVEE.
- Saved-Blend inspection confirms 2,472 Office glass panels and exactly 2,472
  curtain panels, with curtain heights ranging from `0.62 m` to `3.44 m`.
- The curtain mesh is inside the glazing and uses the strengthened frosted
  material at roughness `0.86` with EEVEE `BLENDED` rendering. The preview was
  visually inspected; `python3 -m py_compile build_office.py materials.py` and
  `git diff --check` passed.

Remaining issues: None.

## 2026-08-26 — feature — add random frosted curtain states to Office windows

Branch: `main`.

Added a semi-transparent, high-roughness frosted-glass film just inside each
Office window. Every office pane gets a deterministic random state: full-height
frosting, lower-half frosting, or fully open with no frosting. The film is inset
from the glass and narrowed slightly at the edges so it stays inside the
mullion frame while the original clear glazing and its reflections remain.

Verification:
- Blender 5.2.0 LTS rebuilt `out/office_tower.blend`, `out/office_tower.glb`, and
  `out/office_preview.png` with EEVEE.
- Saved-Blend inspection confirms 2,472 office windows: 1,130 full, 730 half,
  and 612 open; the curtain mesh contains 1,860 panels with height spans of
  `3.44 m` and `1.72 m`. The film material uses alpha `0.52`, roughness `0.72`,
  transmission `0.18`, and EEVEE `BLENDED` rendering.
- The preview was visually inspected; `python3 -m py_compile build_office.py
  materials.py` and `git diff --check` passed.

Remaining issues: None.

## 2026-08-26 — fix — shrink the office ground plane

Branch: `main`.

Reduced the Office ground plane from `220 x 220 m` to `50 x 50 m`, using the
tower's `FOOTPRINT` value so the ground only covers the building's footprint
envelope instead of extending far beyond the tower.

Verification:
- Blender 5.2.0 LTS rebuilt `out/office_tower.blend`, `out/office_tower.glb`, and
  `out/office_preview.png` with EEVEE.
- Saved-Blend inspection confirms `Office_Ground` dimensions are `50.0 x 50.0 m`
  at `z=-0.05`.
- `python3 -m py_compile build_office.py materials.py` and `git diff --check`
  passed; the preview was visually inspected.

Remaining issues: None.

## 2026-08-26 — fix — extend office support columns through the tower

Branch: `main`.

Extended the four existing Office perimeter support columns from the bottom
three pilotis levels to the full `165.0 m` tower height. The lower three levels
remain an open pilotis zone, while the same columns now continue through all
occupied and equipment levels to the roof.

Verification:
- Blender 5.2.0 LTS rebuilt `out/office_tower.blend`, `out/office_tower.glb`, and
  `out/office_preview.png` with EEVEE.
- Saved-Blend inspection confirms `Office_Pilotis` contains 4 columns spanning
  `z=0.0..165.0 m`; the generator and GLB export completed successfully.
- `python3 -m py_compile build_office.py materials.py` and `git diff --check`
  passed.

Remaining issues: None.

## 2026-08-26 — fix — split office ceiling lights into controllable segments

Branch: `main`.

Updated the Office ceiling lighting so each of the 32 radial fan strips on every
office floor is made of three independent panels with visible gaps between
segments. Lighting state is generated per segment with a fixed seed: individual
panels can be off, and each floor also contains a four-strip-wide dark sector so
the whole sector is not forced to remain lit. On and off geometry is kept in
separate objects, with the off panels using a zero-emission material.

Verification:
- Blender 5.2.0 LTS rebuilt `out/office_tower.blend`, `out/office_tower.glb`, and
  `out/office_preview.png` with EEVEE.
- Saved-Blend inspection confirms 2,304 segments total: 1,452 on and 852 off,
  48 ceiling Z levels, `Office_Core` at `18.0 x 18.0 x 165.0 m`, and
  `OfficeCeilingLight_Off` emission strength `0.0`.
- The preview was visually inspected; `python3 -m py_compile build_office.py
  materials.py` and `git diff --check` passed.

Remaining issues: None.

## 2026-08-26 — fix — increase the Office service core

Increased the Office tower's central service core from `14.0 x 14.0 m` to
`18.0 x 18.0 m`. On the 50.0 x 50.0 m floor plate this brings the core to about
13% of gross plan area, a more credible high-rise office proportion while
preserving a deep perimeter office zone. The radial ceiling-light starts move
out automatically with the enlarged core.

Verification:
- Rebuilt `out/office_tower.blend`, `out/office_tower.glb`, and
  `out/office_preview.png` with Blender 5.2.0 LTS using EEVEE.
- Saved-Blend inspection confirms `Office_Core` is `18.0 x 18.0 x 165.0 m`,
  the 768 radial ceiling panels remain outside the core and inside the tower
  footprint, and the glass preview remains the shared 50/50 EEVEE setup.
- `python3 -m py_compile build_office.py materials.py` and `git diff --check`
  passed.

Remaining issues: None.

## 2026-08-26 — fix — distribute office ceiling lights radially

Replaced the Office tower's facade-edge light selection with 32 evenly spaced
fan-shaped ceiling strips on every office floor. Each strip starts just outside
the central service core and expands toward the rounded-square perimeter, like
clock ticks or radial spokes. The strips now sit below the underside of each
floor slab, so they are actual ceiling fixtures rather than lights mounted on
the curtain-wall surface. The former random facade-module clusters were removed.

Verification:
- Rebuilt `out/office_tower.blend`, `out/office_tower.glb`, and
  `out/office_preview.png` with Blender 5.2.0 LTS using EEVEE.
- The generator reports 32 radial strips per office floor and 768 total; its
  geometry assertions and GLB export passed.
- Saved-mesh inspection confirms 768 panels, 48 Z levels, ceiling placement at
  `z=29.60..154.68 m`, and all panel vertices inside the rounded-square
  superellipse footprint.
- `python3 -m py_compile build_office.py materials.py` and `git diff --check`
  passed.

Remaining issues: None.

## 2026-08-26 — fix — align office glass reflection with house

Changed the Office generator to use the same saved EEVEE preview-glass setup as
the house. Its glazing now uses the shared fixed 50% transparent / 50% pure
reflection mix, with EEVEE ray tracing enabled so surrounding scene geometry can
appear in the reflection. The physical definition remains available by setting
`RENDER_ENGINE = "CYCLES"`: Transmission 1.0, Roughness 0.0, and IOR 1.52 then
provide the physical Fresnel response.

Verification:
- Rebuilt `out/office_tower.blend`, `out/office_tower.glb`, and
  `out/office_preview.png` with Blender 5.2.0 LTS.
- Saved-scene inspection confirms EEVEE, ray tracing `True`, preview Mix factor
  `0.5`, pure Anisotropic reflection at roughness `0.0`, and the physical glass
  values IOR `1.52`, Transmission `1.0`, and Roughness `0.0`.
- `python3 -m py_compile build_office.py materials.py`, `git diff --check`, and
  the office material assertions passed.

Remaining issues: None.

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
