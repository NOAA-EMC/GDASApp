#!/bin/bash
set -e

project_binary_dir=$1
project_source_dir=$2

# Prepare runtime environement
export CDATE=2018041512        # Center of current cycle date
export GDATE=2018041506        # Center of previous cycle date
export gcyc=$(echo $GDATE | cut -c9-10)
export CDUMP=gdas
export GDUMP=gdas
export PDY=20180415
export cyc=12
export assim_freq=6            # DA window
export COMOUT=${project_binary_dir}/test/soca/3dvar
export DATA=${COMOUT}/analysis
export COMIN_OBS=${project_binary_dir}/test/soca/obs/r2d2-shared
export COMIN_GES=${project_binary_dir}/test/soca/bkg  # Backgrounds from previous forecast
export CASE_ANL="C48"           # TODO: Replace with or add OCNRES
export CASE="C48"               # TODO: Replace with or add OCNRES
export DOHYBVAR=False
export CASE_ENKF="C192"         # TODO: Needed but doesn't mean anything in this ctest context
export LEVS="75"                # TODO: Same as above
export OBS_LIST=${project_binary_dir}/test/soca/testinput/obs_list.yaml # list of obs for the experiment
export OBS_YAML=${project_binary_dir}/test/soca/testinput/obs_list.yaml # list of obs for the experiment
export OBS_YAML_DIR=${project_source_dir}/parm/soca/obs/config      # path to UFO yaml files

mkdir -p ${project_binary_dir}/test/soca/HOMEgfs/sorc/
export HOMEgfs=${project_binary_dir}/test/soca/HOMEgfs

ufsda_link=${project_binary_dir}/test/soca/HOMEgfs/sorc/gdas.cd
[ ! -L "${ufsda_link}" ] && ln -s ${project_source_dir} ${ufsda_link}

ush_link=${project_binary_dir}/test/soca/HOMEgfs/ush
[ ! -L "${ush_link}" ] && ln -s ${project_source_dir}/ush ${ush_link}

export JEDI_BIN=${project_binary_dir}/bin
export SOCA_INPUT_FIX_DIR=${project_binary_dir}/soca_static      # static soca files
export SOCA_VARS=tocn,socn,ssh
export DOMAIN_STACK_SIZE=2000000
export STATICB_DIR=${project_binary_dir}/test/soca/staticb       # Static B-matrix
export FV3JEDI_STAGE_YAML=${project_binary_dir}/test/soca/testinput/dumy.yaml # Useless atmospheric stuff
export R2D2_OBS_DB=shared
export R2D2_OBS_DUMP=soca
export R2D2_OBS_SRC=gdasapp
export R2D2_OBS_WINDOW=24     # R2D2 sampling DB window

export APRUN_SOCAANAL="$MPIEXEC_EXEC $MPIEXEC_NPROC 6"
