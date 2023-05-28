#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import soundfile as sf
import os
import sys

SAMPLE_RATE = 44100


class Wav:

    def __init__(self, waveforms, bitwidth):

        self.waveforms = waveforms.flatten()
        self.bitwidth = bitwidth
        self.num_waveforms = len(waveforms)
        self.num_samples = len(waveforms[0])
        # print(f'Wav waveforms: {self.num_waveforms}, '
        #       f'samples: {self.num_samples}')

    # https://pysoundfile.readthedocs.io/en/latest/#module-soundfile
    # TODO: custom chunk/meta with number of num_waveforms, num_samples
    def save(self, filename):

        if os.path.exists(filename):
            print(f'File "{filename}" exists',
                  file=sys.stderr)

        normalized = self.waveforms / np.max(np.abs(self.waveforms))

        if self.bitwidth == 32:
            data = np.float32(normalized)
            wav_type = 'FLOAT'

        elif self.bitwidth == 16:
            data = np.int16(normalized * 32767)
            wav_type = 'PCM_16'

        else:
            print(f'wrong bitwidth: {self.bitwidth}')
            exit()

        sf.write(filename, data, SAMPLE_RATE, wav_type)
