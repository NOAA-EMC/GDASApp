#!/bin/bash
set -ex

# Ensure project source directory is provided as argument
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <project_source_dir>"
    exit 1
fi

project_source_dir="$1"
testdatadir="${project_source_dir}/test/soca/testdata"

# Define PDYs, cycs, and obstypes
PDYs=("20180414" "20180415")
cycs=("00" "06" "12" "18")
obstypes=("SSS" "ADT" "icec" "sst")

# Convert cdl files into nc for all cycles and obstypes
for PDY in "${PDYs[@]}"; do
    PDYdir="gdas.${PDY}"
    for cyc in "${cycs[@]}"; do
        for obstype in "${obstypes[@]}"; do
            fullsubdir="$PDYdir/$cyc/$obstype"
            mkdir -p "$fullsubdir"

            indir="${testdatadir}/${fullsubdir}"
            for file in "$indir"/*.cdl; do
                if [ -f "$file" ]; then
                    filename=$(basename -- "$file")
                    filename_noext="${filename%.cdl}"
                    ncgen -o "$fullsubdir/${filename_noext}.nc" "$file"
                fi
            done
        done
    done
done
