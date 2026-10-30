# Roadmap

A living plan for turning this demo into a full adaptive game music system.

## Vision

Most game soundtracks are static loops. This project treats music as a **system**: stems mix live, sections rearrange, events trigger stingers, and timbre responds to gameplay. The goal is not to ship a game - it is to demonstrate that the same architecture used by AAA studios (FMOD, Wwise) can run on a handful of files in a browser, with all audio synthesized from Python source.

The demo will always stay small enough to explain in one page. Every phase adds one axis of adaptivity without breaking the previous ones.

## Current state

Done and shipping in `main`:

- `generate_wav_files.py` v9 produces 4 stems (Air / Motion / Acceleration / Danger) + master, 32-bar loop at 174 BPM.
- Opus encoding via `opusenc` (gapless, pre-skip trimmed against `racing_manifest.json`).
- `index.html` uses Web Audio API: `AudioContext(44100)`, `decodeAudioData`, `AudioBufferSourceNode`, `loopEnd = loopSamples`.
- Adaptive 4-stem mixer: 4 sliders, 4 mode buttons (Menu / Cruise / Boost / Danger), auto narrative every 8 bars, manual override on slider drag.

## Five axes of adaptivity

| Axis | What changes | Status |
|------|--------------|--------|
| **Vertical** | Stem gains | Done (4 stems, modes, sliders) |
| **Horizontal** | Sections, arrangement | Not started (sections are baked into one loop) |
| **Transitions** | Fills, risers, stingers | Partial (riser + snare roll inside the loop) |
| **DSP / timbre** | Filter, reverb, distortion | Not started |
| **Harmonic** | Key, modulation | Not started (fixed D minor) |

Each phase below moves one axis forward.

## Phases

### Phase 1 - Horizontal graph scaffold (JS only)

Build the section graph and transition rules in `index.html`, using the current 4 stems as placeholder content for every section. No new audio files.

Why: validate the architecture (state machine, bar-quantized transitions, section bookkeeping) before generating more content.

Deliverables:
- `SECTIONS` map in JS: A (intro), B (main), C (bridge), LIFT, A' (outro).
- `canTransition(from, to)` rules: transitions only on bar boundaries, some paths require a `dangerLevel` threshold.
- Debug overlay showing current section, bar within section, next allowed transitions.
- Existing stems play continuously; only the "section label" and transition rules change.

Exit criteria: clicking mode buttons and forcing section changes never produces an audible glitch, and the section label always matches a legal path.

### Phase 2 - Stingers

Short one-shot sounds triggered by gameplay events. Separate from the loop.

Deliverables:
- 4 stingers synthesized in Python: `stinger_crash`, `stinger_boost`, `stinger_final_lap`, `stinger_finish`.
- Each is a short WAV (0.3 - 1.5 s), Opus-encoded.
- JS: `playStinger(name)` loads via `decodeAudioData` once at startup, plays through the master gain.
- Stingers duck the main mix by -6 dB for their duration (short sidechain via `setTargetAtTime`).
- Wire one button or key per stinger so they can be tested without gameplay.

Exit criteria: stingers never clip, never overlap themselves, and do not interrupt the loop.

### Phase 3 - Real horizontal sections

Export distinct arrangements from Python. Each section gets its own set of 4 stems.

Deliverables:
- New output naming: `racing_{section}_{stem}_loop.opus`, e.g. `racing_A_air_loop.opus`.
- Python: split the 32-bar loop into 4 exportable sections (A: 8 bars, B: 16 bars, TURN: 4 bars, LIFT: 4 bars). Each section rendered as an independent N-bar loop with its own stems.
- Manifest v10: `sections` block with per-section BPM, bars, loopSamples, key, and stems.
- JS: `SectionGraph` class replaces the Phase 1 placeholder. On transition, the current section fades out (0.15 s) while the next section starts sample-aligned at the same `currentTime`.
- Visual indicator in the UI: current section, next section, and remaining bars before the next legal transition.

Exit criteria: A -> B -> TURN -> A' plays as a continuous piece of music, no audible seams, no phase drift over 10 minutes.

### Phase 4 - DSP automation

Tie timbre to gameplay state. Same files, different processing.

Deliverables:
- `BiquadFilterNode` (LP) per stem bus, cutoff driven by a `speed` parameter (e.g. 800 Hz idle, 8 kHz max).
- `ConvolverNode` with two impulse responses: "open track" (short) and "tunnel" (long). Crossfade on trigger.
- `WaveShaperNode` with tanh curve on acceleration bus, gain driven by `boostLevel`.
- `DelayNode` with feedback on danger bus, wet gain driven by `dangerLevel`.
- All parameters use `setTargetAtTime` with 0.05 - 0.2 s time constants, never abrupt.

Exit criteria: speeding up is audibly felt through timbre, not only loudness. Tunnel entry is obvious. No clicks when parameters move.

### Phase 5 - Harmonic modulation

Allow sections to live in different keys, with musically safe transitions.

Deliverables:
- Python: sections defined with per-section key. Example: A in Dm, B in Dm, C in F major, LIFT in Dm. All at 174 BPM.
- Transition rules extended: some transitions only legal if the key change is prepared (e.g. a one-bar pivot chord).
- JS: when transitioning across keys, schedule the pivot bar from the source section, then switch.

Exit criteria: A -> C -> B sounds like the same piece with a shift in mood, not like two unrelated tracks.

### Phase 6 - Additional tracks

Apply the same engine to other moods. Different track, same architecture.

Deliverables:
- `pixel_sprint` track (platformer, 132 BPM, A minor) - 4 stems, 2-4 sections.
- `quiet_ward` track (horror, 60 BPM, D minor, no percussion) - 4 layers, 1 section, stingers for events.
- A top-level `TRACKS` registry in JS. Menu selects track; the engine loads the corresponding manifest and stems.
- Stingers are track-agnostic where possible, track-specific where needed.

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
    "LIFT": { "bars": 4,  "loopSamples": 243310, "key": "Dm", "stems": ["air","motion","acceleration","danger"] }
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
- **Sample-accurate, not "close enough".** Every loop uses `loopEnd = loopSamples / sampleRate`. No assumptions about decoder behavior.
- **Bar-quantized transitions.** Mode changes, section changes and stinger triggers may be requested at any time, but are applied on the next bar boundary.
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
| 4 | DSP automation | Not started |
| 5 | Harmonic modulation | Not started |
| 6 | Additional tracks | Not started |

Update this table as phases land. Keep the phases small enough that each one is a single commit.
