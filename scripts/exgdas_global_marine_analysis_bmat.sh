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


function bump_vars()
{
    tmp=$(ls -d ${1}_* )
    lov=()
    for v in $tmp; do
        lov[${#lov[@]}]=${v#*_}
    done
    echo "$lov"
}

function concatenate_bump()
{
    bumpdim=$1
    # Concatenate the bump files
    vars=$(bump_vars $bumpdim)
    n=$(wc -w <<< "$vars")
    echo "concatenating $n variables: $vars"
    lof=$(ls ${bumpdim}_${vars[0]})
    echo $lof
    for f in $lof; do
        bumpbase=${f#*_}
        output=bump/${bumpdim}_$bumpbase
        lob=$(ls ${bumpdim}_*/*$bumpbase)
        for b in $lob; do
            ncks -A $b $output
        done
    done
}

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
# Prepare the diagonal of the parametric B
shopt -s nullglob
files=(ocn.bkgerr_stddev.incr.*.nc)
echo $files
if [ ${#files[@]} -gt 0 ]; then
  echo "Diag of B already staged, skipping the parametric diag B"
else
    # TODO: this step should be replaced by a post processing step of the ens. derived std. dev.
    $APRUN_OCNANAL $JEDI_BIN/soca_convertincrement.x parametric_stddev_b.yaml > parametric_stddev_b.out 2>&1
    export err=$?; err_chk
    if [ $err -gt 0  ]; then
        exit $err
    fi
fi
shopt -u nullglob

################################################################################
# Write ensemble weights for the hybrid envar
$APRUN_OCNANAL $JEDI_BIN/gdas_socahybridweights.x soca_ensweights.yaml
export err=$?; err_chk
if [ $err -gt 0  ]; then
    exit $err
fi

################################################################################
# Compute the ens std. dev, ignore ssh variance
# TODO (G): Implement what's below into one single oops application
# 0 - Compute moments of original ensemble, used at the diag of the first 
#     component of the hybrid B
# 1 - Ensemble perturbations:
#       o Vertically Interpolate to the deterministic layers
#       o Recenter around 0 to create an ensemble of perturbations
# 2 - Filter members and apply the linear steric height balance to each members
# 3 - Copy h from deterministic to unbalanced perturbations
# 4 - Compute moments of converted ensemble perturbations

# Compute ensemble moments
clean_yaml soca_clim_ens_moments.yaml
$APRUN_OCNANAL $JEDI_BIN/soca_ensmeanandvariance.x soca_clim_ens_moments.yaml
export err=$?; err_chk
if [ $err -gt 0  ]; then
    exit $err
fi

# Compute ensemble perturbations, vertically remap to cycle's vertical geometry
clean_yaml soca_clim_ens_perts.yaml
$APRUN_OCNANAL $JEDI_BIN/soca_ensrecenter.x soca_clim_ens_perts.yaml
export err=$?; err_chk
if [ $err -gt 0  ]; then
    exit $err
fi

# Vertical filtering of the 3D perturbations and recompute the steric height perturbation
clean_yaml soca_apply_steric.yaml
$APRUN_OCNANAL $JEDI_BIN/soca_convertincrement.x soca_apply_steric.yaml
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
# Set decorrelation scales for bump C
$APRUN_OCNANAL $JEDI_BIN/soca_setcorscales.x soca_setcorscales.yaml
export err=$?; err_chk
if [ $err -gt 0  ]; then
    exit $err
fi

################################################################################
# Set localization scales for the hybrid en. var.
$APRUN_OCNANAL $JEDI_BIN/soca_setcorscales.x soca_setlocscales.yaml
export err=$?; err_chk
if [ $err -gt 0  ]; then
    exit $err
fi

################################################################################
# Compute convolution coefs for C
# TODO (G, C, R, ...): problem with ' character when reading yaml, removing from file for now
# 2D C from bump
if false; then
    # TODO: resurect this section when making use of bump 3D in the static B, skip for now
    yaml_bump2d=soca_bump2d.yaml
    clean_yaml $yaml_bump2d
    $APRUN_OCNANAL $JEDI_BIN/soca_error_covariance_toolbox.x $yaml_bump2d 2>$yaml_bump2d.err
    export err=$?; err_chk
    if [ $err -gt 0  ]; then
        exit $err
    fi

    # 3D C from bump
    yaml_list=`ls soca_bump3d_*.yaml`
    for yaml in $yaml_list; do
        clean_yaml $yaml
        $APRUN_OCNANAL $JEDI_BIN/soca_error_covariance_toolbox.x $yaml 2>$yaml.err
        export err=$?; err_chk
        if [ $err -gt 0  ]; then
            exit $err
        fi
    done
    concatenate_bump 'bump3d'
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
# Create ensemble of perturbations for the cycle

# Use ensemble recenter with "zerocenter"

# Apply inverse balance to perturbations, use deterministic background as trajectory


################################################################################
set +x
if [ $VERBOSE = "YES" ]; then
   echo $(date) EXITING $0 with return code $err >&2
fi
exit $err

################################################################################
