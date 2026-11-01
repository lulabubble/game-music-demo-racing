# TODO: optimization

Supersedes the "adaptive layers" idea of exporting short dry layer
files. We do NOT create racing_*_layer.opus, we do NOT slice buffers,
we do NOT touch the audio pipeline. The stems keep their full 32 bars
and their reverb, and the master stays bit-identical.

Instead, game.js is told where inside the existing full-length stem
each musical section lives, and uses AudioBufferSourceNode.loopStart /
loopEnd to play, skip, or loop sections on the bar grid.

Why this works:
- No clicks: the buffer is the same smooth make_loop'ed stem as before.
- No dry sound: reverb is already baked into the stem.
- No regressions: stems and master stay bit-identical, always.
- Control in game: loopStart/loopEnd can gate any bar-aligned window.

## What is needed

### Step 1 — manifest: timing + sections
- [ ] Add barSeconds = 4 * 60 / bpm to racing_manifest.json
- [ ] Add sectionBars: {name: [startBar, endBar]} derived from the same
      thresholds already used by section_of(bar) in the composer
      (intro 0-8, main 8-24, turnaround 24-28, lift 28-32)
- [ ] Verify: all WAVs bit-identical; only manifest JSON changes

### Step 2 — game.js: section-aware playback
- [ ] Read barSeconds and sectionBars from the manifest
- [ ] Keep sources playing the full stem buffer, loop = true
- [ ] Drive loopStart / loopEnd from section bars:
        loopStart = startBar * barSec * sampleRate
        loopEnd   = endBar   * barSec * sampleRate
- [ ] On section change: set loopStart/loopEnd, then jump playback to
      loopStart (or let it wrap naturally, whichever sounds right)
- [ ] Verify: preview master untouched; playback uses the same files

### Step 3 — map modes to sections
- [ ] Each MODES entry picks a section (and optionally a stem set)
      instead of assuming the full 32-bar loop is "the song"
- [ ] Example: Menu = intro section; Cruise = main; Boost = main
      with acceleration+danger; Danger = lift or main with danger full
- [ ] No audio file changes required for this step

## Out of scope (kept for the record)

- Reverb on short layers, longer layer buffers for the tail, crossfade
  loops at layer boundaries — all unnecessary while we play the full
  stem and gate with loopStart/loopEnd.
- Exporting racing_*_layer.opus — not needed; the full stem is the
  single source of truth.

## Invariants

- Python composer output (WAVs + manifest audio fields) stays
  bit-identical at every step of this work.
- The game never mixes a short loop that does not align to the bar grid.
- Only the manifest and game.js change.
