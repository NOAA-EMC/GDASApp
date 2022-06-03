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

set -e

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
# run executable
#export pgm=$SOCAVAREXE  # TODO (Guillaume): What's that?
#. prep_step             # TODO (Guillaume): What's that?


# TODO (Guillaume): Move that somewhere else
RUNCMD='singularity exec -e /home/gvernier/containers/jedi-gnu-openmpi-dev_latest.sif mpirun'

# Generate soca geometry
$RUNCMD $JEDI_BIN/soca_gridgen.x gridgen.yaml 2> grigen.err

# run 3DVAR FGAT
$RUNCMD $JEDI_BIN/soca_var.x var.yaml 2>var.err

################################################################################
set +x
if [ $VERBOSE = "YES" ]; then
   echo $(date) EXITING $0 with return code $err >&2
fi
exit $err

################################################################################
