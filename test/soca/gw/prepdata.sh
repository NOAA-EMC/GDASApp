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

#cdl2nc4 ADT/rads_adt_3a_2021181.nc4 ${project_source_dir}/testdata/rads_adt_3a_2021181.cdl
#cdl2nc4 ADT/rads_adt_3b_2021181.nc4 ${project_source_dir}/testdata/rads_adt_3b_2021181.cdl
#cdl2nc4 icec/icec_amsr2_north_1.nc4 ${project_source_dir}/testdata/icec_amsr2_north_1.cdl
#cdl2nc4 icec/icec_amsr2_north_2.nc4 ${project_source_dir}/testdata/icec_amsr2_north_2.cdl
#cdl2nc4 icec/icec_amsr2_south_1.nc4 ${project_source_dir}/testdata/icec_amsr2_south_1.cdl
#cdl2nc4 icec/icec_amsr2_south_2.nc4 ${project_source_dir}/testdata/icec_amsr2_south_2.cdl
#cdl2nc4 SSS/sss_smap_1.nc4 ${project_source_dir}/testdata/sss_smap_1.cdl
#cdl2nc4 SSS/sss_smap_2.nc4 ${project_source_dir}/testdata/sss_smap_2.cdl
#cdl2nc4 SSS/sss_smos_1.nc4 ${project_source_dir}/testdata/sss_smos_1.cdl
#cdl2nc4 SSS/sss_smos_2.nc4 ${project_source_dir}/testdata/sss_smos_2.cdl
#cdl2nc4 sst/ghrsst_sst_mb_202107010000.nc4 ${project_source_dir}/testdata/ghrsst_sst_mb_202107010000.cdl
#cdl2nc4 sst/ghrsst_sst_mb_202107010100.nc4 ${project_source_dir}/testdata/ghrsst_sst_mb_202107010100.cdl
#cdl2nc4 sst/viirs_aod_1.nc4 ${project_source_dir}/testdata/viirs_aod_1.cdl
#cdl2nc4 sst/viirs_aod_2.nc4 ${project_source_dir}/testdata/viirs_aod_2.cdl

cdl2nc4 sst/20180415114000-STAR-L3U_GHRSST-SSTsubskin-AVHRRF_MB-ACSPO_V2.80-v02.0-fv01.0.nc ${project_source_dir}/test/soca/testdata/20180415114000-STAR-L3U_GHRSST-SSTsubskin-AVHRRF_MB-ACSPO_V2.80-v02.0-fv01.0.cdl
cdl2nc4 sst/20180415132000-STAR-L3U_GHRSST-SSTsubskin-AVHRRF_MB-ACSPO_V2.80-v02.0-fv01.0.nc ${project_source_dir}/test/soca/testdata/20180415132000-STAR-L3U_GHRSST-SSTsubskin-AVHRRF_MB-ACSPO_V2.80-v02.0-fv01.0.cdl
cdl2nc4 sst/20180415095000-STAR-L3U_GHRSST-SSTsubskin-AVHRRF_MB-ACSPO_V2.80-v02.0-fv01.0.nc ${project_source_dir}/test/soca/testdata/20180415095000-STAR-L3U_GHRSST-SSTsubskin-AVHRRF_MB-ACSPO_V2.80-v02.0-fv01.0.cdl


