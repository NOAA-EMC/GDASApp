#!/bin/bash
# set up and run an atmospheric 3DVar regression test
# usage: regression_test_3dvar.sh <source_dir> <build_dir>
#-------------------------------------------------------------------------------
set -x
srcdir=$1
builddir=$2
rundir=$builddir/test/testrun/regression/atm_3dvar
dir_root=$( cd $srcdir/../../ && pwd )

# Load runtime environment
set +x
echo "Loading runtime environment ..."
source $dir_root/ush/detect_machine.sh
source $dir_root/ush/module-setup.sh
BUILD_TARGET=${MACHINE_ID:-'localhost'}
module use $dir_root/modulefiles
module load GDAS/$BUILD_TARGET
export PATH=$dir_root/install/bin:$PATH
# Detect the Python major.minor version
_regex="[0-9]+\.[0-9]+"
# shellcheck disable=SC2312
if [[ $(python --version) =~ ${_regex} ]]; then
    export PYTHON_VERSION="${BASH_REMATCH[0]}"
else
    echo "FATAL ERROR: Could not detect the python version"
    exit 1
fi
set -x
export PYTHONPATH=$dir_root/install/lib/python${PYTHON_VERSION}/site-packages:$PYTHONPATH

fix_root=$GDASAPP_REGRESSION_TEST_DATA_PATH/fix

# Set variables
cycle=2025102700
export PDY=${cycle:0:8}
export cyc=${cycle:8:2}
export assim_freq=6

export CASE="C384"
export CASE_ANL="C384"
export LEVS="128"
export DATA=./
export COMPONENT=atmos

export layout_x=6
export layout_y=6
export layout_gsib_x=18
export layout_gsib_y=12

export BERROR_YAML="atmosphere_background_error_static_gsibec"
export gsibec_ver=20250505
export fv3jedi_ver=20241115


res="${CASE:1}"
res_anl="${CASE_ANL:1}"
export npx_ges=$((res + 1))
export npy_ges=$((res + 1))
export npz_ges=$((LEVS - 1))
export npx_anl=$((res_anl + 1))
export npy_anl=$((res_anl + 1))
export npz_anl=$((LEVS - 1))
export half_assim_freq=$(($assim_freq / 2))
export gPDY=$(date +%Y%m%d -d "${PDY} ${cyc} - ${assim_freq} hours")
export gcyc=$(date +%H -d "${PDY} ${cyc} - ${assim_freq} hours")
export bPDY=$(date +%Y%m%d -d "${PDY} ${cyc} - ${half_assim_freq} hours")
export bcyc=$(date +%H -d "${PDY} ${cyc} - ${half_assim_freq} hours")
export YYYY=${PDY:0:4}
export MM=${PDY:4:2}
export DD=${PDY:6:2}
export bYYYY=${bPDY:0:4}
export bMM=${bPDY:4:2}
export bDD=${bPDY:6:2}
export OPREFIX=gdas.t${cyc}z.
export APREFIX=gdas.t${cyc}z.
export GPREFIX=gdas.t${gcyc}z.

# Create working directory
mkdir -p $rundir
cd $rundir || exit 1

# Link CRTM coefficients
[ -d $rundir/crtm ] && rm -rf $rundir/crtm
ln -sf $CRTM_FIX $rundir/crtm

