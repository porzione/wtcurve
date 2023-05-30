#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import os
import soundfile as sf
import struct
import sys

WAV_SAMPLE_RATE = 44100

H2P_HEADER = """\
#defaults=no
#cm=OSC
Wave=2
<?

float Wave[%d];
"""
H2P_FMULT = 0.999969


class Wt:

    def __init__(self, waveforms, bitwidth=32):

        self.wf = waveforms.flatten()
        self.num_waveforms, self.num_samples = waveforms.shape
        self.bitwidth = bitwidth
        # print(f'Wav waveforms: {self.num_waveforms}, '
        #       f'samples: {self.num_samples}')

    # https://pysoundfile.readthedocs.io/en/latest/#module-soundfile
    def save_wav(self, fn):

        if os.path.exists(fn):
            print(f'File "{fn}" exists',
                  file=sys.stderr)
            exit()

        normalized = self.wf / np.max(np.abs(self.wf))

        if self.bitwidth == 32:
            data = np.float32(normalized)
            wav_type = 'FLOAT'

        elif self.bitwidth == 16:
            data = np.int16(normalized * 32767)
            wav_type = 'PCM_16'

        else:
            print(f'wrong bitwidth: {self.bitwidth}')
            exit()

        sf.write(fn, data, WAV_SAMPLE_RATE, wav_type)

    # https://github.com/surge-synthesizer/surge/tree/main/scripts/wt-tool
    def save_wt(self, fn):

        if os.path.exists(fn):
            print(f'File "{fn}" exists',
                  file=sys.stderr)
            # exit()

        with open(fn, "wb") as file:
            header = bytearray(12)
            header[:4]   = b'vawt'
            header[4:8]  = struct.pack('<I', self.num_samples)
            header[8:10] = struct.pack('<H', self.num_waveforms)
            # flags:
            # 0x01 is_sample
            # 0x02 loop_sample
            # 0x04 int16/float32 2/4 bytes, int16 if 1
            header[10:12] = b'\x00\x00'
            file.write(header)

            self.wf.astype(np.float32).tofile(file)

    # format borrowed from
    # https://github.com/harveyormston/osc_gen/blob/main/osc_gen/zosc.py
    def save_h2p(self, fn):
        if os.path.exists(fn):
            print(f'File "{fn}" exists', file=sys.stderr)
            # exit()

        with open(fn, "w") as file:
            print(H2P_HEADER % self.num_samples, file=file)

            for tn, i in enumerate(range(0, len(self.wf), self.num_samples), start=1):
                print(f'//table {tn}', file=file)
                wave_values = [f*H2P_FMULT for f in self.wf[i:(i+self.num_samples)]]
                for k, f in enumerate(wave_values):
                    print(f'Wave[{k}] = {f:.10f};', file=file)
                print(f'Selected.WaveTable.set({tn}, Wave);\n', file=file)

            print('?>', file=file)
