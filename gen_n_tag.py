#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import wtcurve
import wttag
import wtcurve_args

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


def tpath(d):
    for ty in types:
        if ty in d:
            return ty

    return types[-1]


def mk_wav(d):
    d['wav'] = True
    wtc = wtcurve.WtCurve(d)
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
    d['wt'] = True
    d['bitwidth'] = 16
    wtc = wtcurve.WtCurve(d)
    wtc.generate()
    fn = wtc.fmt_fname('wt')
    dn = os.path.join(wt_path, tpath(d), fn)
    shutil.copy(fn, dn)


def mk_h2p(d):
    d['h2p'] = True
    wtc = wtcurve.WtCurve(d)
    wtc.generate()
    fn = wtc.fmt_fname('h2p')
    shutil.copy(fn, h2p_path)

def mk_gif(d):
    d['gif'] = True
    wtc = wtcurve.WtCurve(d)
    wtc.generate()

def mk_png(d):
    d['png'] = True
    d['graph'] = True
    wtc = wtcurve.WtCurve(d)
    wtc.generate()

print('variable direct')
mid=30
ga=35
for o in range(-25,26,5):
    #mk_gif({'num_waveforms': wl, 'num_samples': sa, 'mid_yoffset': o,
    #        'mid_width_pct': mid, 'dline': True})
    #mk_png({'num_waveforms': wl, 'num_samples': sa, 'mid_yoffset': o,
    #        'mid_width_pct': mid, 'dline': True})
    #mk_png({'num_waveforms': wl, 'num_samples': sa, 'mid_yoffset': o,
    #        'mid_width_pct': mid, 'dline': True, 'gauss': ga})
    mk_wav({'num_waveforms': wl, 'num_samples': sa, 'mid_yoffset': o,
            'mid_width_pct': mid, 'dline': True})
    mk_wav({'num_waveforms': wl, 'num_samples': sa, 'mid_yoffset': o,
            'mid_width_pct': mid, 'dline': True, 'gauss': ga})
    mk_wt({'num_waveforms': wl, 'num_samples': sa_wt, 'mid_yoffset': o,
           'mid_width_pct': mid, 'dline': True})
    mk_wt({'num_waveforms': wl, 'num_samples': sa_wt,
           'mid_width_pct': mid, 'mid_yoffset': o, 'dline': True, 'gauss': ga})
    mk_h2p({'mid_yoffset': o, 'mid_width_pct': mid, 'dline': True})
    mk_h2p({'mid_yoffset': o, 'mid_width_pct': mid, 'dline': True, 'gauss': ga})

savgol = 10
print(f'savgol={savgol}')
mk_wav({'num_waveforms': wa, 'num_samples': sa, 'savgol': (savgol, 3)})
mk_wt({'num_waveforms': wa, 'num_samples': sa, 'savgol': (savgol, 3)})
mk_h2p({'savgol': (savgol, 3)})

gauss = 40
print(f'gauss={gauss}')
mk_wav({'num_waveforms': wa, 'num_samples': sa, 'gauss': gauss})
mk_wt({'num_waveforms': wa, 'num_samples': sa, 'gauss': gauss})
mk_h2p({'gauss': gauss})

print('bitcrush')
for bc in [3, 4, 5]:
    mk_wav({'num_waveforms': wa, 'num_samples': sa, 'bitcrush': bc})
    mk_wav({'num_waveforms': wa, 'num_samples': sa, 'bitcrush': bc,
            'dline': True})
    mk_wt({'num_waveforms': wa, 'num_samples': sa, 'bitcrush': bc})
    mk_wt({'num_waveforms': wa, 'num_samples': sa, 'bitcrush': bc,
           'dline': True})
    mk_h2p({'bitcrush': bc})
    mk_h2p({'bitcrush': bc, 'dline': True})

print('variable bezier')
for bz in range(1, -10, -1):
    mk_wav({'num_waveforms': wa, 'num_samples': sa, 'bezier': bz})
    mk_wt({'num_waveforms': wa, 'num_samples': sa, 'bezier': bz})
    mk_h2p({'bezier': bz})

print('variable tanh')
for o in [-25, 0, 25, 35]:
    for tanh in range(2, 7, 2):
        mk_wav({'num_waveforms': wa, 'num_samples': sa,
               'tanh': tanh, 'mid_yoffset': o})
        mk_wt({'num_waveforms': wa, 'num_samples': sa,
              'tanh': tanh, 'mid_yoffset': o})
        mk_h2p({'tanh': tanh, 'mid_yoffset': o})

print('variable offset')
for o in range(-25,26,5):
    if o not in [0, wtcurve_args.defaults['mid_yoffset']]:
        mk_wav({'num_waveforms': wa, 'num_samples': sa, 'mid_yoffset': o})
        mk_wt({'num_waveforms': wa, 'num_samples': sa, 'mid_yoffset': o})
        mk_h2p({'mid_yoffset': o})

print('variable exp')
for e in range(3, 9):
    for o in [0, wtcurve_args.defaults['mid_yoffset']]:
        mk_wav({'num_waveforms': wa, 'num_samples': sa, 'exp': e,
                'mid_yoffset': o})
        mk_wt({'num_waveforms': wa, 'num_samples': sa, 'exp': e,
               'mid_yoffset': o})
        mk_h2p({'exp': e, 'mid_yoffset': o})
