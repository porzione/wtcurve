#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import sys
import types
import numpy as np
from scipy.signal import savgol_filter
from scipy.ndimage import gaussian_filter1d
import matplotlib.pyplot as plt
from matplotlib import animation
from wtcurve_args import setup_parser
import wtfile


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

    def _prepare_values(self):
        if isinstance(self.a.bezier, (float, int)):
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
        if self.a.dco:
            self.title = f'{self.title} dco'
            self.suffix = f'{self.suffix}_dco'

        if self.a.h2p:
            self.num_samples = 128
            self.num_waveforms = 16
        else:
            self.num_samples = self.a.num_samples
            self.num_waveforms = self.a.num_waveforms

        self.mid_samples = int((self.a.mid_width_pct / 100) * self.num_samples)
        self.mid_samples -= self.mid_samples % 2
        self._debug(f'mid_samples: {self.mid_samples} '
                    '({self.a.mid_width_pct}% of {self.num_samples})')

        self.mid_widths = np.round(self.mid_samples * np.arange(self.num_waveforms) /
                              (self.num_waveforms - 1)).astype(int)
        self.mid_widths -= self.mid_widths % 2
        self._debug(f'mid_widths: {self.mid_widths}')

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
        """ format file name for saving """
        fname = f'{self.a.mid_width_pct}m_{self.a.mid_yoffset}h_{self.mtype}{self.suffix}'
        if ext in ['wav', 'wt']:
            if self.a.fullname:
                fname = f'{fname}_{self.num_samples}s_{self.num_waveforms}w'
        elif ext == 'gif':
            fname = f'{fname}_anim'
        elif ext not in ['png', 'h2p']:
            raise ValueError(f'Bad file ext: {ext}')

        fname += f'_{add}' if add else ''
        return f'{fname}.{ext}'

    def _title(self):
        return (f'{self.title} m={self.a.mid_width_pct}% '
                f'h={self.mid_yoffset}% '
                f's={self.num_samples} w={self.num_waveforms}')

    def _mk_graph(self):
        x = np.linspace(0, 100, self.num_samples)
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
            plt.savefig(fn, dpi=self.a.dpi)
        else:
            plt.show()

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
            plt.savefig(fn, dpi=int(self.a.dpi*1.2), pad_inches=0)
        else:
            plt.show()

    def _mk_gif(self):
        pct1 = self.num_waveforms / 100
        fig, ax = plt.subplots()
        lines = []
        for pct in range(0, 100, 20):
            line, = ax.plot(self.wt[int(pct*pct1)], 'm-')
            lines.append([line])
        ax.xaxis.set_ticklabels([])
        ax.set_ylabel('Amplitude', fontsize=self.a.fontsize)
        ax.set_title(self._title(), fontsize=self.a.fontsize)
        ax.grid(True)
        anim = animation.ArtistAnimation(fig, lines, interval=500, blit=True)
        fn = self.fmt_fname('gif')
        print(f'saving: {fn}')
        anim.save(fn, writer='pillow', dpi=self.a.dpi)
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
        wt.save_wav(fn)

    def _mk_wt(self):
        fn = self.fmt_fname('wt')
        print(f'saving: {fn} {self.a.bitwidth} bit')
        wt = wtfile.Wt(self.wt, self.a.bitwidth)
        wt.save_wt(fn)

    def _mk_h2p(self):
        fn = self.fmt_fname('h2p')
        print(f'saving: {fn}')
        wt = wtfile.Wt(self.wt)
        wt.save_h2p(fn)

    def generate(self):
        self.wt = np.zeros((self.num_waveforms, self.num_samples))
        self._debug(f'wt shape: {self.wt.shape}')
        xoffsets = np.linspace(0, self.a.mid_width_pct / 100, self.num_waveforms)

        for i in range(self.num_waveforms):
            cx = xoffsets[i]
            self._debug(f'cx: {cx}')

            curve_len = self.num_samples // 2 - self.mid_widths[i] // 2
            self._debug(
                f'i: {i} curve_len: {curve_len}, mw: {self.mid_widths[i]}, '
                f'sum: {curve_len*2+self.mid_widths[i]}')

            ya1 = self.curve_fn(-1, -1, -cx, -self.mid_yoffset, curve_len)
            self._debug(f'ya1: {ya1} ({len(ya1)})')
            ya2 = self.curve_fn(cx, self.mid_yoffset, 1, 1, curve_len)
            self._debug(f'ya2: {ya2} ({len(ya2)})')
            ym = self._line(-cx, -self.mid_yoffset, cx, self.mid_yoffset, self.mid_widths[i])
            self._debug(f'ym: {ym} ({len(ym)})')
            y = np.concatenate((ya1, ym, ya2))
            self._debug(f'y: {y} {y.shape}')
            if self.a.savgol:
                if not self.a.savgol[0] in range(1,100):
                    raise ValueError('savgol window should be in range 1-100%')
                wlen = int(self.num_samples / 100 * self.a.savgol[0])
                y = savgol_filter(y, window_length=wlen, polyorder=self.a.savgol[1])
            if self.a.gauss:
                y = gaussian_filter1d(y, sigma=self.a.gauss)
            if self.a.bitcrush:
                max_val = 2**(self.a.bitcrush) - 1
                y = np.round(y * max_val) / max_val
            if self.a.dco:
                # future experiments
                dc_offset = np.mean(y)
                y -= dc_offset

            self.wt[i] = y

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
