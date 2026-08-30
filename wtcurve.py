#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" generate wavetables for audio synthesizers: WAV, WT, h2p, graphs, gif """

import subprocess
import sys
import numpy as np
from wtcurve_args import MORPHABLE, SAW_MODES, namespace_from, setup_parser
import wtfile

# curvature at t=1 for the morphing power/RC sawtooths
MAX_POWER = 4.0
MAX_RC = 8.0

# tenor vowel formants, five per vowel, from the CSound manual appendix:
# (center Hz, level dB, bandwidth Hz), the bandwidth used as Gaussian sigma
VOWEL_FORMANTS = {
    'a': ((650, 0, 80), (1080, -6, 90), (2650, -7, 120), (2900, -8, 130),
          (3250, -22, 140)),
    'e': ((400, 0, 70), (1700, -14, 80), (2600, -12, 100), (3200, -14, 120),
          (3580, -20, 120)),
    'i': ((290, 0, 40), (1870, -15, 90), (2800, -18, 100), (3250, -20, 120),
          (3540, -30, 120)),
    'o': ((400, 0, 70), (800, -10, 80), (2600, -12, 100), (2800, -12, 130),
          (3000, -26, 135)),
    'u': ((350, 0, 40), (600, -20, 60), (2700, -17, 100), (2900, -14, 120),
          (3300, -26, 120)),
}
VOWEL_F0 = 110.0    # reference fundamental the formants are mapped against
VOWEL_FLOOR = 0.01  # -40 dB source floor under the formant bumps

# guard for parameters a --morph sweep can drive through zero
EPS = 1e-6

# output flags in dispatch order; each has a matching _mk_<name> method
OUTPUTS = ('graph', 'graph3d', 'gif', 'wav', 'wt', 'h2p')


