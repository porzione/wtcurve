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

    def test_cli_distinguishes_default_and_explicit_exponent(self):
        parser = setup_parser()
        options = vars(parser.parse_args(['--wav', '--morph', 'tanh,1,4']))
        self.assertEqual(WtCurve(options).curve_fn.__name__, '_tanh_curve')
        options = vars(parser.parse_args(['--wav', '-e', '5', '--morph', 'tanh,1,4']))
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            WtCurve(options)
        self.assertEqual(curve().a.exp, 5)


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
