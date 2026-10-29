# Suno Context Doubles — Style Prompt Notes

Internal working notes on writing Suno Style prompts for context doubles
(audio-model ingestion mixes of a single stem boosted against the other three).

---

## 1. Purpose and Scope

This document records what we learned about writing Style prompts for Suno when
the goal is to make one stem of a multi-stem track sound dominant, while the
other three stems remain audible as background texture.

In scope:
- how to phrase the front line, the attenuation, and the structure so Suno
  respects them;
- known failure modes and their fixes;
- a checklist for new stems.

Out of scope:
- technical generation of the WAV files (that lives in the Python script);
- mixing, mastering, loudness policy;
- Suno account settings, model versions, or UI beyond Custom Mode and
  Instrumental toggle.

---

## 2. What We Built (brief)

A single track ("Rotor Rush", neurofunk, 174 BPM, D minor, 32-bar loop repeated
twice) is split into four stems. For audio-model ingestion we build one
"context double" per stem: the target stem is boosted, each other stem is
attenuated, and the sum is renormalized.

| Stem         | Front line (target)                      | Type of front line       |
|--------------|------------------------------------------|--------------------------|
| air          | detuned saw pad + mono filtered wind bed | soft                     |
| motion       | pitch-dropping kick + alternating hats   | hard, no low end         |
| acceleration | Reese bass + sine sub + pulse arpeggio   | hard, low-end heavy      |
| danger       | 2-step snare + stereo wind + FX risers   | hard, transient-heavy    |

Context double balance (in the script, not in the prompt):
- target stem multiplied by 3.0 (+9.5 dB);
- each other stem multiplied by 0.33 (-9.5 dB);
- ratio target / others = 9.09x, about +19.2 dB;
- result renormalized to -18 dBFS RMS.

So the number that appears in Style prompts is **19 dB below the front line**.
That number is derived from the script and must match it.

---

## 3. Workflow

1. Custom Mode in Suno. Instrumental toggle ON.
2. Paste Title, Style, Lyrics (Lyrics carries the per-bar production notes).
3. Run 3–4 generations with the same prompt.
4. Listen and pick the best take.
5. Copy the Style **that Suno itself produced** for the winning take, not the
   one we wrote. Suno sometimes rewrites Style internally; the rewritten version
   is the one that actually worked.
6. Compare that Style against the current one, note what changed, and decide
   whether to adopt the change as canon.

Step 5 is the most important habit. The most reliable Styles in this project
came from copying Suno's own rewrite of a successful generation, then merging
verified phrases from another successful variant.

---

## 4. Findings per Stem

| Stem         | Main risk                                              | What worked                                                                 | What did not work                                              |
|--------------|--------------------------------------------------------|------------------------------------------------------------------------------|----------------------------------------------------------------|
| danger       | Suno rebalances the mix back to even levels            | `front line at 0 dB`, per-instrument `attenuated`, `leads over`              | Abstract `heavily attenuated` without a number                 |
| acceleration | Suno pulls the kick and snare forward                  | `X at 0 dB:` with a colon, then a list, then `all 19 dB below`              | Numbers placed at the start of a sentence, far from the list   |
| air          | Suno drifts into ambient; pad becomes static           | `front-line detuned dual-saw pad`, `section-by-section low-pass movement`  | `dry sharp gates` combined with a soft front line              |
| motion       | Suno strips the low end and turns it into a drum solo  | `hold weight beneath`, `as an audible felt presence`, `still a bass-driven track, not a drum solo` | Front line named without any low-end guard                     |

Across all four stems, the following held true:
- genre, tempo, key, and `instrumental` in the first tokens are stronger than
  the same information anywhere later in the prompt;
- a number (`19 dB`) alone is read as "moderately quieter"; the number plus a
  behavior phrase is read as intended;
- `front-line X` as an adjective is stronger than `X at the front`;
- structure (`two identical 32-bar passes, seamless repeat, hard cut at bar 64`)
  works best when placed in the first half of the prompt, not at the end.

---

## 5. Formulation Lexicon

### Works

- `front-line <instrument>` as an adjective.
  Example: `front-line pitch-dropping kick and alternating hats`.
  Stronger than `kick and hats at the front`.

- `<instrument> at 0 dB:` followed by a list, then `all 19 dB below`.
  Example: `Reese bass at 0 dB: detuned dual-saw, low-pass 600 Hz... Pitch-dropping
  kick, hats, snare: all 19 dB below.`
  The colon binds the list into one group; Suno cannot lose the attenuation.

- `as an audible felt presence` attached directly to a dB figure.
  Example: `every other element 19 dB below as an audible felt presence`.
  Prevents Suno from interpreting the number as "remove completely".

- `hold weight beneath <element>`.
  Example: `Reese bass and sine sub hold weight beneath the syncopated kicks`.
  The single most effective guard for stems whose front line contains no bass.

