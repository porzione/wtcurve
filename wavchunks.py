#!/usr/bin/env python
# -*- coding: utf-8 -*-

import struct
import sys
import glob
from os.path import isdir, isfile, join, getsize
from hexdump import hexdump


def read_chunks(file):
    with open(file, 'rb') as f:
        # Read the first 12 bytes, which should be the RIFF header
        riff, wavsize, fformat = struct.unpack('<4sI4s', f.read(12))
        print(f'header: {riff}, size: {wavsize}, format: {fformat}')

        datac = datasz = 0
        samples = waveforms = 0
        # Read each chunk
        while True:
            try:
                # Each chunk starts with a 4-byte ID and a 4-byte size
                # fmt should always be 16, 18 or 40
                raw_h = f.read(8)
                chid, size = struct.unpack('<4sI', raw_h)
                data = f.read(size)
                print(f'chunk id: {chid}, size: {size}')
                if chid == b'fmt ':
                    try:
                        # audio_format, num_channels, sample_rate, byte_rate,
                        # block_align, bits_per_sample
                        fmt, ch, sr, br, ba, bits = struct.unpack(
                            '<HHIIHH', data[:16])
                        print(f'fmt: {fmt}, ch: {ch}, sr: {sr}, br: {br}, '
                              f'ba: {ba}, bits: {bits}')
                        if size > 16:
                            ext_size = struct.unpack('<H', data[16:18])
                            print(f'extension size: {ext_size}')
                            # TODO: process extension data
                    except Exception as e:
                        print("unpack fmt exception:", e)

                elif chid == b'srge':
                    samples = struct.unpack('<H', data[4:6])[0]
                    # hexdump(data)
                elif chid == b'uhWT':
                    waveforms = struct.unpack('<I', data[4:8])[0]
                    hexdump(raw_h+data[:56])
                elif chid == b'clm ':
                    d = data[3:].decode('utf-8')
                    print(d)
                    samples = int(d.split(' ')[0])
                elif chid == b'data':
                    # print(data[:8])
                    datac += 1
                    datasz += size
                elif chid in [b'PEAK', b'fact', b'LGWV', b'JUNK', b'AFAn',
                              b'ID3 ', b'SAUR', b'smpl', b'LIST']:
                    hexdump(data)
                    continue
                else:
                    print('WHO?')
                    hexdump(data[:10])

            except struct.error:
                # print(f'ERR/END: ID: {chid}, size: {size}')
                print(f'data chunks: {datac} size: {datasz}')
                if waveforms > 0:
                    print(f'w:{waveforms} s:{int(datasz/(waveforms*bits/8))}')
                elif samples > 0:
                    print(f'w:{int(datasz//(samples*bits/8))} s:{samples}')
                break

            except Exception as e:
                print("exception occurred:", e)
                break


if len(sys.argv) > 1:
    for inp in sys.argv[1:]:
        if isdir(inp):
            print(f'DIR: {inp}')
            for f in glob.iglob(join(inp, '*.wav')):
                print(f'FILE: {f}')
                read_chunks(f)

        elif isfile:
            print(f'FILE: {inp} size: {getsize(inp)}')
            read_chunks(inp)
