#!/bin/bash
################################################################################
####  UNIX Script Documentation Block
#                      .                                             .
# Script name:         exgdas_global_marine_analysis_run.sh
# Script description:  Runs the global marine analysis with SOCA
#
# Author: Guillaume Vernieres        Org: NCEP/EMC     Date: 2022-04-24
#
# Abstract: This script makes a global model ocean sea-ice analysis using SOCA
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

function socaincr2mom6 {
# Function to process the JEDI/SOCA increment file
# and create a MOM6 increment file with the correct
# variable names and dimensions

  incr=$1
  bkg=$2
  grid=$3
  incr_out=$4

  # Create a temporary directory
  scratch=scratch_socaincr2mom6
  mkdir -p $scratch
  cd $scratch

  # Rename zaxis_1 to Layer in the increment file
  ncrename -d zaxis_1,Layer $incr

  # Extract h from the background file and rename axes to be consistent
  ncks -A -C -v h $bkg h.nc
  ncrename -d time,Time -d zl,Layer -d xh,xaxis_1 -d yh,yaxis_1 h.nc

  # Replace h in the increment file with h from the background file
  ncks -A -C -v h h.nc $incr

  # Add longitude and latitude from the grid file to the increment file
  ncks -A -C -v lon $grid $incr
  ncks -A -C -v lat $grid $incr

  # Move the final increment file to the desired output location
  mv $incr $incr_out

  # Clean up the temporary directory
  cd ..
  rm -r $scratch
}

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

################################################################################
# generate soca geometry
# TODO (Guillaume): Should not use all pe's for the grid generation
# TODO (Guillaume): Does not need to be generated at every cycles, store in static dir?
$APRUN_OCNANAL $JEDI_BIN/soca_gridgen.x gridgen.yaml > gridgen.out 2>&1
export err=$?; err_chk
if [ $err -gt 0  ]; then
    exit $err
fi

################################################################################
# Generate the parametric diag of B
$APRUN_OCNANAL $JEDI_BIN/soca_convertincrement.x parametric_stddev_b.yaml > parametric_stddev_b.out 2>&1
export err=$?; err_chk
if [ $err -gt 0  ]; then
    exit $err
fi
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
