# Wavetable generator for audio synthesis

## wtcurve

I have tested the 32-bit float WAV wavetables with the Linux versions of [Surge XT](https://surge-synthesizer.github.io/), Bitwig [Grid](https://www.bitwig.com/the-grid/)/[Polymer](https://www.bitwig.com/polymer/), [u-he Hive 2](https://u-he.com/products/hive/), and the [Vital](https://vital.audio/) software synthesizers. Other supported formats are: [u-he Zebra 2](https://u-he.com/products/zebra-legacy/) oscillator h2p wavesets, Bitwig and Surge XT wt wavetables (32-bit only).

Currently, wtcurve supports the generation of a single waveform, which can be defined either as a modified exponential function or a Bezier curve. The function's plot is reflected on both the x and y axes, featuring a linear central part. This waveform is commonly used in modern EDM/Psytrance bass sounds. The script also has the capability to generate graph or animated gif of the waveform. The waveform transformation occurs by adjusting the tilt of the center line from a vertical position to a customized angle, where the center line occupies the percentage of the total width specified by the `-m` option.

![Exponential waveforms](images/wtc_60m_25h_5e_anim.gif)

![Bézier waveforms](images/wtc_60m_25h_bz_anim.gif)

Bitwig 3D previews of wavetables that are generated using various parameters
![Bitwig previews](images/bitwig_previews.png)

Defaults: 32 bit float WAV, 256 waveforms, 2048 samples. File size with these parameters is ~2.1Mb

Requirements: Python 3 with [NumPy](https://numpy.org/install/), [Matplotlib](https://matplotlib.org), [soundfile](https://github.com/bastibe/python-soundfile).

Surely there are bugs here.

We have help:

```text
$ wtcurve --help

usage: wtcurve [-h] [-w NUM_WAVEFORMS] [-s {16,32,64,128,256,512,1024,2048,4096}] [--bits {16,32}] [-m MID_WIDTH_PCT] [-o MID_YOFFSET] [-e {2,3,4,5,6,7,8,9}]
               [-B] [--graph] [--wav] [--wt] [--h2p] [--gif] [--dpi DPI] [-O] [-D]

options:
  -h, --help            show this help message and exit
  -w NUM_WAVEFORMS      Number of waveforms (256)
  -s {16,32,64,128,256,512,1024,2048,4096}
                        Number of samples in waveform (2048)
  --bits {16,32}        Bit width (32)
  -m MID_WIDTH_PCT      Middle part width in % (60)
  -o MID_YOFFSET        Offset from y-axis in % (25)
  -e {2,3,4,5,6,7,8,9}  Exponent of curve (5)
  -B                    Build Bezier curve instead of exponent
  --graph               Plot graph
  --wav                 Save wav
  --wt                  Save wt (Bitwig/Surge)
  --h2p                 Save Zebra OSC h2p
  --gif                 Save gif animation
  --dpi DPI             Graph/gif DPI (200)
  -O
  -D                    Debug
```

Try to play with `-m` from 20 to 80, `-o` from 20, `-e` with indicated range. Check the graph with `--graph`, it will show first and last frames. Or check the animation with `--gif`.

## wttag

To ensure compatibility with most synthesizers, wavetables need to be tagged with the wttag script, using the same -w and -s values as specified for the wtcurve. This script adds a WAV chunk to the WAV file, indicating the number of waveforms or samples based on the chunk type. In most cases, using --clm should work fine. Please note that I am unable to test the output WAVs with Serum as I don't have access to it. Example:

```text
wttag -s 2048 -w 256 -i wtc_20m_20h_5e_2048s_256w_32b.wav -o wtv_clm.wav --clm
```

### to be continued

## (C)

All the aforementioned products are the property of their respective creators or owners.

## Warnings

Please make use of backups. While I have taken precautions to avoid overwriting or damaging any existing precious wavetables, unforeseen circumstances can occur. Use backups.
