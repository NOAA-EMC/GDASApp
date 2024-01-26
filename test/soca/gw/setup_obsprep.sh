#!/bin/bash
set -ex

# working directory should be ${PROJECT_BINARY_DIR}/test/soca/gw/obsprep, set in ctest command

project_source_dir=$1


cdl2nc4() {

  local output_nc4="$1"
  local input_cdl="$2"

  echo "Generating ${output_nc4}"
  ncgen -o "$output_nc4" "$input_cdl"
}

PDYs=("20180414" "20180415")

# List of cycs
cycs=("00" "06" "12" "18")

# List of obstypes
obstypes=("SSS" "ADT" "icec" "sst")

testdatadir=${project_source_dir}/test/soca/testdata

# Iterate over PDYs
for PDY in "${PDYs[@]}"; do
    PDYdir=gdas.${PDY}
    # Create PDY directory
    mkdir -p "$PDYdir"

    # Iterate over cycs
    for cyc in "${cycs[@]}"; do
        # Create cyc directory
        mkdir -p "$PDYdir/$cyc"

        # Iterate over obstypes
        for obstype in "${obstypes[@]}"; do

            fullsubdir="$PDYdir/$cyc/$obstype"
            # Create obstype directory
            mkdir -p "$fullsubdir"

            indir=${testdatadir}/${fullsubdir}
            for file in "$indir"/*.cdl; do
                 if [ -f "$file" ]; then
                      filename=$(basename -- "$file")
                      filename_noext="${filename%.cdl}"
                      #cp "$file" $fullsubdir/"${filename_noext}.nc"
                      ncgen -o $fullsubdir/"${filename_noext}.nc" "$file"
                 fi
            done
        done
    done
done

exit


# GHRSST
cdl2nc4 sst/20180415114000-STAR-L3U_GHRSST-SSTsubskin-AVHRRF_MB-ACSPO_V2.80-v02.0-fv01.0.nc \
        ${cdldir}/20180415114000-STAR-L3U_GHRSST-SSTsubskin-AVHRRF_MB-ACSPO_V2.80-v02.0-fv01.0.cdl
cdl2nc4 sst/20180415132000-STAR-L3U_GHRSST-SSTsubskin-AVHRRF_MB-ACSPO_V2.80-v02.0-fv01.0.nc \
        ${cdldir}/20180415132000-STAR-L3U_GHRSST-SSTsubskin-AVHRRF_MB-ACSPO_V2.80-v02.0-fv01.0.cdl
cdl2nc4 sst/20180415095000-STAR-L3U_GHRSST-SSTsubskin-AVHRRF_MB-ACSPO_V2.80-v02.0-fv01.0.nc \
        ${cdldir}/20180415095000-STAR-L3U_GHRSST-SSTsubskin-AVHRRF_MB-ACSPO_V2.80-v02.0-fv01.0.cdl

# Fake AMSR2 icec
cdl2nc4 icec/AMSR2-SEAICE-NH_v2r2_GW1_s201804150835180_e201804151014170_c201804151052280.nc \
        ${project_source_dir}/test/soca/testdata/icec_amsr2_north_1.cdl
cdl2nc4 icec/AMSR2-SEAICE-NH_v2r2_GW1_s201804151014190_e201804151150170_c201804151309570.nc \
        ${project_source_dir}/test/soca/testdata/icec_amsr2_north_2.cdl
cdl2nc4 icec/AMSR2-SEAICE-SH_v2r2_GW1_s201804150835180_e201804151014170_c201804151052280.nc \
        ${project_source_dir}/test/soca/testdata/icec_amsr2_south_1.cdl
cdl2nc4 icec/AMSR2-SEAICE-SH_v2r2_GW1_s201804151014190_e201804151150170_c201804151309570.nc \
        ${project_source_dir}/test/soca/testdata/icec_amsr2_south_2.cdl



rm -rf ${test_dmpdir}
mkdir -p ${test_dmpdir}

cd ${test_dmpdir}

mkdir SSS ADT icec sst

${project_source_dir}/test/soca/gw/prepdata.sh ${project_source_dir}



