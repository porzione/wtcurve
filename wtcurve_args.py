#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" helper for cli arguments """

from argparse import ArgumentParser, ArgumentTypeError

def tuple_2int(value):
    """
    parse and check tuple argument, like (window, polyorder)
    """
    try:
        items = [int(x) for x in value.split(",")]
        if len(items) != 2:
            raise ArgumentTypeError("Tuple argument must contain 2 ints separated by a comma")
        return tuple(items)
    except Exception as exc:
        raise ArgumentTypeError("Invalid tuple argument") from exc

# def tuple_2float(value):
#     try:
#         items = [float(x) for x in value.split(",")]
#         if len(items) != 2:
#             raise ArgumentTypeError("Tuple argument must contain 2 floats separated by a comma")
#         return tuple(items)
#     except:
#         raise ArgumentTypeError("Invalid tuple argument")

def restricted_float1(n):
    n = float(n)
    if n <= 0 or n >= 1.0:
        raise ArgumentTypeError(f"{n} not in range (0, 1.0)")
    return n


# parameters --morph may sweep across the wavetable: name -> (dest, cast)
# the name is the flag as it is typed on the command line, without dashes, so
# --morph e,2,9 sweeps the same thing -e sets
MORPHABLE = {
    'e':         ('exp', float),
    'B':         ('bezier', float),
    'tanh':      ('tanh', float),
    'm':         ('mid_width_pct', int),
    'o':         ('mid_yoffset', int),
    'gauss':     ('gauss', float),
    'bitcrush':  ('bitcrush', int),
    'harmonics': ('harmonics', int),
    'neg':       ('neg', float),
    'sat':       ('sat', float),
    'satbias':   ('satbias', float),
}


def morph_spec(value):
    """
    parse a --morph argument: name,start,end[,lin|log]
    """
    parts = value.split(',')
    if len(parts) not in (3, 4):
        raise ArgumentTypeError(
            f"--morph takes name,start,end[,lin|log] (e.g. harmonics,1,512,log), "
            f"got '{value}'")
    name = parts[0].strip()
    if name not in MORPHABLE:
        raise ArgumentTypeError(
            f"'{name}' is not morphable; choose from: {', '.join(MORPHABLE)}")
    try:
        start, end = float(parts[1]), float(parts[2])
    except ValueError as exc:
        raise ArgumentTypeError(f"--morph {name}: start and end must be numbers") from exc
    if start == end:
        raise ArgumentTypeError(f"--morph {name}: start and end are the same value")
    curve = parts[3].strip() if len(parts) == 4 else 'lin'
    if curve not in ('lin', 'log'):
        raise ArgumentTypeError(f"--morph {name}: curve is lin or log, not '{curve}'")
    if curve == 'log' and (start <= 0 or end <= 0):
        raise ArgumentTypeError(
            f"--morph {name}: a log sweep needs both ends above zero")
    return (name, start, end, curve)


# morphing sawtooth modes: flag value -> title word
SAW_MODES = {
    'ramp': 'plain ramp',
    'harm': 'harmonics',
    'skew': 'skew',
    'pow': 'power',
    'rc': 'RC',
}

defaults = {
    "num_waveforms": 256,
    "num_samples": 2048,
    "bitwidth": 32,
    "dpi": 200,
    "fontsize": 8,
    "exponent": 5,
    "mid_width_pct": 90,
    "mid_yoffset": 25
}

