"""Smooth, scale to target peak, quantize."""
import numpy as np


def smooth_quantized(
    x, filter_size, target_amp, levels=64
):
    k = np.ones(filter_size, dtype=np.float64)
    k = k / filter_size
    s = np.convolve(x, k, mode='same')
    peak = np.max(np.abs(s)) + 1e-9
    s = s / peak * target_amp
    return np.round(s * levels) / levels
