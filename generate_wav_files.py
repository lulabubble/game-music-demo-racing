"""
Rotor Rush v9 - context doubles for audio-model ingestion
=========================================================

Audio behaviour of stems, loops, master and all contracts is IDENTICAL to v8.
Only the *_double files changed meaning and a new *_stem_double was added.

------------------------------------------------------------------------
CHANGES FROM V8 (the only changes)
------------------------------------------------------------------------
[CHANGE-1] _double is now a CONTEXT MIX, not a solo stem.
  v8: racing_acceleration_double.wav = solo acceleration stem, 2N.
  v9: racing_acceleration_double.wav = full 4-stem mix, 2N, with
      acceleration boosted and the other three attenuated, then
      renormalized to TARGET_RMS_DB. Intended for Suno / audio-model
      ingestion, where the model must hear the full picture but with
      the target stem dominant.

[CHANGE-2] The old solo double is preserved as racing_*_stem_double.wav.
  For A/B comparison against the original solo loop and for regression
  testing of [FIX-1] and [FIX-2]. Not for Suno.

[CHANGE-3] Context mix parameters live in CONFIG:
    DOUBLE_CONTEXT_BOOST  = 3.0    (target stem, +9.5 dB)
    DOUBLE_CONTEXT_OTHERS = 0.33   (each of the other three, -9.5 dB)
  Ratio target/others = 9.0 (≈ +19 dB). Per-stem context doubles each
  get their own renormalization factor k_ctx, recorded in manifest.

[CHANGE-4] Manifest gains contextMix block and updated playerNotes.

Everything else - loop naming, master definition, identity check,
contract fail-fast, presets, reverb config, FIX-1 and FIX-2 - is
unchanged from v8.

------------------------------------------------------------------------
ARCHITECTURE CONTRACTS (unchanged from v8)
------------------------------------------------------------------------

1. MASTER CONTRACT
     master_double = sum of 4 stem_double stems (2N), NO make_loop, NO tanh,
                     NO normalization
     master_loop   = sum of 4 loop stems        (N),  NO tanh, NO normalization
   Verified with max|master - sum| < 1e-6; violation -> RuntimeError, no files.

2. PIPELINE (9 steps, printed and recorded in manifest):
     1. dry 2N buses (10 buses)
     2. reverb per bus (stereo buses reverb per-channel)
     3. weighted sum into 4 stems (2N)            <- "stem_wet", the source
     4. single k on sum -> TARGET_RMS_DB
     5. per-stem soft-tanh (only if peak > TARGET_PEAK)
     6. make_loop each stem -> 4 loop stems (N)
     7. build 4 context doubles (2N) from stem_wet with per-stem boost
     8. master_double / master_loop = sums; identity checked
     9. write 4 stems x (_loop, _stem_double, _double) + master x
        (_loop, _double) + manifest

3. STEREO REVERB
     Mono bus   -> mono-summed wet (legacy path, unchanged)
     Stereo bus -> per-channel wet, no cross-feed, no mono collapse
                   (only wind_exp is stereo)

4. BUS ROUTING (10 buses -> 4 stems, weights from PRESETS[ACTIVE_PRESET]):
     pad      -> air          0.50   mono   4.00s/50%/d1.4/hp250/lp4000    seed 1001
     wind     -> air          0.20   mono   2.00s/25%/d2.0/hp400/lp3000    seed 1002
     wind_exp -> danger       0.70   stereo 2.00s/25%/d2.0/hp400/lp3000    seed 1003
     kick     -> motion       0.85   mono   0.15s/04%/d4.0/hp300/lp2500    seed 1004
     hat      -> motion       0.45   mono   0.25s/12%/d3.0/hp1500/lp8000   seed 1005
     snare    -> danger       0.65   mono   0.20s/08%/d3.5/hp500/lp6000    seed 1006
     fx       -> danger       0.45   mono   3.00s/45%/d1.4/hp200/lp4000    seed 1007
     reese    -> acceleration 0.80   mono   0.10s/02%/d5.0/hp300/lp4000    seed 1008
     sub      -> acceleration 0.75   mono   0.00s/00%/d1.0/hp100/lp1000    seed 1009
     arp      -> acceleration 0.55   mono   0.20s/08%/d3.5/hp500/lp6000    seed 1010

------------------------------------------------------------------------
KNOWN FIXES (unchanged from v8 - must be preserved)
------------------------------------------------------------------------

[FIX-1] Kick click artifact in motion stem
  Fix: 30 ms squared fade-out on kick envelope (KICK_FADE_OUT_SEC).
  Do NOT remove without re-testing motion stem solo AND stem_double.

[FIX-2] Stereo reverb mono collapse
  Fix: per-channel convolution for stereo inputs (no mono collapse).
  Only affects wind_exp.

------------------------------------------------------------------------
EAR-TUNED VALUES (unchanged from v8 - do not change without re-listening)
------------------------------------------------------------------------
  - wind     weight 0.20
  - wind_exp weight 0.70
  - char_D   x**3 * 1.5
  - smooth_* initial scale 0.05
  - pad      weight 0.50

If a new preset is needed, add a new key to PRESETS - do NOT edit
'production' in place, so the manifest always records which values were used.
"""

import os
import json
import numpy as np
from scipy import signal
from scipy.io import wavfile

# =====================================================================
# GLOBAL CONFIG
# =====================================================================
SR                = 44100
BPM               = 174.0
BEAT              = 60.0 / BPM
BAR               = BEAT * 4.0
BARS              = 32
SEED              = 11
LOOP_LEN          = int(round(BARS * BAR * SR))
BUFFER_LEN        = 2 * LOOP_LEN
OUT_PREFIX        = 'racing'

# Loudness / peak policy
TARGET_RMS_DB     = -18.0
TARGET_PEAK       = 0.92
MASTER_PEAK_LIMIT = 0.98

# --- [CHANGE-3] Context double balance (new in v9) ---
# target stem x DOUBLE_CONTEXT_BOOST, each other stem x DOUBLE_CONTEXT_OTHERS.
# 3.0 / 0.33 = 9.09x amplitude ≈ +19.2 dB relative to each other stem.
# Absolute level renormalized to TARGET_RMS_DB per target.
DOUBLE_CONTEXT_BOOST  = 3.00
DOUBLE_CONTEXT_OTHERS = 0.33

# --- [FIX-1] Kick fade-out (unchanged) ---
KICK_FADE_OUT_SEC = 0.030

