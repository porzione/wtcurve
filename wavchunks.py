#!/usr/bin/env python
# -*- coding: utf-8 -*-

import struct
import sys
from pathlib import Path

PRINT_DATA_VALUES = 8

def hexdump(data):
    for i in range(0, len(data), 16):
        line = data[i:i+16]
        hex_part = ' '.join(f'{byte:02x}' for byte in line)
        ascii_part = ''.join((chr(byte) if 32 <= byte <= 126 else '.') for byte in line)
        print(f'{i:08x}: {hex_part:47} |{ascii_part}|')

class ChunkProcessor:
    """ wav chunk reader and parser """
    def __init__(self, file):
        self.file = file
        self.datac = self.datasz = 0
        self.samples = self.waveforms = 0
        self.fmtd = None
        self.chsize = 0
        self.raw_h = None

    def unpack_riff(self, data):
        unp = struct.unpack('<4sI4s', data)
        keys = ['riff', 'wavsize', 'fformat']
        return dict(zip(keys, unp))

    def process_fmt(self, data):
        try:
            # audio_format, num_channels, sample_rate, byte_rate, block_align, bits_per_sample
            unp = struct.unpack('<HHIIHH', data[:16])
            keys = ['fmt', 'ch', 'sr', 'br', 'ba', 'bits']
            self.fmtd = dict(zip(keys, unp))
            print(self.fmtd)
            if len(data) > 16:
                ext_size = struct.unpack('<H', data[16:18])
                print(f'extension size: {ext_size}')
        except struct.error as e:
            print("unpack fmt exception:", e)

    def process_data(self, data):
        dlen = PRINT_DATA_VALUES * self.fmtd['bits'] // 8
        print(self.unpack_data(data[:dlen], self.fmtd['bits']))
        self.datac += 1
        self.datasz += self.chsize

    def unpack_data(self, data, bits):
        length = len(data) // (bits // 8)
        try:
            if bits == 32:
                return struct.unpack(f'{length}f', data)
            if bits == 16:
                return struct.unpack(f'{length}H', data)
        except struct.error as e:
            print(f"unpack exception: {e}")
        return None

    def process_uhwt(self, data):
        self.waveforms = struct.unpack('<I', data[4:8])[0]
        hexdump(self.raw_h + data[:56])

    def process_clm(self, data):
        clmd = data[3:].decode('utf-8')
        print(clmd)
        self.samples = int(clmd.split(' ')[0])

    def process_srge(self, data):
        self.samples = struct.unpack('<H', data[4:6])[0]

    def process_skip(self, data):
        pass

    def read_chunks(self):
        chunk_processors = {
            b'clm ': self.process_clm,
            b'fmt ': self.process_fmt,
            b'uhWT': self.process_uhwt,
            b'data': self.process_data,
            b'srge': self.process_srge,

            b'AFAn': self.process_skip,
            b'ID3 ': self.process_skip,
            b'JUNK': self.process_skip,
            b'LGWV': self.process_skip,
            b'LIST': self.process_skip,
            b'PEAK': self.process_skip,
            b'SAUR': self.process_skip,
            b'bext': self.process_skip,
            b'fact': self.process_skip,
            b'junk': self.process_skip,
            b'smpl': self.process_skip,
            b'FLLR': self.process_skip,
        }

        with open(self.file, 'rb') as f:
            print(self.unpack_riff(f.read(12)))
            while True:
                try:
                    self.raw_h = f.read(8)
                    chid, self.chsize = struct.unpack('<4sI', self.raw_h)
                    data = f.read(self.chsize)
                    print(f'chunk id: {chid}, size: {self.chsize}')

                    if chid in chunk_processors:
                        chunk_processors[chid](data)
                    else:
                        print('WHAT?')
                        hexdump(data[:16])
                except struct.error:
                    print(f'data chunks: {self.datac} size: {self.datasz}')
                    if self.waveforms > 0:
                        print(f'w:{self.waveforms} '
                              f's:{int(self.datasz/(self.waveforms*self.fmtd["bits"]/8))}')
                    elif self.samples > 0:
                        print(f'w:{int(self.datasz//(self.samples*self.fmtd["bits"]/8))} '
                              f's:{self.samples}')
                    break
                except Exception as e: # pylint: disable=broad-exception-caught
                    print(f"exception: {e}")
                    break


def process_file(ppath):
    print(f'===== {ppath} size: {ppath.stat().st_size}')
    processor = ChunkProcessor(str(ppath))
    processor.read_chunks()

if len(sys.argv) > 1:
    for inp in sys.argv[1:]:
        path = Path(inp)
        if path.is_dir():
            print(f'DIR: {inp}')
            for file_path in path.glob('*.wav'):
                process_file(file_path)
        elif path.is_file():
            process_file(path)