class WtCurve:
    """ wavetable curve: compute data, save files """

    def __init__(self, args: dict = None):
        """ if args is None then use argparse """

        self._prepare_args(args)
        if not (self.a.debug
                or any(getattr(self.a, name) for name in OUTPUTS)):
            print(f'What to do?\n\n{self.argp.format_help()}')
            sys.exit()

        if self.a.rms and self.a.norm:
            wtfile.print_err('--rms and --norm are two normalizations of the same '
                             'frames: pick one')
            sys.exit(1)

        self.wt = []
        self.frame_fn = None          # a family sets it, else the curve default
        self._prepare_morph()
        self._prepare_mode()
        self._prepare_suffix()
        self._prepare_values()

    def _prepare_args(self, args):
        self.argp = setup_parser()
        if args is None:
            self.a = self.argp.parse_args()
        else:
            self.a = namespace_from(self.argp, args)

    def _debug(self, msg):
        """ debug message helper """
        if self.a.debug:
            print(msg)

    def _prepare_mode(self):
        """ choose the waveform family, its title and file name type """
        if self.a.saw:
            self.frame_fn = getattr(self, f'_saw_{self.a.saw}_frame')
            self.title = f'Saw {SAW_MODES[self.a.saw]} morph'
            self.mtype = f'saw_{self.a.saw}'
        elif self.a.vowel:
            self.frame_fn = self._vowel_frame
            morph = ' morph' if len(self.a.vowel) > 1 else ''
            self.title = f'Vowel {self.a.vowel}{morph}'
            self.mtype = f'vowel_{self.a.vowel}'
        elif self.a.sine:
            self.frame_fn = self._sine_frame
            self.title = 'Sine'
            self.mtype = 'sine'
        elif self.a.bezier is not None:
            self.curve_fn = self._bezier_curve
            self.title = f'Bézier {self.a.bezier}'
            self.mtype = f'F{self.a.bezier:.4g}bz'
        elif self.a.tanh is not None:
            self.curve_fn = self._tanh_curve
            self.title = f'Hyperbolic tangent {self.a.tanh}'
            self.mtype = f'F{self.a.tanh:.4g}ht'
        elif self.a.dline:
            self.curve_fn = self._line
            self.title = 'Direct line'
            self.mtype = 'dl'
        else:
            self.curve_fn = self._exp_curve
            self.title = f'Exponent {self.a.exp}'
            self.mtype = f'{self.a.exp}e'

    def _prepare_suffix(self):
        """ title and file name parts from filters and transforms """
        self.suffix = ''
        if isinstance(self.a.savgol, tuple):
            self.title = f'{self.title} savgol={self.a.savgol}'
            self.suffix = f'{self.suffix}_sg{self.a.savgol[0]}-{self.a.savgol[1]}'
        # numeric transforms: (flag, suffix tag, format); ints keep their
        # plain str() form so existing file names stay stable
        for name, tag, fmt in (('gauss', 'ga', ''), ('bitcrush', 'bc', ''),
                               ('harmonics', 'hm', ''), ('fold', 'fd', '.4g'),
                               ('foldbias', 'fb', '.4g'), ('sat', 'st', '.4g'),
                               ('satbias', 'sb', '.4g'), ('neg', 'ng', '.4g')):
            value = getattr(self.a, name)
            if isinstance(value, (float, int)):
                self.title = f'{self.title} {name}={value:{fmt}}'
                self.suffix = f'{self.suffix}_{tag}{value:{fmt}}'
        for name, _dest, start, _anchor, end, curve, _cast in self.morphs:
            log = ' log' if curve == 'log' else ''
            self.title = f'{self.title} {name}:{start:.4g}..{end:.4g}{log}'
            self.suffix = (f'{self.suffix}_mo{name}{start:.4g}-{end:.4g}'
                           f'{"log" if curve == "log" else ""}')
        if self.a.reverse:
            self.title = f'{self.title} rev'
            self.suffix = f'{self.suffix}_rev'
        if self.a.shift:
            self.title = f'{self.title} shift={self.a.shift}'
            self.suffix = f'{self.suffix}_sh{self.a.shift}'
        if self.a.norm:
            self.title = f'{self.title} norm={self.a.norm:.2g}'
            self.suffix = f'{self.suffix}_no{self.a.norm:.2g}'
        if self.a.rms:
            self.title = f'{self.title} equal RMS'
            self.suffix = f'{self.suffix}_rms'

    def _prepare_morph(self):
        """
        --morph specs, with the anchor each one keeps in the middle waveform

        The value the flag itself carries becomes the middle of the table when
        it lies between the two ends, so a sweep travels from one extreme
        through the waveform the command line describes to the other extreme.
        When it does not (or the flag was never given, as for a filter that is
        off by default) there is nothing to anchor to and the sweep is a plain
        line from start to end.
        """
        self.morphs = []
        for name, start, end, curve in (self.a.morph or []):
            dest, cast = MORPHABLE[name]
            if not hasattr(self.a, dest):
                raise ValueError(f'--morph {name}: parser has no dest {dest}')
            base = getattr(self.a, dest)
            if curve == 'log' and base is not None and base <= 0:
                base = None
            if base is not None and base in (start, end):
                print(f'--morph {name}: the middle waveform is anchored on {base}, which '
                      f'is also an end of the sweep, so half the table stands still - '
                      f'drop the flag to sweep straight through')
            if base is not None and min(start, end) <= base <= max(start, end):
                anchor = float(base)
            else:
                if base is not None:
                    print(f'--morph {name}: {base} is outside {start}..{end}, '
                          f'sweeping straight through instead of anchoring on it')
                anchor = None
            self.morphs.append((name, dest, start, anchor, end, curve, cast))

    @staticmethod
    def _morph_value(start, anchor, end, curve, t):
        """ value at table position t: start .. anchor (at 0.5) .. end """
        if curve == 'log':
            start, end = np.log(start), np.log(end)
            anchor = None if anchor is None else np.log(anchor)
        if anchor is None:
            value = start + (end - start) * t
        elif t <= 0.5:
            value = start + (anchor - start) * (t / 0.5)
        else:
            value = anchor + (end - anchor) * ((t - 0.5) / 0.5)
        return np.exp(value) if curve == 'log' else value

    def _apply_morph(self, t):
        """ set every morphed parameter to what it is at table position t """
        for _name, dest, start, anchor, end, curve, cast in self.morphs:
            value = self._morph_value(start, anchor, end, curve, t)
            setattr(self.a, dest, int(round(value)) if cast is int else float(value))
        if self.morphs and self.a.debug:
            self._debug(f'morphed at t={t:.4f}: '
                        + ', '.join(f'{d}={getattr(self.a, d)}'
                                    for _n, d, *_rest in self.morphs))

    def _prepare_values(self):
        if self.frame_fn is None:
            # no family claimed the table, the curve waveform is the default
            self.frame_fn = self._curve_frame
            self.title = (f'{self.title} m={self.a.mid_width_pct}% '
                          f'o={self.a.mid_yoffset}%')
            ywidth = 2 if self.a.mid_yoffset >= 0 else 3
            self.fname_prefix = (f'{self.a.mid_width_pct}m_'
                                 f'{self.a.mid_yoffset:0{ywidth}d}h_')
        else:
            self.fname_prefix = ''

        if self.a.savgol:
            if self.a.savgol[0] not in range(1, 100):
                raise ValueError('savgol window should be in range 1-99%')
            sizes = [self.a.num_samples]
            if self.a.h2p:
                sizes.append(wtfile.H2P_NUM_SAMPLES)
            for size in sizes:
                wlen = int(size / 100 * self.a.savgol[0])
                if wlen <= self.a.savgol[1]:
                    raise ValueError(
                        f'savgol window of {self.a.savgol[0]}% is {wlen} of '
                        f'{size} samples and must exceed polyorder '
                        f'{self.a.savgol[1]}')

        self._harm_csums = {}

    def _exp_curve(self, x1, y1, x2, y2, num_points):
        """ exponential curve with fixed start and end """
        self._debug(f'curve: {x1} {y1} {x2} {y2} {num_points}')
        if abs(self.a.exp) < EPS:
            # the exp->0 limit is a straight line; --morph e can cross zero,
            # where the formula below divides by zero
            return self._line(x1, y1, x2, y2, num_points)
        x = np.linspace(x1, x2, num_points)
        y = y1 + (y2 - y1) * (np.exp(self.a.exp * (x - x1)) - 1) / \
            (np.exp(self.a.exp * (x2 - x1)) - 1)
        if x1 < 0:
            y_rotated = y2 - (y - y1)
            return y_rotated[::-1]

        return y

    def _bezier_curve(self, x1, y1, _x2, y2, num_points):
        """
        bezier curve with fixed start and end
        args.bezier is also used; only the y values are returned, so the
        control point's x never enters the result
        """
        ctrl_y = (y2 if x1 < 0 else y1) * self.a.bezier
        y_values = np.zeros(num_points)
        for i, t in enumerate(np.linspace(0.0, 1.0, num_points)):
            y_values[i] = (1 - t)**2 * y1 + 2 * (1 - t) * t * ctrl_y + t**2 * y2

        return y_values

    def _tanh_curve(self, x1, y1, x2, y2, num_points):
        if num_points == 0:
            # -m 100 shrinks the curves to nothing at t=1, where x1 == x2
            # would put a zero in the scale denominator
            return np.zeros(0)
        if abs(self.a.tanh) < EPS:
            # the tanh->0 limit is a straight line; --morph tanh can cross
            # zero, where the scale below divides by zero
            return self._line(x1, y1, x2, y2, num_points)
        x = np.linspace(x1, x2, num_points)
        scale = (y2 - y1) / (np.tanh(x2 * self.a.tanh) - np.tanh(x1 * self.a.tanh))
        translation = y1 - scale * np.tanh(x1 * self.a.tanh)
        y = scale * np.tanh(x * self.a.tanh) + translation
        return y

    def _line(self, x1, y1, x2, y2, num_points):
        """ just direct line """
        self._debug(f'line: {x1} {y1} {x2} {y2} {num_points}')

        if x1 == x2:
            y_values = np.linspace(y1, y2, num_points)
        else:
            x_values = np.linspace(x1, x2, num_points)
            y_values = y1 + ((y2 - y1) / (x2 - x1)) * (x_values - x1)
        return y_values

    def fmt_fname(self, ext, add=None):
        """ format file name """
        fname = f'{self.fname_prefix}{self.mtype}{self.suffix}'
        if ext in ['wav', 'wt']:
            if self.a.fullname:
                fname = f'{fname}_{self.a.num_samples}s_{self.a.num_waveforms}w'
        elif ext == 'gif':
            fname = f'{fname}_anim'
        elif ext not in ['png', 'h2p']:
            raise ValueError(f'Bad file ext: {ext}')

        fname += f'_{add}' if add else ''
        return f'{fname}.{ext}'

    def _title(self):
        return f'{self.title} s={self.a.num_samples} w={self.a.num_waveforms}'

    def _plt(self):
        """ matplotlib costs ~0.2 s to import, output-only runs skip it """
        import matplotlib.pyplot as plt  # pylint: disable=import-outside-toplevel
        plt.rcParams['xtick.labelsize'] = self.a.fontsize
        plt.rcParams['ytick.labelsize'] = self.a.fontsize
        plt.rcParams['figure.dpi'] = self.a.dpi
        return plt

    def _finish_plot(self, plt, tag, dpi, **save_kw):
        """ save the current figure to png, or show it """
        if self.a.png:
            fn = self.fmt_fname('png', tag)
            print(f'saving: {fn}')
            plt.savefig(fn, dpi=dpi, **save_kw)
        else:
            plt.show()
        plt.close()

    def _mk_graph(self):
        plt = self._plt()
        x = np.linspace(0, 100, self.a.num_samples)
        plt.xticks(np.arange(min(x), max(x)+1, 25))
        plt.plot(x,self.wt[0], 'm-', label='first waveform')
        plt.plot(x,self.wt[-1], 'c-', label='last waveform')
        ax = plt.gca()
        ax.xaxis.set_ticklabels([])
        plt.ylabel('Amplitude', fontsize=self.a.fontsize)
        plt.title(self._title(), fontsize=self.a.fontsize)
        plt.grid(True)
        plt.legend(fontsize=self.a.fontsize)
        self._finish_plot(plt, '2d', self.a.dpi)

    def _mk_graph3d(self):
        plt = self._plt()
        x = np.arange(self.wt.shape[1])
        y = np.arange(self.wt.shape[0])
        x, y = np.meshgrid(x, y)
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.plot_surface(x, y, self.wt, cmap='twilight')
        ax.view_init(elev=20, azim=250)
        ax.grid(False)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
        plt.title(self._title(), y=0.95, fontsize=self.a.fontsize)
        plt.subplots_adjust(bottom=0, top=1.03)
        self._finish_plot(plt, '3d', int(self.a.dpi*1.2), pad_inches=0)

    def _mk_gif(self):
        plt = self._plt()
        from matplotlib import animation  # pylint: disable=import-outside-toplevel
        fig, ax = plt.subplots()
        lines = []
        for idx in np.linspace(0, self.a.num_waveforms - 1, 6).astype(int):
            line, = ax.plot(self.wt[idx], 'm-')
            lines.append([line])
        ax.xaxis.set_ticklabels([])
        ax.set_ylabel('Amplitude', fontsize=self.a.fontsize)
        ax.set_title(self._title(), fontsize=self.a.fontsize)
        ax.grid(True)
        anim = animation.ArtistAnimation(fig, lines, interval=500, blit=True)
        fn = self.fmt_fname('gif')
        print(f'saving: {fn}')
        anim.save(fn, writer='pillow', dpi=self.a.dpi)
        plt.close()
        if self.a.open:
            try:
                cmd = f'mimeopen {fn}'
                subprocess.run(cmd, shell=True, capture_output=True, text=True,
                               check=False)
            except subprocess.CalledProcessError as e:
                print(e.returncode, e.stdout, e.stderr)

    def _mk_wavlike(self, ext):
        """ wav and wt share everything but the writer """
        fn = self.fmt_fname(ext)
        print(f'saving: {fn} {self.a.bitwidth} bit')
        wt = wtfile.Wt(self.wt, self.a.bitwidth)
        wt.set_normalize(not self.a.norm)
        getattr(wt, f'save_{ext}')(fn)

    def _mk_wav(self):
        self._mk_wavlike('wav')

    def _mk_wt(self):
        self._mk_wavlike('wt')

    def _mk_h2p(self):
        fn = self.fmt_fname('h2p')
        print(f'saving: {fn}')
        # h2p size is fixed, generate the waveforms separately
        # so other outputs keep their own size
        wt = wtfile.Wt(self._gen_waveforms(wtfile.H2P_NUM_WAVEFORMS,
                                           wtfile.H2P_NUM_SAMPLES))
        wt.set_normalize(not self.a.norm)
        wt.save_h2p(fn)

    def _curve_frame(self, t, num_samples):
        """ single frame: two curves joined by the middle line """
        mid_samples = int((self.a.mid_width_pct / 100) * num_samples)
        mid_samples -= mid_samples % 2
        mid_width = int(np.round(mid_samples * t))
        mid_width -= mid_width % 2
        cx = t * self.a.mid_width_pct / 100
        yo = self.a.mid_yoffset * 0.01
        curve_len = num_samples // 2 - mid_width // 2
        self._debug(f'cx: {cx} curve_len: {curve_len}, mw: {mid_width}, '
                    f'sum: {curve_len*2+mid_width}')
        ya1 = self.curve_fn(-1, -1, -cx, -yo, curve_len)
        ya2 = self.curve_fn(cx, yo, 1, 1, curve_len)
        ym = self._line(-cx, -yo, cx, yo, mid_width)
        if self.a.debug:
            # formatting these arrays costs more than computing them,
            # so never build the strings unless -D is on
            self._debug(f'ya1: {ya1} ({len(ya1)})')
            self._debug(f'ya2: {ya2} ({len(ya2)})')
            self._debug(f'ym: {ym} ({len(ym)})')
        return np.concatenate((ya1, ym, ya2))

    @staticmethod
    def _ramp01(num_samples):
        """ one 0..1 cycle, endpoint excluded so the wrap stays periodic """
        return np.linspace(0.0, 1.0, num_samples, endpoint=False)

    @staticmethod
    def _max_harm(num_samples):
        """ band-limit ceiling shared by the additive families """
        return max(1, num_samples // 4)

    def _saw_ramp_frame(self, _t, num_samples):
        """
        plain sawtooth, identical in every frame

        Every other family morphs by construction, which leaves nowhere to
        stand when the motion is supposed to come from --morph alone: sweeping
        saturation over --saw pow sweeps the curvature as well. This mode is
        the still carrier for that.
        """
        return 2.0 * self._ramp01(num_samples) - 1.0

    def _sine_frame(self, _t, num_samples):
        """
        pure sine, identical in every frame

        The second still carrier next to --saw ramp: a wavefolder or any
        other --morph-driven transform wants a clean starting point, and
        for the fold that point is a sine.
        """
        return np.sin(2 * np.pi * np.arange(num_samples) / num_samples)

    def _vowel_frame(self, t, num_samples):
        """
        vowel formant frame: a 1/k source shaped by five Gaussian formant
        bumps, interpolated across the --vowel sequence as t moves

        Formants are absolute frequencies and a wavetable has none, so
        they are mapped onto harmonics of VOWEL_F0; played near that
        pitch the vowels sit where a tenor puts them, higher and every
        formant scales up with the pitch, which reads as a shrinking
        head. The floor keeps a trace of the source under vowels whose
        first formant sits far above the fundamental.
        """
        seq = self.a.vowel
        if len(seq) == 1:
            fmt = np.array(VOWEL_FORMANTS[seq], dtype=float)
        else:
            pos = t * (len(seq) - 1)
            idx = min(int(pos), len(seq) - 2)
            va = np.array(VOWEL_FORMANTS[seq[idx]], dtype=float)
            vb = np.array(VOWEL_FORMANTS[seq[idx + 1]], dtype=float)
            fmt = va + (vb - va) * (pos - idx)
            self._debug(f'vowel: {seq[idx]}..{seq[idx + 1]} '
                        f'frac {pos - idx:.3f}')
        k = np.arange(1, self._max_harm(num_samples) + 1)
        freq = k * VOWEL_F0
        # fmt columns: center Hz, level dB, bandwidth Hz
        filt = VOWEL_FLOOR + (
            10 ** (fmt[:, 1:2] / 20)
            * np.exp(-0.5 * ((freq - fmt[:, 0:1]) / fmt[:, 2:3]) ** 2)
        ).sum(axis=0)
        spectrum = np.zeros(num_samples // 2 + 1, dtype=complex)
        # the source is a glottal ramp, so every harmonic keeps the phase
        # it has in the ascending saw
        spectrum[k] = 1j * (filt / k) * (num_samples / 2)
        return np.fft.irfft(spectrum, num_samples)

    def _saw_harm_frame(self, t, num_samples):
        """
        additive saw frame: harmonics count grows geometrically with t,
        equal fundamental level across frames; the sum of sin(kx)/k is the
        descending saw, so it is negated to ascend like the other saw modes
        """
        csum = self._harm_csums.get(num_samples)
        if csum is None:
            # cumulative sums over the 1/k harmonic series, computed once:
            # a frame with n harmonics is just row n-1
            max_harm = self._max_harm(num_samples)
            x = np.arange(num_samples) / num_samples
            k = np.arange(1, max_harm + 1)
            csum = np.cumsum(np.sin(2 * np.pi * np.outer(k, x)) / k[:, None],
                             axis=0)
            self._harm_csums[num_samples] = csum
        n = int(round(len(csum) ** t))
        self._debug(f'harmonics: {n}')
        return (-2 / np.pi) * csum[n - 1]

    def _saw_skew_frame(self, t, num_samples):
        """
        sawtooth skew frame: ramp turnaround moves from first sample
        (reverse saw) through the middle (triangle) to last sample (saw)
        """
        peak = int(round(t * (num_samples - 1)))
        self._debug(f'skew peak: {peak}')
        y = np.empty(num_samples)
        y[:peak + 1] = np.linspace(-1, 1, peak + 1)
        y[peak:] = np.linspace(1, -1, num_samples - peak)
        return y

    @staticmethod
    def _dc_free(y):
        """
        centre a frame on zero, keeping the peak it had

        A bent ramp is not symmetric about zero, so it carries an offset that
        grows with the bend - up to 0.6 of full scale at the far end of the
        power morph, 0.75 of the RC one. In a wavetable that offset is not
        harmless: an oscillator sweeping the table steps its output every time
        it crosses a frame, and the offset eats the headroom that peak
        normalisation then charges the audible part of the waveform for.
        """
        peak = np.abs(y).max()
        y = y - y.mean()
        new_peak = np.abs(y).max()
        return y * (peak / new_peak) if new_peak else y

    @staticmethod
    def _equal_rms(frames):
        """
        scale every frame to the same RMS

        Peak normalization makes the wavetable position part volume control: a
        sine and a saw of the same peak differ by 2.8 dB of RMS, and every table
        measured so far drifts across its sweep - 4.8 dB for the power morph,
        7.3 for RC, 3.8 for the saturation-bias one, which is enough to hear as
        a fade rather than as a timbre change. Equalizing RMS is what leaves
        only the timbre moving.

        The level is not a parameter: the whole table is peak-normalized after
        this, which cancels any factor common to every frame, so the only thing
        that matters is that the frames agree. A silent frame stays silent.
        """
        rms = np.sqrt(np.mean(np.square(frames), axis=1))
        loudest = rms.max()
        if loudest <= 0:
            return frames
        scale = np.divide(loudest, rms, out=np.ones_like(rms), where=rms > 0)
        return frames * scale[:, None]

    def _saw_pow_frame(self, t, num_samples):
        """
        power-curved saw frame: the ramp is bent by a power function,
        t morphs the exponent from 1 (linear saw) to MAX_POWER
        (rounded bottom, sharp top)
        """
        power = MAX_POWER ** t
        self._debug(f'power: {power}')
        return self._dc_free(2.0 * np.power(self._ramp01(num_samples), power) - 1.0)

    def _saw_rc_frame(self, t, num_samples):
        """
        analog RC saw frame: capacitor charging curve 1 - e^(-t/RC),
        t morphs the rate constant from ~0 (linear saw) to MAX_RC
        (sharp bottom, rounded top)
        """
        rc = max(MAX_RC * t, EPS)
        self._debug(f'rc constant: {rc}')
        charge = 1.0 - np.exp(-self._ramp01(num_samples) * rc)
        return self._dc_free(
            2.0 * (charge - charge[0]) / (charge[-1] - charge[0]) - 1.0)

    @staticmethod
    def _asymmetric(y, neg):
        """
        scale the negative half, the asymmetry a hardware oscillator has

        Cutting one half creates even harmonics where a symmetric waveform had
        none, which is the whole point, and it also creates a DC offset, which
        no wavetable may carry: an oscillator would step the output every time
        it crossed a frame. So the offset is removed and the peak the waveform
        had before is restored.
        """
        return WtCurve._dc_free(np.where(y < 0, y * neg, y))

    @staticmethod
    def _fold(y, gain, bias):
        """
        triangle wavefolder, the west coast timbre control

        gain * y + bias runs out of [-1, 1] and is reflected back at every
        edge it crosses, the Buchla way: harmonics pour in as the folds
        multiply, non-monotonically - partials rise and fall as each fold
        passes through. The bias breaks the fold symmetry, which is where
        the even harmonics come from, and also puts DC on the result, so
        it is re-centred afterwards.
        """
        return WtCurve._dc_free(
            np.abs(np.mod(gain * y + bias - 1.0, 4.0) - 2.0) - 1.0)

    @staticmethod
    def _saturate(y, drive, bias):
        """
        tanh saturation with an offset, the analog oscillator stage

        A hardware saw is not a straight ramp: the stage that buffers it
        saturates, and it does so asymmetrically, so the top of the ramp
        compresses while the bottom stays. tanh(drive * y + bias) with
        drive 1.26 and bias 0.63 reproduces one such captured saw to a
        correlation of 0.9935, and the bias is the half of it that matters -
        without it the curve is symmetric and the result is just a quieter saw.
        """
        return WtCurve._dc_free(np.tanh(drive * y + bias))

    @staticmethod
    def _band_limit(y, harmonics):
        """ keep the first n harmonics, drop the rest """
        spectrum = np.fft.rfft(y)
        spectrum[harmonics + 1:] = 0
        return np.fft.irfft(spectrum, len(y))

    def _post_process(self, y):
        """ filters and transforms applied to one frame """
        if self.a.fold is not None and self.a.fold > 0:
            y = self._fold(y, self.a.fold,
                           self.a.foldbias if self.a.foldbias is not None else 0.0)
        if self.a.neg is not None and self.a.neg != 1.0:
            y = self._asymmetric(y, self.a.neg)
        if self.a.sat is not None and self.a.sat > 0:
            y = self._saturate(y, self.a.sat, self.a.satbias if self.a.satbias is not None else 0.0)
        if self.a.harmonics is not None:
            # 0, reachable when --morph sweeps down to it, keeps DC only;
            # skipping the band-limit there would leave the frame full-bright
            y = self._band_limit(y, max(self.a.harmonics, 0))
        if self.a.savgol:
            from scipy.signal import savgol_filter  # pylint: disable=import-outside-toplevel
            wlen = int(len(y) / 100 * self.a.savgol[0])
            y = savgol_filter(y, window_length=wlen, polyorder=self.a.savgol[1])
        if self.a.gauss:
            from scipy.ndimage import gaussian_filter1d  # pylint: disable=import-outside-toplevel
            y = gaussian_filter1d(y, sigma=self.a.gauss)
        if self.a.bitcrush:
            max_val = 2**(self.a.bitcrush) - 1
            y = np.round(y * max_val) / max_val
        if self.a.reverse:
            y = y[::-1]
        if self.a.shift:
            y = np.roll(y, shift=self.a.shift)
        if self.a.norm:
            y = wtfile.normalize(y, self.a.norm)
        return y

    def _gen_waveforms(self, num_waveforms, num_samples):
        """ compute wavetable array with shape (num_waveforms, num_samples) """
        if num_waveforms > 1:
            morphs = np.linspace(0, 1, num_waveforms)
        else:
            morphs = np.array([1.0])
        frames = []
        for t in morphs:
            self._apply_morph(t)
            frames.append(self._post_process(self.frame_fn(t, num_samples)))
        frames = np.array(frames)
        if self.a.rms:
            frames = self._equal_rms(frames)
        return frames

    def generate(self):
        self.wt = self._gen_waveforms(self.a.num_waveforms, self.a.num_samples)

        if self.a.debug:
            np.set_printoptions(threshold=np.inf, precision=None, suppress=True)
            print('full wavetable:', self.wt)
            sys.exit()

        for name in OUTPUTS:
            if getattr(self.a, name):
                getattr(self, f'_mk_{name}')()

def __main__():
    wtc = WtCurve()
    wtc.generate()

if __name__ == '__main__':
    __main__()