def setup_parser():
    """
    configure all the flags and defaults
    """
    argp = ArgumentParser()

    # General options
    argp.add_argument("-D", action="store_true", dest="debug", help="Print a lot of debug messages")

    # Waveform options
    waveform_group = argp.add_argument_group("Waveform options")
    waveform_group.add_argument("-w", dest="num_waveforms", type=int,
                                default=defaults['num_waveforms'],
                                help="Number of waveforms; 1 renders the last, "
                                     "fully morphed frame (default: %(default)s)")
    waveform_group.add_argument(
        "-s", dest="num_samples", type=int,
        choices=[2**i for i in range(4, 13)], default=defaults['num_samples'],
        help="Number of samples in waveform (default: %(default)s)"
    )
    waveform_group.add_argument(
        "--16", dest="bitwidth", action='store_const', const=16, default=defaults['bitwidth'],
        help="Make 16-bit wavetable (default: %(default)s)"
    )
    waveform_group.add_argument("-m", dest="mid_width_pct", type=int,
                                default=defaults['mid_width_pct'],
                                help="Middle part width in %% (default: %(default)s)")
    waveform_group.add_argument("-o", dest="mid_yoffset", type=int, default=defaults['mid_yoffset'],
                               help="Offset from y-axis in %% (default: %(default)s)")
    waveform_group.add_argument("-e", dest="exp", type=int, choices=range(2, 10),
                                default=defaults['exponent'],
                                help="Exponent of curve (default: %(default)s)")
    waveform_group.add_argument("--tanh", dest="tanh", type=float,
                              help="Hyperbolic float tangent, e.g. 4.0")
    waveform_group.add_argument("-B", dest="bezier", type=float,
                               help="Bezier control point float multiplier, best -9.0..4.0")
    waveform_group.add_argument("-L", action='store_true', dest="dline",
                               help="Direct line instead of curve")
    waveform_group.add_argument("--saw", dest="saw", choices=list(SAW_MODES),
                                help="Morphing sawtooth: ramp holds a plain saw in "
                                     "every frame, for a table whose motion comes "
                                     "entirely from --morph; harm morphs sine to saw "
                                     "by adding harmonics, skew morphs reverse saw "
                                     "to saw through triangle, pow and rc morph the "
                                     "ramp curvature from linear to power-bent "
                                     "or RC capacitor charge shaped")
    waveform_group.add_argument("--harmonics", dest="harmonics", type=int,
                                help="Band-limit every waveform to this many harmonics, "
                                     "e.g. 32; morphable")
    waveform_group.add_argument("--neg", dest="neg", type=float,
                                help="Scale the negative half of the waveform, e.g. 0.5 "
                                     "for the asymmetry of a hardware oscillator; DC is "
                                     "removed and the peak restored afterwards; morphable")
    waveform_group.add_argument("--sat", dest="sat", type=float,
                                help="Drive the waveform through tanh, e.g. 1.26; the "
                                     "asymmetric soft clipping of an analog oscillator "
                                     "stage when paired with --satbias; zero or less "
                                     "disables it, mid-morph frames included; morphable")
    waveform_group.add_argument("--satbias", dest="satbias", type=float,
                                help="Offset fed into --sat, e.g. 0.63, which compresses "
                                     "one half of the waveform more than the other; DC is "
                                     "removed afterwards; morphable")
    waveform_group.add_argument("--morph", dest="morph", type=morph_spec, action='append',
                                metavar="NAME,START,END[,lin|log]",
                                help="Sweep a parameter across the wavetable: START in the "
                                     "first waveform, END in the last, and the value the "
                                     "flag itself carries in the middle one. Add ,log for "
                                     "a geometric sweep, which is what a harmonic count or "
                                     "any other ratio-like quantity wants. Repeatable. "
                                     f"Morphable: {', '.join(MORPHABLE)}")
    waveform_group.add_argument("--rev", action='store_true', dest="reverse",
                                help="Reverse waveform")
    waveform_group.add_argument("--shift", dest="shift", type=int,
                                help="Shift (roll) waveform, int samples")
    waveform_group.add_argument("--norm", dest="norm", type=restricted_float1,
                                help="Normalize every waveform to this peak, float, e.g. 0.8")
    waveform_group.add_argument("--rms", action='store_true', dest="rms",
                                help="Normalize every waveform to the same RMS, so that "
                                     "sweeping the wavetable position changes timbre and "
                                     "not loudness; the table is peak-normalized as a "
                                     "whole afterwards. Not usable with --norm, which "
                                     "equalizes peaks instead and is what causes the "
                                     "drift.")

    # Filter options
    filter_group = argp.add_argument_group("Filter options")
    filter_group.add_argument("--savgol", dest="savgol", type=tuple_2int,
                              help="Savitzky-Golay filter window_len(%%),polyorder, e.g. 51,3")
    filter_group.add_argument("--gauss", dest="gauss", type=int,
                              help="Gaussian filter int sigma, e.g. 2")
    filter_group.add_argument("--bitcrush", dest="bitcrush", type=int,
                              help="Bitcrush int depth, e.g. 5")

    # Output options
    output_group = argp.add_argument_group("Output options")
    output_group.add_argument("--graph", action="store_true", dest="graph", help="Plot graph")
    output_group.add_argument("--graph3d", action="store_true", dest="graph3d",
                              help="Plot 3D graph")
    output_group.add_argument("--png", action="store_true", dest="png",
                              help="Save graph to png file")
    output_group.add_argument("--wav", action="store_true", dest="wav", help="Save wav")
    output_group.add_argument("--wt", action="store_true", dest="wt", help="Save wt (Bitwig/Surge)")
    output_group.add_argument("--h2p", action="store_true", dest="h2p",
                              help="Save Zebra 2 OSC h2p, forced 128 samples / 16 waveforms")
    output_group.add_argument("--gif", action="store_true", dest="gif", help="Save gif animation")
    output_group.add_argument("--dpi", dest="dpi", type=int,
                              help="Graph/gif DPI (default: %(default)s)", default=defaults["dpi"])
    output_group.add_argument("--fontsize", dest="fontsize", type=int,
                              help="Graph/gif fontsize (default: %(default)s)",
                              default=defaults["fontsize"])
    output_group.add_argument("-O", action="store_true", dest="open", help="Open gif")
    output_group.add_argument("--fullfn", action="store_true", dest="fullname",
                              help="Add full info to file name")

    return argp
