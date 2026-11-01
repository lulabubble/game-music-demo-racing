# TODO

## Adaptive layers (short-term)

Goal: let the game gate short, self-contained loops per stem, while the
Python composer keeps producing the same stems and the same master
(bit-identical to the previous commit at every step until step 4).

Constraint for now: layers are DRY (no reverb). Reverb stays on the stems.
Consequence to accept: in-game mix is drier and shorter than the preview
master. Fixing that by putting reverb on layers (and lengthening layers
for the tail) is deferred — see below.

### Step 1 — scaffold, no-op
- [ ] Add LAYER_SPEC to track_first_demo/config.py: every layer {'loop_bars': None}
- [ ] Add materialize(layer, master_len) to engine.py; None -> identity
- [ ] Insert materialize step into the composer pipeline
- [ ] Verify: all WAVs and racing_manifest.json bit-identical to previous commit

### Step 2 — export dry layers
- [ ] Group dry buses into dry stems (same weights, no reverb)
- [ ] make_loop each dry stem using its loop_bars (currently None = master length)
- [ ] Write racing_*_layer.opus alongside the stems
- [ ] Verify: existing stems and master bit-identical

### Step 3 — manifest + game.js
- [ ] Manifest: add barSeconds and layers: [{name, loopBars, loopSeconds}]
- [ ] game.js: load racing_*_layer.opus, set loopEnd = buffer.duration per source
- [ ] Verify: preview master untouched

### Step 4 — musical decision
- [ ] Set loop_bars per layer (e.g. 4/4/4/8)
- [ ] Verify: stems and master bit-identical; layers intentionally new
- Note: 4 bars == one full Dm-Bb-F-C progression, loops harmonically clean

## Deferred

- [ ] Reverb on layers, not only on stems
  - Requires longer layer buffers so the reverb tail fits
  - Requires choosing a loop point that does not click across the tail
  - Out of scope until layer scaffolding is done and verified
