# Roadmap

A living plan for turning this demo into a full adaptive game music system.

## Vision

Most game soundtracks are static loops. This project treats music as a **system**: stems mix live, sections rearrange, events trigger stingers, and timbre responds to gameplay. The goal is not to ship a game - it is to demonstrate that the same architecture used by AAA studios (FMOD, Wwise) can run on a handful of files in a browser, with all audio synthesized from Python source.

The demo will always stay small enough to explain in one page. Every phase adds one axis of adaptivity without breaking the previous ones.

## Current state

Done and shipping in `main`:

- `generate_wav_files.py` v9 produces 4 stems (Air / Motion / Acceleration / Danger) + master, 32-bar loop at 174 BPM.
- **Per-bus reverb is already baked into the WAV files** via `fftconvolve` with custom impulse responses (see `REVERB_CFG`). The stems in `racing_*_loop.wav` already contain all reverb tails, folded at the loop boundary by Python.
- Opus encoding via `opusenc` (gapless, pre-skip trimmed against `racing_manifest.json`).
- `index.html` uses Web Audio API: `AudioContext(44100)`, `decodeAudioData`, `AudioBufferSourceNode`, `loopEnd = loopSamples`.
- Adaptive 4-stem mixer: 4 sliders, 4 mode buttons (Menu / Cruise / Boost / Danger), auto narrative every 8 bars, manual override on slider drag.

## Five axes of adaptivity

| Axis | What changes | Status |
|------|--------------|--------|
| **Vertical** | Stem gains | Done (4 stems, modes, sliders) |
| **Horizontal** | Sections, arrangement | Not started (sections are baked into one loop) |
| **Transitions** | Fills, risers, stingers | Partial (riser + snare roll inside the loop) |
| **DSP / timbre** | Filter, distortion | Not started (reverb is already baked-in, not live) |
| **Harmonic** | Key, modulation | Not started (fixed D minor) |

Each phase below moves one axis forward.

## Reverb policy: baked-in, not live

This is a deliberate architectural decision, worth stating up front:

- **Baked-in (in WAV, from Python):** reverb, delay tails, anything that decays over time or would leak past the loop boundary.
- **Real-time (Web Audio):** only stateless effects - `BiquadFilterNode`, `WaveShaperNode`. These do not accumulate tails and are safe on loop boundaries.

Why:

1. `ConvolverNode` cannot fold its tail back into the loop. On `loopEnd`, the reverb from the end of the buffer does not continue into the start. That produces an audible cut on every loop. Python's `fold_tail` solves this; Web Audio's `ConvolverNode` cannot.
2. Convolution is the most expensive operation in Web Audio. Four stems x ConvolverNode on a phone is a real risk of crackle and CPU spikes.
3. Baked-in reverb is portable: the same file works in Unity, Godot, FMOD, Wwise, and any browser, without re-exporting impulse responses.
4. What the sound designer heard in Python is what the player hears in the browser. No surprises from browser-specific convolution.

Real-time DSP in Phase 4 is therefore limited to **filter and distortion only**.

## Phases

### Phase 1 - Horizontal graph scaffold (JS only)

Build the section graph and transition rules in `index.html`, using the current 4 stems as placeholder content for every section. No new audio files.

Why: validate the architecture (state machine, bar-quantized transitions, section bookkeeping) before generating more content.

Deliverables:
- `SECTIONS` map in JS: A (intro), B (main), TURN (turnaround), LIFT (lift). A' (outro) is optional and added only when real outro content exists.
- `canTransition(from, to)` rules: transitions only on bar boundaries, some paths require a `dangerLevel` threshold.
- Debug overlay showing current section, bar within section, next allowed transitions.
- Existing stems play continuously; only the "section label" and transition rules change. Audio does not switch yet, since all sections use the same stems.

Exit criteria: clicking mode buttons and forcing section changes never produces an audible glitch, and the section label always matches a legal path.

### Phase 2 - Stingers

