#!/bin/bash

wav_path=/home/ftp/audio/Wavetables/WT1/My
wt_path=~/Music/Bitwig/Library/Wavetables/WT1/My
h2p_path=~/.u-he/Zebra2/Modules/Oscillator/My/
sa=2048
wa=256

##for c_wa in 64 128 ; do
##  ./wtcurve --fullfn -s $sa -w $c_wa --wav
##  ./wtcurve --fullfn -s $sa -w $c_wa --wt --bits 16
##  ./wtcurve --fullfn -s $sa -w $c_wa -B --wav
##  ./wtcurve --fullfn -s $sa -w $c_wa -B --wt --bits 16
##  ./wtcurve --fullfn -s $sa -w $c_wa -L --wav
##  ./wtcurve --fullfn -s $sa -w $c_wa -L --wt --bits 16
##done

echo gauss
for ga in 2 4 6; do
  ./wtcurve --fullfn -s $sa -w $wa --gauss $ga --wav
  ./wtcurve --fullfn -s $sa -w $wa --gauss $ga --wt --bits 16
  ./wtcurve --gauss $ga --h2p
done

echo savgol
for sg in 20 50; do
  ./wtcurve --fullfn -s $sa -w $wa --savgol ${sg},3 --wav
  ./wtcurve --fullfn -s $sa -w $wa --savgol ${sg},3 --wt --bits 16
  ./wtcurve --savgol ${sg},3 --h2p
done

echo variable m/o
for ((m=30; m<=90; m+=30)); do
  for ((o=25; o<=40; o+=5)); do
    ./wtcurve --fullfn -s $sa -w $wa -m $m -o $o --wav
    ./wtcurve --fullfn -s $sa -w $wa -m $m -o $o --wav -B
    ./wtcurve --fullfn -s $sa -w 128 -m $m -o $o --wav -L
    ./wtcurve --fullfn -s $sa -w $wa -m $m -o $o --wt --bits 16
    ./wtcurve --fullfn -s $sa -w $wa -m $m -o $o --wt -B --bits 16
    ./wtcurve --fullfn -s $sa -w 128 -m $m -o $o --wt -L --bits 16
    ./wtcurve -m $m -o $o --h2p
    ./wtcurve -m $m -o $o --h2p -B
    ./wtcurve -m $m -o $o --h2p -L
  done
done

echo variable o with gauss/savgol
for o in 25 35 50; do
  ./wtcurve --fullfn -s $sa -w $wa -o $o --wav --gif -L --gauss 1
  ./wtcurve --fullfn -s $sa -w $wa -o $o --wav --gif -L --savgol 51,3
  ./wtcurve --fullfn -s $sa -w 128 -o $o --wt --bits 16 -L --gauss 1
  ./wtcurve --fullfn -s $sa -w 128 -o $o --wt --bits 16 -L --savgol 51,3
  ./wtcurve -L --gauss 1 --h2p
  ./wtcurve -L --savgol 51,3 --h2p
done

for e in {2..9}; do
  if [[ $e -ne 5 ]] ; then
    ./wtcurve --fullfn -s $sa -w $wa -e $e --wav
    ./wtcurve --fullfn -s $sa -w $wa -e $e --wt --bits 16
    ./wtcurve -e $e --h2p
  fi
done

shopt -s extglob
pat_ext="\.(\w+)$"
pat_wa="([0-9]+)w"
pat_sa="([0-9]+)s"
pat_ty="_(dl|bz|[0-9]e)_"
for file in *.wav *.wt ; do
  echo FILE: $file
  if [[ $file =~ $pat_ext ]] ; then
    ext=${BASH_REMATCH[1]}
  fi
  if [[ $file =~ $pat_wa ]] ; then
    c_wa=${BASH_REMATCH[1]}
  fi
  if [[ $file =~ $pat_sa ]] ; then
    c_sa=${BASH_REMATCH[1]}
  fi
  if [[ $file =~ $pat_ty ]] ; then
    c_ty=${BASH_REMATCH[1]}
  fi
  #echo ext: $ext wa: $c_wa sa: $c_sa ty: $c_ty
  case "$c_ty" in
    [0-9]e)
      ty_path="exp"
      ;;
    bz)
      ty_path="bezier"
      ;;
    dl)
      ty_path="dline"
      ;;
    *)
      echo no ty
      exit
  esac
  name2=$(echo "$file"|sed 's/_[0-9]\+s_[0-9]\+w//g')
  case "$ext" in
    "wav")
      ./wttag -s $c_sa -w $c_wa --clm --of -i $file -o $wav_path/$ty_path/$name2 -m
      ;;
    "wt")
      destdir="$wt_path/$ty_path"
      [ -d "$destdir" ] || mkdir -p "$destdir"
      cp -v "$file" $destdir/$name2
      ;;
  esac
done

rsync *.h2p $h2p_path/

