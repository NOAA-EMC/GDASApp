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
PREP_JEDI_INSTALL=NO
COMPILER="${COMPILER:-intel}"

while getopts "p:t:c:hvdfap" opt; do
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
    p)
      PREP_JEDI_INSTALL=YES
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

# The below logic is used to search for an existing JEDI install, put it in
# the path and reduce the main bundle to not build JEDI pacakges.
# -------------------------------------------------------------------------

# If there is an environment variable called SEARCH_FOR_JEDI_INSTALL then add -DBUILD_JEDI=OFF to CMAKE_OPTS
if [[ -n ${SEARCH_FOR_JEDI_INSTALL:-} ]]; then

  # Not supported yet so just exit
  echo "SEARCH_FOR_JEDI_INSTALL is not supported yet"
  exit 1

  # Check that the environment variable JEDI_INSTALL_SEARCH_PATH is set to something and if not
  # message and abort
  if [[ -z ${JEDI_INSTALL_SEARCH_PATH:-} ]]; then
    echo "SEARCH_FOR_JEDI_INSTALL is set but JEDI_INSTALL_SEARCH_PATH is not set for this machine"
    echo "Unse SEARCH_FOR_JEDI_INSTALL and run again."
    exit 1
  fi

  # Get JEDI big hash
  JEDI_BIG_HASH=$(python get_big_jedi_hash.py)

  # Check for existence of $JEDI_INSTALL_SEARCH_PATH/$JEDI_BIG_HASH/bin/gdas.x
  # If found then add the JEDI install directories to the path and turn off the building of JEDI
  if [[ -f $JEDI_INSTALL_SEARCH_PATH/$JEDI_BIG_HASH/bin/gdas.x ]]; then

    # Add the JEDI install directories to the path
    req_libraries = "oops fv3jedi soca"
    for lib in $req_libraries; do
      export CMAKE_PREFIX_PATH=$CMAKE_PREFIX_PATH:$JEDI_INSTALL_SEARCH_PATH/$JEDI_BIG_HASH/lib64/$lib/cmake
    done

    # Turn off the building of JEDI
    CMAKE_OPTS+=" -DBUILD_JEDI=OFF"

    # Link everything in $JEDI_INSTALL_PATH/bin to build/bin
    # This is needed because g-w will look for executables in build/bin
    # Temporary until g-w would see these exes in the path.
    for f in $JEDI_INSTALL_SEARCH_PATH/$JEDI_BIG_HASH/bin/*; do
      ln -sf $f $BUILD_DIR/bin/
    done

  fi

fi

# The below logic is used to for preparing a JEDI install for the current
# set of hashes that JEDI is set against.
# -------------------------------------------------------------------------

# If PREP_JEDI_INSTALL is YES then build everything in bundle
if [[ $PREP_JEDI_INSTALL == 'YES' ]]; then

  # Assert that SEARCH_FOR_JEDI_INSTALL is not set
  if [[ -n ${SEARCH_FOR_JEDI_INSTALL:-} ]]; then
    echo "SEARCH_FOR_JEDI_INSTALL is set but PREP_JEDI_INSTALL is also set"
    echo "Unset SEARCH_FOR_JEDI_INSTALL and run again."
    exit 1
  fi

  # Assert that JEDI_INSTALL_SEARCH_PATH is set
  if [[ -z ${JEDI_INSTALL_SEARCH_PATH:-} ]]; then
    echo "PREP_JEDI_INSTALL is set but JEDI_INSTALL_SEARCH_PATH is not set for this machine"
    echo "Set JEDI_INSTALL_SEARCH_PATH and run again or turn off PREP_JEDI_INSTALL"
    exit 1
  fi

  # Get JEDI big hash
  JEDI_BIG_HASH=$(python get_big_jedi_hash.py)

  # Assert that $JEDI_INSTALL_SEARCH_PATH/$JEDI_BIG_HASH/bin/gdas.x does not already exist
  if [[ -f $JEDI_INSTALL_SEARCH_PATH/$JEDI_BIG_HASH/bin/gdas.x ]]; then
    echo "$JEDI_INSTALL_SEARCH_PATH/$JEDI_BIG_HASH/bin/gdas.x already exists so no need to prepare"
    echo "a JEDI install with this set of hashes"
    exit 1
  fi

  # Turn off the build of the GDAS-JEDI repos
  CMAKE_OPTS+=" -BUILD_GDAS_JEDI=OFF"

  # Set BUILD_JCSDA to on (need to make the whole package so the whole package can be installed)
  BUILD_JCSDA=YES

  # Set the prefix to $JEDI_INSTALL_SEARCH_PATH/$JEDI_BIG_HASH
  INSTALL_PREFIX=$JEDI_INSTALL_SEARCH_PATH/$JEDI_BIG_HASH
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
    cd $b
    make -j ${BUILD_JOBS:-6} VERBOSE=$BUILD_VERBOSE
    cd ../
  done
fi
set +x

# Install
if [[ -n ${INSTALL_PREFIX:-} ]]; then
  echo "Installing ..."
  set -x
  make install
  set +x
fi

exit 0
