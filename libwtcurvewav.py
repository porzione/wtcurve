#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import soundfile as sf
import struct
import os

SAMPLE_RATE = 44100


def add_chunk(src_name, dst_name, chunk):
    chid, size = struct.unpack('<4sI', chunk[:8])
    print(f'New chunk ID: {chid}, size: {size}, len: {len(chunk)}')
    dst = open(dst_name, 'wb')
    with open(src_name, 'rb') as src:
        data = src.read(12)
        riff, size, fformat = struct.unpack('<4sI4s', data)
        print(f'RIFF header: {riff}, size: {size}, format: {fformat}')
        dst.write(data)
        while True:
            try:
                # Each chunk starts with a 4-byte ID and a 4-byte size
                head = src.read(8)
                chid, size = struct.unpack('<4sI', head)
                print(f'Chunk ID: {chid}, size: {size}')
                data = src.read(size)
                print(f'read size: {len(data)}')
                if chid in [b'PEAK', b'fact']:
                    continue
                elif chid == b'data':
                    # write new chunk before b'data'
                    dst.write(chunk)
                dst.write(head)
                dst.write(data)

            except struct.error:
                # If struct.unpack fails, it means we've run out of data, so we break the loop
                # print(f'ERR/END: ID: {chid}, size: {size}')
                break

    dst_size = os.fstat(dst.fileno()).st_size
    print(dst_size)
    dst.seek(4)
    dst.write((dst_size - 8).to_bytes(4, 'little'))
    dst.close()


class Wav:

    def __init__(self, waveforms, bitwidth, basename):

        self.waveforms = waveforms
        self.bitwidth = bitwidth
        self.basename = basename
        self.num_waveforms = len(self.waveforms)
        self.num_samples = len(self.waveforms[0])
        print(
            f'Wav num_waveforms: {self.num_waveforms}, num_samples: {self.num_samples}')

    def save(self):

        # Normalize the frames to the range of -1 to 1
        normalized_frames = self.waveforms / np.max(np.abs(self.waveforms))

        if self.bitwidth == 32:
            normalized_frames_typed = normalized_frames.astype(np.float32)
            wav_type = 'FLOAT'

        elif self.bitwidth == 16:
            # Convert frames to 16-bit signed integer format
            normalized_frames_typed = (
                normalized_frames *
                32767).astype(
                np.int16)
            wav_type = 'PCM_16'

        else:
            print(f'wrong bitwidth: {self.bitwidth}')
            exit()

        sf.write(f'wtc_{self.basename}.wav',
                 normalized_frames_typed.flatten(),
                 SAMPLE_RATE,
                 wav_type)

    def copy_uhe(self, descr='Funny string'):

        # 00 00 00 00 00 01 00 00 -> 256
        # 00 00 00 00 54 00 00 00 -> 84
        newck = bytearray(b'uhWT')
        newck.extend((272).to_bytes(4, 'little'))
        newck.extend(b'\x00' * 4)
        newck.extend(self.num_waveforms.to_bytes(2, 'little'))
        newck.extend(b'\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00')
        newck.extend(b'Funny string')
        #      TODO: ^^^ string_var.encode("utf-8")
        newck.extend(b'\x00' * (272 - len(newck) + 8))
        # print(len(newck); hexdump(newck)

        add_chunk(
            f'wtc_{self.basename}.wav',
            f'wtcu_{self.basename}.wav',
            newck
        )

    def copy_surge(self):
        newck = bytearray(b'srge')
        newck.extend((8).to_bytes(4, 'little'))
        newck.extend((1).to_bytes(4, 'little'))
        newck.extend(self.num_samples.to_bytes(4, 'little'))
        # print(len(newck); hexdump(newck)
        add_chunk(
            f'wtc_{self.basename}.wav',
            f'wtcs_{self.basename}.wav',
            newck
        )