Short one-shot sounds triggered by gameplay events. Separate from the loop.

Deliverables:
- 4 stingers synthesized in Python: `stinger_crash`, `stinger_boost`, `stinger_final_lap`, `stinger_finish`.
- Each is a short WAV (0.3 - 1.5 s) with **reverb baked in** (same IR policy as the stems).
- Opus-encoded, played via `decodeAudioData` once at startup, through the master gain.
- Stingers duck the main mix by -6 dB for their duration (short sidechain via `setTargetAtTime`).
- Wire one button or key per stinger so they can be tested without gameplay.

Exit criteria: stingers never clip, never overlap themselves, and do not interrupt the loop.

### Phase 3 - Real horizontal sections

Export distinct arrangements from Python. Each section gets its own set of 4 stems.

Deliverables:
- New output naming: `racing_{section}_{stem}_loop.opus`, e.g. `racing_A_air_loop.opus`.
- Python: split the 32-bar loop into 4 exportable sections (A: 8 bars, B: 16 bars, TURN: 4 bars, LIFT: 4 bars). Each section rendered as an independent N-bar loop with its own stems and its own baked-in reverb.
- Manifest v10: `sections` block with per-section BPM, bars, loopSamples, key, and stems.
- JS: `SectionGraph` class replaces the Phase 1 placeholder. On transition, the next section starts with `AudioBufferSourceNode.start(when, offset)` where `offset` matches the current bar position inside the target section, so the new section enters in phase with the bar grid. The outgoing section fades over 0.15 s while the incoming section is already running.
- Visual indicator in the UI: current section, next section, and remaining bars before the next legal transition.

Why offset start matters: without it, each section starts from sample 0 regardless of where the bar grid currently is, and the two sections drift out of phase. With offset start, both sit on the same bar boundary, and the crossfade is musically transparent.

Exit criteria: A -> B -> TURN -> LIFT -> A plays as a continuous piece of music, no audible seams, no phase drift over 10 minutes.

### Phase 4 - Real-time DSP (stateless only)

Tie timbre to gameplay state, without reverb or delay in the live path. Reverb and delay remain baked-in from Python.

Deliverables:
- `BiquadFilterNode` (lowpass) per stem bus. Cutoff driven by a `speed` parameter (e.g. 800 Hz idle, 8 kHz max). Time constant 0.1 s.
- `WaveShaperNode` with a tanh curve on the acceleration bus. Drive gain driven by `boostLevel`. Time constant 0.05 s.
- Optional: a second `BiquadFilterNode` (highpass) on the danger bus, cutoff driven by `dangerLevel`, to make danger feel "thinner" and more urgent.
- All parameters use `setTargetAtTime`, never abrupt.

Explicitly out of scope in this phase:
- `ConvolverNode` (reverb) - stays baked-in.
- `DelayNode` - tail would leak past `loopEnd`; if added later, it must be baked-in from Python.

Exit criteria: speeding up is audibly felt through timbre, not only loudness. No clicks when parameters move. CPU on a mid-range Android phone stays below 30% with all four stems playing.

### Phase 5 - Harmonic modulation

Allow sections to live in different keys, with musically safe transitions.

Deliverables:
- Python: sections defined with per-section key. Example: A in Dm, B in Dm, TURN in Dm, LIFT in F major. All at 174 BPM.
- Manifest: `key` field per section, and optional `pivotBar` field when a prepared modulation is desired.
- JS: when transitioning across keys, if `pivotBar` is set, schedule the pivot bar from the source section before switching. If not set, transition directly on the bar boundary - acceptable in DnB, where direct key shifts are common.

Exit criteria: A -> LIFT -> B sounds like the same piece with a shift in mood, not like two unrelated tracks.

### Phase 6 - Additional tracks

Apply the same engine to other moods. Different track, same architecture.

