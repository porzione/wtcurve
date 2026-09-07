"""Regression checks for wavetable generation and export."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from wtcurve import WtCurve
from wtcurve_args import morph_spec
from wtfile import Wt


def curve(**options):
    """Build a small table without writing output files."""
    with contextlib.redirect_stdout(io.StringIO()):
        return WtCurve({'wav': True, 'num_waveforms': 5,
                        'num_samples': 128, **options})


def frames(table):
    """Generate using the table's configured dimensions."""
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


if __name__ == '__main__':
    unittest.main()
