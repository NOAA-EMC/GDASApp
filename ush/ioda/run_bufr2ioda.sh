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
if [[ $# -ne 5 ]] ; then
    echo "usage:"
    echo "      $0 YYYYMMDDHH gdas|gfs /path/to/files.bufr_d/ /path/to/templates.yaml/ /path/to/output.ioda/"
    exit 1
fi

# input parameters
CDATE=${CDATE:-$1}
RUN=${RUN:-$2}
BUFR_dir=${BUFR_dir:-$3}
YAML_template_dir=${YAML_template_dir:-$4}
out_dir=${out_dir:-$5}

# derived parameters
PDY=$(echo $CDATE | cut -c1-8)
cyc=$(echo $CDATE | cut -c9-10)

# get list of BUFR files in input directory using glob
BUFR_files=$(ls $BUFR_dir/${RUN}.t${cyc}z.*.bufr_d)
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
    # get BUFR type from input BUFR file name
    BUFRbase=$(basename $f)
    BUFRtype_base=$(echo "${BUFRbase%.*.*}")
    BUFRtype=$(echo "${BUFRtype_base#*.*.}")
    echo "Now processing $BUFRtype"
    # get path to YAML template file for this BUFR file
    YAML_template=$YAML_template_dir/bufr_${BUFRtype}.yaml
    # check if the YAML template exists
    if [ ! -f $YAML_template ]; then
        echo "${YAML_template} does not exist, skipping ${BUFRtype}!"
        continue
    fi
    # need to create a usable YAML from the template
    

    # run BUFR2IODA for the created YAML file

done

# do extra stuff for the prepbufr file
#-----------
# first, check if the prepBUFR file exists
#if [ -f $BUFR_dir/${RUN}.t${cyc}z.prepbufr ]; then
#    echo "Will process $BUFR_dir/${RUN}.t${cyc}z.prepbufr"
#    # there are multiple YAMLs to run through
#    prepBUFR_YAMLS="prepbufr_adpupa prepbufr_adpsfc"
#fi
