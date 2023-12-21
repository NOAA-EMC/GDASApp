#!/bin/bash
set -ex

project_source_dir=$1

# working directory should be ${PROJECT_BINARY_DIR}/test/soca/gw/obsproc, set in ctest command
#test_dmpdir="gdas.20180415/12"
test_dmpdir="gdas.20180415/00"

rm -rf ${test_dmpdir}
mkdir -p ${test_dmpdir}

cd ${test_dmpdir}

mkdir SSS ADT icec sst

#${project_source_dir}/test/soca/gw/prepdata.sh ${project_source_dir}/utils/test/
${project_source_dir}/test/soca/gw/prepdata.sh ${project_source_dir}