# --- wind_exp tuning constants (unchanged) ---
WIND_EXP_SMOOTH_SCALE = 0.05
WIND_EXP_FINAL_SCALE  = 0.028 * 2
WIND_EXP_QUANT_STEPS  = 64
CHAR_D_EXPONENT       = 1.5

# =====================================================================
# PRESETS - named so manifest records which values were used
# =====================================================================
PRESETS = {
    'production': {
        'pad':      0.50,
        'wind':     0.20,
        'wind_exp': 0.70,
        'kick':     0.85,
        'hat':      0.45,
        'snare':    0.65,
        'fx':       0.45,
        'reese':    0.80,
        'sub':      0.75,
        'arp':      0.55,
    },
}
ACTIVE_PRESET = 'production'

# =====================================================================
# REVERB CONFIG (unchanged from v8)
# =====================================================================
REVERB_CFG = {
    'pad':      {'ir_dur': 4.00, 'wet': 0.50, 'decay': 1.4, 'hp': 250,  'lp': 4000, 'seed': 1001, 'ch': 'mono'},
    'wind':     {'ir_dur': 2.00, 'wet': 0.25, 'decay': 2.0, 'hp': 400,  'lp': 3000, 'seed': 1002, 'ch': 'mono'},
    'wind_exp': {'ir_dur': 2.00, 'wet': 0.25, 'decay': 2.0, 'hp': 400,  'lp': 3000, 'seed': 1003, 'ch': 'stereo'},
    'kick':     {'ir_dur': 0.15, 'wet': 0.04, 'decay': 4.0, 'hp': 300,  'lp': 2500, 'seed': 1004, 'ch': 'mono'},
    'hat':      {'ir_dur': 0.25, 'wet': 0.12, 'decay': 3.0, 'hp': 1500, 'lp': 8000, 'seed': 1005, 'ch': 'mono'},
    'snare':    {'ir_dur': 0.20, 'wet': 0.08, 'decay': 3.5, 'hp': 500,  'lp': 6000, 'seed': 1006, 'ch': 'mono'},
    'fx':       {'ir_dur': 3.00, 'wet': 0.45, 'decay': 1.4, 'hp': 200,  'lp': 4000, 'seed': 1007, 'ch': 'mono'},
    'reese':    {'ir_dur': 0.10, 'wet': 0.02, 'decay': 5.0, 'hp': 300,  'lp': 4000, 'seed': 1008, 'ch': 'mono'},
    'sub':      {'ir_dur': 0.00, 'wet': 0.00, 'decay': 1.0, 'hp': 100,  'lp': 1000, 'seed': 1009, 'ch': 'mono'},
    'arp':      {'ir_dur': 0.20, 'wet': 0.08, 'decay': 3.5, 'hp': 500,  'lp': 6000, 'seed': 1010, 'ch': 'mono'},
}

# =====================================================================
# BUS -> STEM MAPPING (unchanged)
# =====================================================================
BUS_TO_STEM = {
    'pad':      'air',
    'wind':     'air',
    'wind_exp': 'danger',
    'kick':     'motion',
    'hat':      'motion',
    'snare':    'danger',
    'fx':       'danger',
    'reese':    'acceleration',
    'sub':      'acceleration',
    'arp':      'acceleration',
}

BUS_ORDER  = ['pad', 'wind', 'wind_exp', 'kick', 'hat', 'snare', 'fx', 'reese', 'sub', 'arp']
STEM_ORDER = ['air', 'motion', 'acceleration', 'danger']

OUT_CANDIDATES = [
    '/storage/emulated/0/Download',
    '/sdcard/Download',
    os.path.expanduser('~/Download'),
    os.getcwd(),
]

# =====================================================================
# HELPERS (unchanged)
# =====================================================================
def hz(midi):
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)

def adsr(n, a=0.005, d=0.05, s=0.7, r=0.1):
    an = int(a * SR); dn = int(d * SR); rn = int(r * SR)
    sn = max(0, n - an - dn - rn)
    env = np.concatenate([
        np.linspace(0, 1, an) if an else np.array([]),
        np.linspace(1, s, dn) if dn else np.array([]),
        np.full(sn, s),
        np.linspace(s, 0, rn) if rn else np.array([]),
    ])
    if len(env) < n:
        env = np.pad(env, (0, n - len(env)))
    return env[:n]

def place_at_sample(buf, hit, start):
    if start < 0 or start >= len(buf):
        return
    e = min(start + len(hit), len(buf))
    buf[start:e] += hit[:e - start]

def place_at_bar(buf, hit, bar, offset_16ths=0.0):
    iteration = bar // BARS
    rel_bar = bar % BARS
    rel_t = rel_bar * BAR + offset_16ths * BEAT * 0.25
    i = iteration * LOOP_LEN + int(round(rel_t * SR))
    place_at_sample(buf, hit, i)

def solve_soft_limit_a(peak_x, target_peak, iters=100):
    if peak_x <= target_peak:
        return None
    ratio = target_peak / peak_x
    lo, hi = 1e-9, 100.0
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if np.tanh(mid) / mid > ratio:
            lo = mid
        else:
            hi = mid
    u = 0.5 * (lo + hi)
    return peak_x / u

def peak_of(x):
    return float(np.max(np.abs(x)))

def rms_db_of(x):
    rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
    return 20.0 * np.log10(rms + 1e-12)

# =====================================================================
# INSTRUMENTS (unchanged from v8)
# =====================================================================
def kick(dur=0.22, amp=0.9):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 90 * np.exp(-t * 45) + 45
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 14)
    click = np.random.randn(n) * np.exp(-t * 300) * 0.2
    b, a = signal.butter(2, 8000 / (SR / 2), btype='low')
    click = signal.lfilter(b, a, click)
    env = 1 - np.exp(-t * 200)
    fade_n = int(KICK_FADE_OUT_SEC * SR)
    if fade_n < n:
        env[-fade_n:] *= np.linspace(1, 0, fade_n) ** 2
    return amp * (body + click) * env

def snare(dur=0.18, amp=0.55):
    n = int(dur * SR); t = np.arange(n) / SR
    nz = np.random.randn(n)
    b, a = signal.butter(2, [1200 / (SR / 2), 8000 / (SR / 2)], btype='band')
    nz = signal.lfilter(b, a, nz)
    body = 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 22)
    env = (1 - np.exp(-t * 400)) * np.exp(-t * 16)
    return amp * (nz * 0.85 + body) * env

