# TODO

Waveform families and transforms worth adding. The bar: a shape earns a place
only if the wavetable position axis does something musical with it. Ordered by
payoff for effort.

## Done

- **`--fold GAIN` / `--foldbias BIAS`** - triangle wavefolder, the west coast
  timbre control. A sine driven into the fold at growing gain adds harmonics
  the characteristic non-monotonic way (partials rise and fall as folds pass
  through); the bias breaks the symmetry and manufactures even harmonics,
  same pattern as `--sat`/`--satbias`. Shipped with the still sine carrier
  `--sine`, which is independently useful under `--neg`, `--sat` and
  `--harmonics`. Measured: `--sine --fold 3 --morph fold,1,6` moves the
  centroid 4.2 octaves; bias 0.5 at fold 3 takes even-to-odd from 0 to 0.73.
- **`--vowel SEQ`** - vowel formant wavetable: a `1/k` glottal source shaped
  by five Gaussian formant bumps, the CSound manual tenor set, interpolated
  across the sequence; formants map onto harmonics of a 110 Hz reference.
  Measured: the `a` frame peaks on harmonics 6 and 10 (650/1080 Hz), vowel
  pairs sit 10-18 dB RMS apart in log spectrum, `aeiou` drifts 4.2 dB RMS.

## Next

- **`--fm RATIO`** - single-cycle FM: `sin(2*pi*x + I*sin(2*pi*k*x))`, sweep
  the index `I` from 0 to ~8. The DX brightness envelope frozen into a table;
  `k` picks the flavor: 1 brassy, 2 hollow, 3 metallic. A phase offset on the
  modulator (`--fmbias`) breaks symmetry for even harmonics. Cheap, huge
  range, and unlike pow/rc the centroid genuinely travels.

## Later

- **Windowed sync / CZ resonance** (`--saw reso` or own family) - a cosine at
  k times the frequency, amplitude-windowed by one descending ramp so the
  cycle stays continuous; sweep `k`, fractional allowed. Filter resonance
  sweep without a filter - the PPG/Casio trick, the sound wavetables are
  bought for. The window is a saw, so it fits the saw-family dispatch.
- **Even/odd balance** (`--even X`, morphable post-process) - scale the
  even-numbered harmonics in the spectrum (the rfft plumbing exists in
  `_band_limit`). At 0 a saw goes hollow and square-like, at 1 full series;
  clarinet to brass without touching the fundamental. Controls the even
  series exactly, where `--neg` does it as a side effect.
- **Spectral tilt** (`--tilt`, dB/oct, morphable) - multiply harmonic `k` by
  `k^(-slope)`. A smooth brightness axis: where the `--harmonics` sweep is an
  opening filter with a hard edge, tilt is a lamp dimmer, and it avoids the
  discrete steps at low harmonic counts.
- **`--blend famA:famB`** - generate two families and crossfade their
  magnitude spectra across the table. Each family already sits behind
  `frame_fn(t, num_samples)`, so a blend frame is two calls and an rfft mix;
  turns N families into N^2 tables (vowel to saw, fold to reso, ...).

## Ranked lower

- **Hard sync** (raw, unwindowed) - overlaps with reso but aliases worse and
  clicks at the wrap.
- **Chebyshev stacks** - exact per-harmonic control, but additive plus
  `--even`/`--tilt` cover it more intuitively.

## Structure

Decision from the 2026-08-30 four-angle review: do NOT split wtcurve.py yet.
The pain of recent features was multi-site registration, not file length,
and that was fixed in place (single family sentinel, OUTPUTS table, shared
`namespace_from`). Split when the second remaining family from this file
lands or wtcurve.py crosses ~850 lines (pylint ceiling is 1000), whichever
comes first. Boundaries then: `wtdsp.py` (constants, frame families, the
static shapers - pure code motion), `wtplot.py` (graph/graph3d/gif), while
`wtcurve.py` keeps its name and the WtCurve class since gen_n_tag.py
imports it and it is the entry point. Do not extract the morph engine or
the naming: they are the orchestration itself.

## Parked

- Duplicate join samples in `_curve_frame` (curve end and middle line start
  share an x): two one-sample flat spots per frame, inaudible. Fixing it
  changes every curve-family output byte-wise, so only worth folding into
  some future change that reshapes the frame anyway.
- Vectorizing `_bezier_curve`'s loop is ~200x faster but NOT bit-identical
  (numpy array `**2` vs scalar `pow` differ by 1 ulp on ~10 of 2048 points):
  needs a deliberate golden-file refresh, not a silent refactor.
- RIFF chunk unpackers are duplicated between wttag.py and wavchunks.py
  (same struct formats, same pad-byte fix twice). Sharing is blocked by
  wavchunks.py executing at import time - give it a main guard first.
- A shapers registry (flag + MORPHABLE entry + suffix tag in one row) only
  pays for itself when a sixth shaper lands (`--even` is the candidate);
  the apply order in `_post_process` must stay explicit either way.
