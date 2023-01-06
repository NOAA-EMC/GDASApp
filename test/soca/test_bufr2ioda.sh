#!/bin/bash

set -x

PROJECT_BINARY_DIR=${1}
OBSSOURCE=${2}

rm -fv ${PROJECT_BINARY_DIR}/test/testoutput/${OBSSOURCE}_201804*.nc

CMD=${PROJECT_BINARY_DIR}/bin/bufr2ioda.x
OBSYAML=${PROJECT_BINARY_DIR}/test/testinput/${OBSSOURCE}.yaml

${CMD} ${OBSYAML}