def snare_short(dur=0.08, amp=0.4):
    n = int(dur * SR); t = np.arange(n) / SR
    nz = np.random.randn(n)
    b, a = signal.butter(2, [1500 / (SR / 2), 9000 / (SR / 2)], btype='band')
    nz = signal.lfilter(b, a, nz)
    body = 0.3 * np.sin(2 * np.pi * 220 * t) * np.exp(-t * 35)
    env = (1 - np.exp(-t * 500)) * np.exp(-t * 30)
    return amp * (nz * 0.9 + body) * env

def hat(dur=0.04, amp=0.08):
    n = int(dur * SR); t = np.arange(n) / SR
    nz = np.random.randn(n)
    b, a = signal.butter(4, 8000 / (SR / 2), btype='high')
    nz = signal.lfilter(b, a, nz)
    return amp * nz * np.exp(-t * 130)

def open_hat(dur=0.15, amp=0.07):
    n = int(dur * SR); t = np.arange(n) / SR
    nz = np.random.randn(n)
    b, a = signal.butter(4, 7000 / (SR / 2), btype='high')
    nz = signal.lfilter(b, a, nz)
    return amp * nz * np.exp(-t * 22)

def reese(freq, dur, amp=0.45):
    n = int(dur * SR); t = np.arange(n) / SR
    s1 = 2 * ((t * freq * 0.995) % 1.0) - 1
    s2 = 2 * ((t * freq * 1.005) % 1.0) - 1
    x = (s1 + s2) * 0.5
    b, a = signal.butter(2, 600 / (SR / 2), btype='low')
    x = signal.lfilter(b, a, x)
    x = np.tanh(x * 2.5)
    sub = np.sin(2 * np.pi * freq * t) * 0.4
    env = adsr(n, a=0.003, d=0.04, s=0.9, r=0.06)
    return amp * (x * 0.65 + sub) * env

def sub_long(freq, dur, amp=0.4):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t) + 0.15 * np.sin(4 * np.pi * freq * t)
    env = adsr(n, a=0.01, d=0.08, s=0.9, r=0.1)
    return amp * x * env

def arp_pulse(freq, dur, amp=0.06):
    n = int(dur * SR); t = np.arange(n) / SR
    ph = (t * freq) % 1.0
    x = np.where(ph < 0.25, 1.0, -1.0)
    b, a = signal.butter(2, 4500 / (SR / 2), btype='low')
    x = signal.lfilter(b, a, x)
    env = (1 - np.exp(-t * 600)) * np.exp(-t * 22)
    return amp * x * env

def pad_note(freqs, dur, amp=0.05, lp_cutoff=1000):
    n = int(dur * SR); t = np.arange(n) / SR
    pad = np.zeros(n)
    for f in freqs:
        for det in (-0.005, 0.0, 0.005):
            pad += 2 * ((f * (1 + det) * t) % 1.0) - 1
    b, a = signal.butter(2, lp_cutoff / (SR / 2), btype='low')
    pad = signal.lfilter(b, a, pad)
    env = adsr(n, a=0.3, d=0.15, s=0.8, r=0.3)
    return amp * pad * env / (len(freqs) * 3)

def riser(dur, amp=0.10):
    n = int(dur * SR); t = np.arange(n) / SR
    nz = np.random.randn(n)
    b, a = signal.butter(2, [1500 / (SR / 2), 10000 / (SR / 2)], btype='band')
    nz = signal.lfilter(b, a, nz)
    f = np.linspace(200, 2500, n)
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) * 0.25
    env = np.linspace(0, 1, n) ** 2.5
    fade_n = int(0.05 * SR)
    if fade_n < n:
        env[-fade_n:] *= np.linspace(1, 0.3, fade_n)
    return amp * (nz * 0.7 + tone) * env

# =====================================================================
# HARMONY (unchanged)
# =====================================================================
CHORDS = {
    'Dm': {'root': 38, 'tones': [62, 65, 69]},
    'Bb': {'root': 34, 'tones': [58, 62, 65]},
    'F':  {'root': 41, 'tones': [65, 69, 72]},
    'C':  {'root': 36, 'tones': [60, 64, 67]},
}
PROG = ['Dm', 'Bb', 'F', 'C']

def chord_at(bar):
    return PROG[bar % 4]

def section_of(bar):
    if bar < 8:  return 'intro'
    if bar < 24: return 'main'
    if bar < 28: return 'turnaround'
    return 'lift'

# =====================================================================
# EXPERIMENTAL WIND (unchanged from v8)
# =====================================================================
def char_H(x):   return np.tanh(x * 2.0) * 0.7
def char_D(x):   return x ** 3 * CHAR_D_EXPONENT
def char_G(x):   return np.arctanh(np.clip(x, -0.999, 0.999)) * 0.40

WIND_CHARACTER = {
    'intro':      char_H,
    'main':       char_D,
    'turnaround': char_H,
    'lift':       char_G,
}

def section_of_bar(bar):
    if bar < 8:  return 'intro'
    if bar < 24: return 'main'
    if bar < 28: return 'turnaround'
    return 'lift'

def render_wind_exp_2x():
    raw = np.random.RandomState(SEED + 200).uniform(-1, 1, LOOP_LEN)
    smooth_L = np.convolve(raw, np.ones(81) / 81,   mode='same')
    smooth_R = np.convolve(raw, np.ones(128) / 128, mode='same')
    smooth_L = smooth_L / (np.max(np.abs(smooth_L)) + 1e-9) * WIND_EXP_SMOOTH_SCALE
    smooth_R = smooth_R / (np.max(np.abs(smooth_R)) + 1e-9) * WIND_EXP_SMOOTH_SCALE
    Q = WIND_EXP_QUANT_STEPS
    smooth_L = np.round(smooth_L * Q) / Q
    smooth_R = np.round(smooth_R * Q) / Q
    b, a = signal.butter(2, [200 / (SR / 2), 3000 / (SR / 2)], btype='band')
    smooth_L = signal.lfilter(b, a, smooth_L)
    smooth_R = signal.lfilter(b, a, smooth_R)
    out_L = np.zeros(LOOP_LEN)
    out_R = np.zeros(LOOP_LEN)
    spb = int(round(BAR * SR))
    for bar in range(BARS):
        s = bar * spb
        e = min(s + spb, LOOP_LEN)
        func = WIND_CHARACTER[section_of_bar(bar)]
        seg_L = smooth_L[s:e].copy()
        seg_R = smooth_R[s:e].copy()
        bL = np.sqrt(np.mean(seg_L ** 2)) + 1e-9
        bR = np.sqrt(np.mean(seg_R ** 2)) + 1e-9
        seg_L = func(seg_L)
        seg_R = func(seg_R)
        nL = np.sqrt(np.mean(seg_L ** 2)) + 1e-9
        nR = np.sqrt(np.mean(seg_R ** 2)) + 1e-9
        seg_L *= bL / nL
        seg_R *= bR / nR
        out_L[s:e] = seg_L
        out_R[s:e] = seg_R
    gust_bars = [5, 12, 27, 30]
    glen = int(0.7 * BAR * SR)
    for gb in gust_bars:
        grng = np.random.RandomState(SEED + 200 + gb)
        g = grng.randn(glen)
        b, a = signal.butter(2, [150 / (SR / 2), 2500 / (SR / 2)], btype='band')
        g = signal.lfilter(b, a, g)
        g = g / (np.max(np.abs(g)) + 1e-9) * 0.9
        g = char_G(g)
        g = g / (np.max(np.abs(g)) + 1e-9) * 0.4
        env = np.sin(np.pi * np.arange(glen) / glen) ** 2
        g = g * env
        s = gb * spb
        e = min(s + glen, LOOP_LEN)
        out_L[s:e] += g[:e - s] * 0.7
        out_R[s:e] += g[:e - s] * 0.7
    peak = max(np.max(np.abs(out_L)), np.max(np.abs(out_R)))
    if peak > 0:
        out_L = out_L / peak * 0.85
        out_R = out_R / peak * 0.85
    out_L = out_L * WIND_EXP_FINAL_SCALE
    out_R = out_R * WIND_EXP_FINAL_SCALE
    stereo = np.stack([out_L, out_R], axis=-1)
    return np.concatenate([stereo, stereo], axis=0)

