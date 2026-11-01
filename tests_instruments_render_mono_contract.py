"""Tests for the instrument contract.

Imports ONLY from the contract, never from _impl.
Verifies the contract's promises, not the implementation details.
SR is hardcoded here; will import from config later.
"""
import unittest
import numpy as np

from instruments_render_mono_contract import (
    kick, snare, snare_short, hat, open_hat, riser,
    reese, sub_long, arp_pulse, pad_note,
)

SR = 44100  # hardcoded until config exists

# (name, factory, expected_dur_sec, expected_amp)
CASES = [
    ('kick',        lambda: kick(),                                    0.22, 0.90),
    ('snare',       lambda: snare(),                                   0.18, 0.55),
    ('snare_short', lambda: snare_short(),                             0.08, 0.40),
    ('hat',         lambda: hat(),                                     0.04, 0.08),
    ('open_hat',    lambda: open_hat(),                                0.15, 0.07),
    ('riser',       lambda: riser(1.0),                                1.00, 0.10),
    ('reese',       lambda: reese(55.0, 0.5),                          0.50, 0.45),
    ('sub_long',    lambda: sub_long(55.0, 0.5),                       0.50, 0.40),
    ('arp_pulse',   lambda: arp_pulse(440.0, 0.1),                     0.10, 0.06),
    ('pad_note',    lambda: pad_note([220.0, 277.18, 329.63], 1.0),    1.00, 0.05),
]

# Instruments that use np.random; others must be deterministic.
RNG_NAMES = {'kick', 'snare', 'snare_short', 'hat', 'open_hat', 'riser'}


class TestShapeAndDtype(unittest.TestCase):
    def test_returns_ndarray(self):
        for name, factory, _, _ in CASES:
            with self.subTest(name=name):
                self.assertIsInstance(factory(), np.ndarray)

    def test_dtype_float64(self):
        for name, factory, _, _ in CASES:
            with self.subTest(name=name):
                self.assertEqual(factory().dtype, np.float64)

    def test_mono_1d(self):
        for name, factory, _, _ in CASES:
            with self.subTest(name=name):
                self.assertEqual(factory().ndim, 1)

    def test_shape_matches_dur(self):
        for name, factory, dur, _ in CASES:
            with self.subTest(name=name):
                expected = int(round(dur * SR))
                self.assertEqual(factory().shape, (expected,))


class TestValues(unittest.TestCase):
    def test_finite(self):
        for name, factory, _, _ in CASES:
            with self.subTest(name=name):
                buf = factory()
                self.assertTrue(np.all(np.isfinite(buf)), f"{name} has NaN/Inf")

    def test_peak_around_amp(self):
        # peak abs should be <= amp * 3.0 (noise-based instruments overshoot more)
        # and > amp * 0.1 (not silent)
        for name, factory, _, amp in CASES:
            with self.subTest(name=name):
                peak = float(np.max(np.abs(factory())))
                self.assertLessEqual(peak, amp * 3.0,
                                     f"{name} peak {peak:.4f} > {amp*3.0:.4f}")
                self.assertGreater(peak, amp * 0.1,
                                   f"{name} peak {peak:.4f} too quiet")

    def test_not_hard_clipped(self):
        # exactly ±1.0 everywhere would mean clipping; check not all at 1.0
        for name, factory, _, _ in CASES:
            with self.subTest(name=name):
                buf = factory()
                at_one = int(np.sum(np.abs(buf) >= 0.999))
                self.assertLess(at_one, len(buf) // 10,
                                f"{name}: {at_one}/{len(buf)} samples at ±1.0")


class TestDeterminism(unittest.TestCase):
    def test_deterministic_instruments(self):
        for name, factory, _, _ in CASES:
            if name in RNG_NAMES:
                continue
            with self.subTest(name=name):
                np.random.seed(123)
                a = factory()
                np.random.seed(123)
                b = factory()
                np.testing.assert_array_equal(a, b)

    def test_rng_instruments_reproducible_with_same_seed(self):
        for name, factory, _, _ in CASES:
            if name not in RNG_NAMES:
                continue
            with self.subTest(name=name):
                np.random.seed(42)
                a = factory()
                np.random.seed(42)
                b = factory()
                np.testing.assert_array_equal(
                    a, b, f"{name} not reproducible with same seed"
                )

    def test_rng_instruments_differ_with_different_seed(self):
        for name, factory, _, _ in CASES:
            if name not in RNG_NAMES:
                continue
            with self.subTest(name=name):
                np.random.seed(1)
                a = factory()
                np.random.seed(2)
                b = factory()
                self.assertFalse(np.array_equal(a, b),
                                 f"{name} identical under different seeds")


class TestLongDurationStability(unittest.TestCase):
    def test_pad_note_1s_stable(self):
        np.random.seed(7)
        buf = pad_note([220.0, 277.18, 329.63], 1.0)
        self.assertTrue(np.all(np.isfinite(buf)))
        self.assertLessEqual(float(np.max(np.abs(buf))), 0.05 * 3.0)

    def test_riser_2s_stable(self):
        np.random.seed(7)
        buf = riser(2.0)
        self.assertTrue(np.all(np.isfinite(buf)))
        self.assertLessEqual(float(np.max(np.abs(buf))), 0.10 * 3.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
