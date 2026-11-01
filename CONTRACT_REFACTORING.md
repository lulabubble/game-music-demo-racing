# Contract-based refactoring

How we are gradually splitting `generate_wav_files.py` (a monolith)
into contract modules.

## Why

- The monolith is ~700 lines: hard to hold in context, hard to edit in
  isolation, hard to test.
- Contract modules let us think about *behaviour* separately from
  *implementation*.
- Small files are easier to read, review, change, replace.

## Pattern

For each logical unit:

- `X_contract.py` — short, self-contained description: what goes in,
  what comes out, what is guaranteed. No implementation details, no
  "see impl".
- `X_impl.py` — the implementation itself.
- `tests_X.py` — optional, verifies the contract.
- The contract **must be shorter than the implementation**. If it is
  not, it is not a contract, it is a second copy of the code.

## Imports

- Alias on import when the name is too generic or may collide with
  another module (`soft as wind_soft`).
- No `from X import *`.

## Done so far

### instruments_render_mono

- Contract and impl separated.
- Ten instruments: `kick`, `snare`, `snare_short`, `hat`, `open_hat`,
  `riser`, `reese`, `sub_long`, `arp_pulse`, `pad_note`.
- Imports consolidated into a single block.
- Hash verified, module wired into `generate_wav_files.py`.

### sfx_functional_mono_noise_wind

- Contract and impl separated.
- Three curves: `soft`, `aggressive`, `extreme`.
- Imported with aliases `wind_soft`, `wind_aggressive`, `wind_extreme`.
- `char_H` / `char_D` / `char_G` are now thin wrappers over the shared
  curves. Behaviour verified bit-for-bit, no difference.

### math_render_smooth_quantized

- Contract and impl separated.
- One function: `smooth_quantized` (smooth → scale → quantize).
- Wired into `render_wind_exp_2x`, replacing the duplicated inline
  code (L: 81, R: 128). Output is bit-identical to before.

## Rules we settled on

1. Contract is always shorter than the impl.
2. Contract is self-contained: inputs, outputs, guarantees. No
   "See impl".
3. No technical details in the contract (`np.convolve`, `mode='same'`,
   epsilons) — those belong in the impl.
4. Alias on import to avoid name collisions.
5. One commit per extraction, with a check before the commit.
6. Config / global constants stay untouched until the logic is done.

## Not extracted yet (candidates)

- `reverb`: `make_ir_stereo` + `apply_reverb`
- `timeline`: `hz`, `place_at_sample`, `place_at_bar`, `chord_at`,
  `section_of`
- `dsp_utils`: `peak_of`, `rms_db_of`, `solve_soft_limit_a`,
  `make_loop`, `sidechain_duck`
- `render_wind_exp_2x` → its own module
- `context_double`: `make_context_double`
- manifest assembly → its own function
- top-of-file docstring → `ARCHITECTURE.md`

## What it gave us

- `generate_wav_files.py` is smaller and reads like a pipeline.
- Every extracted module can be tested on its own.
- Wind curves live in one place, with no duplication.
- Bit-identical behaviour is verified after every step — no audio
  regressions.
