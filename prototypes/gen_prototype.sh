#!/bin/bash
set -e

# ==============================================================================
usage() {
  set +x
  echo
  echo "Usage: $0 -c <config> -h"
  echo
  echo "  -c  Configuration for prototype defined in shell script <config>"
  echo "  -h  display this message and quit"
  echo
  exit 1
}

# ==============================================================================
while getopts "c:h" opt; do
  case $opt in
    c)
      config=$OPTARG
      ;;
    h|\?|:)
      usage
      ;;
  esac
done

# source the input configuration
source $config

# create directories
mkdir -p $PROTOROOT/$PSLOT

# clone/build/link workflow and GDASApp
cd $PROTOROOT/$PSLOT
git clone -b $GWHASH https://github.com/NOAA-EMC/global-workflow.git
cd global-workflow/sorc
git clone -b $GDASHASH https://github.com/NOAA-EMC/GDASApp.git gdas.cd
./checkout.sh -g
./build_all.sh
./link_workflow.sh
