#!/bin/bash
# called for test_gdasapp_util_prepdata, and by
# test/soca/gw/setup_obsproc.sh for test_gdasapp_soca_setup_obsproc


set -e

cdl2nc4() {

  local output_nc4="$1"
  local input_cdl="$2"

  echo "Generating ${output_nc4}"
  ncgen -o "$output_nc4" "$input_cdl"
}

project_source_dir=$1

cdldir=${project_source_dir}/test/soca/testdata

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
cdl2nc4 icec/AMSR2-SEAICE-NH_v2r2_GW1_s201804151014190_e201804151150170_c201804151309570.nc \
        ${project_source_dir}/test/soca/testdata/icec_amsr2_south_2.cdl

# Fake RADS ADT
cdl2nc4 ADT/rads_adt_3a_2018105.nc ${project_source_dir}/test/soca/testdata/rads_adt_3a_2018105.cdl
cdl2nc4 ADT/rads_adt_3b_2018105.nc ${project_source_dir}/test/soca/testdata/rads_adt_3b_2018105.cdl