- `still a bass-driven drum and bass track, not a drum solo`.
  Genre guard for motion-like stems. Add when the front line is kick and hats.

- `section-by-section low-pass movement` plus explicit values if needed.
  Example: `low-pass opens 800 Hz in intro, 1600 Hz in main, closes to 700 Hz in
  turnaround, opens to 1100 Hz in lift`.
  `section-by-section` alone is often ignored; explicit values are respected.

- `two identical 32-bar passes, seamless repeat, hard cut at bar 64`.
  All three structural facts in one clause. Placing this early in the prompt
  gives better structure than placing it last.

- `open hats 150 ms on the "and" of 4`.
  Timing beats description. Without the timing, Suno often flattens hats into
  even 16ths.

- `syncopated on beats 1, 2.5 and 3.5`.
  Numbers beat the word `syncopated`. Without positions, Suno picks its own
  syncopation.

### Does not work

- `heavily attenuated` without a number.
  Suno reads it as "somewhat quieter" and often returns a near-balanced mix.

- A bare `19 dB below` with no behavior phrase.
  Suno may interpret it as "quiet but present at a moderate level", not as
  "ghost texture". Pair it with `as an audible felt presence` or with a
  per-instrument behavior word (`distant`, `near-silent`, `ghost`).

- `dry sharp gates` combined with a soft front line (air).
  Contradicts the nature of pad and wind. Suno either hardens them, losing the
  air character, or drifts into ambient, losing the genre. For soft stems,
  drop `dry/gated` and use `section-by-section` plus behavioral descriptors.

- Genre, tempo, and key placed after the instrument list.
  They get weaker weight. Always first tokens.

- `instrumental` as the last word.
  Usually fine for neurofunk, but risky for other genres. Put it in the first
  clause.

---

## 6. Failure Modes and Fixes

| Symptom                                                     | Likely cause                                                  | Fix                                                                 |
|-------------------------------------------------------------|---------------------------------------------------------------|---------------------------------------------------------------------|
| Suno returns a near-balanced mix                            | `19 dB` read as "moderately quieter"                          | add `as an audible felt presence`; or replace the number with behavior (`felt, not heard`) |
| Bass disappears, track sounds like drums only               | front line has no low end and no low-end guard                | add `hold weight beneath` and `still a bass-driven track, not a drum solo` |
| Track drifts into ambient                                   | `dry sharp gates` conflicting with a soft front line          | remove `dry/gated`; add `section-by-section`; keep pad and wind named as front line |
| Pad is static from start to end                             | `section-by-section` ignored                                  | spell out all filter values explicitly per section                  |
| Kick is even, no syncopation                                | `syncopated` without positions                                | add `syncopated on beats 1, 2.5 and 3.5`                            |
| Hats are flat 16ths, open hat missing                       | open hat mentioned without timing                             | add `open hats 150 ms on the "and" of 4`                            |
| Suno adds a final chord or fade                             | no loop guard                                                 | end Lyrics with `[Cut at bar 64, no resolution, loop back]`         |
| Repeat is shortened or varied                               | `the pass repeats` instead of `two identical passes`          | use `two identical 32-bar passes, seamless repeat`                  |
| Tempo drifts to 165 or 180                                  | tempo not in first tokens                                     | put `driving 174 BPM in D minor` immediately after the genre        |
| Snare becomes a full backbeat instead of a ghost             | `ghost` read as "with reverb"                                 | use `ghost 2-step snare on 2 and 4, distant snap, not a backbeat`   |

---

## 7. Checklist for New Stems

Before sending a Style to Suno, confirm all of the following:

- [ ] Genre, tempo, key, and `instrumental` appear in the first clause.
- [ ] Front line is named explicitly, using `front-line <instrument>`.
- [ ] Attenuation uses a number **and** a behavior phrase together.
- [ ] If the front line contains no bass, `hold weight beneath` is present.
- [ ] If the front line is soft (pad, wind), `dry/gated` is removed and
      `section-by-section` is present.
- [ ] Syncopated or timed elements carry explicit beat positions or durations.
- [ ] `two identical 32-bar passes, seamless repeat, hard cut at bar 64` is
      present, ideally in the first half.
- [ ] Lyrics end with a loop guard (`[Cut at bar 64, no resolution]`).
- [ ] No game names, no project names, no story context. Only what is audible.

---

## 8. Open Questions and Next Experiments

- Is the number in `19 dB below` read literally? We have only tested at -19 dB.
  Testing -12 dB and -25 dB would show whether Suno scales the attenuation or
  treats any number as "quiet".

- Does `hold weight beneath` work outside drum and bass? For Pixel Sprint
  (chiptune, front line = kick + arp) it should be tested; for Quiet Ward
  (ambient, soft front line) it is probably irrelevant.

