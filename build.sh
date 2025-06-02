#!/bin/bash

# build.sh
# 1 - determine host, load modules on supported hosts; proceed w/o otherwise
# 2 - configure; build; install
# 4 - optional, run unit tests

set -eu

echo "Start ... `date`"
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
  hera | orion | hercules | wcoss2 | noaacloud | gaeac5 | gaeac6 | ursa )
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

CMAKE_OPTS+=" -DCLONE_JCSDADATA=$CLONE_JCSDADATA -DMACHINE=$BUILD_TARGET"

# TODO: Remove LD_LIBRARY_PATH line as soon as permanent solution is available
if [[ $BUILD_TARGET == 'wcoss2' ]]; then
    export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/opt/cray/pe/mpich/8.1.19/ofi/intel/19.0/lib"
fi

BUILD_DIR=${BUILD_DIR:-$dir_root/build}
if [[ $CLEAN_BUILD == 'YES' ]]; then
  [[ -d ${BUILD_DIR} ]] && rm -rf ${BUILD_DIR}
fi
mkdir -p ${BUILD_DIR} && cd ${BUILD_DIR}

# activate tests based on if this is cloned within the global-workflow
WORKFLOW_BUILD=${WORKFLOW_BUILD:-"OFF"}
CMAKE_OPTS+=" -DWORKFLOW_TESTS=${WORKFLOW_TESTS:-${WORKFLOW_BUILD}}"

# If this is a workflow build, set INSTALL_PREFIX to Global Workflow home directory
if [[ $WORKFLOW_BUILD == 'ON' ]]; then
  if [[ -n "${INSTALL_PREFIX:-}" ]]; then
    echo "Warning: INSTALL_PREFIX is set to '${INSTALL_PREFIX}', but this is a workflow build. It will be ignored."
  fi

  INSTALL_PREFIX="${dir_root}/../.."
fi

# If INSTALL_PREFIX is not empty; install at INSTALL_PREFIX
[[ -n "${INSTALL_PREFIX:-}" ]] && CMAKE_OPTS+=" -DCMAKE_INSTALL_PREFIX=${INSTALL_PREFIX}"

# Link MOM6 and Icepack in SOCA to submodules in the UFS repo
if [[ $WORKFLOW_BUILD == 'ON' ]]; then
  rm -rf $dir_root/sorc/soca/external/mom6/MOM6
  rm -rf $dir_root/sorc/soca/external/icepack/Icepack
  ln -sf $dir_root/../ufs_model.fd/MOM6-interface/MOM6/ $dir_root/sorc/soca/external/mom6/MOM6
  ln -sf $dir_root/../ufs_model.fd/CICE-interface/CICE/icepack/ $dir_root/sorc/soca/external/icepack/Icepack
fi

# JCSDA changed test data things, need to make a dummy CRTM directory
if [ -d "$dir_root/bundle/fix/test-data-release/" ]; then rm -rf $dir_root/bundle/fix/test-data-release/; fi
if [ -d "$dir_root/bundle/test-data-release/" ]; then rm -rf $dir_root/bundle/test-data-release/; fi
mkdir -p $dir_root/bundle/fix/test-data-release/
mkdir -p $dir_root/bundle/test-data-release/
ln -sf $GDASAPP_TESTDATA/crtm $dir_root/bundle/fix/test-data-release/crtm
ln -sf $GDASAPP_TESTDATA/crtm $dir_root/bundle/test-data-release/crtm

# Configure
echo "Configuring ... `date`"
set -x
cmake \
  ${CMAKE_OPTS:-} \
  $dir_root/bundle
set +x

# Install or build depending on whether INSTALL_PREFIX is set
if [[ -n ${INSTALL_PREFIX:-} ]]; then
  # Install
  echo "Installing ... `date`"
  set -x
  make install -j ${BUILD_JOBS:-8}
  set +x

  # If this is a workflow build, copy the installed files to the Global Workflow exec directory
  if [[ $WORKFLOW_BUILD == 'ON' ]]; then
    echo "Copying installed files to Global Workflow exec directory ..."
    mv $INSTALL_PREFIX/bin/gdas* $INSTALL_PREFIX/exec/

    # Rename and move the bufr2ioda executable
    # Note: this is a hack which will be removed once bufr2ioda is out of GDASApp
    mv $INSTALL_PREFIX/bin/bufr2ioda.x $INSTALL_PREFIX/exec/gdas_bufr2ioda.x 

    # Delete the original bin directory
    rm -rf $INSTALL_PREFIX/bin/
  fi
else
  # Build
  echo "Building ... `date`"
  set -x
  if [[ $BUILD_JCSDA == 'YES' ]]; then
    make -j ${BUILD_JOBS:-8} VERBOSE=$BUILD_VERBOSE
  else
    builddirs="gdas iodaconv land-imsproc land-jediincr gdas-utils bufr-query da-utils"
    for b in $builddirs; do
      cd $b
      set +x
      echo "Building $b ... `date`"
      set -x
      make -j ${BUILD_JOBS:-8} VERBOSE=$BUILD_VERBOSE
      cd ../
    done
  fi
  set +x
  fi
  echo "Finish ... `date`"
exit 0
