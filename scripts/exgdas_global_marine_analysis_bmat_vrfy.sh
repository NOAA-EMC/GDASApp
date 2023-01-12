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
export DIRAC="${HOMEgfs}/sorc/gdas.cd/ush/ufsda/dirac_yaml.py"

################################################################################
# generate dirac yamls
cat > dirac_output.yaml << EOL
datadir: ./Data
exp: dirac_test
type: an
EOL

${DIRAC} --varyaml 'var.yaml' \
         --fields 'soca_gridspec.nc' \
         --dim1 'xaxis_1' \
         --dim2 'yaxis_1' \
         --diracyaml 'dirac.yaml' \
         --step 20 \
         --level 1 \
         --fieldindex 1 \
         --statevars tocn socn ssh cicen hicen \
         --diracoutput dirac_output.yaml
export err=$?

################################################################################
# run the dirac application
$APRUN_OCNANAL $JEDI_BIN/soca_dirac.x dirac.yaml > dirac.out 2>&1
export err=$?

################################################################################

exit ${err}

################################################################################
