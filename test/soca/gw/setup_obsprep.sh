#!/bin/bash
set -ex

# working directory as set in cmake assumed to be ${PROJECT_BINARY_DIR}/test/soca/gw/obsprep
# which is the soca ctest's fake dmpdir
# Ensure project source directory is provided as argument
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <project_source_dir>"
    exit 1
fi

project_source_dir="$1"
testdatadir="${project_source_dir}/test/soca/testdata"

#clean up previous attempts
rm -rf gdas.20180414  gdas.20180415

# Define PDYs, cycs, and obstypes
PDYs=("20180414" "20180415")
cycs=("00" "06" "12" "18")
obstypes=("insitu" "sss" "adt" "icec" "sst")

# Convert cdl files into nc for all cycles and obstypes
for PDY in "${PDYs[@]}"; do
    PDYdir="gdas.${PDY}"
    for cyc in "${cycs[@]}"; do
        for obstype in "${obstypes[@]}"; do
            if [ $obstype != "insitu" ]; then
                fullsubdir="$PDYdir/$cyc/ocean/$obstype"
            else
                fullsubdir="$PDYdir/$cyc/atmos"
            fi
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
#echo "Copy subsampled BUFR into atmos directory..."
#for f in ${project_source_dir}/build/gdas/test/testdata/*_subsampled; do
#    cp -p $f atmos/
#done