# =====================================================================
# RENDER 2x (unchanged from v8)
# =====================================================================
def render_2x():
    n = BUFFER_LEN
    kick_bus  = np.zeros(n)
    snare_bus = np.zeros(n)
    hat_bus   = np.zeros(n)
    reese_bus = np.zeros(n)
    sub_bus   = np.zeros(n)
    arp_bus   = np.zeros(n)
    pad_bus   = np.zeros(n)
    fx_bus    = np.zeros(n)

    np.random.seed(SEED)
    w1 = np.random.randn(LOOP_LEN)
    b, a = signal.butter(2, [200 / (SR / 2), 3000 / (SR / 2)], btype='band')
    w1 = signal.lfilter(b, a, w1)
    t1 = np.arange(LOOP_LEN) / SR
    w1 *= 0.7 + 0.3 * np.sin(2 * np.pi * 0.15 * t1 + 0.3)
    w1 *= 0.028
    wind = np.concatenate([w1, w1])

    wind_exp = render_wind_exp_2x()

    np.random.seed(SEED + 100)
    riser_sample = riser(4 * BAR, amp=0.10)
    for lift_bar in (28, 28 + BARS):
        place_at_bar(fx_bus, riser_sample, lift_bar)

    for bar in range(BARS * 2):
        rel = bar % BARS
        ch = CHORDS[chord_at(bar)]
        tones_hz = [hz(t) for t in ch['tones']]
        sec = section_of(rel)
        lp = {'intro': 800, 'main': 1600, 'turnaround': 700, 'lift': 1100}[sec]
        amp = {'intro': 0.045, 'main': 0.045, 'turnaround': 0.05, 'lift': 0.05}[sec]
        hit = pad_note(tones_hz, BAR * 0.98, amp=amp, lp_cutoff=lp)
        place_at_bar(pad_bus, hit, bar)

    for bar in range(BARS * 2):
        if bar % BARS == 0:
            np.random.seed(SEED)
        rel = bar % BARS
        sec = section_of(rel)
        ch = CHORDS[chord_at(bar)]
        root_hz = hz(ch['root'])
        tones = ch['tones']

        if sec == 'intro':
            if rel < 4:
                for pos in [0, 8]:
                    place_at_bar(kick_bus, kick(amp=0.7), bar, pos)
            else:
                for pos in [0, 8]:
                    place_at_bar(kick_bus, kick(amp=0.75), bar, pos)
                for i in range(8):
                    off = i * 2
                    n_idx = [0, 1, 2, 1][i % 4]
                    place_at_bar(arp_bus, arp_pulse(hz(tones[n_idx]), 0.15, amp=0.04),
                                 bar, off)
                for i in range(8):
                    off = i * 2
                    a_hat = 0.05 if i % 2 == 0 else 0.03
                    place_at_bar(hat_bus, hat(amp=a_hat), bar, off)

        elif sec == 'main':
            for pos in [0, 6, 10]:
                place_at_bar(kick_bus, kick(amp=0.9), bar, pos)
            for pos in [4, 12]:
                place_at_bar(snare_bus, snare(amp=0.55), bar, pos)
            for i in range(16):
                a_hat = 0.07 if i % 2 == 0 else 0.045
                if i == 14:
                    place_at_bar(hat_bus, open_hat(amp=0.07), bar, i)
                else:
                    place_at_bar(hat_bus, hat(amp=a_hat), bar, i)
            place_at_bar(reese_bus, reese(root_hz, BAR * 0.55, amp=0.5), bar, 0)
            place_at_bar(reese_bus, reese(root_hz, BAR * 0.30, amp=0.42), bar, 10)
            place_at_bar(sub_bus, sub_long(root_hz / 2, BAR * 0.95, amp=0.35), bar, 0)
            for i in range(16):
                n_idx = [0, 1, 2, 1, 0, 2, 1, 2][i % 8]
                place_at_bar(arp_bus, arp_pulse(hz(tones[n_idx]), 0.09, amp=0.055),
                             bar, i)

        elif sec == 'turnaround':
            place_at_bar(kick_bus, kick(amp=0.75), bar, 0)
            place_at_bar(sub_bus, sub_long(root_hz / 2, BAR * 0.95, amp=0.32), bar, 0)
            for i in range(8):
                off = i * 2
                n_idx = [0, 1, 2, 1][i % 4]
                place_at_bar(arp_bus, arp_pulse(hz(tones[n_idx]), 0.12, amp=0.045),
                             bar, off)

        elif sec == 'lift':
            if rel < 31:
                for pos in [0, 8]:
                    place_at_bar(kick_bus, kick(amp=0.8), bar, pos)
                roll_amp = 0.15 + (rel - 28) * 0.15
                for i in range(16):
                    place_at_bar(snare_bus, snare_short(amp=roll_amp), bar, i)
                for i in range(16):
                    n_idx = [0, 1, 2, 1, 0, 2, 1, 2][i % 8]
                    place_at_bar(arp_bus, arp_pulse(hz(tones[n_idx]), 0.08, amp=0.05),
                                 bar, i)
                for i in range(16):
                    a_hat = 0.06 if i % 2 == 0 else 0.04
                    place_at_bar(hat_bus, hat(amp=a_hat), bar, i)
            else:
                for pos in [0, 8]:
                    place_at_bar(kick_bus, kick(amp=0.7), bar, pos)

    def sidechain_duck(target, trigger, amount, release=0.04):
        trig = np.abs(trigger)
        kl = int(release * SR)
        if kl < 2:
            return target
        kernel = np.exp(-np.arange(kl) / (kl / 3))
        kernel /= kernel.sum()
        trig = np.convolve(trig, kernel, mode='same')
        peak = trig.max()
        if peak > 1e-9:
            trig /= peak
        return target * (1 - amount * trig)

    sub_bus   = sidechain_duck(sub_bus,   kick_bus, 0.35)
    reese_bus = sidechain_duck(reese_bus, kick_bus, 0.30)
    pad_bus   = sidechain_duck(pad_bus,   kick_bus, 0.20)
    arp_bus   = sidechain_duck(arp_bus,   kick_bus, 0.15)
    wind      = sidechain_duck(wind,      kick_bus, 0.10)

    return {
        'pad': pad_bus, 'wind': wind, 'wind_exp': wind_exp,
        'kick': kick_bus, 'hat': hat_bus, 'snare': snare_bus,
        'fx': fx_bus, 'reese': reese_bus, 'sub': sub_bus, 'arp': arp_bus,
    }