- Is `section-by-section` needed for hard stems, or only for soft ones? So far
  it appeared only in air. Test on motion to see whether it adds value there.

- Can one Style cover two stems at once (for example motion and acceleration
  together), or does each stem require its own prompt? If the former works,
  the total number of generations drops sharply.

- Does Suno's internal Style rewrite converge when the same prompt is run
  repeatedly, or does it drift? Tracking the copied Styles across 10 generations
  would answer this.

---

## 9. Appendix: Successful Styles (verbatim)

These are the Style strings that produced the best takes, copied from Suno's
own output after generation. Use them as the starting point for the same stem,
and as reference for phrasing new stems.

### 9.1 danger

    Neurofunk / techstep drum and bass, driving 174 BPM in D minor; instrumental,
    dry sharply gated snare-forward mix — tight beat-2-and-4 snare with 190 Hz
    body, band-passed noise and 180 ms tail leads over a stereo distorted
    filtered wind bed and 4-bar reverb-heavy riser sweeps; continuous wind bed
    shifts from soft overdrive to cubic to arctanh distortion by section;
    attenuated kick, alternating 16th hats, detuned low-passed Reese bass,
    sustained sine sub, 25%-duty pulse arpeggio and slowly opening detuned saw
    pad all sit 19 dB below the front line as ghost texture; two identical
    32-bar passes, seamless repeat, open D minor, hard cut at bar 64.

### 9.2 acceleration

    Neurofunk / techstep drum and bass, driving 174 BPM in D minor; Reese bass
    at 0 dB: detuned dual-saw ±0.5%, low-pass 600 Hz, tanh saturation, bar-length
    hit on beat 1 and second hit on the and of 3 in the drop; sustained sine sub
    with 15% octave harmonic at 95% bar length; 25%-duty pulse-wave arpeggio on
    16ths, low-pass 4.5 kHz. Pitch-dropping kick, alternating hats, distant
    2-step snare, filtered wind, slowly opening pad, 4-bar risers: all 19 dB
    below. Dry, sharply gated, bass-forward mix; two identical 32-bar passes,
    seamless repeat, open D minor, hard cut at bar 64; instrumental.

### 9.3 air

    Neurofunk / techstep drum and bass, instrumental, driving 174 BPM in
    D minor; dry sharp gates, pad and mono filtered wind bed at the front with
    all other elements 19 dB below. Detuned dual-saw pad with 300 ms attack and
    section-by-section low-pass movement; continuous mono wind bed with soft
    overdrive and slow drift. Distant Reese buzz, near-silent sine sub, faint
    pulse-wave arpeggio, barely audible pitch-dropping kick, distant 2-step
    snare, ticking hats, ghost stereo distorted wind, distant reverb-heavy
    riser sweeps. Two identical 32-bar passes, seamless repeat, hard cut at
    bar 64.

### 9.4 motion

    Neurofunk / techstep drum and bass, driving 174 BPM in D minor; dry sharp
    gates, with kick and hats at 0 dB and every other element 19 dB below as an
    audible felt presence; two identical 32-bar passes, seamless repeat, hard
    cut at bar 64. Punchy kick pitches 90→45 Hz with a 2–5 kHz click and 30 ms
    squared fade; open hats on the "and" of 4; Reese bass and sine sub hold
    weight beneath syncopated kicks, ghost 2-step snare, faint arpeggio, thin
    stereo wind, soft pad and distant risers; instrumental.

---

## 10. Anti-patterns (verbatim, do not reuse)

Kept only as a reminder of what fails and why. Do not copy into Suno.

### 10.1 air, first attempt

    Neurofunk / techstep drum and bass, instrumental; dry, sharply gated
    bass-forward mix, front line at 0 dB, other elements attenuated by 19 dB,
    two identical 32-bar passes with a hard cut at bar 64; driving 174 BPM,
    open on D minor; detuned dual-saw Reese bass ...

Why it failed: the front line was never named, so Suno chose its own (the
Reese bass). The attenuation was placed before the list, so Suno applied it
loosely. `dry, sharply gated` reinforced the wrong direction for a soft stem.

### 10.2 motion, first attempt

    Neurofunk / techstep drum and bass with front-line pitch-dropping kick and
    alternating sharp-gated hats, distant Reese buzz, near-silent sine sub,
    faint pulse-wave arpeggio, ghost 2-step snare, filtered wind, detuned saw
    pad, and distant reverb-heavy riser sweeps; driving 174 BPM in D minor,
    tightly controlled levels with all supporting elements 19 dB below kick and
    hats, two identical 32-bar passes with seamless repeat, hard cut at bar 64,
    harmony left open.

Why it failed: no low-end guard. The front line (kick and hats) contains no
bass, and nothing told Suno to keep the low end audible, so it stripped it and
the result read as a drum solo rather than as drum and bass.
