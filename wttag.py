#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=too-many-nested-blocks

from argparse import ArgumentParser
import types
import struct
import os
import sys
import numpy as np


TAGS = {
    'uhe': b'uhWT',
    'surge': b'srge',
    'clm': b'clm '
}


class Chunk:
    """ create wavetable chunks """

    DESCR = 'github.com/porzione/wtcurve'

    def __init__(self, num_waveforms, num_samples):

        self.num_waveforms = num_waveforms
        self.num_samples = num_samples
        self.description = f'{Chunk.DESCR} w:{num_waveforms} s:{num_samples}'
        print(f'description: {self.description}')

    def mk_uhe(self):
        chlen = 272
        chunk = bytearray(chlen+8)  # header
        chunk[:4] = TAGS['uhe']
        chunk[4:8] = struct.pack('<I', chlen)
        chunk[8:12] = b'\x00' * 4
        chunk[12:14] = struct.pack('<H', self.num_waveforms)
        chunk[17] = 8  # magick number
        bdescr = self.description.encode('ascii')
        chunk[24:24+len(bdescr)] = bdescr
        return chunk

    def mk_surge(self):
        chunk = bytearray(16)
        chunk[:4] = TAGS['surge']
        chunk[4:8] = struct.pack('<I', 8)
        chunk[8:12] = struct.pack('<I', 1)
        chunk[12:16] = struct.pack('<I', self.num_samples)
        return chunk

    def mk_clm(self):
        ck_id = TAGS['clm']
        ck_da = bytearray(f'<!>{self.num_samples} 10000000 {self.description}', 'ascii')[:48]
        ck_sz = len(ck_da)
        if ck_sz % 2 != 0:
            ck_da += b'\0'
        chunk = ck_id + struct.pack('<I', ck_sz) + ck_da
        return chunk

def setup_parser():
    argp = ArgumentParser()
    argp.add_argument("-w", dest="num_waveforms", type=int,
                      help="Number of frames/waveforms")
    argp.add_argument("-s", required=True, dest="num_samples", type=int,
                      choices=np.power(2, np.arange(3, 13)), help="Number of samples in one frame")
    argp.add_argument("--surge", action='store_true', dest="tag_surge", help="Add Surge tag")
    argp.add_argument("--uhe", action='store_true', dest="tag_uhe", help="Add u-he (e.g. Hive) tag")
    argp.add_argument("--clm", action='store_true', dest="tag_clm", help="Add clm (e.g. Serum) tag")
    argp.add_argument("-i", required=True, dest="src_file", help="Source file")
    argp.add_argument("-o", required=True, dest="dst_file", help="Output file")
    argp.add_argument("--of", action='store_true', dest="ov_file", help="Overwrite output file")
    argp.add_argument("--ot", action='store_true', dest="ov_tags", help="Overwrite tags")
    argp.add_argument("-m", action='store_true', dest="mkdir", help="Make destination directories")
    argp.add_argument("-a", action='store_true', dest="all_tags", help="Do not skip extra tags")
    return argp

class Tagger:
    """ add chunk to file """

    def __init__(self, args: dict = None):
        """ if args is None then use argparse """

        self._prepare_args(args)
        self._prepare()

    def _prepare_args(self, args):
        self.argp = setup_parser()
        if args is None:
            self.a = self.argp.parse_args()
            return

        args_dict = {}
        for action in self.argp._actions: # pylint: disable=protected-access
            if hasattr(action, 'dest'):
                dest = action.dest
                if dest in args:
                    args_dict[dest] = args[dest]
                elif hasattr(action, 'default'):
                    args_dict[dest] = action.default

        self.a = types.SimpleNamespace(**args_dict)

    def _prepare(self):

        if not os.path.isfile(self.a.src_file):
            print(f'Source file "{self.a.src_file}" not exists or not file.')
            sys.exit(1)

        if os.path.isfile(self.a.dst_file) and not self.a.ov_file:
            print(f'Destination file "{self.a.dst_file}" exists.')
            sys.exit(2)

        if os.path.isfile(self.a.dst_file) and os.path.samefile(self.a.src_file, self.a.dst_file):
            print('Source and destination are the same file')
            sys.exit(3)

        dst_path = os.path.dirname(self.a.dst_file)
        if not os.path.isdir(dst_path) and self.a.mkdir:
            print(f'mkdir: {dst_path}')
            os.makedirs(dst_path, mode=0o755)

        self.chunk = Chunk(self.a.num_waveforms, self.a.num_samples)

    def customize(self):
        pass

    def _unpack_riff(self, data):
        unp = struct.unpack('<4sI4s', data)
        keys = ['riff', 'wavsize', 'fformat']
        return dict(zip(keys, unp))

    def _unpack_fmt(self, data):
        unp = struct.unpack('<HHIIHH', data[:16])
        keys = ['fmt', 'ch', 'sr', 'br', 'ba', 'bits']
        return dict(zip(keys, unp))

    def tag(self):
        print(f'tag: {self.a.src_file} -> {self.a.dst_file}')
        with open(self.a.src_file, 'rb') as src:
            data = src.read(12)
            print(self._unpack_riff(data))
            with open(self.a.dst_file, 'wb') as dst:
                dst.write(data)
                found_chunks = []
                while True:
                    try:
                        head = src.read(8)
                        chid, size = struct.unpack('<4sI', head)
                        found_chunks.append(chid)
                        print(f'chunk id: {chid}, size: {size}')
                        data = bytearray(src.read(size))
                        # print(f'read size: {len(data)}')
                        if chid in [b'PEAK', b'fact'] and not self.a.all_tags:
                            continue
                        if chid == b'fmt ':
                            print(self._unpack_fmt(data))
                            data[8:12] = struct.pack('<I', 0)  # zero rate
                        elif chid == b'data':
                            # write new chunks before data
                            for tag, tval in TAGS.items():
                                if getattr(self.a, f'tag_{tag}'):
                                    if tval in found_chunks and not self.a.ov_tags:
                                        print(f'skip {tag}')
                                    else:
                                        print(f'write {tag}')
                                        dst.write(getattr(self.chunk, f'mk_{tag}')())

                        dst.write(head)
                        dst.write(data)

                    except struct.error:
                        break

                # update size in header
                dst_size = os.fstat(dst.fileno()).st_size
                dst.seek(4)
                dst.write((dst_size - 8).to_bytes(4, 'little'))
                dst.close()


def __main__():
    tagger = Tagger()
    tagger.tag()

if __name__ == '__main__':
    __main__()
