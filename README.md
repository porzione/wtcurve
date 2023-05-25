# wtcurve

Tool for generating morphing wavetables used in audio synthesis.

I have tested the 32-bit float WAV wavetables with the Linux versions of Surge XT, Bitwig Grid/Polymer, u-he Hive 2, and the Vital software synthesizers.

Currently, the software supports only one waveform, which is a modified exponential function. The function's plot is reflected on both the x and y axes, featuring a square central part. This waveform is commonly used in modern EDM/Psytrance bass sounds. The script also has the capability to generate a visual graph of the waveform

![Default waveforms](images/Figure_1.png)

Defaults: 32 bit float WAV, 256 waveforms, 2048 samples.

Requirements: python 3.x with numpy, matplotlib, soundfile.

Surely there are bugs here.

We have help:

```text
wtcurve --help
usage: wtcurve [-h] [-w NUM_WAVEFORMS] [-s {16,32,64,128,256,512,1024,2048,4096}] [--bits {16,32}] [-m MID_WIDTH_PCT] [-o MID_HOFFSET] [-e {2,3,4,5,6,7,8,9}] [--graph] [--dpi DPI] [--wav] [-D]

options:
  -h, --help            show this help message and exit
  -w NUM_WAVEFORMS      Number of frames/waveforms (256)
  -s {16,32,64,128,256,512,1024,2048,4096}
                        Number of samples in one frame (2048)
  --bits {16,32}        Bits width (32)
  -m MID_WIDTH_PCT      Percents in middle part (20)
  -o MID_HOFFSET        Percents of middle horizontal offset from y=0 (20)
  -e {2,3,4,5,6,7,8,9}  Exponent of curve (5)
  --graph               Plot graph
  --dpi DPI             Graph DPI
  --wav                 Save wav
  -D                    Debug
```

Try to play with `-m` from 20 to 50, `-o` from 20 to 70, `-e` with indicated range. Check the graph with `--graph`, it will show first and last frames.

# wttag

To ensure compatibility with most synthesizers, wavetables need to be tagged with the wttag script, using the same -w and -s values as specified for the wtcurve. This script adds a WAV chunk to the WAV file, indicating the number of waveforms or samples based on the chunk type. In most cases, using --clm should work fine. Please note that I am unable to test the output WAVs with Serum as I don't have access to it. Example:

```text
wttag -s 2048 -w 256 -i wtc_20m_20h_5e_2048s_256w_32b.wav -o wtv_clm.wav --clm
```

## to be continued

## (C)

All the aforementioned products are the property of their respective creators or owners.

## Warnings

Please make use of backups. While I have taken precautions to avoid overwriting or damaging any existing precious wavetables, unforeseen circumstances can occur. Use backups.
