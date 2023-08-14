#!/bin/bash
#--------------------------------------------------------------------------------------
# run_bufr2ioda.sh
# This driver script will:
# - generate config files from templates for each BUFR file
# - use bufr2ioda python scripts or executable and produce output IODA files
# usage:
#       run_bufr2ioda.sh YYYYMMDDHH $DMPDIR /path/to/templates $COM_OBS
#
#--------------------------------------------------------------------------------------
if [[ $# -ne 5 ]] ; then
    echo "usage:"
    echo "      $0 YYYYMMDDHH gdas|gfs /path/to/files.bufr_d/ /path/to/templates /path/to/output.ioda/"
    exit 1
fi

# input parameters
CDATE=${CDATE:-$1}
RUN=${RUN:-$2}
DMPDIR=${DMPDIR:-$3}
config_template_dir=${config_template_dir:-$4}
COM_OBS=${COM_OBS:-$5}

# derived parameters
PDY=$(echo $CDATE | cut -c1-8)
cyc=$(echo $CDATE | cut -c9-10)

# get gdasapp root directory
readonly DIR_ROOT=$(cd "$(dirname "$(readlink -f -n "${BASH_SOURCE[0]}" )" )/../.." && pwd -P)
BUFR2IODA=$DIR_ROOT/build/bin/bufr2ioda.x
USH_IODA=$DIR_ROOT/ush/ioda
BUFRYAMLGEN=$USH_IODA/gen_bufr2ioda_yaml.py
BUFRJSONGEN=$USH_IODA/gen_bufr2ioda_json.py

# create output directory if it doesn't exist
mkdir -p $COM_OBS
if [ $? -ne 0 ]; then
    echo "cannot make $COM_OBS"
    exit 1
fi

#---------------------------------------------------------
# for some BUFR files, we will use python scripts
# and for others, bufr2ioda.x

#---------------------------
#----- python and json -----
# first specify what observation types will be processed by a script
BUFR_py="satwind_amv_goes"

for obtype in $BUFR_py; do
  cd $COM_OBS # TEMPORARY
  # this loop assumes that there is a python script and template with the same name
  echo "Processing ${obtype}..."

  # first generate a JSON from the template
  ${BUFRJSONGEN} -t ${config_template_dir}/bufr2ioda_${obtype}.json -o ${COM_OBS}/${obtype}_${PDY}${cyc}.json

  # now use the converter script for the ob type
  python3 $USH_IODA/bufr2ioda_${obtype}.py

  # check if converter was successful
  if [ $? == 0 ]; then
    # remove JSON file
    rm -rf ${COM_OBS}/${obtype}_${PDY}${cyc}.json
  else
    # warn and keep the JSON file
    echo "Problem running converter script for ${obtype}"
  fi
done

#----------------------------
#---- bufr2ioda and yaml ----
# need to ask Emily which will be YAML based
BUFR_yaml=""
