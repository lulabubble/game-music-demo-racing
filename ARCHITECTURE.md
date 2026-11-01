# Architecture

How audio assets are structured, how the engine produces them, and
where track-specific data ends and track-agnostic logic begins.

The project is being refactored incrementally. This document describes
the target structure and the terminology used everywhere in code,
manifest, filenames, and commit messages.

## Vocabulary

### Layer

A **layer** is a short, musical loop, aligned to the bar grid, that
the game can start, stop, fade, or swap independently of other layers.

- Length: any multiple of a bar, not necessarily equal to the master.
- Owner: the track. Only the track decides what plays in a layer.
- Example: `racing_acceleration.layer.wav` at 2 bars, looped by the
  game when acceleration is active.
- Not to be confused with a "section": a section (intro / main /
  turnaround / lift) is a narrative position in the demo arrangement.
  A layer is a musical element that can be gated at any time.

### Stem

A **stem** is a full-length submix: one of the four audio components
(air, motion, acceleration, danger) resampled / looped to exactly the
master length.

- Length: equal to the master, by definition.
- Owner: the engine. Produced by `materialize(layer)`.
- Example: `racing_acceleration.stem.wav` at 32 bars.
- A stem is the materialized form of a layer. If the layer already
  spans the full length, `materialize` is the identity function and
  the stem is bit-identical to the layer.

### Master

The **master** is the sum of all stems, mixed at unity.

- Length: equal to each stem.
- Owner: the engine.
- Contract: `master = sum(stems)`, verified with max|diff| < 1e-6.
- The master is a preview of the full mix. In game, the game mixes
  the layers, not the master.

## Pipeline

The engine (`engine.render_track`) runs the same pipeline for every
track:

    buses      (track-specific, full length)
      -> reverb per bus
      -> grouping into layers
      -> materialize layers -> stems
      -> RMS normalize (single k on sum)
      -> per-stem soft-tanh (only if peak > TARGET_PEAK)
      -> make_loop per stem
      -> context doubles (from stems, per target)
      -> master = sum(stems); identity checked
      -> write files + manifest

Stage boundaries that matter:

- **bus -> layer**: track-owned. Bus routing, weights, and reverb
  parameters come from `track_*/config.py`.
- **layer -> stem**: engine-owned. `materialize(layer, master_len)`
  loops the layer to master length. When `layer.length == master_len`,
  materialize is the identity function.
- **stem -> master**: engine-owned. Enforced by contract; violation
  raises, no files written.

## The contract lives at the master

During refactoring, the only invariant that is enforced is

    master = sum(materialize(layers))

Everything upstream of that — layer lengths, layer count, whether a
layer is a 2-bar loop or a 32-bar submix — is free. This is what
"adaptive layers" means in this project: a track can ship short
layers, and the engine will loop them to master length to produce the
preview master.

A consequence for verification:

- While refactoring the engine or the composer, verify both
  `hash(stem) == hash_expected` and `hash(master) == hash_expected`.
  This catches accidental changes in the move itself.
- Once adaptive layers are shipped, only `hash(master)` is guaranteed.
  A layer's own hash may differ (it is a shorter, equivalent
  representation) while the materialized stem and the master stay
  unchanged.

## Where code lives

| Concern                           | Module                            | Track-specific |
|-----------------------------------|-----------------------------------|----------------|
| Reverb, make_loop, sidechain,     | `engine.py`                       | no             |
| peak/rms, tanh, materialize,      |                                   |                |
| render_track, manifest assembly   |                                   |                |
| Rhythm, loudness, presets,        | `track_*/config.py`               | yes            |
| reverb params, bus routing,       |                                   |                |
| harmony, layer spec               |                                   |                |
| What plays at which sample        | `track_*/arrangement.py`          | yes            |
| (`render_buses`)                  |                                   |                |
| Instruments (mono, per hit)       | `instruments_render_mono_*`       | no             |
| Wind character curves             | `sfx_functional_mono_noise_wind_*`| no             |
| Boxcar smooth + quantize          | `math_render_smooth_quantized_*`  | no             |
| Entry point (one per track)       | `track_*/generate_wav_files.py`   | per track      |

Imports are strictly downward: entry point imports track config,
arrangement, and engine. Arrangement imports engine and the shared
instrument modules. Engine imports nothing track-specific. Track
config imports nothing.

## Naming in config.py

- `LAYER_SPEC` — one entry per layer: `{'loop_bars': None | int}`.
  `None` means "same length as master" (no materialization).
- `LAYER_ORDER` — deterministic ordering of layers in grouping,
  manifest, and file writes.
- `BUS_TO_LAYER` — which layer each bus contributes to.
- `PRESETS` — per-preset bus weights.
- `REVERB_CFG` — per-bus reverb parameters.

At the time of writing, all layers have `loop_bars = None`, so
`materialize` is the identity function. This is intentional: the
engine supports adaptive layers from day one, but no track uses them
yet.

## Manifest

The manifest records both sides of the materialization boundary:

- `layers`: `[{name, loopBars, sourceSamples}]` — what the track
  produced.
- `stems`: `[{name, samples, materializedFrom: {layer, loopBars}}]` —
  what the engine produced after materialization.
- `master`: `{peak, rms, identityDiff}` — the contract check.

When `loopBars == masterBars`, `materializedFrom.loopBars` equals
`masterBars` and the stem is a copy of the layer (bit-identical in
that case, though this is not required by the contract).

## Non-goals

- The engine never knows which track is rendering. It receives a
  config module and an arrangement function.
- The track never writes files. It only produces buses.
- The master is never summed by the track. Only `engine.render_track`
  performs the master sum and the contract check.
- Reverb parameters are data, not code. New presets are added to
  `PRESETS`; existing presets are not edited in place so the manifest
  always records which values produced a given run.
