#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" process wavetable files """

import sys
import os
import struct
import numpy as np
import soundfile as sf

WAV_SAMPLE_RATE = 44100

H2P_HEADER = """\
#defaults=no
#cm=OSC
Wave=2
<?

float Wave[%d];
"""
H2P_FMULT = 0.999969
# u-he Zebra 2 OSC format is fixed
H2P_NUM_WAVEFORMS = 16
H2P_NUM_SAMPLES = 128

def print_err(msg):
    print(msg, file=sys.stderr)


def normalize(arr, level=1.0):
    """ scale array so the absolute peak equals level """
    peak = np.max(np.abs(arr))
    return arr / peak * level if peak > 0 else arr


class Wt:
    """
    save wavetables
    """

    def __init__(self, waveforms, bitwidth=32):
        """
        waveforms: numpy array with shape (waveforms, samples)
        """

        self.wf = waveforms.flatten()
        self.num_waveforms, self.num_samples = waveforms.shape
        if bitwidth not in [16, 32]:
            print_err(f'wrong bitwidth: {bitwidth}')
            sys.exit(1)

        self.bitwidth = bitwidth
        self.normalize = True

    def set_normalize(self, is_required):
        self.normalize = bool(is_required)

    def _normalized(self):
        return normalize(self.wf) if self.normalize else self.wf

    @staticmethod
    def _exists(fn):
        """ refuse to overwrite: precious wavetables live out there """
        if os.path.exists(fn):
            print_err(f'File "{fn}" exists')
            return True
        return False

    def _data(self):
        """ normalized samples converted to the output dtype """
        normalized = self._normalized()
        if self.bitwidth == 32:
            return normalized.astype(np.float32)
        return (normalized * 32767).astype(np.int16)

    def save_wav(self, fn):
        """
        save WAV wavetable, 16 PCM / 32 float
        https://pysoundfile.readthedocs.io/en/latest/#module-soundfile
        """

        if self._exists(fn):
            return

        wav_type = 'FLOAT' if self.bitwidth == 32 else 'PCM_16'
        sf.write(fn, self._data(), WAV_SAMPLE_RATE, wav_type)

    def save_wt(self, fn):
        """
        save WT wavetable for Surge XT and Bitwig
        https://github.com/surge-synthesizer/surge/blob/main/resources/data/wavetables/WT%20fileformat.txt
        """

        if self._exists(fn):
            return

        with open(fn, "wb") as file:
            header = bytearray(12)
            header[:4]   = b'vawt'
            header[4:8]  = struct.pack('<I', self.num_samples)
            header[8:10] = struct.pack('<H', self.num_waveforms)
            # flags: 0x04 data is int16, 0x08 the int16 uses the full range;
            # without 0x08 Surge assumes 15-bit data and doubles the level
            flags = 0 if self.bitwidth == 32 else 0x0C
            header[10:12] = struct.pack('<H', flags)
            file.write(header)
            self._data().tofile(file)

    def save_h2p(self, fn):
        """
        save h2p wavetable for u-he Zebra 2 oscillator
        source array should be (H2P_NUM_WAVEFORMS, H2P_NUM_SAMPLES)
        format borrowed from
        https://github.com/harveyormston/osc_gen/blob/main/osc_gen/zosc.py
        """
        if self._exists(fn):
            return

        wf = self._normalized()

        with open(fn, "w", encoding="utf-8") as file:
            print(H2P_HEADER % self.num_samples, file=file)

            for tn, i in enumerate(range(0, len(wf), self.num_samples), start=1):
                print(f'//table {tn}', file=file)
                wave_values = [f*H2P_FMULT for f in wf[i:(i+self.num_samples)]]
                for k, f in enumerate(wave_values):
                    print(f'Wave[{k}] = {f:.10f};', file=file)
                print(f'Selected.WaveTable.set({tn}, Wave);\n', file=file)

            print('?>', file=file)
