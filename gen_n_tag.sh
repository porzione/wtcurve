#!/bin/bash

# destination paths for tagged files
wav_path=/home/ftp/audio/Wavetables/WT1/My
wt_path=~/Music/Bitwig/Library/Wavetables/WT1/My
h2p_path=~/.u-he/Zebra2/Modules/Oscillator/My
# samples
sa=2048
# waveforms
wa=256
# waveforms in simple tables
wl=64

echo bitcrush
for bitcrush in 3 4 5; do
  ./wtcurve --fullfn -s $sa -w $wa --bitcrush $bitcrush --wav --gif
  ./wtcurve --fullfn -s $sa -w $wa --bitcrush $bitcrush --wt --16
  ./wtcurve --bitcrush $bitcrush --h2p
done

tanh=5
o=5
echo tanh=$tanh o=$o
# need smaller offset
./wtcurve --fullfn -s $sa -w $wa -o $o --tanh $tanh --wav --gif
./wtcurve --fullfn -s $sa -w $wa -o $o --tanh $tanh --wt --16
./wtcurve --fullfn -s $sa -w $wa -o $o --tanh $tanh -L --wav --gif
./wtcurve --fullfn -s $sa -w $wa -o $o --tanh $tanh -L --wt --16
./wtcurve --tanh $tanh -o $o --h2p
./wtcurve --tanh $tanh -o $o --h2p -L

gauss=40
echo gauss=$gauss
./wtcurve --fullfn -s $sa -w $wa --gauss $gauss --wav --gif
./wtcurve --fullfn -s $sa -w $wa --gauss $gauss --wt --16
./wtcurve --fullfn -s $sa -w $wa --gauss $gauss -B --wav --gif
./wtcurve --fullfn -s $sa -w $wa --gauss $gauss -B --wt --16
./wtcurve --gauss $gauss --h2p

savgol=10
echo savgol=$savgol
./wtcurve --fullfn -s $sa -w $wa --savgol ${savgol},3 --wav --gif
./wtcurve --fullfn -s $sa -w $wa --savgol ${savgol},3 --wt --16
./wtcurve --fullfn -s $sa -w $wa --savgol ${savgol},3 -B --wav --gif
./wtcurve --fullfn -s $sa -w $wa --savgol ${savgol},3 -B --wt --16
./wtcurve -w $wa --savgol ${savgol},3 --h2p

echo variable offset
for o in 25 35; do
  ./wtcurve --fullfn -s $sa -w $wa -o $o --wav --gif
  ./wtcurve --fullfn -s $sa -w $wa -o $o --wav -B --gif
  ./wtcurve --fullfn -s $sa -w $wl -o $o --wav -L --gif
  ./wtcurve --fullfn -s $sa -w $wa -o $o --wt --16
  ./wtcurve --fullfn -s $sa -w $wa -o $o --wt -B --16
  ./wtcurve --fullfn -s $sa -w $wl -o $o --wt -L --16
  ./wtcurve -o $o --h2p
  ./wtcurve -o $o --h2p -B
  ./wtcurve -o $o --h2p -L
done

echo variable exp
for e in {4..9}; do
  if [[ $e -ne 5 ]] ; then
    ./wtcurve --fullfn -s $sa -w $wa -e $e --wav
    ./wtcurve --fullfn -s $sa -w $wa -e $e --wt --16
    ./wtcurve -e $e --h2p
  fi
done

test -d "$wav_path" || exit
test -d "$wt_path" || exit
test -d "$h2p_path" || exit

echo tagging
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

