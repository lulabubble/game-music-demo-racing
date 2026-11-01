"""
Track: Rotor Rush — first demo.

Track-specific data only: rhythm, loudness policy, presets, reverb,
bus routing, harmony. Anything that could plausibly differ between two
tracks lives here.

Project-wide constants (SR, output paths) stay in generate_wav_files.py.
Derived values (BEAT, BAR, LOOP_LEN, BUFFER_LEN) are computed there too,
from these primitives.
"""

# Rhythm
BPM  = 174.0
BARS = 32
SEED = 11

# Output filename prefix
OUT_PREFIX = 'racing'

# Loudness / peak policy
TARGET_RMS_DB     = -18.0
TARGET_PEAK       = 0.92
MASTER_PEAK_LIMIT = 0.98

# Context double balance (v9)
DOUBLE_CONTEXT_BOOST  = 3.00
DOUBLE_CONTEXT_OTHERS = 0.33

# Kick fade-out (FIX-1)
KICK_FADE_OUT_SEC = 0.030

# wind_exp tuning
WIND_EXP_SMOOTH_SCALE = 0.05
WIND_EXP_FINAL_SCALE  = 0.028 * 2
WIND_EXP_QUANT_STEPS  = 64
CHAR_D_EXPONENT       = 1.5

# Presets - named so manifest records which values were used
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

# Reverb config per bus
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

# Bus -> stem mapping
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

# Harmony
CHORDS = {
    'Dm': {'root': 38, 'tones': [62, 65, 69]},
    'Bb': {'root': 34, 'tones': [58, 62, 65]},
    'F':  {'root': 41, 'tones': [65, 69, 72]},
    'C':  {'root': 36, 'tones': [60, 64, 67]},
}
PROG = ['Dm', 'Bb', 'F', 'C']
