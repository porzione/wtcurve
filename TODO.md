# TODO

Waveform families and transforms worth adding. The bar: a shape earns a place
only if the wavetable position axis does something musical with it. Ordered by
payoff for effort.

## In progress

- **`--fold GAIN` / `--foldbias BIAS`** - triangle wavefolder, the west coast
  timbre control. A sine driven into the fold at growing gain adds harmonics
  the characteristic non-monotonic way (partials rise and fall as folds pass
  through); the bias breaks the symmetry and manufactures even harmonics,
  same pattern as `--sat`/`--satbias`. Needs a still sine carrier (`--sine`),
  which is independently useful under `--neg`, `--sat` and `--harmonics`.

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
- **Vowel formants** (`--vowel aeiou`) - build the spectrum directly: a `1/k`
  source series times two or three Gaussian formant bumps, irfft back; the
  morph interpolates formant frequencies between vowels across the table.
  Needs a vowel formant table and a sequence parser; the frame math is just
  shaped magnitudes.
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

## Parked

- Duplicate join samples in `_curve_frame` (curve end and middle line start
  share an x): two one-sample flat spots per frame, inaudible. Fixing it
  changes every curve-family output byte-wise, so only worth folding into
  some future change that reshapes the frame anyway.
