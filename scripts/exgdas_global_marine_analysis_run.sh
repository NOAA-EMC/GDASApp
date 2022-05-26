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

################################################################################
#  Link COMOUT/analysis to $DATA/Data
#$NLN $COMOUT/analysis $DATA/Data

#  Link YAML to $DATA
#$NLN $COMOUT/analysis/fv3jedi_var.yaml $DATA/fv3jedi_var.yaml

#  Link executable to $DATA
#$NLN $JEDIVAREXE $DATA/fv3jedi_var.x

################################################################################
# run executable
#export pgm=$JEDIVAREXE
#. prep_step
#$APRUN_ATMANAL $DATA/fv3jedi_var.x $DATA/fv3jedi_var.yaml 1>&1 2>&2
#export err=$?; err_chk

################################################################################
# translate FV3-JEDI increment to FV3 readable format
#atminc_jedi=`ls $DATA/Data/anl/atminc_latlon*`
#atminc_fv3=$COMOUT/${CDUMP}.${cycle}.atminc.nc
#$INCPY $atminc_jedi $atminc_fv3

################################################################################
# Create log file noting creating of analysis increment file
#echo "$CDUMP $CDATE atminc and tiled sfcanl done at `date`" > $COMOUT/${CDUMP}.${cycle}.loginc.txt

################################################################################
set +x
if [ $VERBOSE = "YES" ]; then
   echo $(date) EXITING $0 with return code $err >&2
fi
exit $err

################################################################################
