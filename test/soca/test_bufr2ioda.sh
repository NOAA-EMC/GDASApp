#!/bin/bash

set -x

PROJECT_BINARY_DIR=${1}
OBSSOURCE=${2}
CMD=${PROJECT_BINARY_DIR}/bin/bufr2ioda.x
OBSYAML=${PROJECT_BINARY_DIR}/test/testinput/${OBSSOURCE}.yaml

rm -fv ${PROJECT_BINARY_DIR}/test/testoutput/${OBSSOURCE}_20180415.nc
rm -fv ${PROJECT_BINARY_DIR}/test/testoutput/${OBSSOURCE}_201804.nc

${CMD} ${OBSYAML}



