#!/bin/bash
################################################################################
####  UNIX Script Documentation Block
#                      .                                             .
# Script name:         exgdas_global_marine_analysis_bmat.sh
# Script description:  Performs calculations in preparation for the global
#                      marine analysis with SOCA
#
# Author: Andrew Eichamnn   Org: NCEP/EMC     Date: 2023-01-12
#
# Abstract: This script does the follwing in preparation for creating the
#           global model ocean sea-ice analysis using SOCA:
#           - generates the DA grid
#           - computes diagonal of B based on the background if a std. dev. file
#             was not staged. TODO: Remove this option in the future
#           - creates the bump correlation operators
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
# Generate soca geometry if needed
if [[ -e 'soca_gridspec.nc' ]]; then
    echo "soca_gridspc.nc already exists, skip the grid generation step"
else
    # Run soca_gridgen.x if the grid was not staged
    # TODO (Guillaume): Should not use all pe's for the grid generation
    $APRUN_OCNANAL $JEDI_BIN/soca_gridgen.x gridgen.yaml
    export err=$?; err_chk
    if [ $err -gt 0  ]; then
        exit $err
    fi
fi

################################################################################
# Write ensemble weights for the hybrid envar
$APRUN_OCNANAL $JEDI_BIN/gdas_socahybridweights.x soca_ensweights.yaml
export err=$?; err_chk
if [ $err -gt 0  ]; then
    exit $err
fi

################################################################################
# Ensemble perturbations for the EnVAR and diagonal of static B
# Static B:
#   - Compute moments of original ensemble with the balanced ssh removed
#     from the statistics
#
# Ensemble of perturbations:
#   - apply the linear steric height balance to each members, using the
#     deterministic for trajectory.
#   - add the unblanced ssh to the steric ssh field
# Diagnostics:
#   - variance explained by the steric heigh
#   - moments

# Process static ensemble
clean_yaml soca_clim_ens_moments.yaml
$APRUN_OCNANAL $JEDI_BIN/gdas_ens_handler.x soca_ensb.yaml
export err=$?; err_chk
if [ $err -gt 0  ]; then
    exit $err
fi

################################################################################
# Correlation and Localization operators
shopt -s nullglob
files=(./bump/*.nc)
echo $files
if [ ${#files[@]} -gt 0 ]; then
    echo "BUMP/NICAS correlation and localization already staged, skipping BUMP initialization"
    set +x
    if [ $VERBOSE = "YES" ]; then
        echo $(date) EXITING $0 with return code $err >&2
    fi
    exit $err  # Exit early, we're done with B
    shopt -u nullglob
fi

################################################################################
# Set localization scales for the hybrid en. var.
$APRUN_OCNANAL $JEDI_BIN/soca_setcorscales.x soca_setlocscales.yaml
export err=$?; err_chk
if [ $err -gt 0  ]; then
    exit $err
fi

################################################################################
# Compute convolution coefs for L
clean_yaml soca_bump_loc.yaml
$APRUN_OCNANAL $JEDI_BIN/soca_error_covariance_toolbox.x soca_bump_loc.yaml
export err=$?; err_chk
if [ $err -gt 0  ]; then
    exit $err
fi

################################################################################
set +x
if [ $VERBOSE = "YES" ]; then
   echo $(date) EXITING $0 with return code $err >&2
fi
exit $err

################################################################################
