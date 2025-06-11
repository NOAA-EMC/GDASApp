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
INSTALL_PREFIX="${dir_root}/install"
CMAKE_INSTALL_LIBDIR="lib"
CMAKE_OPTS=""
BUILD_TARGET="${MACHINE_ID:-'localhost'}"
BUILD_VERBOSE="NO"
CLONE_JCSDADATA="NO"
CLEAN_BUILD="NO"
COMPILER="${COMPILER:-intel}"
WORKFLOW_BUILD=${WORKFLOW_BUILD:-"OFF"}

while getopts "w:t:c:hvdfa" opt; do
  case $opt in
    w)
      HOMEgfs=$OPTARG
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

# Set WORKFLOW_TESTS as CMake option
CMAKE_OPTS+=" -DWORKFLOW_TESTS=${WORKFLOW_TESTS:-${WORKFLOW_BUILD}}"

if [[ $WORKFLOW_BUILD == 'ON' ]]; then
  # Link MOM6 and Icepack in SOCA to submodules in the UFS repo
  rm -rf $dir_root/sorc/soca/external/mom6/MOM6
  rm -rf $dir_root/sorc/soca/external/icepack/Icepack
  ln -sf $HOMEgfs/sorc/ufs_model.fd/MOM6-interface/MOM6/ $dir_root/sorc/soca/external/mom6/MOM6
  ln -sf $HOMEgfs/sorc/ufs_model.fd/CICE-interface/CICE/icepack/ $dir_root/sorc/soca/external/icepack/Icepack
fi

# Set INSTALL_PREFIX as CMake option
CMAKE_OPTS+=" -DCMAKE_INSTALL_PREFIX=${INSTALL_PREFIX}"

# Set CMAKE_INSTALL_LIBDIR as CMake option
CMAKE_OPTS+=" -DCMAKE_INSTALL_LIBDIR=${CMAKE_INSTALL_LIBDIR}"

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

# Install
echo "Installing ... `date`"
set -x
make install -j ${BUILD_JOBS:-8}
set +x

# If this is a workflow build, copy the installed files to the Global Workflow exec directory
if [[ $WORKFLOW_BUILD == 'ON' ]]; then
  echo "Copying installed files to Global Workflow directories ..."

  # Make sure the required install directories exist in the Global Workflow
  mkdir -p "$HOMEgfs"/exec
  mkdir -p "$HOMEgfs/$CMAKE_INSTALL_LIBDIR"

  # Move GDASApp executables from GDASApp to the Global Workflow
  mv "$INSTALL_PREFIX/bin"/gdas* "$HOMEgfs/exec/"

  # Move GDASApp executables (from submodules) that don't have a gdas_* prefix in the name
  mv "$INSTALL_PREFIX/bin/bufr2ioda.x" "$HOMEgfs/exec/gdas_bufr2ioda.x"
  mv "$INSTALL_PREFIX/bin/calcfIMS.exe" "$HOMEgfs/exec/gdas_calcfIMS.x" # .exe -> .x
  mv "$INSTALL_PREFIX/bin/apply_incr.exe" "$HOMEgfs/exec/gdas_apply_incr.x" # .exe -> .x

  # Move libraries from GDASApp to the Global Workflow
  mv "$INSTALL_PREFIX/$CMAKE_INSTALL_LIBDIR"/* "$HOMEgfs/$CMAKE_INSTALL_LIBDIR/"

  # Make sure INSTALL_PREFIX is not equal to GDASApp or Global Workflow root before deleting it
  if [[ "$INSTALL_PREFIX" == "$HOMEgfs" ]]; then
    echo "Error: INSTALL_PREFIX is equal to Global Workflow root."
    exit 1
  fi
  if [[ "$INSTALL_PREFIX" == "$dir_root" ]]; then
    echo "Error: INSTALL_PREFIX is equal to GDASApp root."
    exit 1
  fi

  # Delete the GDASApp install directory
  #rm -rf "$INSTALL_PREFIX"
fi
echo "Finish ... `date`"
exit 0