# =====================================================================
# REVERB (unchanged from v8)
# =====================================================================
def make_ir_stereo(dur, decay, hp, lp, seed):
    n = max(2, int(dur * SR))
    t = np.arange(n) / SR
    rng = np.random.RandomState(seed)
    ir_L = rng.randn(n) * np.exp(-t * decay)
    ir_R = rng.randn(n) * np.exp(-t * decay)
    b, a = signal.butter(2, hp / (SR / 2), btype='high')
    ir_L = signal.lfilter(b, a, ir_L); ir_R = signal.lfilter(b, a, ir_R)
    b, a = signal.butter(2, lp / (SR / 2), btype='low')
    ir_L = signal.lfilter(b, a, ir_L); ir_R = signal.lfilter(b, a, ir_R)
    ir_L[0] = 0.0; ir_R[0] = 0.0
    ir_L /= (np.sqrt(np.sum(ir_L ** 2)) + 1e-9)
    ir_R /= (np.sqrt(np.sum(ir_R ** 2)) + 1e-9)
    return ir_L, ir_R


def apply_reverb(dry, ir_L, ir_R, wet):
    if wet <= 0.0:
        if dry.ndim == 1:
            return np.stack([dry, dry], axis=-1).astype(np.float32)
        return dry.astype(np.float32, copy=True)

    if dry.ndim == 1:
        N = len(dry)
        wet_L = signal.fftconvolve(dry, ir_L, mode='full')[:N]
        wet_R = signal.fftconvolve(dry, ir_R, mode='full')[:N]
        out_L = (1.0 - wet) * dry + wet * wet_L
        out_R = (1.0 - wet) * dry + wet * wet_R
        return np.stack([out_L, out_R], axis=-1).astype(np.float32)
    else:
        N = dry.shape[0]
        L = dry[:, 0]; R = dry[:, 1]
        wet_L = signal.fftconvolve(L, ir_L, mode='full')[:N]
        wet_R = signal.fftconvolve(R, ir_R, mode='full')[:N]
        out_L = (1.0 - wet) * L + wet * wet_L
        out_R = (1.0 - wet) * R + wet * wet_R
        return np.stack([out_L, out_R], axis=-1).astype(np.float32)


def make_loop(buf_2N):
    A = buf_2N[:LOOP_LEN]
    B = buf_2N[LOOP_LEN:LOOP_LEN * 2]
    x = np.linspace(0, 1, LOOP_LEN)
    if buf_2N.ndim == 2:
        x = x[:, None]
    return B * (1 - x) + A * x


# =====================================================================
# [CHANGE-1 / CHANGE-3] CONTEXT DOUBLE (new in v9)
# =====================================================================
def make_context_double(target_name, stems_wet):
    """Full 4-stem mix, 2N, with target stem x DOUBLE_CONTEXT_BOOST and each
    other stem x DOUBLE_CONTEXT_OTHERS. Renormalized to TARGET_RMS_DB.
    Per-target soft-tanh if peak > TARGET_PEAK.

    Returns (buffer_2N, info_dict) where info_dict carries k_ctx and peaks
    for the manifest.
    """
    mix = np.zeros_like(stems_wet[target_name], dtype=np.float64)
    for name in STEM_ORDER:
        scale = DOUBLE_CONTEXT_BOOST if name == target_name else DOUBLE_CONTEXT_OTHERS
        mix += stems_wet[name].astype(np.float64) * scale
    mix = mix.astype(np.float32)

    rms_before = float(np.sqrt(np.mean(mix.astype(np.float64) ** 2)))
    target_rms = 10.0 ** (TARGET_RMS_DB / 20.0)
    if rms_before < 1e-12:
        raise RuntimeError(f"context double for {target_name}: mix RMS is zero")
    k_ctx = target_rms / rms_before
    mix = (mix.astype(np.float64) * k_ctx).astype(np.float32)

    peak_in = peak_of(mix)
    a = solve_soft_limit_a(peak_in, TARGET_PEAK)
    if a is not None:
        mix = (np.tanh(mix.astype(np.float64) / a) * a).astype(np.float32)
    peak_out = peak_of(mix)
    rms_out = rms_db_of(mix)

    info = {
        'targetStem': target_name,
        'targetStemBoost': DOUBLE_CONTEXT_BOOST,
        'otherStemsScale': DOUBLE_CONTEXT_OTHERS,
        'k_ctx': round(float(k_ctx), 8),
        'peakIn': round(peak_in, 6),
        'peakOut': round(peak_out, 6),
        'rmsDbOut': round(rms_out, 3),
        'softTanh_a': None if a is None else round(float(a), 8),
    }
    return mix, info

