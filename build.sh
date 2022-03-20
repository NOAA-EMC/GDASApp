#!/bin/bash

# build.sh
# 1 - determine host, load modules on supported hosts; proceed w/o otherwise
# 2 - configure; build; install
# 4 - optional, run unit tests

set -eu

dir_root="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# ==============================================================================
usage() {
  set +x
  echo
  echo "Usage: $0 -p <prefix> | -t <target> -h"
  echo
  echo "  -p  installation prefix <prefix>    DEFAULT: ${dir_root}/install"
  echo "  -t  target to build <target>        DEFAULT: $(hostname)"
  echo "  -h  display this message and quit"
  echo
  exit 1
}

# ==============================================================================

# Defaults:
INSTALL_PREFIX="${dir_root}/install"
BUILD_TARGET="$(hostname)"

while getopts "p:t:h" opt; do
  case $opt in
    p)
      INSTALL_PREFIX=$OPTARG
      ;;
    t)
      BUILD_TARGET=$OPTARG
      ;;
    h|\?|:)
      usage
      ;;
  esac
done


dir_modules=$dir_root/modulefiles

case ${BUILD_TARGET} in
  hera | orion)
    echo "Building GDASApp on $BUILD_TARGET"
    source $MODULESHOME/init/sh
    module purge
    module use $dir_modules
    module load GDAS/${BUILD_TARGET:-}
    CMAKE_OPTS+=" -DMPIEXEC_EXECUTABLE=$MPIEXEC_EXEC -DMPIEXEC_NUMPROC_FLAG=$MPIEXEC_NPROC"
    module list
    ;;
  $(hostname))
    echo "Building GDASApp on $BUILD_TARGET"
    ;;
  *)
    echo "Building GDASApp on unknown target: $BUILD_TARGET"
    ;;
esac

BUILD_DIR=${BUILD_DIR:-$dir_root/build}
[[ -d ${BUILD_DIR} ]] && rm -rf ${BUILD_DIR}
mkdir -p ${BUILD_DIR} && cd ${BUILD_DIR}

# Configure
echo "Configuring ..."
set -x
cmake \
  -DCMAKE_INSTALL_PREFIX=${INSTALL_PREFIX} \
  ${CMAKE_OPTS:-} \
  $dir_root
set +x

# Build
echo "Building ..."
set -x
make -j ${BUILD_JOBS:-6} VERBOSE=${BUILD_VERBOSE:-}
set +x

# Install
echo "Installing ..."
set -x
make install
set +x

exit 0
