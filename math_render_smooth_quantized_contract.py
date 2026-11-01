"""
smooth_quantized(x, filter_size, target_amp, levels=64) -> ndarray

Smooths x over filter_size samples, scales peak to target_amp,
quantizes to 1/levels steps. Output same length as x.
"""

from math_render_smooth_quantized_impl import smooth_quantized
