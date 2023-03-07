#!/bin/bash
#--------------------------------------------------------------------------------------
# run_bufr2ioda.sh
# This driver script will:
# - determine list of input BUFR files available
# - generate YAMLs from templates for each BUFR file
# - run BUFR2IODA.x and produce output IODA files
# usage:
#       run_bufr2ioda.sh YYYYMMDDHH /path/to/files.bufr_d/ /path/to/templates.yaml/ /path/to/output.ioda/
#
#--------------------------------------------------------------------------------------
if [[ $# -ne 4 ]] ; then
    echo "usage:"
    echo "      $0 YYYYMMDDHH /path/to/files.bufr_d/ /path/to/templates.yaml/ /path/to/output.ioda/"
    exit 1
fi

# input parameters
BUFR_dir=$2
YAML_template_dir=$3
out_dir=$4

# there are extra YAMLs for things like the prepBUFR file
prepBUFR_YAMLS="prepbufr_adpupa prepbufr_adpsfc"

# get list of BUFR files in input directory using glob
BUFR_files=$(ls $BUFR_dir/*.bufr_d)
if [ $? -ne 0 ]; then
  echo "No BUFR files found! in $BUFR_dir"
  exit 1
fi

# create output directory if it doesn't exist
mkdir -p $out_dir
if [ $? -ne 0 ]; then
  echo "cannot make $out_dir"
  exit 1
fi

# loop through available BUFR files
for f in $BUFR_files; do
done
