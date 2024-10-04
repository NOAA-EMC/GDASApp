#! /usr/bin/env bash

################################################################################
####  UNIX Script Documentation Block
#                      .                                             .
# Script name:         exgdas_global_marine_analysis_chkpt.sh
# Script description:  Prepare MOM6 IAU increment and insert the seaice analysis
#                       in the CICE6 restart
#
# Author: Guillaume Vernieres        Org: NCEP/EMC     Date: 2023-04-01
#
# Abstract: This script does the following:
#           1 - Post processing of the ocean increment for MOM6 IAU.
#           2 - De-aggregates the sea-ice analysis and prepares the CICE6 analysis restart
#           3 - Optionaly interpolates the Tref increment from the NSST analysis onto the
#               MOM6 grid and merges it with the JEDI/SOCA increment
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

# prepare nsst yaml
if [ $DO_MERGENSST = "YES" ]; then
cat > nsst.yaml << EOF
sfc_fcst: ${COM_ATMOS_HISTORY_PREV}/${GPREFIX}sfcf006.nc
sfc_ana: ${COM_ATMOS_ANALYSIS}/${APREFIX}sfcanl.nc
nlayers: 5
EOF

   ${HOMEgfs}/sorc/gdas.cd/ush/socaincr2mom6.py --incr "${soca_incr}" \
                                                --bkg "${DATA}/INPUT/MOM.res.nc" \
                                                --grid "${DATA}/soca_gridspec.nc" \
                                                --out "${mom6_iau_incr}" \
                                                --nsst_yaml "nsst.yaml"
else
   $APRUN_OCNANAL ${JEDI_BIN}/gdas_incr_handler.x socaincr2mom6.yaml
fi
export err=$?
if [ $err -gt 0  ]; then
    exit $err
fi

################################################################################
# Insert seaice analysis in CICE6 restart
# TODO: This should probably be in a separate j-job, that includes
#       the mom6 incr postprocessing from above.

$APRUN_OCNANAL ${JEDI_BIN}/gdas.x soca convertstate soca_2cice_arctic.yaml
err=$?; err_chk
$APRUN_OCNANAL ${JEDI_BIN}/gdas.x soca convertstate soca_2cice_antarctic.yaml
export err=$?; err_chk

################################################################################
set +x
if [ $VERBOSE = "YES" ]; then
   echo $(date) EXITING $0 with return code $err >&2
fi
exit $err

################################################################################
