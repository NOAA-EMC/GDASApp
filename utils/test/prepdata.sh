#!/bin/bash
set -e

project_source_dir=$1

ncgen -o rads_adt_3a_2021181.nc4 ${project_source_dir}/testdata/rads_adt_3a_2021181.cdl
ncgen -o rads_adt_3b_2021181.nc4 ${project_source_dir}/testdata/rads_adt_3b_2021181.cdl
ncgen -o icec_amsr2_north_1.nc4 ${project_source_dir}/testdata/icec_amsr2_north_1.cdl
ncgen -o icec_amsr2_north_2.nc4 ${project_source_dir}/testdata/icec_amsr2_north_2.cdl
ncgen -o icec_amsr2_south_1.nc4 ${project_source_dir}/testdata/icec_amsr2_south_1.cdl
ncgen -o icec_amsr2_south_2.nc4 ${project_source_dir}/testdata/icec_amsr2_south_2.cdl
