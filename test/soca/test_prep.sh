#!/bin/bash
set -e

project_binary_dir=$1
project_source_dir=$2

# Prepare runtime environement
export CDATE=2018041512        # Center of current cycle date
export GDATE=2018041506        # Center of previous cycle date
export assim_freq=6            # DA window
export COMOUT=${project_binary_dir}/test/soca/3dvar
export COMIN_OBS=${project_binary_dir}/test/soca/obs/r2d2-shared
export COMIN_GES=${project_binary_dir}/test/soca/bkg  # Backgrounds from previous forecast
export CASE="C48"               # TODO: Replace with or add OCNRES
export CASE_ENKF="C192"         # TODO: Needed but doesn't mean anything in this ctest context
export LEVS="75"                # TODO: Same as above
export OBS_YAML=${project_binary_dir}/test/soca/testinput/obs_list.yaml # list of obs for the experiment
export OBS_YAML_DIR=${project_source_dir}/parm/soca/obs/config      # path to UFO yaml files

mkdir -p ${project_binary_dir}/test/soca/HOMEgfs/sorc/ufs_da.fd/
export HOMEgfs=${project_binary_dir}/test/soca/HOMEgfs

ufsda_link=${project_binary_dir}/test/soca/HOMEgfs/sorc/ufs_da.fd/UFS-DA
[ ! -L "${ufsda_link}" ] && ln -s ${project_source_dir} ${ufsda_link}

ush_link=${project_binary_dir}/test/soca/HOMEgfs/ush
[ ! -L "${ush_link}" ] && ln -s ${project_source_dir}/ush ${ush_link}

export STATICB_DIR=${project_binary_dir}/test/soca/staticb                    # Static B-matrix
export FV3JEDI_STAGE_YAML=${project_binary_dir}/test/soca/testinput/dumy.yaml # Useless atmospheric stuff
export R2D2_OBS_DB=shared
export R2D2_OBS_DUMP=soca
export R2D2_OBS_SRC=gdasapp
export R2D2_OBS_WINDOW=24     # R2D2 sampling DB window

# Run prep step
echo "============================= Testing exgdas_global_marine_analysis_prep.py for clean exit"
${project_source_dir}/scripts/exgdas_global_marine_analysis_prep.py > exgdas_global_marine_analysis_prep.log

# Test that the obs were fetched
echo "============================= Testing for the presence of obs in the fetch target directory"
if [ ! "$(ls -A ${project_binary_dir}/test/soca/3dvar/analysis/obs/2018041512/)" ]; then
    exit 1
fi

# Test that the obs path in var.yaml exist
echo "============================= Testing the existence of obs in var.vaml"
obslist=`grep obsfile $COMOUT/analysis/var.yaml | grep -v obs_out`
for o in $obslist; do
    if [ ! "$o" == "obsfile:" ]; then
        if test -f "${project_binary_dir}/test/soca/3dvar/analysis/$o"; then
            echo " - $o exists"
        else
            echo " - $o does not exist"
            exit 1
        fi
    fi
done