# Copy BC files
mkdir -p $rundir/bc
cp -rf $GDASAPP_REGRESSION_TEST_DATA_PATH/varbc/gdas.${gPDY}/${gcyc}/atmos/* $rundir/bc/.

# Copy FV3-JEDI files
mkdir -p $rundir/fv3jedi
cp -rf $fix_root/fv3jedi/${fv3jedi_ver}/fv3files/akbk${npz_anl}.nc4 $rundir/fv3jedi/akbk.nc4
cp -rf $fix_root/fv3jedi/${fv3jedi_ver}/fv3files/fmsmpp.nml $rundir/fv3jedi/fmsmpp.nml
cp -rf $fix_root/fv3jedi/${fv3jedi_ver}/fv3files/field_table_gfdl $rundir/fv3jedi/field_table

# Copy observations
mkdir -p $rundir/obs
cp -rf $GDASAPP_REGRESSION_TEST_DATA_PATH/obs/gdas.${PDY}/${cyc}/atmos/* $rundir/obs/.

# Copy backgrounds
mkdir -p $rundir/bkg
cp -rf $GDASAPP_REGRESSION_TEST_DATA_PATH/bkg/${CASE}/gdas.${gPDY}/${gcyc}/model/atmos/history/${GPREFIX}cubed_sphere_grid_atmf006.nc $rundir/bkg/.
cp -rf $GDASAPP_REGRESSION_TEST_DATA_PATH/bkg/${CASE}/gdas.${gPDY}/${gcyc}/model/atmos/history/${GPREFIX}cubed_sphere_grid_sfcf006.nc $rundir/bkg/.

# Copy background error files
mkdir -p $rundir/berror
cp -rf $fix_root/gsibec/${gsibec_ver}/${CASE_ANL}/gfs_gsi_global.nml $rundir/berror/.
cp -rf $fix_root/gsibec/${gsibec_ver}/${CASE_ANL}/gsi-coeffs-gfs-global.nc4 $rundir/berror/.

# Create output directories
mkdir -p $rundir/anl

# Link executable
ln -sf $builddir/../bin/gdas.x $rundir/.

# create JCB YAML
cat > $rundir/atm_3dvar_jcb_input.yaml << EOF
# Search path for model and obs for JCB
# -------------------------------------
algorithm_path: "$dir_root/parm/jcb-algorithms"
app_path_algorithm: "$dir_root/parm/jcb-gdas/algorithm/atmosphere"
app_path_model: "$dir_root/parm/jcb-gdas/model/atmosphere"
app_path_observations: "$dir_root/parm/jcb-gdas/observations/atmosphere"
app_path_observation_chronicle: "$dir_root/parm/jcb-gdas/observation_chronicle/atmosphere"


# Places where we deviate from the generic file name of a yaml
# ------------------------------------------------------------
#final_increment_file: final_increment_gaussian
final_increment_file: atmosphere_final_increment_cubed_sphere
output_ensemble_increments_file: atmosphere_output_ensemble_increments_cubed_sphere
posterior_output_file: atmosphere_posterior_output_cubed_sphere
model_file: atmosphere_model_pseudo
initial_condition_file: atmosphere_background  # Initial conditions for 4D apps is background
background_error_file: "$BERROR_YAML"


# Assimilation window
# -------------------
window_begin: "${bYYYY}-${bMM}-${bDD}T${bcyc}:00:00Z"
window_length: "PT${assim_freq}H"
bound_to_include: begin
minimizer: DRPCG
final_diagnostics_departures: anlmob
final_prints_frequency: PT3H
number_of_outer_loops: 1
analysis_variables: [eastward_wind,northward_wind,air_temperature,air_pressure_at_surface,water_vapor_mixing_ratio_wrt_moist_air,cloud_liquid_ice,cloud_liquid_water,ozone_mass_mixing_ratio]

# Model things
# ------------
# Geometry
atmosphere_layout_x: $layout_x
atmosphere_layout_y: $layout_y
atmosphere_npx_ges: $npx_ges
atmosphere_npy_ges: $npy_ges
atmosphere_npz_ges: $npz_ges
atmosphere_npx_anl: $npx_anl
atmosphere_npy_anl: $npy_anl
atmosphere_npz_anl: $npz_anl

atmosphere_fv3jedi_files_path: ./fv3jedi  # Ideally this would be {{DATA}}/fv3jedi but FMS

# Background
atmosphere_background_path: ./bkg
atmosphere_background_ensemble_path: ./ens/mem%mem%

# Default background time is for 3D applications
atmosphere_background_time_iso: "${YYYY}-${MM}-${DD}T${cyc}:00:00Z"

# Background error
atmosphere_bump_data_directory: "./berror"
atmosphere_gsibec_path: "./berror"
atmosphere_number_ensemble_members: 0
atmosphere_layout_gsib_x: $layout_gsib_x
atmosphere_layout_gsib_y: $layout_gsib_y

# Forecasting
atmosphere_forecast_timestep: "PT6H"

# Write final increment on Guassian grid in variational
atmosphere_final_increment_prefix: "./anl/atminc."

atmosphere_variational_history_prefix: $GPREFIX
atmosphere_variational_analysis_prefix: $APREFIX

# IAU hours
atmosphere_iau_hours: 6,
atmosphere_iau_times_iso: ["${YYYY}-${MM}-${DD}T${cyc}:00:00Z"]

algorithm: 3dvar

# Observation things
# ------------------
observations:
 - prepbufr_adpsfc
 - atms_n20
 - atms_n21
 - atms_npp
#observations: all_observations

crtm_coefficient_path: "$rundir/crtm/"

# Naming conventions for observational files
atmosphere_obsdatain_path: "$rundir/obs"
atmosphere_obsdatain_prefix: "$OPREFIX"
atmosphere_obsdatain_suffix: ".nc"

atmosphere_obsdataout_path: "$rundir/anl"
atmosphere_obsdataout_prefix: diag_
atmosphere_obsdataout_suffix: "_${cycle}.nc"

# Naming conventions for bias correction files
atmosphere_obsbiasin_acft_path: "$rundir/bc"
atmosphere_obsbiasin_acft_prefix: "$GPREFIX"
atmosphere_obsbiasin_acft_suffix: ".satbias.nc"
atmosphere_obsbiasin_path: "$rundir/bc"
atmosphere_obsbiasin_prefix: "$GPREFIX"
atmosphere_obsbiasin_suffix: ".satbias.nc"
atmosphere_obstlapsein_prefix: "$GPREFIX"
atmosphere_obstlapsein_suffix: ".tlapse.txt"
atmosphere_obsbiascovin_prefix: "$GPREFIX"
atmosphere_obsbiascovin_suffix: ".satbias.nc"
atmosphere_obsbiascovin_acft_prefix: "$GPREFIX"
atmosphere_obsbiascovin_acft_suffix: ".satbias.nc"

atmosphere_obsbiasout_path: "$rundir/bc"
atmosphere_obsbiasout_prefix: "$APREFIX"
atmosphere_obsbiasout_suffix: ".satbias.nc"
atmosphere_obsbiasout_acft_path: "$rundir/bc"
atmosphere_obsbiasout_acft_prefix: "$APREFIX"
atmosphere_obsbiasout_acft_suffix: ".satbias.nc"
atmosphere_obsbiascovout_prefix: "$APREFIX"
atmosphere_obsbiascovout_suffix: ".satbias_cov.nc"
atmosphere_obsbiascovout_acft_prefix: "$APREFIX"
atmosphere_obsbiascovout_acft_suffix: ".satbias_cov.nc"
EOF

# render YAML with JCB
echo "Calling JCB render"
jcb render $rundir/atm_3dvar_jcb_input.yaml $rundir/atm_3dvar.yaml

if [ $? -ne 0 ]; then
   echo "YAML creation failed"
   exit 1
fi

# run variational application
nprocs=$((layout_x * layout_y * 6))
exename="gdas.x"
cd $rundir || exit 1

# Export library path
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:${dir_root}/install/lib"

# Create yaml with job configuration
# TODO make below machine specific
memory="350Gb"
nodes=$(( (nprocs / 36 ) ))
APRUN="srun -n ${nprocs} --cpu-bind=cores"

if [[ ${MACHINE_ID} == "gaeac6" ]]; then
    memory=0
fi
config_yaml="./config_atm_3dvar_submit.yaml"
cat <<EOF > ${config_yaml}
machine: ${MACHINE_ID}
homegdas: ${dir_root}
job_name: gdasapp_regtest_atm_3dvar_submit
walltime: "00:10:00"
nodes: ${nodes}
ntasks_per_node: 36
threads_per_task: 1
memory: ${memory}
command: $APRUN $rundir/$exename fv3jedi variational $rundir/atm_3dvar.yaml
filename: submit_gdasapp_regtest_atm_3dvar.sh
EOF

# Create script to execute j-job. Set job scheduler
${dir_root}/test/generate_job_script.py ${config_yaml}
SCHEDULER=$(echo $(grep SCHEDULER ${dir_root}/test/workflow/hosts/${MACHINE_ID}.yaml | cut -d":" -f2) | tr -d ' ')

# Submit script to execute j-job
if [[ $SCHEDULER = 'slurm' ]]; then
    sbatch --export=ALL --wait submit_gdasapp_regtest_atm_3dvar.sh
elif [[ $SCHEDULER = 'pbspro' ]]; then
    qsub -V -W block=true submit_gdasapp_regtest_atm_3dvar.sh
else
    mpirun -n $nprocs $rundir/$exename fv3jedi variational atm_3dvar.yaml
fi
