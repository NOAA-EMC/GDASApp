#!/bin/bash
################################################################################
####  UNIX Script Documentation Block
#                      .                                             .
# Script name:         exgdas_global_marine_analysis_bmat_vrfy.sh
# Script description:  Diagnose the JEDI/SOCA B-matrix
#
# Author: Guillaume Vernieres        Org: NCEP/EMC     Date: 2023-01-12
#
# Abstract: This script runs the JEDI/SOCA dirac application with the B-matrix
#           used in the variational step
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
# Compute the impulse response of the B-matrix from the variational application
# field = 1: tocn
# field = 2: socn
# field = 3: ssh
# field = 4: cicen
# field = 5: hicen

arr=("tocn" "socn" "ssh" "cicen" "hicen")
level=1
ndiracs=100

for i in "${!arr[@]}"
do
    var=${arr[i]}
    ifield=$((i+1))
    # generate dirac yamls
cat > dirac_output.yaml << EOL
datadir: ./Data
exp: dirac_${var}_${level}
type: an
EOL

    ${DIRAC} --varyaml 'var.yaml' \
             --fields 'soca_gridspec.nc' \
             --dim1 'xaxis_1' \
             --dim2 'yaxis_1' \
             --diracyaml 'dirac.yaml' \
             --ndiracs ${ndiracs} \
             --level ${level} \
             --fieldindex ${ifield} \
             --statevars tocn socn ssh cicen hicen \
             --diracoutput dirac_output.yaml
    export err=$?

    # run the dirac application
    $APRUN_OCNANAL $JEDI_BIN/soca_dirac.x dirac.yaml > dirac.out 2>&1
    export err=$?
done

################################################################################

exit ${err}

################################################################################
