#!/bin/bash
set -e

project_source_dir=$1

ncgen -o rads_adt_j3_2021182.nc4 ${project_source_dir}/testdata/rads_adt_j3_2021182.cdl
ncgen -o ghrsst_sst_mb_202107010000.cdl ${project_source_dir}/testdata/ghrsst_sst_mb_202107010000.cdl
ncgen -o ghrsst_sst_mb_202107010100.cdl ${project_source_dir}/testdata/ghrsst_sst_mb_202107010100.cdl
