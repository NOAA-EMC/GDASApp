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

function clean_yaml()
{
    mv $1 tmp_yaml;
    sed -e "s/'//g" tmp_yaml > $1
}

################################################################################
# run 3DVAR FGAT
clean_yaml var.yaml
$APRUN_OCNANAL $JEDI_BIN/soca_var.x var.yaml > var.out 2>&1
export err=$?; err_chk


# increments update for MOM6
# Note: ${DATA}/INPUT/MOM.res.nc points to the MOM6 history file from the start of the window
#       and is used to get the valid vertical geometry of the increment
socaincr=$(ls -t ${DATA}/Data/ocn.*3dvar*.incr* | head -1)
mom6incr=${COMOUT}/inc.nc
( socaincr2mom6 ${socaincr} ${DATA}/INPUT/MOM.res.nc ${DATA}/soca_gridspec.nc ${mom6incr} )



################################################################################
set +x
if [ $VERBOSE = "YES" ]; then
   echo $(date) EXITING $0 with return code $err >&2
fi
exit $err

################################################################################
