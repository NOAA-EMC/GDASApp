#!/bin/bash
set -ex

project_source_dir=$1

# working directory should be ${PROJECT_BINARY_DIR}/test/soca/gw/obsprep, set in ctest command
test_dmpdir="gdas.20180415/12"

rm -rf ${test_dmpdir}
mkdir -p ${test_dmpdir}

cd ${test_dmpdir}

mkdir atmos SSS ADT icec sst

${project_source_dir}/test/soca/gw/prepdata.sh ${project_source_dir}

echo "Copy subsampled BUFR into atmos directory..."
for f in $PWD/../../../../../testdata/*_subsampled; do
    cp -p $f atmos/
done


