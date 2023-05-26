#!/bin/bash

directories=(
    "/home/ftp/audio/Wavetables/WT2/KimuraTaroFree"
    "/home/ftp/audio/Wavetables/WT2/KimuraTaroAnalog"
    "/home/ftp/audio/Wavetables/WT2/KimuraTaroBox"
    "/home/ftp/audio/Wavetables/WT2/OceanSwift"
)

old_base="/home/ftp/audio/Wavetables/WT2"
new_base="/home/ftp/audio/Wavetables/WT1"

for dir in "${directories[@]}"; do
    find "$dir" -type f -name "*.wav" | while read -r file; do
        new_file=${file//$old_base/$new_base}
        ./wttag -s 2048 -i "$file" -o "$new_file" --clm -m
    done
done
