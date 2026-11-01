import numpy as np

def soft(x):
    """tanh(2x) * 0.7.
    Bounded ±0.7, smooth.
    """
    return np.tanh(x * 2.0) * 0.7


def aggressive(x, exponent=1.5):
    """x**3 * exponent.
    Unbounded, pushes loud/quiet apart.
    """
    return x ** 3 * exponent


def extreme(x):
    """arctanh(clip(x, ±0.999)) * 0.4.
    Unbounded, explodes at edges.
    """
    c = np.clip(x, -0.999, 0.999)
    return np.arctanh(c) * 0.40