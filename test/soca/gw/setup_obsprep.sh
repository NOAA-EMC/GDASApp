#!/bin/bash
set -ex

project_source_dir=$1

# working directory should be ${PROJECT_BINARY_DIR}/test/soca/gw/obsprep, set in ctest command
test_dmpdir="gdas.20180415/12"

rm -rf ${test_dmpdir}
mkdir -p ${test_dmpdir}

cd ${test_dmpdir}

mkdir -p ocean/sss ocean/adt ocean/icec ocean/sst

${project_source_dir}/test/soca/gw/prepdata.sh ${project_source_dir}

