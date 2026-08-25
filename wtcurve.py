#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" generate wavetables for audio synthesizers: WAV, WT, h2p, graphs, gif """

import subprocess
import sys
import types
import numpy as np
from scipy.signal import savgol_filter
from scipy.ndimage import gaussian_filter1d
import matplotlib.pyplot as plt
from matplotlib import animation
from wtcurve_args import SAW_MODES, setup_parser
import wtfile

# curvature at t=1 for the morphing power/RC sawtooths
MAX_POWER = 4.0
MAX_RC = 8.0


class WtCurve:
    """ wavetable curve: compute data, save files """

    def __init__(self, args: dict = None):
        """ if args is None then use argparse """

        self._prepare_args(args)
        if not (self.a.wav or self.a.graph or self.a.graph3d or
                self.a.debug or self.a.gif or self.a.h2p or self.a.wt):
            print(f'What to do?\n\n{self.argp.format_help()}')
            sys.exit()

        self.dbg = self.a.debug
        self.wt = []
        self.saved_files = []
        self._prepare_mode()
        self._prepare_suffix()
        self._prepare_values()
        # for attr, value in vars(self).items():
        #     if attr != 'mid_widths':
        #         print(f"{attr}: {value}")

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

    def _debug(self, msg):
        """ debug message helper """
        if self.dbg:
            print(msg)

    def _prepare_mode(self):
        """ choose the waveform family, its title and file name type """
        if self.a.saw:
            self.frame_fn = getattr(self, f'_saw_{self.a.saw}_frame')
            self.title = f'Saw {SAW_MODES[self.a.saw]} morph'
            self.mtype = f'saw_{self.a.saw}'
        elif isinstance(self.a.bezier, (float, int)):
            self.curve_fn = self._bezier_curve
            self.title = f'Bézier {self.a.bezier}'
            self.mtype = f'F{self.a.bezier:.4g}bz'
        elif isinstance(self.a.tanh, (float, int)):
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
        if isinstance(self.a.gauss, (float, int)):
            self.title = f'{self.title} gauss={self.a.gauss}'
            self.suffix = f'{self.suffix}_ga{self.a.gauss}'
        if isinstance(self.a.bitcrush, (float, int)):
            self.title = f'{self.title} bitcrush={self.a.bitcrush}'
            self.suffix = f'{self.suffix}_bc{self.a.bitcrush}'
        if self.a.reverse:
            self.title = f'{self.title} rev'
            self.suffix = f'{self.suffix}_rev'
        if self.a.shift:
            self.title = f'{self.title} shift={self.a.shift}'
            self.suffix = f'{self.suffix}_sh{self.a.shift}'
        if self.a.norm:
            self.title = f'{self.title} norm={self.a.norm:.2g}'
            self.suffix = f'{self.suffix}_no{self.a.norm:.2g}'

    def _prepare_values(self):
        if self.a.saw:
            self.fname_prefix = ''
        else:
            self.frame_fn = self._curve_frame
            self.title = (f'{self.title} m={self.a.mid_width_pct}% '
                          f'o={self.a.mid_yoffset}%')
            ywidth = 2 if self.a.mid_yoffset >= 0 else 3
            self.fname_prefix = (f'{self.a.mid_width_pct}m_'
                                 f'{self.a.mid_yoffset:0{ywidth}d}h_')

        if self.a.savgol and self.a.savgol[0] not in range(1, 100):
            raise ValueError('savgol window should be in range 1-100%')

        self._harm_csums = {}
        self.mid_yoffset = self.a.mid_yoffset * 0.01
        self._debug(f'mid_yoffset: {self.mid_yoffset}')

    def wavetable(self):
        return self.wt

    def _exp_curve(self, x1, y1, x2, y2, num_points):
        """ exponential curve with fixed start and end """
        self._debug(f'curve: {x1} {y1} {x2} {y2} {num_points}')
        x = np.linspace(x1, x2, num_points)
        y = y1 + (y2 - y1) * (np.exp(self.a.exp * (x - x1)) - 1) / \
            (np.exp(self.a.exp * (x2 - x1)) - 1)
        if x1 < 0:
            y_rotated = y2 - (y - y1)
            return y_rotated[::-1]

        return y

    def _bezier_curve(self, x1, y1, x2, y2, num_points):
        """
        bezier curve with fixed start and end
        args.bezier is also used
        """
        t_values = np.linspace(0.0, 1.0, num_points)
        x_values = np.zeros(num_points)
        y_values = np.zeros(num_points)
        x = np.where(x1 < 0, x1, x2)
        y = np.where(x1 < 0, y2, y1) * self.a.bezier
        # print(f'args {self.a.bezier} -> {x},{y}')

        for i, t in enumerate(t_values):
            x_values[i] = (1 - t)**2 * x1 + 2 * (1 - t) * t * x + t**2 * x2
            y_values[i] = (1 - t)**2 * y1 + 2 * (1 - t) * t * y + t**2 * y2

        return y_values

    def _tanh_curve(self, x1, y1, x2, y2, num_points):
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

    def _mk_graph(self):
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
        if self.a.png:
            fn = self.fmt_fname('png', '2d')
            print(f'saving: {fn}')
            plt.savefig(fn, dpi=self.a.dpi)
        else:
            plt.show()
        plt.close()

    def _mk_graph3d(self):
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
        if self.a.png:
            fn = self.fmt_fname('png', '3d')
            print(f'saving: {fn}')
            plt.savefig(fn, dpi=int(self.a.dpi*1.2), pad_inches=0)
        else:
            plt.show()
        plt.close()

    def _mk_gif(self):
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

    def _mk_wav(self):
        fn = self.fmt_fname('wav')
        print(f'saving: {fn} {self.a.bitwidth} bit')
        wt = wtfile.Wt(self.wt, self.a.bitwidth)
        wt.set_normalize(not self.a.norm)
        wt.save_wav(fn)

    def _mk_wt(self):
        fn = self.fmt_fname('wt')
        print(f'saving: {fn} {self.a.bitwidth} bit')
        wt = wtfile.Wt(self.wt, self.a.bitwidth)
        wt.set_normalize(not self.a.norm)
        wt.save_wt(fn)

    def _mk_h2p(self):
        fn = self.fmt_fname('h2p')
        print(f'saving: {fn}')
        # h2p size is fixed, generate the waveforms separately
        # so other outputs keep their own size
        wt = wtfile.Wt(self._gen_waveforms(wtfile.H2P_NUM_WAVEFORMS,
                                           wtfile.H2P_NUM_SAMPLES))
        wt.save_h2p(fn)

    def _curve_frame(self, t, num_samples):
        """ single frame: two curves joined by the middle line """
        mid_samples = int((self.a.mid_width_pct / 100) * num_samples)
        mid_samples -= mid_samples % 2
        mid_width = int(np.round(mid_samples * t))
        mid_width -= mid_width % 2
        cx = t * self.a.mid_width_pct / 100
        curve_len = num_samples // 2 - mid_width // 2
        self._debug(f'cx: {cx} curve_len: {curve_len}, mw: {mid_width}, '
                    f'sum: {curve_len*2+mid_width}')
        ya1 = self.curve_fn(-1, -1, -cx, -self.mid_yoffset, curve_len)
        self._debug(f'ya1: {ya1} ({len(ya1)})')
        ya2 = self.curve_fn(cx, self.mid_yoffset, 1, 1, curve_len)
        self._debug(f'ya2: {ya2} ({len(ya2)})')
        ym = self._line(-cx, -self.mid_yoffset, cx, self.mid_yoffset, mid_width)
        self._debug(f'ym: {ym} ({len(ym)})')
        return np.concatenate((ya1, ym, ya2))

    def _saw_harm_frame(self, t, num_samples):
        """
        additive saw frame: harmonics count grows geometrically with t,
        equal fundamental level across frames
        """
        csum = self._harm_csums.get(num_samples)
        if csum is None:
            # cumulative sums over the 1/k harmonic series, computed once:
            # a frame with n harmonics is just row n-1
            max_harm = max(1, num_samples // 4)
            x = np.arange(num_samples) / num_samples
            k = np.arange(1, max_harm + 1)
            csum = np.cumsum(np.sin(2 * np.pi * np.outer(k, x)) / k[:, None],
                             axis=0)
            self._harm_csums[num_samples] = csum
        n = int(round(len(csum) ** t))
        self._debug(f'harmonics: {n}')
        return (2 / np.pi) * csum[n - 1]

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

    def _saw_pow_frame(self, t, num_samples):
        """
        power-curved saw frame: the ramp is bent by a power function,
        t morphs the exponent from 1 (linear saw) to MAX_POWER
        (rounded bottom, sharp top)
        """
        power = MAX_POWER ** t
        self._debug(f'power: {power}')
        ramp = np.linspace(0.0, 1.0, num_samples, endpoint=False)
        return self._dc_free(2.0 * np.power(ramp, power) - 1.0)

    def _saw_rc_frame(self, t, num_samples):
        """
        analog RC saw frame: capacitor charging curve 1 - e^(-t/RC),
        t morphs the rate constant from ~0 (linear saw) to MAX_RC
        (sharp bottom, rounded top)
        """
        rc = max(MAX_RC * t, 1e-6)
        self._debug(f'rc constant: {rc}')
        ramp = np.linspace(0.0, 1.0, num_samples, endpoint=False)
        charge = 1.0 - np.exp(-ramp * rc)
        return self._dc_free(
            2.0 * (charge - charge[0]) / (charge[-1] - charge[0]) - 1.0)

    def _post_process(self, y):
        """ filters and transforms applied to one frame """
        if self.a.savgol:
            wlen = int(len(y) / 100 * self.a.savgol[0])
            y = savgol_filter(y, window_length=wlen, polyorder=self.a.savgol[1])
        if self.a.gauss:
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
        return np.array([self._post_process(self.frame_fn(t, num_samples))
                         for t in morphs])

    def generate(self):
        self.wt = self._gen_waveforms(self.a.num_waveforms, self.a.num_samples)

        if self.dbg:
            np.set_printoptions(threshold=np.inf, precision=None, suppress=True)
            print('full wavetable:', self.wt)
            sys.exit()

        np.set_printoptions(linewidth=100, precision=2, suppress=True)

        plt.rcParams['xtick.labelsize'] = self.a.fontsize
        plt.rcParams['ytick.labelsize'] = self.a.fontsize
        plt.rcParams['figure.dpi'] = self.a.dpi

        actions = {
            'graph': self._mk_graph,
            'graph3d': self._mk_graph3d,
            'gif': self._mk_gif,
            'wav': self._mk_wav,
            'wt': self._mk_wt,
            'h2p': self._mk_h2p
        }
        for arg, action in actions.items():
            if getattr(self.a, arg):
                action()

def __main__():
    wtc = WtCurve()
    wtc.generate()

if __name__ == '__main__':
    __main__()
