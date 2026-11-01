"""
Instrument contract.
Import these, do not reimplement.

Return: MONO np.ndarray, float64, 1-D.
shape=(int(round(dur*SR)),), SR = render rate.
Peak abs <= amp for tonal (kick, reese, sub_long, arp_pulse, pad_note);
up to ~3*amp for noise-based (snare, snare_short, hat, open_hat, riser).
Not clipped, self-enveloped.
Mono only; stereo lives in composer.
Uses np.random (global): seed before call.
  [rng] = uses np.random, needs seed.
  Unmarked = deterministic.
Constraints: no I/O, no print, no globals.
Section-agnostic.
"""

# fmt: off
# isort: off
from instruments_render_mono_impl import (

# kick(dur=0.22, amp=0.9)   [rng]
# pitch-drop sine + click, 30 ms fade (FIX-1)
kick,

# snare(dur=0.18, amp=0.55)   [rng]
# band-passed noise + 190 Hz body
snare,

# snare_short(dur=0.08, amp=0.4)   [rng]
# short band-passed noise for rolls
snare_short,

# hat(dur=0.04, amp=0.08)   [rng]
# high-passed noise, very short
hat,

# open_hat(dur=0.15, amp=0.07)   [rng]
# high-passed noise, longer decay
open_hat,

# riser(dur, amp=0.10)   [rng]
# noise + rising 200->2500 Hz tone
riser,

# reese(freq, dur, amp=0.45)
# detuned saw + sub, LP, soft-clip
reese,

# sub_long(freq, dur, amp=0.4)
# sine + 2nd harmonic at 0.15
sub_long,

# arp_pulse(freq, dur, amp=0.06)
# 25% pulse, LP, sharp decay
arp_pulse,

# pad_note(freqs, dur, amp=0.05, lp_cutoff=1000)
# detuned saws, LP at lp_cutoff
pad_note,

)
# fmt: on
# isort: on