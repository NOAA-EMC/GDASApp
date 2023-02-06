#!/bin/bash
set -e

project_binary_dir=$1
project_source_dir=$2

soca_static=${project_binary_dir}/soca_static
mkdir -p ${soca_static}
mkdir -p ${soca_static}/INPUT
mkdir -p ${soca_static}/bump
mkdir -p ${soca_static}/bkgerr/stddev

lowres=${project_source_dir}/soca/test/Data

cp -L ${lowres}/workdir/{diag_table,field_table} ${soca_static}
cp -L ${project_source_dir}/test/soca/fix/MOM_input ${soca_static}
cp -L ${lowres}/{fields_metadata.yml,godas_sst_bgerr.nc,rossrad.dat} ${soca_static}
mv ${soca_static}/fields_metadata.yml ${soca_static}/fields_metadata.yaml
cp -L ${project_source_dir}/soca/test/testinput/obsop_name_map.yml ${soca_static}/obsop_name_map.yaml
cp -L ${lowres}/72x35x25/input.nml ${soca_static}/inputnml
cp -L ${lowres}/72x35x25/INPUT/{hycom1_25.nc,ocean_mosaic.nc,grid_spec.nc,layer_coord25.nc,ocean_hgrid.nc,ocean_topog.nc} ${soca_static}/INPUT
