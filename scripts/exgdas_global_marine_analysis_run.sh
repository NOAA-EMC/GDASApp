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
# run executable
#export pgm=$SOCAVAREXE  # TODO (Guillaume): What's that?
#. prep_step             # TODO (Guillaume): What's that?

# Generate soca geometry
# TODO (Guillaume): Should not use all pe's for the grid generation
# TODO (Guillaume): Does not need to be generated at every cycles, store in static dir?
$APRUN_SOCAANAL $JEDI_BIN/soca_gridgen.x gridgen.yaml 2> grigen.err

# Generate the parametric diag of B
$APRUN_SOCAANAL $JEDI_BIN/soca_convertincrement.x parametric_stddev_b.yaml 2> parametric_stddev_b.err

# run 3DVAR FGAT
$APRUN_SOCAANAL $JEDI_BIN/soca_var.x var.yaml 2>var.err

################################################################################
set +x
if [ $VERBOSE = "YES" ]; then
   echo $(date) EXITING $0 with return code $err >&2
fi
exit $err

################################################################################
