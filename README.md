# Game Music Demo — Racing

A browser demo of **adaptive game music** in a racing context.

## What this is

Four synthesized music stems — Air, Motion, Acceleration, Danger — play together in the browser via Web Audio API. Instead of switching tracks, the game changes the **mix**: each stem's volume responds to player state, mode changes, or manual sliders.

All music is **100% Python-generated**. Every note, texture and loop is synthesized from scratch in `generate_wav_files.py` using NumPy + SciPy — no samples, no external audio assets. The WAV files are encoded to Opus for the web, and `racing_manifest.json` records the exact loop length for sample-accurate playback.

## Suno relationship

Suno is used **only as creative inspiration** — equivalent to listening to music and getting ideas from it. No Suno output is used directly. Everything in this repo is reproducible from source.

## What this demo tests

- **Adaptive 4-stem mixer** — Air / Motion / Acceleration / Danger
- **Sample-accurate looping** — Web Audio API, exact `loopSamples` from manifest
- **Gapless Opus** — decoder pre-skip/padding trimmed to the manifest length
- **Mode-based narrative** — Menu / Cruise / Boost / Danger, auto-advances every 8 bars
- **Manual override** — drag any slider to switch from auto to manual

## Play

👉 **[Open the demo](https://lulabubble.github.io/game-music-demo-racing/)**

## Status

- [x] GitHub Pages test page
- [x] Opus stems + sample-accurate Web Audio loop
- [x] Adaptive 4-stem mixer with modes and auto narrative
- [ ] Racing scene (obstacles, coins)
- [ ] Gameplay-driven mode changes
- [ ] Track switching (Pixel Sprint / Quiet Ward)

## Built with

- Plain HTML / CSS / JS — no dependencies, no build step
- Python (`generate_wav_files.py`) — all audio synthesis
- NumPy + SciPy — DSP from scratch

## Copy-paste for Discord / coding channels

> Built a browser demo of adaptive game music: 4 fully Python-synthesized stems (Air / Motion / Acceleration / Danger), mixed live in Web Audio API. Gapless Opus loops trimmed to exact `loopSamples` for sample-accurate playback. Modes auto-advance every 8 bars, or drag any slider to take over manually. 👉 https://lulabubble.github.io/game-music-demo-racing/

## Files

- `index.html` — the demo (Canvas + Web Audio)
- `generate_wav_files.py` — the full audio generator
- `racing_manifest.json` — BPM, loop length, per-stem metadata
- `racing_*_loop.opus` — 4 stems + master, 96 kbps gapless
- `SUNO_NOTES.md` — prompt notes used as inspiration only