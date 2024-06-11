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
CHECK_FOR_EXISTING_JEDI_INSTALL="NO"
COMPILER="${COMPILER:-intel}"

while getopts "p:t:c:hvdfab" opt; do
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
    b)
      CHECK_FOR_EXISTING_JEDI_INSTALL=YES
      ;;
    h|\?|:)
      usage
      ;;
  esac
done

# Set GDAS_CMAKE_OPTS amd JEDI_CMAKE_OPTS to CMAKE_OPTS
GDAS_CMAKE_OPTS=$CMAKE_OPTS
JEDI_CMAKE_OPTS=$CMAKE_OPTS

case ${BUILD_TARGET} in
  hera | orion | hercules | wcoss2 | noaacloud | gaea)
    echo "Building GDASApp on $BUILD_TARGET"
    source $dir_root/ush/module-setup.sh
    module use $dir_root/modulefiles
    module load GDAS/$BUILD_TARGET.$COMPILER
    GDAS_CMAKE_OPTS+=" -DMPIEXEC_EXECUTABLE=$MPIEXEC_EXEC -DMPIEXEC_NUMPROC_FLAG=$MPIEXEC_NPROC"
    JEDI_CMAKE_OPTS+=" -DMPIEXEC_EXECUTABLE=$MPIEXEC_EXEC -DMPIEXEC_NUMPROC_FLAG=$MPIEXEC_NPROC -DBUILD_GSIBEC=ON"
    module list
    ;;
  $(hostname))
    echo "Building GDASApp on $BUILD_TARGET"
    ;;
  *)
    echo "Building GDASApp on unknown target: $BUILD_TARGET"
    ;;
esac

# The build happens in two steps. In the first step the JEDI bundle code is built and installed. In
# second step the GDAS code is built, against the installed JEDI code.

# Step 1: Build the JEDI code
# ---------------------------

# Optionally the script can also look on the local machine for an existing version of the JEDI
# bundle for all the hashes that this repo needs. This saves building the JEDI code, which can be
# a lenghty process, especially on machines with busy file systems.

JEDI_INSTALL_DIR=${JEDI_BUILD_DIR:-$dir_root/jedi_bundle/install}

if [[ $CHECK_FOR_EXISTING_JEDI_INSTALL == 'YES' ]]; then

  echo "Link to an existing JEDI build for the hashes in this repo. Not supported yet."
  exit(1)

  # 1. Accumulate hashes for JEDI repos
  # 2. Search for the existing install directory
  # 3. Link it to $JEDI_INSTALL_DIRECTORY

else

  # Build the JEDI code
  JEDI_BUILD_DIR=${JEDI_BUILD_DIR:-$dir_root/jedi_bundle/build}

  if [[ $CLEAN_BUILD == 'YES' ]]; then
    [[ -d ${JEDI_BUILD_DIR} ]] && rm -rf ${JEDI_BUILD_DIR}
  fi
  mkdir -p ${JEDI_BUILD_DIR}

  # Assemble the CMAKE options
  JEDI_CMAKE_OPTS+=" -DCLONE_JCSDADATA=$CLONE_JCSDADATA"

  # JEDI code is always installed in the jedi_bundle/install directory
  JEDI_CMAKE_OPTS+=" -DCMAKE_INSTALL_PREFIX=${JEDI_INSTALL_DIR}"

  # Link in the CRTM test data if building on hera
  if [[ $BUILD_TARGET == 'hera' ]]; then
    if [ -d "$dir_root/bundle/fix/test-data-release/" ]; then rm -rf $dir_root/bundle/fix/test-data-release/; fi
    if [ -d "$dir_root/bundle/test-data-release/" ]; then rm -rf $dir_root/bundle/test-data-release/; fi
    mkdir -p $dir_root/bundle/fix/test-data-release/
    mkdir -p $dir_root/bundle/test-data-release/
    ln -sf $GDASAPP_TESTDATA/crtm $dir_root/bundle/fix/test-data-release/crtm
    ln -sf $GDASAPP_TESTDATA/crtm $dir_root/bundle/test-data-release/crtm
  fi

  # Configure JEDI build
  cd ${JEDI_BUILD_DIR}
  echo "Configuring JEDI bundle..."
  set -x
  cmake ${JEDI_CMAKE_OPTS:-} $dir_root/jedi_bundle
  set +x

  # Make and install the JEDI code
  echo "Making JEDI bundle..."
  set -x
  if [[ $BUILD_JCSDA == 'YES' ]]; then
    make -j ${BUILD_JOBS:-6} VERBOSE=$BUILD_VERBOSE
  else
    builddirs="gdas-jedi iodaconv land-imsproc land-jediincr"
    for b in $builddirs; do
      cd $b
      make -j ${BUILD_JOBS:-6} VERBOSE=$BUILD_VERBOSE install
      cd ../
    done
  fi
  set +x

fi

# Step 1b: Put the installed JEDI code in the path
# ------------------------------------------------

exit(0)


# Step 2: Build the GDAS bundle
# -----------------------------

GDAS_BUILD_DIR=${GDAS_BUILD_DIR:-$dir_root/build}
if [[ $CLEAN_BUILD == 'YES' ]]; then
  [[ -d ${GDAS_BUILD_DIR} ]] && rm -rf ${GDAS_BUILD_DIR}
fi
mkdir -p ${GDAS_BUILD_DIR} && cd ${GDAS_BUILD_DIR}

# If INSTALL_PREFIX is not empty; install at INSTALL_PREFIX
[[ -n "${INSTALL_PREFIX:-}" ]] && GDAS_CMAKE_OPTS+=" -DCMAKE_INSTALL_PREFIX=${INSTALL_PREFIX}"

# activate tests based on if this is cloned within the global-workflow
WORKFLOW_BUILD=${WORKFLOW_BUILD:-"OFF"}
GDAS_CMAKE_OPTS+=" -DWORKFLOW_TESTS=${WORKFLOW_BUILD}"

# Configure GDAS bundle
echo "Configuring GDAS bundle..."
set -x
cmake ${CMAKE_OPTS:-} $dir_root/bundle
set +x

# Build
INSTALL = ""
if [[ -n ${INSTALL_PREFIX:-} ]]; then
  INSTALL = "install"
fi

echo "Making GDAS bundle ..."
set -x
make -j ${BUILD_JOBS:-6} VERBOSE=$BUILD_VERBOSE $INSTALL
set +x

# TODO Update global-workflow and remove the below. To prevent failures of the tasks link the gdas.x
# to the gdas_bundle build directory.
ln -sf $dir_root/jedi_bundle/install/bin/gdas.x $dir_root/build/bin/gdas.x

exit 0
