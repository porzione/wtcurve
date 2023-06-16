#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
# import numpy as np
import wtcurve
import wttag
# import wtcurve_args

# destination paths for tagged files
wav_path = '/home/ftp/audio/Wavetables/WT1/My'
wt_path = os.path.expanduser('~/Music/Bitwig/Library/Wavetables/WT1/My')
h2p_path = os.path.expanduser('~/.u-he/Zebra2/Modules/Oscillator/My')
# samples
sa = 2048
# samples in simple wt waveforms
sa_wt = 1024
# waveforms
wa = 256
# waveforms in simple waveforms
wl = 64

types = ['bezier', 'tanh', 'dline', 'exp']

for t in types:
    os.makedirs(os.path.join(wav_path, t), exist_ok=True)
    os.makedirs(os.path.join(wt_path, t), exist_ok=True)
    os.makedirs(os.path.join(h2p_path, t), exist_ok=True)


def tpath(d):
    for ty in types:
        if ty in d:
            return ty

    return types[-1]

def mk_wav(d):
    wtc = wtcurve.WtCurve(d|{'wav': True})
    wtc.generate()
    fn = wtc.fmt_fname('wav')
    dn = os.path.join(wav_path, tpath(d), fn)
    tagger = wttag.Tagger({
        'num_waveforms': d['num_waveforms'],
        'num_samples': d['num_samples'],
        'src_file': fn,
        'dst_file': dn,
        'ov_file': True,
        'mkdir': True, 'tag_clm': True})
    tagger.tag()

def mk_wt(d):
    wtc = wtcurve.WtCurve(d|{'wt': True, 'bitwidth': 16})
    wtc.generate()
    fn = wtc.fmt_fname('wt')
    dn = os.path.join(wt_path, tpath(d), fn)
    shutil.move(fn, dn)


def mk_h2p(d):
    wtc = wtcurve.WtCurve(d|{'h2p': True})
    wtc.generate()
    fn = wtc.fmt_fname('h2p')
    dn = os.path.join(h2p_path, tpath(d), fn)
    shutil.move(fn, dn)

def mk_gif(d):
    wtc = wtcurve.WtCurve(d|{'gif': True})
    wtc.generate()

def mk_png(d):
    wtc = wtcurve.WtCurve(d|{'png': True, 'graph': True})
    wtc.generate()

def gen_direct():
    print('variable direct')
    mid=90
    ga=35
    for o in range(-25,26,5):
        bdict = {'num_waveforms': wl, 'num_samples': sa, 'dline': True,
                 'mid_yoffset': o, 'mid_width_pct': mid}
        # mk_gif(bdict)
        # mk_gif(bdict|{'gauss': ga})
        mk_wav(bdict)
        mk_wav(bdict|{'gauss': ga})
        mk_wt(bdict|{'num_samples': sa_wt})
        mk_wt(bdict|{'num_samples': sa_wt, 'gauss': ga})
        mk_h2p(bdict)
        mk_h2p(bdict|{'gauss': ga})

def gen_savgol():
    print('savgol')
    bdict = {'num_waveforms': wa, 'num_samples': sa, 'savgol': (10, 3)}
    mk_wav(bdict)
    mk_wt(bdict)
    mk_h2p(bdict)

def gen_gauss():
    print('gauss')
    bdict = {'num_waveforms': wa, 'num_samples': sa, 'gauss': 40}
    mk_wav(bdict)
    mk_wt(bdict)
    mk_h2p(bdict)

def gen_bitcrush():
    print('bitcrush')
    for bc in [4, 5, 6]:
        bdict = {'num_waveforms': wa, 'num_samples': sa, 'bitcrush': bc}
        mk_wav(bdict)
        mk_wav(bdict|{'dline': True})
        mk_wt(bdict)
        mk_wt(bdict|{'dline': True})
        mk_h2p(bdict)
        mk_h2p(bdict|{'dline': True})

def gen_bezier():
    print('variable bezier')
    for o in range(-25,26,25):
        for bz in range(1, -6, -1):
            bdict = {'num_waveforms': wa, 'num_samples': sa,
                     'bezier': bz,'mid_yoffset': o}
            mk_wav(bdict)
            mk_wt(bdict)
            mk_h2p(bdict)
            if o == 0:
                # all bezier with offset 0 are the same
                break

def gen_tanh():
    print('variable tanh')
    for o in [-25, -15, 0, 15, 25]:
        for tanh in range(2, 5, 1):
            bdict = {'num_waveforms': wa, 'num_samples': sa, 'tanh': tanh,
                     'mid_yoffset': o}
            mk_wav(bdict)
            mk_wt(bdict)
            mk_h2p(bdict)

def gen_exp():
    print('variable offset/exp')
    for e in range(2, 9, 1):
        for o in [-20, -10, 0, 15, 25]:
            bdict = {'num_waveforms': wa, 'num_samples': sa, 'exp': e,
                    'mid_yoffset': o}
            mk_wav(bdict)
            mk_wt(bdict)
            mk_h2p(bdict)

def gen_shift():
    print('shift')
    bdict = {'num_waveforms': wa, 'num_samples': sa, 'mid_yoffset': 0,
             'shift': sa // 2, 'mid_width_pct': 99}
    # bdict['gif'] = True
    mk_wav(bdict|{'exp': 2})
    mk_wav(bdict|{'tanh': 1.5})
    mk_wav(bdict|{'bezier': 0 })
    mk_wav(bdict|{'dline': True })
    mk_wt(bdict|{'exp': 2})
    mk_wt(bdict|{'tanh': 1.5})
    mk_wt(bdict|{'bezier': 0 })
    mk_wt(bdict|{'dline': True })
    bdict['shift'] = 64  # h2p has fixed 128 samples
    mk_h2p(bdict|{'exp': 2})
    mk_h2p(bdict|{'tanh': 1.5})
    mk_h2p(bdict|{'bezier': 0})
    mk_h2p(bdict|{'dline': True})

gen_shift()
gen_direct()
gen_savgol()
gen_gauss()
gen_bitcrush()
gen_bezier()
gen_tanh()
gen_exp()
