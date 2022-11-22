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
  echo "  -p  installation prefix <prefix>    DEFAULT: <none>"
  echo "  -t  target to build for <target>    DEFAULT: $(hostname)"
  echo "  -c  additional CMake options        DEFAULT: <none>"
  echo "  -v  build with verbose output       DEFAULT: NO"
  echo "  -f  force a clean build             DEFAULT: NO"
  echo "  -d  include JCSDA ctest data        DEFAULT: NO"
  echo "  -h  display this message and quit"
  echo
  exit 1
}

# ==============================================================================

# Defaults:
INSTALL_PREFIX=""
CMAKE_OPTS=""
BUILD_TARGET="$(hostname)"
BUILD_VERBOSE="NO"
CLONE_JCSDADATA="NO"
CLEAN_BUILD="NO"

while getopts "p:t:c:hvd" opt; do
  case $opt in
    p)
      INSTALL_PREFIX=$OPTARG
      ;;
    t)
      BUILD_TARGET=$OPTARG
      ;;
    c)
      CMAKE_OPTS=$OPTARG
      ;;
    v)
      BUILD_VERBOSE=YES
      ;;
    d)
      CLONE_JCSDADATA=YES
      ;;
    f)
      CLEAN_BUILD=YES
      ;;
    h|\?|:)
      usage
      ;;
  esac
done

case ${BUILD_TARGET} in
  hera | orion)
    echo "Building GDASApp on $BUILD_TARGET"
    set +e
    source $MODULESHOME/init/sh
    module purge
    module use $dir_root/modulefiles
    module load GDAS/$BUILD_TARGET
    CMAKE_OPTS+=" -DMPIEXEC_EXECUTABLE=$MPIEXEC_EXEC -DMPIEXEC_NUMPROC_FLAG=$MPIEXEC_NPROC -DBUILD_GSIBEC=ON"
    CMAKE_OPTS+=" -DCLONE_JCSDADATA=$CLONE_JCSDADATA"
    module list
    set -e
    ;;
  $(hostname))
    echo "Building GDASApp on $BUILD_TARGET"
    ;;
  *)
    echo "Building GDASApp on unknown target: $BUILD_TARGET"
    ;;
esac

BUILD_DIR=${BUILD_DIR:-$dir_root/build}
if [[ $CLEAN_BUILD == 'YES' ]]; then
  [[ -d ${BUILD_DIR} ]] && rm -rf ${BUILD_DIR}
fi
mkdir -p ${BUILD_DIR} && cd ${BUILD_DIR}

# If INSTALL_PREFIX is not empty; install at INSTALL_PREFIX
[[ -n "${INSTALL_PREFIX:-}" ]] && CMAKE_OPTS+=" -DCMAKE_INSTALL_PREFIX=${INSTALL_PREFIX}"

# Configure
echo "Configuring ..."
set -x
cmake \
  ${CMAKE_OPTS:-} \
  $dir_root
set +x

# Build
echo "Building ..."
builddirs="fv3-jedi soca iodaconv"
set -x
for b in $builddirs; do
  cd $b
  make -j ${BUILD_JOBS:-6} VERBOSE=$BUILD_VERBOSE
  cd ../
done
set +x

# Install
if [[ -n ${INSTALL_PREFIX:-} ]]; then
  echo "Installing ..."
  set -x
  make install
  set +x
fi

exit 0
