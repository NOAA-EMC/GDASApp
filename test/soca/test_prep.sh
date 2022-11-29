#!/bin/bash
set -e

project_binary_dir=$1
project_source_dir=$2

source ${project_source_dir}/test/soca/test_utils.sh

# Remove previously fetched obs
rm -f ${project_binary_dir}/test/soca/3dvar/gdas.t12z.{sst,adt,sss,salt}*.nc4

# Export runtime env. variables
source ${project_source_dir}/test/soca/runtime_vars.sh $project_binary_dir $project_source_dir

# Get low res static files from the soca sandbox
source ${project_source_dir}/test/soca/static.sh $project_binary_dir $project_source_dir

# MOM6's diag output needs to be renamed
i=3
lof=`ls ${project_binary_dir}/test/soca/bkg/RESTART/ocn_da_*`
for f in $lof; do
  cp $f ${project_binary_dir}/test/soca/bkg/gdas.t12z.ocnf00$i.nc
  i=$(($i+1))
done

# Run prep step
echo "============================= Testing exgdas_global_marine_analysis_prep.py for clean exit"
${project_source_dir}/scripts/exgdas_global_marine_analysis_prep.py

# Test that the obs path in var.yaml exist
echo "============================= Testing the existence of obs and bkg in var.vaml"
obslist=`grep 'gdas.t12z' ${DATA}/var.yaml`
for o in $obslist; do
    echo "----------------------- "$o
    case $o in
        "obsfile:")
            base=''
            continue
            ;;
        "ocn_filename:")
            base=${project_binary_dir}/test/soca/bkg/
            continue
            ;;
        "remap_filename:")
            base=''
            continue
            ;;
    esac
    test_file ${base}$o
done

# Test that the static files have been linked properly
echo "============================= Test that the static files have been linked properly"
test_file $(readlink ${DATA}/diag_table)
test_file $(readlink ${DATA}/field_table)
test_file $(readlink ${DATA}/fields_metadata.yaml)
test_file $(readlink ${DATA}/godas_sst_bgerr.nc)
test_file $(readlink ${DATA}/rossrad.dat)
test_file $(readlink ${DATA}/MOM_input)
