"""
Engine: generic, track-agnostic DSP and pipeline helpers.

Nothing in this module knows about any particular track. It does not
import from track_*. Everything it needs about timing, sample rate, or
loop length is passed in as a parameter.

Used by the composer (generate_wav_files.py), which owns the pipeline
and knows which track to render. Eventually render_track() will live
here too; for now only the leaf helpers do.
"""

import numpy as np
from scipy import signal


def peak_of(x):
    return float(np.max(np.abs(x)))


def rms_db_of(x):
    rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
    return 20.0 * np.log10(rms + 1e-12)


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


def make_loop(buf_2N, loop_len):
    A = buf_2N[:loop_len]
    B = buf_2N[loop_len:loop_len * 2]
    x = np.linspace(0, 1, loop_len)
    if buf_2N.ndim == 2:
        x = x[:, None]
    return B * (1 - x) + A * x


def make_ir_stereo(dur, decay, hp, lp, seed, sr):
    n = max(2, int(dur * sr))
    t = np.arange(n) / sr
    rng = np.random.RandomState(seed)
    ir_L = rng.randn(n) * np.exp(-t * decay)
    ir_R = rng.randn(n) * np.exp(-t * decay)
    b, a = signal.butter(2, hp / (sr / 2), btype='high')
    ir_L = signal.lfilter(b, a, ir_L); ir_R = signal.lfilter(b, a, ir_R)
    b, a = signal.butter(2, lp / (sr / 2), btype='low')
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


def sidechain_duck(target, trigger, amount, sr, release=0.04):
    trig = np.abs(trigger)
    kl = int(release * sr)
    if kl < 2:
        return target
    kernel = np.exp(-np.arange(kl) / (kl / 3))
    kernel /= kernel.sum()
    trig = np.convolve(trig, kernel, mode='same')
    peak = trig.max()
    if peak > 1e-9:
        trig /= peak
    return target * (1 - amount * trig)
