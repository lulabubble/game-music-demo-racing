"""
Instrument contract.
Import these, do not reimplement.

Return: MONO np.ndarray, float64, 1-D.
shape=(int(round(dur*SR)),), SR = render rate.
Values ~[-amp, +amp], not clipped, self-enveloped.
Mono only; stereo lives in composer.
Uses np.random (global): seed before call.
  [rng] = uses np.random, needs seed.
  Unmarked = deterministic.
Constraints: no I/O, no print, no globals.
Section-agnostic.
"""

# kick(dur=0.22, amp=0.9)   [rng]
# pitch-drop sine + click, 30 ms fade (FIX-1)
from instruments_render_mono_impl import kick

# snare(dur=0.18, amp=0.55)   [rng]
# band-passed noise + 190 Hz body
from instruments_render_mono_impl import snare

# snare_short(dur=0.08, amp=0.4)   [rng]
# short band-passed noise for rolls
from instruments_render_mono_impl import snare_short

# hat(dur=0.04, amp=0.08)   [rng]
# high-passed noise, very short
from instruments_render_mono_impl import hat

# open_hat(dur=0.15, amp=0.07)   [rng]
# high-passed noise, longer decay
from instruments_render_mono_impl import open_hat

# riser(dur, amp=0.10)   [rng]
# noise + rising 200->2500 Hz tone
from instruments_render_mono_impl import riser

# reese(freq, dur, amp=0.45)
# detuned saw + sub, LP, soft-clip
from instruments_render_mono_impl import reese

# sub_long(freq, dur, amp=0.4)
# sine + 2nd harmonic at 0.15
from instruments_render_mono_impl import sub_long

# arp_pulse(freq, dur, amp=0.06)
# 25% pulse, LP, sharp decay
from instruments_render_mono_impl import arp_pulse

# pad_note(freqs, dur, amp=0.05, lp_cutoff=1000)
# detuned saws, LP at lp_cutoff
from instruments_render_mono_impl import pad_note