Deliverables:
- `pixel_sprint` track (platformer, 132 BPM, A minor) - 4 stems, 2-4 sections.
- `quiet_ward` track (horror, 60 BPM, D minor, no percussion) - 4 layers, 1 section, stingers for events. Reverb is even more critical here and stays fully baked-in.
- A top-level `TRACKS` registry in JS. Menu selects track; the engine loads the corresponding manifest and stems.
- Stingers are **per-track**: DnB stingers and horror stingers share the loading mechanism but not the content.

Exit criteria: switching tracks in the menu reloads stems cleanly and the mixer behaves identically.

## Architecture notes

File layout on GitHub Pages:

```
index.html
racing_manifest.json
racing_A_air_loop.opus
racing_A_motion_loop.opus
racing_A_acceleration_loop.opus
racing_A_danger_loop.opus
racing_B_air_loop.opus
... (one set per section per stem)
stinger_crash.opus
stinger_boost.opus
stinger_final_lap.opus
stinger_finish.opus
```

Every `.opus` file contains its own reverb tail, folded at the loop boundary by Python. The browser never adds reverb.

Manifest (v10 sketch):

```json
{
  "track": "Rotor Rush",
  "version": 10,
  "bpm": 174.0,
  "sampleRate": 44100,
  "sections": {
    "A":    { "bars": 8,  "loopSamples": 486621, "key": "Dm", "stems": ["air","motion","acceleration","danger"] },
    "B":    { "bars": 16, "loopSamples": 973242, "key": "Dm", "stems": ["air","motion","acceleration","danger"] },
    "TURN": { "bars": 4,  "loopSamples": 243310, "key": "Dm", "stems": ["air","motion","acceleration","danger"] },
    "LIFT": { "bars": 4,  "loopSamples": 243310, "key": "F",  "stems": ["air","motion","acceleration","danger"], "pivotBar": true }
  },
  "transitions": [
    { "from": "A", "to": "B",    "when": "bar_boundary" },
    { "from": "B", "to": "TURN", "when": "dangerLevel > 0.7" },
    { "from": "TURN", "to": "B", "when": "bar_boundary" },
    { "from": "B", "to": "LIFT", "when": "progress > 0.9" },
    { "from": "LIFT", "to": "A", "when": "bar_boundary" }
  ]
}
```

The engine reads `transitions` as data, not hardcoded `if`s. Adding a new path is editing the manifest, not the code.

## Design decisions

- **All audio is Python-synthesized.** No samples, no external assets, no Suno output. Suno is used only as creative inspiration (see `SUNO_NOTES.md`).
- **Reverb and delay are baked-in, not live.** See the "Reverb policy" section above. Only stateless DSP runs in the browser.
- **Sample-accurate, not "close enough".** Every loop uses `loopEnd = loopSamples / sampleRate`. No assumptions about decoder behavior.
- **Bar-quantized transitions.** Mode changes, section changes and stinger triggers may be requested at any time, but are applied on the next bar boundary.
- **Offset-aware section starts.** When switching sections, the incoming section starts at the offset that matches the current bar position, so the bar grid is preserved across the transition.
- **Additive phases.** No phase rewrites the previous one. The final system is the sum of its phases.
- **One HTML file, no build step.** Every phase stays inside `index.html` plus static assets. No bundlers, no frameworks.
- **Local-first testing.** `python -m http.server 8000` for iteration. GitHub Pages for delivery.

## Non-goals

- A full game. Simple shapes only (square, triangle, rectangles).
- 3D, physics engines, or shaders.
- Multiplayer, saves, leaderboards.
- A backend. Everything runs client-side.

## Status table

| Phase | Title | Status |
|-------|-------|--------|
| 0 | Baseline: 4 stems, adaptive mixer | Done |
| 1 | Horizontal graph scaffold (JS) | Not started |
| 2 | Stingers | Not started |
| 3 | Real horizontal sections (Python) | Not started |
| 4 | Real-time DSP (filter, distortion) | Not started |
| 5 | Harmonic modulation | Not started |
| 6 | Additional tracks | Not started |

Update this table as phases land. Keep the phases small enough that each one is a single commit.
