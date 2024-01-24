#!/bin/bash

set -x

PROJECT_BINARY_DIR=${1}
PROJECT_SOURCE_DIR=${2}
CMAKE_BINARY_DIR=${3}
OBSSOURCE=${4}
CMD=${CMAKE_BINARY_DIR}/bin/bufr2ioda.x
OBSYAML=${PROJECT_SOURCE_DIR}/ush/land/${OBSSOURCE}.yaml

OUTFILE=`grep obsdataout ${OBSYAML} | cut -d'"' -f2`

echo "the following might not exist"
rm -v ${PROJECT_BINARY_DIR}/test/${OUTFILE}

${CMD} ${OBSYAML}
rc=$?

ls ${PROJECT_BINARY_DIR}/test/${OUTFILE}
ra=$?
rc=$((rc+ra))

export err=$rc

exit $err
