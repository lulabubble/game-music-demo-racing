"""
SFX functional mono noise wind contract.
Import these, do not reimplement.

Curves are element-wise: input np.ndarray (any shape)
-> output np.ndarray of the same shape and dtype.
No cross-sample mixing, no filtering, no state.
Output is not clipped unless
the curve itself is bounded.
No I/O, no print, no globals.
"""

# fmt: off
# isort: off
from sfx_functional_mono_noise_wind_impl import (

# soft(x)
# Bounded, smooth, monotone. Rounds peaks.
soft,

# aggressive(x, exponent=1.5)
# Unbounded, monotone.
# Widens gap between quiet and loud.
aggressive,

# extreme(x)
# Unbounded, monotone.
# Lifts detail, explodes near ±1.
extreme,

)
# fmt: on
# isort: on