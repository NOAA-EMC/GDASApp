#!/bin/bash

set -x

PROJECT_BINARY_DIR=${1}
CMAKE_BINARY_DIR=${1}
OBSSOURCE=${3}
CMD=${CMAKE_BINARY_DIR}/bin/bufr2ioda.x
OBSYAML=${PROJECT_BINARY_DIR}/../ush/land/${OBSSOURCE}.yaml

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
