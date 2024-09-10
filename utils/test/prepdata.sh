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


cdl2nc4 rads_adt_3a_2021181.nc4 ${project_source_dir}/testdata/rads_adt_3a_2021181.cdl
cdl2nc4 rads_adt_3b_2021181.nc4 ${project_source_dir}/testdata/rads_adt_3b_2021181.cdl
cdl2nc4 icec_amsr2_north_1.nc4 ${project_source_dir}/testdata/icec_amsr2_north_1.cdl
cdl2nc4 icec_amsr2_north_2.nc4 ${project_source_dir}/testdata/icec_amsr2_north_2.cdl
cdl2nc4 icec_amsr2_south_1.nc4 ${project_source_dir}/testdata/icec_amsr2_south_1.cdl
cdl2nc4 icec_amsr2_south_2.nc4 ${project_source_dir}/testdata/icec_amsr2_south_2.cdl
cdl2nc4 icec_mirs_snpp_1.nc4 ${project_source_dir}/testdata/icec_mirs_snpp_1.cdl
cdl2nc4 icec_mirs_snpp_2.nc4 ${project_source_dir}/testdata/icec_mirs_snpp_2.cdl
cdl2nc4 icec_jrr_n20_1.nc4 ${project_source_dir}/testdata/icec_jrr_n20_1.cdl
cdl2nc4 icec_jrr_n20_2.nc4 ${project_source_dir}/testdata/icec_jrr_n20_2.cdl
cdl2nc4 sss_smap_1.nc4 ${project_source_dir}/testdata/sss_smap_1.cdl
cdl2nc4 sss_smap_2.nc4 ${project_source_dir}/testdata/sss_smap_2.cdl
cdl2nc4 sss_smos_1.nc4 ${project_source_dir}/testdata/sss_smos_1.cdl
cdl2nc4 sss_smos_2.nc4 ${project_source_dir}/testdata/sss_smos_2.cdl
cdl2nc4 ghrsst_sst_ma_202103241540.nc4 ${project_source_dir}/testdata/ghrsst_sst_ma_202103241540.cdl
cdl2nc4 ghrsst_sst_ma_202103241550.nc4 ${project_source_dir}/testdata/ghrsst_sst_ma_202103241550.cdl
cdl2nc4 viirs_aod_1.nc4 ${project_source_dir}/testdata/viirs_aod_1.cdl
cdl2nc4 viirs_aod_2.nc4 ${project_source_dir}/testdata/viirs_aod_2.cdl
