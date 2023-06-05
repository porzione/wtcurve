#!/usr/bin/env python
# -*- coding: utf-8 -*-

from argparse import ArgumentParser, ArgumentTypeError


def tuple_2int(value):
    try:
        items = [int(x) for x in value.split(",")]
        if len(items) != 2:
            raise ArgumentTypeError("Tuple argument must contain 2 ints separated by a comma")
        return tuple(items)
    except:
        raise ArgumentTypeError("Invalid tuple argument")

#def tuple_2float(value):
#    try:
#        items = [float(x) for x in value.split(",")]
#        if len(items) != 2:
#            raise ArgumentTypeError("Tuple argument must contain 2 floats separated by a comma")
#        return tuple(items)
#    except:
#        raise ArgumentTypeError("Invalid tuple argument")


def setup_parser():
    argp = ArgumentParser()

    # Default values
    defaults = {
        "num_waveforms": 256,
        "num_samples": 2048,
        "bitwidth": 32,
        "dpi": 200,
        "fontsize": 8,
        "exponent": 5,
        "mid_width_pct": 60,
        "mid_yoffset": 25
    }

    # General options
    argp.add_argument("-D", action="store_true", dest="debug", help="Enable debug mode")

    # Waveform options
    waveform_group = argp.add_argument_group("Waveform options")
    waveform_group.add_argument("-w", dest="num_waveforms", type=int, default=defaults['num_waveforms'],
                               help="Number of waveforms (default: %(default)s)")
    waveform_group.add_argument(
        "-s", dest="num_samples", type=int, choices=[2**i for i in range(4, 13)], default=defaults['num_samples'],
        help="Number of samples in waveform (default: %(default)s)"
    )
    waveform_group.add_argument(
        "--16", dest="bitwidth", action='store_const', const=16, default=defaults['bitwidth'],
        help="Make 16-bit wavetable (default: %(default)s)"
    )
    waveform_group.add_argument("-m", dest="mid_width_pct", type=int, default=defaults['mid_width_pct'],
                               help="Middle part width in %% (default: %(default)s)")
    waveform_group.add_argument("-o", dest="mid_yoffset", type=int, default=defaults['mid_yoffset'],
                               help="Offset from y-axis in %% (default: %(default)s)")
    waveform_group.add_argument("-e", dest="exp", type=int, choices=range(2, 10), default=defaults['exponent'],
                               help="Exponent of curve (default: %(default)s)")
    waveform_group.add_argument("-B", dest="bezier", type=float, help="Bezier control points float multiplier")
    waveform_group.add_argument("-L", action='store_true', dest="direct", help="Use direct line instead of curve")

    # Filter options
    filter_group = argp.add_argument_group("Filter options")
    filter_group.add_argument("--savgol", dest="savgol", type=tuple_2int, help="Savitzky-Golay filter window_length_pct(%%),polyorder, e.g. '51,3'")
    filter_group.add_argument("--gauss", dest="gauss", type=int, help="Gaussian filter int sigma, e.g. 2")
    filter_group.add_argument("--bitcrush", dest="bitcrush", type=int, help="Bitcrush int depth, e.g. 5")
    filter_group.add_argument("--tanh", dest="tanh", type=float, help="Hyperbolic float tangent, e.g. 4.0")
    filter_group.add_argument("--dco", action='store_true', dest="dco", help="Apply DC offset WIP!")

    # Output options
    output_group = argp.add_argument_group("Output options")
    output_group.add_argument("--graph", action="store_true", dest="graph", help="Plot graph")
    output_group.add_argument("--graph3d", action="store_true", dest="graph3d", help="Plot 3D graph")
    output_group.add_argument("--png", action="store_true", dest="png", help="Save graph to png file")
    output_group.add_argument("--wav", action="store_true", dest="wav", help="Save wav")
    output_group.add_argument("--wt", action="store_true", dest="wt", help="Save wt (Bitwig/Surge)")
    output_group.add_argument("--h2p", action="store_true", dest="h2p", help="Save Zebra OSC h2p")
    output_group.add_argument("--gif", action="store_true", dest="gif", help="Save gif animation")
    output_group.add_argument("--dpi", dest="dpi", type=int, help="Graph/gif DPI (default: %(default)s)", default=defaults["dpi"])
    output_group.add_argument("--fontsize", dest="fontsize", type=int, help="Graph/gif fontsize (default: %(default)s)", default=defaults["fontsize"])
    output_group.add_argument("-O", action="store_true", dest="open", help="Open gif")
    output_group.add_argument("--fullfn", action="store_true", dest="fullname", help="Add full info to file name")

    return argp
