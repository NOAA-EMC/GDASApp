#!/bin/bash
################################################################################
####  UNIX Script Documentation Block
#                      .                                             .
# Script name:         exgdas_global_marine_analysis_chkpt.sh
# Script description:  Prepare MOM6 IAU increment and insert the seaice analysis
#                       in the CICE6 restart
#
# Author: Guillaume Vernieres        Org: NCEP/EMC     Date: 2023-04-01
#
# Abstract: Doodads for ocean and seaice DA
#
# $Id$
#
# Attributes:
#   Language: POSIX shell
#   Machine:
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

################################################################################
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
export err=$?; err_chk

################################################################################
# Insert seaice analysis in CICE6 restart
# TODO: This should probably be in a separate j-job, that includes
#       the mom6 incr postprocessing from above.

$APRUN_OCNANAL ${JEDI_BIN}/soca_convertstate.x soca_2cice_arctic.yaml
$APRUN_OCNANAL ${JEDI_BIN}/soca_convertstate.x soca_2cice_antarctic.yaml
export err=$?; err_chk

################################################################################
set +x
if [ $VERBOSE = "YES" ]; then
   echo $(date) EXITING $0 with return code $err >&2
fi
exit $err

################################################################################
