#!/bin/bash
# called for test_gdasapp_util_prepdata, and by
# test/soca/gw/setup_obsproc.sh for test_gdasapp_soca_setup_obsproc

# TODO: It needs to point to experimental obs instead of prepdata.sh
# Get the machine hostname
MACHINE_NAME=$(hostname)

# Check if the machine name is "hera"
if [[ "$MACHINE_NAME" =~ ^hfe0[1-9]$ || "$MACHINE_NAME" =~ ^hfe1[01]$ ]]; then
    echo "Running on hera, loading anaconda modules."
    module use -a /contrib/anaconda/modulefiles
    module load anaconda/latest
else
    echo "Not running on hera, skipping anaconda module loading."
fi

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
cdl2nc4 icec_abi_g16_1.nc4 ${project_source_dir}/testdata/icec_abi_g16_1.cdl
cdl2nc4 icec_abi_g16_2.nc4 ${project_source_dir}/testdata/icec_abi_g16_2.cdl
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
cdl2nc4 insitu_profile_argo_1.nc4 ${project_source_dir}/testdata/insitu_profile_argo_1.cdl
cdl2nc4 insitu_profile_argo_2.nc4 ${project_source_dir}/testdata/insitu_profile_argo_2.cdl
cdl2nc4 ghrsst_sst_ma_202103241540.nc4 ${project_source_dir}/testdata/ghrsst_sst_ma_202103241540.cdl
cdl2nc4 ghrsst_sst_ma_202103241550.nc4 ${project_source_dir}/testdata/ghrsst_sst_ma_202103241550.cdl
cdl2nc4 viirs_aod_1.nc4 ${project_source_dir}/testdata/viirs_aod_1.cdl
cdl2nc4 viirs_aod_2.nc4 ${project_source_dir}/testdata/viirs_aod_2.cdl
