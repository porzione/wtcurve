"""Regression checks for wavetable generation and export."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from wtcurve import WtCurve
from wtcurve_args import morph_spec, setup_parser
from wtfile import Wt


def curve(**options):
    """Build a small table without writing output files."""
    with contextlib.redirect_stdout(io.StringIO()):
        return WtCurve({'wav': True, 'num_waveforms': 5,
                        'num_samples': 128, **options})


def frames(table):
    """Generate using the table's configured dimensions."""
    # pylint: disable=protected-access
    return table._gen_waveforms(table.a.num_waveforms, table.a.num_samples)


class SilenceTests(unittest.TestCase):
    """Zero harmonics must remain silence through normalization and export."""

    def test_zero_harmonics_exports_silence(self):
        for family in ({'sine': True}, {'saw': 'ramp'}):
            for bitwidth in (16, 32):
                with self.subTest(family=family, bitwidth=bitwidth):
                    data = frames(curve(harmonics=0, rms=True, **family))
                    np.testing.assert_array_equal(data, np.zeros_like(data))
                    writer = Wt(data, bitwidth)
                    with tempfile.TemporaryDirectory() as directory:
                        wav = Path(directory) / 'silence.wav'
                        wt = Path(directory) / 'silence.wt'
                        writer.save_wav(wav)
                        writer.save_wt(wt)
                        samples, _ = sf.read(wav)
                        self.assertFalse(np.any(samples))
                        dtype = '<i2' if bitwidth == 16 else '<f4'
                        samples = np.frombuffer(wt.read_bytes(), dtype=dtype, offset=12)
                        self.assertFalse(np.any(samples))

    def test_rms_morph_preserves_silent_endpoint(self):
        data = frames(curve(saw='ramp', rms=True,
                            morph=[morph_spec('harmonics,0,4')]))
        self.assertFalse(np.any(data[0]))
        self.assertTrue(np.isfinite(data).all())
        rms = np.sqrt(np.mean(data[1:] ** 2, axis=1))
        np.testing.assert_allclose(rms, rms[0])


class MorphFamilyTests(unittest.TestCase):
    """Implicit selectors must activate the requested curve without an anchor."""

    def test_implicit_curve_matches_explicit_unanchored_curve(self):
        for name, dest, start, end in [('B', 'bezier', -7, 2), ('tanh', 'tanh', 1, 4)]:
            with self.subTest(name=name):
                spec = morph_spec(f'{name},{start},{end}')
                implicit = curve(morph=[spec])
                explicit = curve(morph=[spec], **{dest: end + 1})
                self.assertIsNone(implicit.morphs[0][3])
                np.testing.assert_allclose(frames(implicit), frames(explicit))
                self.assertFalse(np.allclose(frames(curve()), frames(implicit)))

    def test_conflicting_curve_morphs_fail(self):
        for options in [{'saw': 'ramp'}, {'sine': True}, {'vowel': 'a'},
                        {'dline': True}, {'bezier': 1}, {'exp': 5},
                        {'morph': [morph_spec('B,-7,2'), morph_spec('tanh,1,4')]}]:
            with self.subTest(options=options), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    curve(**{'morph': [morph_spec('tanh,1,4')], **options})
                self.assertEqual(error.exception.code, 2)

    def test_explicit_value_remains_the_midpoint_anchor(self):
        table = curve(tanh=2, morph=[morph_spec('tanh,1,4')])
        self.assertEqual(table.morphs[0][3], 2)
        np.testing.assert_allclose(frames(table)[2], frames(curve(tanh=2))[2])

    def test_default_exponent_does_not_anchor_its_morph(self):
        spec = morph_spec('e,2,9')
        implicit = curve(morph=[spec])
        self.assertIsNone(implicit.morphs[0][3])
        self.assertEqual(implicit.title.split(' e:')[0], 'Exponent morph')
        self.assertEqual(curve(exp=5, morph=[spec]).morphs[0][3], 5)
        # an unanchored sweep is not the same table as one anchored on 5
        self.assertFalse(np.allclose(frames(implicit), frames(curve(exp=5, morph=[spec]))))

    def test_cli_distinguishes_default_and_explicit_exponent(self):
        parser = setup_parser()
        options = vars(parser.parse_args(['--wav', '--morph', 'tanh,1,4']))
        self.assertEqual(WtCurve(options).curve_fn.__name__, '_tanh_curve')
        options = vars(parser.parse_args(['--wav', '-e', '5', '--morph', 'tanh,1,4']))
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            WtCurve(options)
        self.assertEqual(curve().a.exp, 5)


class TanhTests(unittest.TestCase):
    """Endpoint scaling must remain finite when tanh itself saturates."""

    def test_large_rates_are_finite_and_keep_endpoints(self):
        for rate in (40, -40, 1000, -1000, 1e6):
            for width in (0, 90, 100):
                with self.subTest(rate=rate, width=width), np.errstate(all='raise',
                                                                     under='ignore'):
                    data = frames(curve(tanh=rate, mid_width_pct=width,
                                        num_samples=2048, num_waveforms=256))
                    self.assertTrue(np.isfinite(data).all())
                    self.assertLessEqual(np.abs(data).max(), 1)
                    # At width 100 the last frame consists only of the middle line.
                    np.testing.assert_allclose(data[:-1, 0], -1)
                    np.testing.assert_allclose(data[:-1, -1], 1)

    def test_matches_direct_formula_at_ordinary_rates(self):
        for rate in (-4, -0.1, 0.1, 4):
            table = curve(tanh=rate)
            for start, end in ((-1, -0.9), (0.9, 1), (-1, 1)):
                with self.subTest(rate=rate, interval=(start, end)):
                    x = np.linspace(start, end, 128)
                    expected = -1 + 2 * ((np.tanh(rate * x) - np.tanh(rate * start))
                                        / (np.tanh(rate * end) - np.tanh(rate * start)))
                    actual = table._tanh_curve(start, -1, end, 1, 128)  # pylint: disable=protected-access
                    np.testing.assert_allclose(actual, expected, atol=1e-12)

    def test_zero_crossing_has_linear_middle_frame(self):
        data = frames(curve(tanh=0, morph=[morph_spec('tanh,-40,40')]))
        self.assertTrue(np.isfinite(data).all())
        np.testing.assert_allclose(data[2], frames(curve(dline=True))[2])


class SmoothingTests(unittest.TestCase):
    """Smoothing treats each frame as a repeating cycle."""

    def test_sine_stays_a_single_harmonic(self):
        for options in ({'gauss': 40}, {'savgol': (51, 3)}):
            with self.subTest(options=options):
                data = frames(curve(sine=True, num_samples=2048, **options))[0]
                spectrum = np.fft.rfft(data)
                self.assertLess(abs(spectrum[0]), 1e-9)
                self.assertLess(np.max(np.abs(spectrum[2:])), 1e-9)
                self.assertGreater(abs(spectrum[1]), 1)
                self.assertLessEqual(abs(data[0] - data[-1]),
                                     np.max(np.abs(np.diff(data))) + 1e-12)


if __name__ == '__main__':
    unittest.main()
