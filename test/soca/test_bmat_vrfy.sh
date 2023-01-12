#!/bin/bash
set -e

project_binary_dir=$1
project_source_dir=$2

source ${project_source_dir}/test/soca/test_utils.sh

# Clean test files created during a previous test
echo "============================= Test that the grid has been generated"
#rm -f  ${DATA}/Data/dirac???

# Export runtime env. variables
source ${project_source_dir}/test/soca/runtime_vars.sh $project_binary_dir $project_source_dir

# B-matrix diagnostic step
echo "============================= Testing exgdas_global_marine_analysis_bamt_vrfy.sh for clean exit"
${project_source_dir}/scripts/exgdas_global_marine_analysis_bmat_vrfy.sh > exgdas_global_marine_analysis_bmat_vrfy.log

echo "============================= Test that the dirac file has been generated"
#test_file  ${DATA}/soca_gridspec.nc
