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


function clean_yaml()
{
    mv $1 tmp_yaml;
    sed -e "s/'//g" tmp_yaml > $1
}

################################################################################
# run 3DVAR FGAT
clean_yaml var.yaml
$APRUN_OCNANAL $JEDI_BIN/soca_var.x var.yaml
export err=$?; err_chk


# prepare MOM6 IAU increment
# Note: ${DATA}/INPUT/MOM.res.nc points to the MOM6 history file from the start of the window
#       and is used to get the valid vertical geometry of the increment
# TODO: Check what to do with (u,v), it seems that MOM6's iau expects (u, v) on the tracer grid
soca_incr=$(ls -t ${DATA}/Data/ocn.*3dvar*.incr* | head -1)
mom6_iau_incr=${DATA}/inc.nc
${HOMEgfs}/sorc/gdas.cd/ush/socaincr2mom6.py --incr "${soca_incr}" \
                                             --bkg "${DATA}/INPUT/MOM.res.nc" \
                                             --grid "${DATA}/soca_gridspec.nc" \
                                             --out "${mom6_iau_incr}"

# insert seaice analysis in CICE6 restart
# TODO: This should probably be in a separate j-job, that includes 
#       the mom6 incr postprocessing from above. 
launcher=$(echo $APRUN_OCNANAL | cut -d' ' -f1)
${launcher} -n 1 ${JEDI_BIN}/soca_convertstate.x soca_2cice_arctic.yaml
${launcher} -n 1 ${JEDI_BIN}/soca_convertstate.x soca_2cice_antarctic.yaml


################################################################################
set +x
if [ $VERBOSE = "YES" ]; then
   echo $(date) EXITING $0 with return code $err >&2
fi
exit $err

################################################################################
