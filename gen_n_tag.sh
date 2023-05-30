#!/bin/bash


m_start=30
m_end=90
m_step=30

o_start=20
o_end=35
o_step=5

for ((m=m_start; m<=m_end; m+=m_step)); do
  for ((o=o_start; o<=o_end; o+=o_step)); do
    ./wtcurve -m $m -o $o --wav
    ./wtcurve -m $m -o $o --wav -B
    ./wtcurve -m $m -o $o --wt
    ./wtcurve -m $m -o $o --wt -B
  done
done

for e in {2..9}; do
  if [[ $e -ne 5 ]] ; then
    ./wtcurve -e $e --wav --wt
    ./wtcurve -e $e --h2p
  fi
done

find . -maxdepth 1 -type f -regex ".*[0-9]e.*\.wav" | while IFS= read -r file; do
    ./wttag -s 2048 -w 256 --clm --of -i $file -m -o /home/ftp/audio/Wavetables/WT1/My/exponential/$file
done
find . -maxdepth 1 -type f -regex ".*bz.*\.wav" | while IFS= read -r file; do
    ./wttag -s 2048 -w 256 --clm --of -i $file -m -o /home/ftp/audio/Wavetables/WT1/My/bezier/$file
done

rsync *e_*.wt ~/Music/Bitwig/Library/Wavetables/WT1/My/exponential/
rsync *_bz_*.wt ~/Music/Bitwig/Library/Wavetables/WT1/My/bezier/

rsync *.h2p ~/.u-he/Zebra2/Modules/Oscillator/My/
