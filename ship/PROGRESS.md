# Ship — Progress

The purple-hulled liner is the largest of the three ships in
`longtest 25.skp` (SketchUp 24.0.483). Geometry is extracted into
`ship_data/` (`ship_mesh.npz`, `parts.json`, `textures/`) and rebuilt
by `build_ship.py`. The SKP itself is the source of truth for the
hull shape; the Blender scene is a faithful import plus a handful of
explicit extras listed below.

## 2026-10-23 — feat — storey decks, clear framed glass, no invented hull

The SKP is a hollow shell: no floor plates inside the purple hull, and
the superstructure glazing is a single unframed pane whose shader
read as frosted (transmission 0.85, roughness 0.08, DITHERED alpha).
The previous conversion also lofted extra `Bow_Shell` / `Stern_Shell` /
`Bow_Deck` skins that were not in the SKP and changed the silhouette.

What is in the SKP, kept as-is:

* purple hull triangles, including the existing bow wedge (stem at
  x=-172.5, waterline at x=-140.8, |y|=14.7, then full 22 m beam from
  x=-128) and the stern slope (x=162.5 at z=15 down to x=172.5 at z=0);
* every superstructure, deck, window, lifeboat and pool mesh, with
  SketchUp material colours;
* waterline at z=0 after centering the world-space mid-point.

What is added, and why:

* **Interior decks.** A 30 cm slab on every occupied storey
  (`DECK_LEVELS` = 6, 9, 12, 15, 18, 22.5, 27, 30, 33, 36, 39.5, 44 m)
  so the ship is not a hollow box when looking through the glass.
  Each level is sliced through the SKP walls at 0.4 m steps from
  0.6 m below the storey to just under the next, rasterised at 0.2 m,
  dilated 8 cells (~1.6 m) to close balcony-door gaps, then flood-filled
  from the grid border. Anything not reachable from outside becomes
  deck. Where the SKP already has a horizontal surface at that level
  the new slab is left out, so it never lies coplanar with SKP faces.
  Pool footprints are also excluded, including one storey above so a
  36 m slab does not cap the pool. A 6-cell morphological opening
  drops stray balcony-bay speckles. The hull's open-topped bow wedge
  is closed by the 15 m slab (its SKP walls stop at z=15) — this is a
  new floor, not a new hull skin.
* **Clear glass.** Every `Glass_*` and `Window_Glass` material is
  `materials.make_glass` (the house / Harukas / Stack shader):
  roughness 0, transmission 1, IOR 1.52, near-white cool tint
  `(0.93, 0.97, 1.00)`. EEVEE uses the 50/50 glossy / transparent
  preview mix so the panes reflect and stay see-through. The old
  Principled-with-alpha-0.55 / roughness-0.08 path is gone.
* **Window frames.** `Window_Frames` puts a 12 cm white-aluminium bar
  around every glazed polygon plus a mullion every 1.5 m along the
  pane (roof glass is a 3 m grid). Bar ends are pulled in 1.5 cm
  (`FRAME_END_GAP`) so they do not sit on the deck or wall plane the
  pane meets.
* **Z-fighting.** Coplanar SKP layers of different materials are
  grouped ignoring facing (an up-facing roof and a down-facing ceiling
  on the same plane fight just as hard) and pushed 3 cm along each
  triangle's own normal (`_fix_coplanar`, step=0.03). Combined with
  the frame-end gap this drops `check_stack_zfight.py` from 2786
  overlapping pairs to 243, of which ~10 still involve the frames.

What is *not* done, on purpose:

* no lofted bow or stern skins (`Bow_Shell` / `Stern_Shell` /
  `Bow_Deck` are verified absent);
* no invented promenade liners, fascia, convex-hull deck fills or
  bulkheads (the previous conversion's leftovers);
* no recolour of the slate-blue hull as navy — `Hull_Purple` stays
  SKP sRGB `(0.282, 0.239, 0.545)`.

Build:

```bash
blender --background --factory-startup --python-exit-code 1 --python build_ship.py
blender --background --factory-startup --python-exit-code 1 --python build_ship.py -- --no-render
blender --background --factory-startup --python-exit-code 1 --python verify_ship.py
```

Outputs (git-ignored) live in `out/`: `elegant_ship.blend` and
`hero.png` / `side.png` / `aerial.png` / `bow.png`.

Remaining issues: the SKP itself still has coplanar interior faces
that the 3 cm offset does not fully hide at every camera; interior
decks are schematic floor plates, not cabin layouts.
