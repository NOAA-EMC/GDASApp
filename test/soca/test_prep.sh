#!/bin/bash
set -e

project_binary_dir=$1
project_source_dir=$2

source ${project_source_dir}/test/soca/test_utils.sh

# Export runtime env. variables
source ${project_source_dir}/test/soca/runtime_vars.sh $project_binary_dir $project_source_dir

# Get low res static files from the soca sandbox
source ${project_source_dir}/test/soca/static.sh $project_binary_dir $project_source_dir

# MOM6's diag output need to be renamed
i=3
lof=`ls ${project_binary_dir}/test/soca/bkg/RESTART/ocn_da_*`
for f in $lof; do
  ln -sf $f ${project_binary_dir}/test/soca/bkg/gdas.t12z.ocnf00$i.nc
  i=$(($i+1))
done

# Run prep step
echo "============================= Testing exgdas_global_marine_analysis_prep.py for clean exit"
${project_source_dir}/scripts/exgdas_global_marine_analysis_prep.py > exgdas_global_marine_analysis_prep.log

# Test that the obs path in var.yaml exist
echo "============================= Testing the existence of obs and bkg in var.vaml"
obslist=`grep 'gdas.t12z' $COMOUT/analysis/var.yaml`
for o in $obslist; do
    echo "----------------------- "$o
    if [ "$o" == "obsfile:" ]; then
      base=''
      continue
    fi
    if [ "$o" == "ocn_filename:" ]; then
      base=${project_binary_dir}/test/soca/bkg/
      continue
    fi
    test_file ${base}$o
done

# Test that the static files have been linked properly
echo "============================= Test that the static files have been linked properly"
test_file $(readlink ${project_binary_dir}/test/soca/3dvar/analysis/diag_table)
test_file $(readlink ${project_binary_dir}/test/soca/3dvar/analysis/field_table)
test_file $(readlink ${project_binary_dir}/test/soca/3dvar/analysis/fields_metadata.yaml)
test_file $(readlink ${project_binary_dir}/test/soca/3dvar/analysis/godas_sst_bgerr.nc)
test_file $(readlink ${project_binary_dir}/test/soca/3dvar/analysis/rossrad.dat)
test_file $(readlink ${project_binary_dir}/test/soca/3dvar/analysis/MOM_input)
