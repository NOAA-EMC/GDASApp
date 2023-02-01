#!/bin/bash
################################################################################
####  UNIX Script Documentation Block
#                      .                                             .
# Script name:         exgdas_global_marine_analysis_bmat.sh
# Script description:  Performs calculations in preparation for the global 
#                      marine analysis with SOCA
#
# Author: Andrew Eichamnn   Org: NCEP/EMC     Date: 2023-01-12
#
# Abstract: This script does the follwing in preparation for creating the 
#           global model ocean sea-ice analysis using SOCA:
#           - generates the DA grid
#           - computes diagonal of B based on the background
#           - creates the bump correlation operators
#
# $Id$
#
# Attributes:
#   Language: POSIX shell
#   Machine: Orion
#
################################################################################

#  Set environment.
export VERBOSE=${VERBOSE:-"YES"}
if [ $VERBOSE = "YES" ]; then
   echo $(date) EXECUTING $0 $* >&2
   set -x
fi

#  Directories
pwd=$(pwd)

#  Utilities
export NLN=${NLN:-"/bin/ln -sf"}


function bump_vars()
{
    tmp=$(ls -d ${1}_* )
    lov=()
    for v in $tmp; do
        lov[${#lov[@]}]=${v#*_}
    done
    echo "$lov"
}

function concatenate_bump()
{
    bumpdim=$1
    # Concatenate the bump files
    vars=$(bump_vars $bumpdim)
    n=$(wc -w <<< "$vars")
    echo "concatenating $n variables: $vars"
    lof=$(ls ${bumpdim}_${vars[0]})
    echo $lof
    for f in $lof; do
        bumpbase=${f#*_}
        output=bump/${bumpdim}_$bumpbase
        lob=$(ls ${bumpdim}_*/*$bumpbase)
        for b in $lob; do
            ncks -A $b $output
        done
    done
}

function clean_yaml()
{
    mv $1 tmp_yaml;
    sed -e "s/'//g" tmp_yaml > $1
}

function find_closest_bkgerr 
{
  input_date=$1
  filenames=$2
  files=($(ls ${filenames}))
  closest_file=""
  closest_diff=99999999999
  closest_date=""
  for file in "${files[@]}"; do
    file_date=$(echo "$file" | cut -d '.' -f 2)
    diff=$(date -d "$input_date" +%s -d "$file_date" +%s)
    diff=${diff#-}
    if [[ $diff -lt $closest_diff ]]; then
      closest_file=$file
      closest_diff=$diff
      closest_date=$file_date
    fi
  done
  echo "$closest_file"
}

################################################################################
# generate soca geometry
# TODO (Guillaume): Should not use all pe's for the grid generation
# TODO (Guillaume): Does not need to be generated at every cycles, store in static dir?
$APRUN_OCNANAL $JEDI_BIN/soca_gridgen.x gridgen.yaml
export err=$?; err_chk
if [ $err -gt 0  ]; then
    exit $err
fi

################################################################################
# Generate the parametric diag of B

# Window begin date
dt=$((assym_freq / 2))
gdate=$(date -d "${PDY:0:4}-${PDY:4:2}-${PDY:6:2} ${cyc}:00:00" +%s)
gdate=$((gdate - dt * 3600))
gdate=$(date -d @$gdate +"%Y-%m-%dT%H:%M:%SZ")

# Find the bkg error closest to the begining of the window
domains=("ocn" "ice")
for domain in "${domains[@]}"; do
    cp $(find_closest_bkgerr "${gdate}" "${SOCA_INPUT_FIX_DIR}/../bkgerror/${domain}.ensstddev.fc.*.nc") \
       ${domain}.bkgerr_stddev.incr.${gdate}.nc
done


#cp ${SOCA_INPUT_FIX_DIR}/../bkgerror/ocn.ensstddev.fc.2019-06-30T00:00:00Z.PT0S.nc ocn.bkgerr_stddev.incr.${gdate}.nc
#cp ${SOCA_INPUT_FIX_DIR}/../bkgerror/ice.ensstddev.fc.2019-06-30T00:00:00Z.PT0S.nc ice.bkgerr_stddev.incr.${gdate}.nc
#$APRUN_OCNANAL $JEDI_BIN/soca_convertincrement.x clim_stddev_b.yaml
#export err=$?; err_chk
#if [ $err -gt 0  ]; then
#    exit $err
#fi

################################################################################
set +x
if [ $VERBOSE = "YES" ]; then
   echo $(date) EXITING $0 with return code $err >&2
fi
exit $err

################################################################################

################################################################################
# Set decorrelation scales for bump C
$APRUN_OCNANAL $JEDI_BIN/soca_setcorscales.x soca_setcorscales.yaml > soca_setcorscales.out 2>&1
export err=$?; err_chk
if [ $err -gt 0  ]; then
    exit $err
fi

# TODO (G, C, R, ...): problem with ' character when reading yaml, removing from file for now
# 2D C from bump
yaml_bump2d=soca_bump2d.yaml
clean_yaml $yaml_bump2d
$APRUN_OCNANAL $JEDI_BIN/soca_error_covariance_training.x $yaml_bump2d 2>$yaml_bump2d.err
export err=$?; err_chk
if [ $err -gt 0  ]; then
    exit $err
fi

# 3D C from bump
yaml_list=`ls soca_bump3d_*.yaml`
for yaml in $yaml_list; do
    clean_yaml $yaml
    $APRUN_OCNANAL $JEDI_BIN/soca_error_covariance_training.x $yaml 2>$yaml.err
    export err=$?; err_chk
    if [ $err -gt 0  ]; then
        exit $err
    fi
done
concatenate_bump 'bump3d'

################################################################################
set +x
if [ $VERBOSE = "YES" ]; then
   echo $(date) EXITING $0 with return code $err >&2
fi
exit $err

################################################################################
