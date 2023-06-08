#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=too-many-branches

import sys
import os
import subprocess
import re
import shutil
import argparse

# destination paths for tagged files
wav_path = '/home/ftp/audio/Wavetables/WT1/My'
wt_path = os.path.expanduser('~/Music/Bitwig/Library/Wavetables/WT1/My')
h2p_path = os.path.expanduser('~/.u-he/Zebra2/Modules/Oscillator/My')
# samples
sa = 2048
# waveforms
wa = 256
# waveforms in simple tables
wl = 64

argp = argparse.ArgumentParser()
argp.add_argument('--go', action='store_true', help='Really run')
args = argp.parse_args()


def run(cmd):
    print(f'cmd: {cmd}')
    if not args.go:
        return

    try:
        subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       check=False)
    except subprocess.CalledProcessError as ex:
        print(ex.returncode, ex.stdout, ex.stderr)


print('variable bezier')
for b in range(1, -10, -1):
    run(f'./wtcurve --fullfn -s {sa} -w {wa} -B{b} --wav --gif')
    run(f'./wtcurve --fullfn -s {sa} -w {wa} -B{b} --wt')
    run(f'./wtcurve -s {sa} -w {wa} -B{b} --h2p')

print('bitcrush')
for bitcrush in [3, 4, 5]:
    run(f'./wtcurve --fullfn -s {sa} -w {wa} --bitcrush {bitcrush} --wav --gif')
    run(f'./wtcurve --fullfn -s {sa} -w {wa} --bitcrush {bitcrush} --wt --16')
    run(f'./wtcurve --bitcrush {bitcrush} --h2p')

print('variable tanh')
for o in [25, 35]:
    for tanh in range(2, 7, 2):
        run(f'./wtcurve --fullfn -s {sa} -w {wa} -o {o} --tanh {tanh} --wav --gif')
        run(f'./wtcurve --fullfn -s {sa} -w {wa} -o {o} --tanh {tanh} --wt --16')
        run(f'./wtcurve --tanh {tanh} -o {o} --h2p')

gauss = 40
print(f'gauss={gauss}')
run(f'./wtcurve --fullfn -s {sa} -w {wa} --gauss {gauss} --wav --gif')
run(f'./wtcurve --fullfn -s {sa} -w {wa} --gauss {gauss} --wt --16')
run(f'./wtcurve --gauss {gauss} --h2p')

savgol = 10
print(f'savgol={savgol}')
run(f'./wtcurve --fullfn -s {sa} -w {wa} --savgol {savgol},3 --wav --gif')
run(f'./wtcurve --fullfn -s {sa} -w {wa} --savgol {savgol},3 --wt --16')
run(f'./wtcurve -w {wa} --savgol {savgol},3 --h2p')

print('variable offset')
for o in [25, 35]:
    run(f'./wtcurve --fullfn -s {sa} -w {wa} -o {o} --wav --gif')
    run(f'./wtcurve --fullfn -s {sa} -w {wl} -o {o} --wav -L --gif')
    run(f'./wtcurve --fullfn -s {sa} -w {wa} -o {o} --wav -L --gauss 35 --gif')
    run(f'./wtcurve --fullfn -s {sa} -w {wa} -o {o} --wt --16')
    run(f'./wtcurve --fullfn -s {sa} -w {wl} -o {o} --wt -L --16')
    run(f'./wtcurve --fullfn -s {sa} -w {wa} -o {o} --wt -L --gauss 35 --16')
    run(f'./wtcurve -o {o} --h2p')
    run(f'./wtcurve -o {o} --h2p -L')
    run(f'./wtcurve -o {o} --h2p -L --gauss 35')

print('variable exp')
for e in range(1, 10):
    if e != 5:
        run(f'./wtcurve --fullfn -s {sa} -w {wa} -e {e} --wav')
        run(f'./wtcurve --fullfn -s {sa} -w {wa} -e {e} --wt --16')
        run(f'./wtcurve -e {e} --h2p')

if not os.path.isdir(wav_path):
    sys.exit()
if not os.path.isdir(wt_path):
    sys.exit()
if not os.path.isdir(h2p_path):
    sys.exit()

print('tagging')
patterns = {
    'ext': re.compile(r'\.(\w+)$'),
    'wa': re.compile(r'([0-9]+)w'),
    'sa': re.compile(r'([0-9]+)s'),
    'ty': re.compile(r'_(dl|[0-9F.-]+(bz|ht)|[0-9]e)_?')
}
ty_dict = {
    r'\d+e$': 'exp',
    r'[0-9F.-]+bz$': 'bezier',
    r'[0-9F.-]+ht$': 'tanh',
    r'dl$': 'dline'
}

for file in os.listdir():
    if file.endswith('.wav') or file.endswith('.wt'):
        print(f'file: {file}')
        matches = {key: pattern.search(file)
                   for key, pattern in patterns.items()}
        ext, c_wa, c_sa, c_ty = [
            match.group(1) if match else None for match in matches.values()]

        # print(f"ext: {ext} wa: {c_wa} sa: {c_sa} ty: '{c_ty}'")
        ty_path = None
        for pattern, value in ty_dict.items():
            if re.match(pattern, c_ty):
                ty_path = value
                break

        if ty_path is None:
            print('unknown ty')
            sys.exit(1)

        name2 = re.sub(r'_[0-9]+s_[0-9]+w', '', file)
        if ext == 'wav':
            run(f'./wttag -s {c_sa} -w {c_wa} --clm --of -i {file} '
                f'-o {wav_path}/{ty_path}/{name2} -m')
        elif ext == 'wt':
            destdir = f'{wt_path}/{ty_path}'
            if not os.path.isdir(destdir):
                os.makedirs(destdir)
            dst = f'{destdir}/{name2}'
            print(f'copy to: {dst}')
            if args.go:
                shutil.copy(file, f'{dst}')


for file in os.listdir():
    if file.endswith('.h2p'):
        if args.go:
            shutil.copy(file, h2p_path)
