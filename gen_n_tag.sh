#!/bin/bash

m_start=25
m_end=75
m_step=25

o_start=20
o_end=80
o_step=20

for ((m=m_start; m<=m_end; m+=m_step)); do
  for ((o=o_start; o<=o_end; o+=o_step)); do
    ./wtcurve -m $m -o $o --wav
    ./wtcurve -m $m -o $o --wav -B
  done
done

for w in *e_*.wav; do ./wttag -s 2048 -w 256 --clm -i $w -m -o /home/ftp/audio/Wavetables/WT1/My/exponential/$w; done
for w in *_bz_*.wav; do ./wttag -s 2048 -w 256 --clm -i $w -m -o /home/ftp/audio/Wavetables/WT1/My/bezier/$w; done
