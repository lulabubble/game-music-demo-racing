"""Instruments implementation (mono).
See instruments_render_mono_contract.py for the contract.
SR and KICK_FADE_OUT_SEC live here for now; move to config later.
"""
import numpy as np
from scipy import signal

SR = 44100
KICK_FADE_OUT_SEC = 0.030


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