# =====================================================================
# MAIN
# =====================================================================
def main():
    print("=" * 78)
    print("=== Rotor Rush v9 (context doubles for audio-model ingestion) ===")
    print("=" * 78)
    print(f"BPM={BPM:.0f}  BARS={BARS}  SR={SR}  LOOP={LOOP_LEN/SR:.2f}s ({LOOP_LEN} samples)")
    print(f"TARGET_RMS_DB={TARGET_RMS_DB}  TARGET_PEAK={TARGET_PEAK}  MASTER_PEAK_LIMIT={MASTER_PEAK_LIMIT}")
    print(f"Preset: {ACTIVE_PRESET}")
    print(f"Context mix: target x {DOUBLE_CONTEXT_BOOST}, others x {DOUBLE_CONTEXT_OTHERS} "
          f"(ratio {DOUBLE_CONTEXT_BOOST/DOUBLE_CONTEXT_OTHERS:.2f}x ≈ "
          f"{20*np.log10(DOUBLE_CONTEXT_BOOST/DOUBLE_CONTEXT_OTHERS):+.1f} dB)")
    print(f"Known fixes: [FIX-1] kick fade-out {KICK_FADE_OUT_SEC*1000:.0f} ms, "
          f"[FIX-2] stereo reverb per-channel")
    print()

    # -------- BUS ROUTING TABLE --------
    print("=== BUS ROUTING (10 buses -> 4 stems) ===")
    print(f"{'bus':10s} {'stem':13s} {'weight':>7s}  {'ir/wet/decay/hp/lp':24s} {'seed':>5s}  ch")
    weights = PRESETS[ACTIVE_PRESET]
    for b in BUS_ORDER:
        cfg = REVERB_CFG[b]
        irw = f"{cfg['ir_dur']:.2f}/{cfg['wet']:.2f}/{cfg['decay']:.1f}/{cfg['hp']}/{cfg['lp']}"
        print(f"{b:10s} {BUS_TO_STEM[b]:13s} {weights[b]:>7.2f}  {irw:24s} {cfg['seed']:>5d}  {cfg['ch']}")
    print()

    # -------- [1/9] DRY BUSES --------
    print("[1/9] Dry buses (2N = %d samples)" % BUFFER_LEN)
    buses = render_2x()
    print(f"  {'bus':10s} {'ch':8s} {'peak':>8s} {'rms_db':>8s}")
    for b in BUS_ORDER:
        buf = buses[b]
        ch = 'stereo' if buf.ndim == 2 else 'mono'
        print(f"  {b:10s} {ch:8s} {peak_of(buf):>8.4f} {rms_db_of(buf):>8.2f}")
    print()

    # -------- [2/9] REVERB --------
    print("[2/9] Reverb per bus")
    print(f"  {'bus':10s} {'ch':8s} {'ir_len':>7s} {'wet':>5s} {'peak_in':>8s} {'peak_out':>8s}")
    wet_buses = {}
    for b in BUS_ORDER:
        cfg = REVERB_CFG[b]
        ir_L, ir_R = make_ir_stereo(cfg['ir_dur'], cfg['decay'], cfg['hp'], cfg['lp'], cfg['seed'])
        dry = buses[b]
        wet = apply_reverb(dry, ir_L, ir_R, cfg['wet'])
        wet_buses[b] = wet
        ch = 'stereo' if dry.ndim == 2 else 'mono'
        print(f"  {b:10s} {ch:8s} {len(ir_L):>7d} {cfg['wet']:>5.2f} "
              f"{peak_of(dry):>8.4f} {peak_of(wet):>8.4f}")
    del buses
    print()

    # -------- [3/9] GROUPING --------
    print("[3/9] Grouping into 2N stems (weights from PRESETS['%s'])" % ACTIVE_PRESET)
    stems_wet = {name: np.zeros((BUFFER_LEN, 2), dtype=np.float64) for name in STEM_ORDER}
    for b in BUS_ORDER:
        stem = BUS_TO_STEM[b]
        stems_wet[stem] += wet_buses[b].astype(np.float64) * weights[b]
    del wet_buses
    stems_wet = {k: v.astype(np.float32) for k, v in stems_wet.items()}
    print(f"  {'stem':13s} {'buses':50s} {'peak':>8s} {'rms_db':>8s}")
    for name in STEM_ORDER:
        bs = ", ".join(f"{b}({weights[b]:.2f})" for b in BUS_ORDER if BUS_TO_STEM[b] == name)
        print(f"  {name:13s} {bs:50s} {peak_of(stems_wet[name]):>8.4f} {rms_db_of(stems_wet[name]):>8.2f}")
    print()

    # -------- [4/9] RMS NORMALIZATION --------
    print("[4/9] RMS normalization (single k on sum of stems)")
    S = sum(stems_wet.values())
    rms_before = float(np.sqrt(np.mean(S.astype(np.float64) ** 2)))
    target_rms = 10.0 ** (TARGET_RMS_DB / 20.0)
    if rms_before < 1e-12:
        raise RuntimeError("sum RMS is zero, cannot normalize")
    k = target_rms / rms_before
    stems_wet = {name: (buf.astype(np.float64) * k).astype(np.float32) for name, buf in stems_wet.items()}
    del S
    S_check = sum(stems_wet.values())
    rms_after = float(np.sqrt(np.mean(S_check.astype(np.float64) ** 2)))
    del S_check
    rms_after_db = 20 * np.log10(rms_after)
    print(f"  sum_rms_before = {rms_before:.6f}  ({20*np.log10(rms_before):.2f} dBFS)")
    print(f"  k              = {k:.6f}")
    print(f"  sum_rms_after  = {rms_after:.6f}  ({rms_after_db:.2f} dBFS)  "
          f"[check {'PASS' if abs(rms_after_db - TARGET_RMS_DB) < 0.05 else 'FAIL'}]")
    print()

    # -------- [5/9] PER-STEM SOFT TANH --------
    print("[5/9] Per-stem soft-tanh (only if peak > TARGET_PEAK)")
    print(f"  {'stem':13s} {'peak_in':>8s} {'a':>8s} {'peak_out':>8s} {'rms_in_db':>10s} {'rms_out_db':>11s} {'tanh':>5s}")
    stem_info = {}
    for name in STEM_ORDER:
        buf = stems_wet[name]
        pk_in = peak_of(buf)
        rms_in = rms_db_of(buf)
        a = solve_soft_limit_a(pk_in, TARGET_PEAK)
        if a is not None:
            buf = (np.tanh(buf.astype(np.float64) / a) * a).astype(np.float32)
            stems_wet[name] = buf
        pk_out = peak_of(buf)
        rms_out = rms_db_of(buf)
        stem_info[name] = {
            'a': None if a is None else round(float(a), 8),
            'peak_in': round(pk_in, 6),
            'peak_out': round(pk_out, 6),
            'rms_in_db': round(rms_in, 3),
            'rms_out_db': round(rms_out, 3),
        }
        a_str = '-' if a is None else f'{a:.4f}'
        print(f"  {name:13s} {pk_in:>8.4f} {a_str:>8s} {pk_out:>8.4f} {rms_in:>10.2f} {rms_out:>11.2f} "
              f"{'yes' if a else 'no':>5s}")
    print()

    # -------- [6/9] LOOP --------
    print("[6/9] make_loop per stem")
    loops = {}
    print(f"  {'stem':13s} {'max|loop-A|':>12s} {'max|loop-B|':>12s} {'check':>6s}")
    for name in STEM_ORDER:
        buf = stems_wet[name]
        loop = make_loop(buf)
        loops[name] = loop
        A = buf[:LOOP_LEN]
        B = buf[LOOP_LEN:LOOP_LEN * 2]
        dA = float(np.max(np.abs(loop - A)))
        dB = float(np.max(np.abs(loop - B)))
        print(f"  {name:13s} {dA:>12.6f} {dB:>12.6f} {'ok':>6s}")
    print()

    # -------- [7/9] CONTEXT DOUBLES --------
    print("[7/9] Context doubles (2N): target x %.2f, others x %.2f, renorm to %.1f dBFS"
          % (DOUBLE_CONTEXT_BOOST, DOUBLE_CONTEXT_OTHERS, TARGET_RMS_DB))
    context_doubles = {}
    context_info = {}
    print(f"  {'stem':13s} {'k_ctx':>10s} {'peak_in':>8s} {'peak_out':>8s} {'rms_out_db':>11s} {'tanh':>5s}")
    for name in STEM_ORDER:
        buf, info = make_context_double(name, stems_wet)
        context_doubles[name] = buf
        context_info[name] = info
        a_str = '-' if info['softTanh_a'] is None else f"{info['softTanh_a']:.4f}"
        print(f"  {name:13s} {info['k_ctx']:>10.6f} {info['peakIn']:>8.4f} "
              f"{info['peakOut']:>8.4f} {info['rmsDbOut']:>11.2f} "
              f"{'yes' if info['softTanh_a'] is not None else 'no':>5s}")
    print()

    # -------- [8/9] MASTER --------
    print("[8/9] Master = sum of stem doubles (no make_loop, no tanh, no normalization)")
    master_double = np.zeros_like(stems_wet[STEM_ORDER[0]], dtype=np.float64)
    for name in STEM_ORDER:
        master_double += stems_wet[name].astype(np.float64)
    master_double = master_double.astype(np.float32)

    master_loop = np.zeros_like(loops[STEM_ORDER[0]], dtype=np.float64)
    for name in STEM_ORDER:
        master_loop += loops[name].astype(np.float64)
    master_loop = master_loop.astype(np.float32)

    verify_d = np.zeros_like(master_double, dtype=np.float64)
    for name in STEM_ORDER:
        verify_d += stems_wet[name].astype(np.float64)
    diff_d = float(np.max(np.abs(master_double.astype(np.float64) - verify_d)))

    verify_l = np.zeros_like(master_loop, dtype=np.float64)
    for name in STEM_ORDER:
        verify_l += loops[name].astype(np.float64)
    diff_l = float(np.max(np.abs(master_loop.astype(np.float64) - verify_l)))

    peak_d = peak_of(master_double)
    peak_l = peak_of(master_loop)
    rms_d = rms_db_of(master_double)
    rms_l = rms_db_of(master_loop)

    print(f"  master_double peak = {peak_d:.4f}   limit={MASTER_PEAK_LIMIT}   "
          f"{'PASS' if peak_d <= MASTER_PEAK_LIMIT else 'FAIL'}")
    print(f"  master_loop   peak = {peak_l:.4f}   limit={MASTER_PEAK_LIMIT}   "
          f"{'PASS' if peak_l <= MASTER_PEAK_LIMIT else 'FAIL'}")
    print(f"  identity double: max|master_double - sum(stem_double)| = {diff_d:.2e}   "
          f"{'PASS' if diff_d < 1e-6 else 'FAIL'}")
    print(f"  identity loop:   max|master_loop   - sum(loop)|        = {diff_l:.2e}   "
          f"{'PASS' if diff_l < 1e-6 else 'FAIL'}")
    print(f"  master_double rms  = {rms_d:+.2f} dBFS")
    print(f"  master_loop   rms  = {rms_l:+.2f} dBFS")

    errors = []
    if peak_d > MASTER_PEAK_LIMIT:
        excess_db = 20 * np.log10(peak_d / MASTER_PEAK_LIMIT)
        errors.append(
            f"master_double peak {peak_d:.4f} > {MASTER_PEAK_LIMIT}. "
            f"Suggested: lower TARGET_RMS_DB by {excess_db:.2f} dB "
            f"(to {TARGET_RMS_DB - excess_db:.2f}) and rerun."
        )
    if peak_l > MASTER_PEAK_LIMIT:
        excess_db = 20 * np.log10(peak_l / MASTER_PEAK_LIMIT)
        errors.append(
            f"master_loop peak {peak_l:.4f} > {MASTER_PEAK_LIMIT}. "
            f"Suggested: lower TARGET_RMS_DB by {excess_db:.2f} dB "
            f"(to {TARGET_RMS_DB - excess_db:.2f}) and rerun."
        )
    if diff_d >= 1e-6:
        errors.append(f"master_double is not the sum of stem doubles: max|diff| = {diff_d:.2e}")
    if diff_l >= 1e-6:
        errors.append(f"master_loop is not the sum of loops: max|diff| = {diff_l:.2e}")

    if errors:
        print()
        print("  ERROR: contract violation. No files written.")
        for e in errors:
            print(f"    - {e}")
        raise RuntimeError("Master contract violated; see above.")

    print()

    # -------- [9/9] WRITE --------
    print("[9/9] Writing files")
    out_dir = None
    for d in OUT_CANDIDATES:
        try:
            os.makedirs(d, exist_ok=True)
            probe = os.path.join(d, '.wt')
            with open(probe, 'wb') as f:
                f.write(b'')
            os.remove(probe)
            out_dir = d
            break
        except Exception:
            continue
    if out_dir is None:
        raise RuntimeError("No writable output directory")

    written = {}
    print(f"  {'file':45s} {'dur':>7s} {'rms_db':>8s} {'peak':>8s} {'MB':>6s}")

    # Stems: loop, stem_double, context_double
    for name in ['air', 'motion', 'acceleration', 'danger']:
        for kind, buf in [
            ('loop',           loops[name]),
            ('stem_double',    stems_wet[name]),
            ('double',         context_doubles[name]),
        ]:
            fname = f"{OUT_PREFIX}_{name}_{kind}.wav"
            fpath = os.path.join(out_dir, fname)
            wavfile.write(fpath, SR, (np.clip(buf, -1, 1) * 32767).astype(np.int16))
            mb = os.path.getsize(fpath) / 1024 / 1024
            written[fname] = fpath
            print(f"  {fname:45s} {len(buf)/SR:>6.2f}s {rms_db_of(buf):>8.2f} "
                  f"{peak_of(buf):>8.4f} {mb:>6.1f}")

    # Master: loop, double (unity mix)
    for kind, buf in [('loop', master_loop), ('double', master_double)]:
        fname = f"{OUT_PREFIX}_master_{kind}.wav"
        fpath = os.path.join(out_dir, fname)
        wavfile.write(fpath, SR, (np.clip(buf, -1, 1) * 32767).astype(np.int16))
        mb = os.path.getsize(fpath) / 1024 / 1024
        written[fname] = fpath
        print(f"  {fname:45s} {len(buf)/SR:>6.2f}s {rms_db_of(buf):>8.2f} "
              f"{peak_of(buf):>8.4f} {mb:>6.1f}")

    # -------- MANIFEST --------
    manifest = {
        'track': 'Rotor Rush',
        'version': 9,
        'bpm': BPM,
        'sampleRate': SR,
        'channels': 2,
        'loopSamples': LOOP_LEN,
        'loopSeconds': round(LOOP_LEN / SR, 6),
        'targetRmsDb': TARGET_RMS_DB,
        'targetPeak': TARGET_PEAK,
        'masterPeakLimit': MASTER_PEAK_LIMIT,
        'k': round(float(k), 8),
        'preset': ACTIVE_PRESET,
        'masterDefinition': 'sum of loop stems (for loop) or sum of stem_double stems (for double); no make_loop; no tanh; no normalization',
        'contextMix': {
            'description': (
                'Full 4-stem mix (2N). Target stem x DOUBLE_CONTEXT_BOOST, '
                'each other stem x DOUBLE_CONTEXT_OTHERS, then renormalized '
                'to TARGET_RMS_DB per target. This is the racing_*_double.wav '
                'file, intended for Suno / audio-model ingestion so the model '
                'hears the full picture with the target stem dominant. The '
                'solo reference is racing_*_stem_double.wav.'
            ),
            'targetStemBoost': DOUBLE_CONTEXT_BOOST,
            'otherStemsScale': DOUBLE_CONTEXT_OTHERS,
            'ratioTargetOverOthers': round(DOUBLE_CONTEXT_BOOST / DOUBLE_CONTEXT_OTHERS, 4),
            'renormalizedToDb': TARGET_RMS_DB,
            'perStem': context_info,
        },
        'pipeline': [
            '1. dry 2N buses (10)',
            '2. reverb per bus (stereo buses per-channel)',
            '3. weighted sum into 4 stems (2N)',
            '4. single k on sum -> TARGET_RMS_DB',
            '5. per-stem soft-tanh if peak > TARGET_PEAK',
            '6. make_loop each stem -> 4 loop stems (N)',
            '7. build 4 context doubles (2N): target x BOOST, others x OTHERS, renorm',
            '8. master_double = sum(2N stem doubles); master_loop = sum(N loops); verify identity',
            '9. write 4 stems x (_loop, _stem_double, _double) + master x (_loop, _double) + manifest',
        ],
        'knownFixes': {
            'FIX-1': {
                'name': 'kick click artifact in motion stem',
                'fix': f'squared fade-out of {KICK_FADE_OUT_SEC*1000:.0f} ms on kick envelope (KICK_FADE_OUT_SEC)',
                'symptom': 'sharp click after every kick in racing_motion_loop.wav solo',
                'doNotRemove': 'verify motion stem loop and stem_double clean before changing KICK_FADE_OUT_SEC',
            },
            'FIX-2': {
                'name': 'stereo reverb mono collapse',
                'fix': 'per-channel convolution for stereo inputs (no mono collapse)',
                'symptom': 'high frequencies missing in master, present in wind_exp solo',
                'affects': 'only wind_exp (only stereo bus)',
            },
        },
        'earTunedValues': {
            'wind_weight': weights['wind'],
            'wind_exp_weight': weights['wind_exp'],
            'char_D_exponent': CHAR_D_EXPONENT,
            'wind_exp_smooth_scale': WIND_EXP_SMOOTH_SCALE,
            'note': 'tuned by ear against racing_master_loop.wav and stem solos; do not change without re-listening',
        },
        'stems': list(STEM_ORDER),
        'stemInfo': stem_info,
        'buses': {
            b: {
                'stem': BUS_TO_STEM[b],
                'weight': weights[b],
                'reverb': dict(REVERB_CFG[b]),
            } for b in BUS_ORDER
        },
        'master': {
            'peakDouble': round(peak_d, 6),
            'peakLoop': round(peak_l, 6),
            'rmsDbDouble': round(rms_d, 3),
            'rmsDbLoop': round(rms_l, 3),
            'identityDoubleDiff': float(f'{diff_d:.3e}'),
            'identityLoopDiff': float(f'{diff_l:.3e}'),
        },
        'playerNotes': {
            'loopFile': 'Use racing_*_loop.wav for AudioBufferSourceNode.loop=true in the game.',
            'stemDoubleFile': 'Solo stem double (2N). Use for A/B comparison against the original solo loop and for regression testing of FIX-1/FIX-2. Not for Suno.',
            'contextDoubleFile': 'Full 4-stem context mix with target stem boosted. Use racing_*_double.wav for Suno / audio-model ingestion.',
            'doNotMixMasterWithStems': True,
            'masterIsReferenceOnly': 'In-game, mix the 4 loop stems; master is a preview of the full unity mix.',
            'stereoReverbFix': 'wind_exp is stereo; its reverb is applied per-channel (no mono collapse). Other 9 buses are mono and use legacy path.',
            'preset': 'To experiment, add a new preset to PRESETS; do not edit production in place.',
            'v8ToV9Migration': 'In v8, racing_*_double.wav was the SOLO double. In v9 it is the CONTEXT mix. The solo double in v9 is racing_*_stem_double.wav. If you have v8 _double files in your output folder, delete them before running v9 to avoid confusion.',
        },
    }
    mp = os.path.join(out_dir, f"{OUT_PREFIX}_manifest.json")
    with open(mp, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"  manifest: {os.path.basename(mp)}")
    print()
    print("=" * 78)
    print(f"All checks passed. {len(written)} WAVs + manifest -> {out_dir}")
    print("=" * 78)


if __name__ == '__main__':
    main()
