# TODO

Waveform families and transforms worth adding. The bar: a shape earns a place
only if the wavetable position axis does something musical with it. Ordered by
payoff for effort.

## Wanted

- **`--fm RATIO`** - single-cycle FM: `sin(2*pi*x + I*sin(2*pi*k*x))`, sweep
  the index `I` from 0 to ~8. The DX brightness envelope frozen into a table;
  `k` picks the flavor: 1 brassy, 2 hollow, 3 metallic. A phase offset on the
  modulator (`--fmbias`) breaks symmetry for even harmonics. Cheap, huge
  range, and unlike pow/rc the centroid genuinely travels.
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

Do NOT split wtcurve.py yet: the pain of recent features was multi-site
registration, not file length, and that was fixed in place. Revisit when
another family lands or the file crosses ~850 lines (730 as of 2026-09-07,
pylint ceiling 1000);
the seams then are `wtdsp.py` (constants, frame families, static shapers)
and `wtplot.py` (graph/graph3d/gif), with WtCurve staying in wtcurve.py as
the entry point. The morph engine and the naming are the orchestration -
they do not move.

`test_wtcurve.py` (unittest, `python -m pytest test_wtcurve.py`) covers the
regressions fixed so far: silence at zero harmonics, periodic smoothing,
implicit curve families and their anchors, tanh stability. Every new family
or shaper should add a case there. CI still runs only pylint; adding the
tests to the workflow is the next cheap win.

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
