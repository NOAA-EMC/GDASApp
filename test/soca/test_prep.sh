#!/bin/bash
set -e

project_binary_dir=$1
project_source_dir=$2

# Export runtime env. variables
source ${project_source_dir}/test/soca/runtime_vars.sh $project_binary_dir $project_source_dir

# Run prep step
echo "============================= Testing exgdas_global_marine_analysis_prep.py for clean exit"
${project_source_dir}/scripts/exgdas_global_marine_analysis_prep.py > exgdas_global_marine_analysis_prep.log

# Test that the obs were fetched
echo "============================= Testing for the presence of obs in the fetch target directory"
if [ ! "$(ls -A ${project_binary_dir}/test/soca/3dvar/analysis/obs/)" ]; then
    exit 1
fi

# Test that the obs path in var.yaml exist
echo "============================= Testing the existence of obs in var.vaml"
obslist=`grep obsfile $COMOUT/analysis/var.yaml | grep -v obs_out`
for o in $obslist; do
    if [ ! "$o" == "obsfile:" ]; then
        if test -f "${project_binary_dir}/test/soca/3dvar/analysis/$o"; then
            echo " - $o exists"
        else
            echo " - $o does not exist"
            exit 1
        fi
    fi
done
