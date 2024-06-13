#!/bin/bash

# build.sh
# 1 - determine host, load modules on supported hosts; proceed w/o otherwise
# 2 - configure; build; install
# 4 - optional, run unit tests

set -eu

dir_root="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source $dir_root/ush/detect_machine.sh

# ==============================================================================
usage() {
  set +x
  echo
  echo "Usage: $0 -p <prefix> | -t <target> -h"
  echo
  echo "  -p  installation prefix <prefix>    DEFAULT: <none>"
  echo "  -t  target to build for <target>    DEFAULT: $MACHINE_ID"
  echo "  -c  additional CMake options        DEFAULT: <none>"
  echo "  -v  build with verbose output       DEFAULT: NO"
  echo "  -f  force a clean build             DEFAULT: NO"
  echo "  -d  include JCSDA ctest data        DEFAULT: NO"
  echo "  -a  build everything in bundle      DEFAULT: NO"
  echo "  -h  display this message and quit"
  echo
  exit 1
}

# ==============================================================================

# Defaults:
INSTALL_PREFIX=""
CMAKE_OPTS=""
BUILD_TARGET="${MACHINE_ID:-'localhost'}"
BUILD_VERBOSE="NO"
CLONE_JCSDADATA="NO"
CLEAN_BUILD="NO"
BUILD_JCSDA="NO"
COMPILER="${COMPILER:-intel}"

while getopts "p:t:c:hvdfa" opt; do
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
    a)
      BUILD_JCSDA=YES
      ;;
    h|\?|:)
      usage
      ;;
  esac
done

case ${BUILD_TARGET} in
  hera | orion | hercules | wcoss2 | noaacloud | gaea)
    echo "Building GDASApp on $BUILD_TARGET"
    source $dir_root/ush/module-setup.sh
    module use $dir_root/modulefiles
    module load GDAS/$BUILD_TARGET.$COMPILER
    CMAKE_OPTS+=" -DMPIEXEC_EXECUTABLE=$MPIEXEC_EXEC -DMPIEXEC_NUMPROC_FLAG=$MPIEXEC_NPROC -DBUILD_GSIBEC=ON"
    module list
    ;;
  $(hostname))
    echo "Building GDASApp on $BUILD_TARGET"
    ;;
  *)
    echo "Building GDASApp on unknown target: $BUILD_TARGET"
    ;;
esac

CMAKE_OPTS+=" -DCLONE_JCSDADATA=$CLONE_JCSDADATA"

BUILD_DIR=${BUILD_DIR:-$dir_root/build}
if [[ $CLEAN_BUILD == 'YES' ]]; then
  [[ -d ${BUILD_DIR} ]] && rm -rf ${BUILD_DIR}
fi
mkdir -p ${BUILD_DIR} && cd ${BUILD_DIR}

# If INSTALL_PREFIX is not empty; install at INSTALL_PREFIX
[[ -n "${INSTALL_PREFIX:-}" ]] && CMAKE_OPTS+=" -DCMAKE_INSTALL_PREFIX=${INSTALL_PREFIX}"

# activate tests based on if this is cloned within the global-workflow
WORKFLOW_BUILD=${WORKFLOW_BUILD:-"OFF"}
CMAKE_OPTS+=" -DWORKFLOW_TESTS=${WORKFLOW_BUILD}"

# JCSDA changed test data things, need to make a dummy CRTM directory
if [[ $BUILD_TARGET == 'hera' ]]; then
  if [ -d "$dir_root/bundle/fix/test-data-release/" ]; then rm -rf $dir_root/bundle/fix/test-data-release/; fi
  if [ -d "$dir_root/bundle/test-data-release/" ]; then rm -rf $dir_root/bundle/test-data-release/; fi
  mkdir -p $dir_root/bundle/fix/test-data-release/
  mkdir -p $dir_root/bundle/test-data-release/
  ln -sf $GDASAPP_TESTDATA/crtm $dir_root/bundle/fix/test-data-release/crtm
  ln -sf $GDASAPP_TESTDATA/crtm $dir_root/bundle/test-data-release/crtm
fi

# Before configuring, look for an exising JEDI install for this platform and set of JEDI hashes.
# If found add the the library paths (containning cmake files) to the path.

# Check if environement variable SEARCH_FOR_JEDI_INSTALL is set and exit if it is since this is not
# yet supported
if [[ -n ${SEARCH_FOR_JEDI_INSTALL:-} ]]; then
  # This is a placeholder for a future feature
  echo "ERROR: SEARCH_FOR_JEDI_INSTALL is not yet supported"
  exit 1
fi

# Configure
echo "Configuring ..."
set -x
cmake \
  ${CMAKE_OPTS:-} \
  $dir_root/bundle
set +x

# Build
echo "Building ..."
set -x
if [[ $BUILD_JCSDA == 'YES' ]]; then
  make -j ${BUILD_JOBS:-6} VERBOSE=$BUILD_VERBOSE
else
  builddirs="gdas iodaconv land-imsproc land-jediincr gdas-utils"
  for b in $builddirs; do
    # Check that b exists and if it does perform the build
    if [ -d $b ]; then
      cd $b
      make -j ${BUILD_JOBS:-6} VERBOSE=$BUILD_VERBOSE
      cd ../
    else
      echo "WARNING: $b was not part of the bundle, skipping build. Usually this happens because it was found in the path"
    fi

  done
fi
set +x

# Install
if [[ -n ${INSTALL_PREFIX:-} ]]; then
  echo "Installing ..."
  set -x
  # TODO: this does not simply copy files to install. It will build the rest of the bundle that was
  # not built above but with one processor, and then install it. We might need to think about what
  # we actually want here. We could install individual packages but that would leave lots of
  # libraries out. Install potentially only makes sense with $BUILD_JCSDA
  make install
  set +x
fi

# If we were searching for a JEDI build we should link all the executables in that install to the
# gdas build directory. global-workflow tasks look for the executables there.
if [[ -n ${SEARCH_FOR_JEDI_INSTALL:-} ]]; then
  # This is a placeholder for a future feature
  echo "ERROR: SEARCH_FOR_JEDI_INSTALL is not yet supported"
  exit 1
fi

exit 0
