#!/bin/bash

[[ -z "$IKNOWWHATIDO" ]] && exit 1

directories=(
    "/home/ftp/audio/Wavetables/WT2/KimuraTaroFree"
    "/home/ftp/audio/Wavetables/WT2/KimuraTaroAnalog"
    "/home/ftp/audio/Wavetables/WT2/KimuraTaroBox"
    "/home/ftp/audio/Wavetables/WT2/OceanSwift"
)

old_path="WT2"
new_path="WT1"

for dir in "${directories[@]}"; do
    find "$dir" -type f -name "*.wav" | while read -r file; do
        new_file=${file//$old_path/$new_path}
        echo ./wttag -s 2048 -i "$file" -o "$new_file" --clm -m
    done
done
