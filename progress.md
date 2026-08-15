# Progress

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
