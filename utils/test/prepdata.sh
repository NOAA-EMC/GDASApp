#!/bin/bash
set -e

project_source_dir=$1

ncgen -o rads_adt_3a_2021181.nc4 ${project_source_dir}/testdata/rads_adt_3a_2021181.cdl
ncgen -o rads_adt_3a_2021182.nc4 ${project_source_dir}/testdata/rads_adt_3a_2021182.cdl
ncgen -o rads_adt_3b_2021181.nc4 ${project_source_dir}/testdata/rads_adt_3b_2021181.cdl
ncgen -o rads_adt_3b_2021182.nc4 ${project_source_dir}/testdata/rads_adt_3b_2021182.cdl
ncgen -o rads_adt_c2_2021181.nc4 ${project_source_dir}/testdata/rads_adt_c2_2021181.cdl
ncgen -o rads_adt_c2_2021182.nc4 ${project_source_dir}/testdata/rads_adt_c2_2021182.cdl
ncgen -o rads_adt_j3_2021181.nc4 ${project_source_dir}/testdata/rads_adt_j3_2021181.cdl
ncgen -o rads_adt_j3_2021182.nc4 ${project_source_dir}/testdata/rads_adt_j3_2021182.cdl
ncgen -o rads_adt_sa_2021181.nc4 ${project_source_dir}/testdata/rads_adt_sa_2021181.cdl
ncgen -o rads_adt_sa_2021182.nc4 ${project_source_dir}/testdata/rads_adt_sa_2021182.cdl

