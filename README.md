# wtcurve
Generate morphing exponential wavetables for audio synthesis 

32-bit float wav wavetables tested with Linux versions of Surge XT, Bitwig Grid/Polymer, u-he Hive 2, Vital software synthesizers. 

Currently, only one waveform is supported, a corrected exponential function with a plot reflected on the x and y axes with a square central part. This is a very typical waveform for modern EDM/Psytrance bass sound. Script can plot the graph as well.

Defaults: 32 bit float wav, 256 waveforms, 2048 files.

Requirements: python 3.x with numpy, matplotlib, soundfile.

Surely there are bugs here. 

We have help:

```
$ ./wtcurve --help
usage: wtcurve [-h] [-w NUM_WAVEFORMS] [-s {8,16,32,64,128,256,512,1024,2048}] [--bits {16,32}] [-m MID_WIDTH_PCT] [-o MID_HOFFSET] [-e {2,3,4,5,6,7,8,9}] [--graph] [--wav] [-D]

options:
  -h, --help            show this help message and exit
  -w NUM_WAVEFORMS      Number of frames/waveforms (256)
  -s {8,16,32,64,128,256,512,1024,2048}
                        Number of samples in one frame (2048)
  --bits {16,32}        Bits (32)
  -m MID_WIDTH_PCT      Percents in middle part (20)
  -o MID_HOFFSET        Percents of middle horizontal offset from y=0 (20)
  -e {2,3,4,5,6,7,8,9}  Exponent of curve (5)
  --graph               Plot graph
  --wav                 Save wav
  -D                    Debug
  ```
  
  Try to play with with `-m` from 20 to 50, `-o` from 20 to 70, `-e` with indicated range. Check the graph with `--graph` - it will show first and last frame.
  
  ## to be continued
