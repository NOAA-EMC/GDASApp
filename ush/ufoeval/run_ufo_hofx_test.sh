#!/bin/bash
# run_hfo_hofx_test.sh
# This script is intended to simplify/automate large portions
# of the UFO acceptance for GDAS.
# This script will:
# - Create a working directory
# - Stage fix files, obs, geovals, etc.
# - Run the UFO test executable(s) necessary
# - Produce an EVA YAML
# - Run EVA
#-------------------------------------------------------------

# ==============================================================================
usage() {
  set +x
  echo
  echo "Usage: $0 [-c cycle] [-q] [-x] [-s] [-k] [-h] instrument"
  echo
  echo "  -c  cycle to run DEFAULT=2021080100"
  echo "  -q  run without data filtering"
  echo "  -x  don't run eva DEFAULT=run eva"
  echo "  -s  just produce eva stats plots DEFAULT=produce lots of plots"
  echo "  -k  keep output directory"
  echo "  -h  display this message and quit"
  echo
  exit 1
}

# ==============================================================================

cycle=2024021900
run_filtering=YES
run_eva=YES
eva_stats_only=NO
keep_output=NO 

while getopts "c:hsxq" opt; do
  case $opt in
    c)
      cycle=$OPTARG
      ;;
    q)
      run_filtering=NO
      ;;
    x)
      run_eva=NO 
      ;;
    s)
      eva_stats_only=YES
      ;;
    k)
      keep_output=YES
      ;;
    h|\?|:)
      usage
      ;;
  esac
done
shift $((OPTIND - 1))

if [ $# -ne 1 ]; then
   echo "Incorrect number of arguments"
   usage 
fi

obtype=$1

#--------------- User modified options below -----------------

machine=${machine:-orion} 

if [ $machine = orion ]; then
   if [ $run_filtering == NO ]; then
      workdir=/work2/noaa/da/$LOGNAME/ufoeval/$cycle/${obtype}_noqc
      echo "Run without data filtering"
   else
      workdir=/work2/noaa/da/$LOGNAME/ufoeval/$cycle/${obtype}
   fi
   GDASApp=${GDASApp:-/work2/noaa/da/$LOGNAME/git/GDASApp/} # Change this to your own branch
   JCBinstall=${JCBinstall:-/work2/noaa/da/cmartin/CI/GDASApp/opt}
   JCBpylib=$JCBinstall/lib/python3.7/site-packages
elif [ $machine = hera ]; then
   if [ $run_filtering == NO ]; then
      workdir=/scratch1/NCEPDEV/stmp2/$LOGNAME/ufoeval/$cycle/${obtype}_noqc
   else
      workdir=/scratch1/NCEPDEV/stmp2/$LOGNAME/ufoeval/$cycle/${obtype}
   fi
   GDASApp=${GDASApp:-/scratch1/NCEPDEV/da/$LOGNAME/git/GDASApp/} # Change this to your own branch
   JCBinstall=${JCBinstall:-/scratch1/NCEPDEV/da/Cory.R.Martin/CI/GDASApp/opt}
   JCBpylib=$JCBinstall/lib/python3.10/site-packages
else
   echo "Machine " $machine "not found"
   exit 1
fi

if [ $keep_output = YES ]; then
  datetime=`date +%F:%T`
  workdir=${workdir}_datetime
fi

exename=test_ObsFilters.x

#-------------- Do not modify below this line ----------------
# paths that should only be changed by an expert user

dataprocdate=20240815 # Production date of test data

obtype_short=${obtype:0:4}
if [ $obtype_short = "cris" ] || [ $obtype_short = "iasi" ] || [ $obtype_short = "hirs" ] || [ $obtype_short = "sevi" ] || \
   [ $obtype_short = "avhr" ] || [ $obtype_short = "mhs_" ] || [ $obtype_short = "ssmi" ] || [ $obtype_short = "amsu" ] || \
   [ $obtype_short = "atms" ]; then
   radiance="YES"
else 
   radiance="NO"
fi

if [ $machine = orion ]; then
    export Datapath='/work2/noaa/da/acollard/UFO_eval/data/gsi_geovals_l127/nofgat_feb2024/'$dataprocdate 
    FixDir=/work2/noaa/da/cmartin/GDASApp/fix
elif [ $machine = hera ]; then
    export Datapath='/scratch1/NCEPDEV/da/Emily.Liu/UFO_eval/data/gsi_geovals_l127/nofgat_aug2021/'$dataprocdate
    FixDir=/scratch1/NCEPDEV/da/Cory.R.Martin/GDASApp/fix
else
   echo "Machine " $machine "not found"
   exit
fi

GeoDir=$Datapath/geovals/
ObsDir=$Datapath/obs/
BCDir=$Datapath/bc/

# other variables that should not change often
export CDATE=$cycle
export assim_freq=6
export half_assim_freq=$(($assim_freq / 2))
export GDATE=$(date +%Y%m%d%H -d "${CDATE:0:8} ${CDATE:8:2} - ${assim_freq} hours")
export BDATE=$(date +%Y%m%d%H -d "${CDATE:0:8} ${CDATE:8:2} - ${half_assim_freq} hours")
export PDY=${CDATE:0:8}
export cyc=${CDATE:8:2}
export YYYY=${CDATE:0:4}
export MM=${CDATE:4:2}
export DD=${CDATE:6:2}
export gPDY=${GDATE:0:8}
export gcyc=${GDATE:8:2}
export bPDY=${BDATE:0:8}
export bcyc=${BDATE:8:2}
export bYYYY=${BDATE:0:4}
export bMM=${BDATE:4:2}
export bDD=${BDATE:6:2}
export CASE="C768"
export CASE_ANL="C384"
export LEVS="128"
export DATA=./
export COMPONENT=atmos
export OPREFIX=gdas.t${cyc}z
export APREFIX=gdas.t${cyc}z
export GPREFIX=gdas.t${gcyc}z

# Load Modules for GDASApp
module use $GDASApp/modulefiles
module load GDAS/$machine
export PYTHONPATH=$GDASApp/ush:$PYTHONPATH

# Create and set up the working directory
[ -d $workdir ] && rm -rf $workdir
mkdir -p $workdir

# Link CRTM coefficients
[ -d $workdir/crtm ] && rm -rf $workdir/crtm
ln -sf $FixDir/crtm/2.4.0 $workdir/crtm

# copy BC files
if [ $radiance = "YES" ]; then
  cp -rf $BCDir/${GPREFIX}.${obtype}.tlapse.txt $workdir/${GPREFIX}.${obtype}.tlapse.txt
  cp -rf $BCDir/${GPREFIX}.${obtype}.satbias.nc $workdir/${GPREFIX}.${obtype}.satbias.nc
fi

# Copy obs and geovals
cp -rf $GeoDir/${obtype}_geoval_${cycle}.nc4 $workdir/${OPREFIX}.${obtype}_geoval.tm00.nc
cp -rf $ObsDir/${obtype}_obs_${cycle}.nc4 $workdir/${OPREFIX}.${obtype}.tm00.nc

# Link executable
ln -sf $GDASApp/build/bin/$exename $workdir/.

echo "Generating YAML"

# Copy/generate YAML for test executable
# need to add JCB to PATH and PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$JCBpylib
export PATH=$PATH:$JCBinstall/bin
# First, create the input file for JCB

cat > $workdir/temp.yaml << EOF
# Search path for model and obs for JCB
# -------------------------------------
algorithm_path: "$GDASApp/parm/jcb-algorithms"
app_path_algorithm: "$GDASApp/parm/jcb-gdas/algorithm/atmosphere"
app_path_model: "$GDASApp/parm/jcb-gdas/model/atmosphere"
app_path_observations: "$GDASApp/parm/jcb-gdas/observations/atmosphere"
app_path_observation_chronicle: "$GDASApp/parm/jcb-gdas/observation_chronicle/atmosphere"


# Places where we deviate from the generic file name of a yaml
# ------------------------------------------------------------
#final_increment_file: final_increment_gaussian
final_increment_file: final_increment_cubed_sphere
output_ensemble_increments_file: output_ensemble_increments_cubed_sphere
model_file: model_pseudo
initial_condition_file: background  # Initial conditions for 4D apps is background


# Assimilation window
# -------------------
window_begin: "${bYYYY}-${bMM}-${bDD}T${bcyc}:00:00Z"
window_length: "PT${assim_freq}H"
bound_to_include: begin

# Default background time is for 3D applications
atmosphere_background_time_iso: "${YYYY}-${MM}-${DD}T${cyc}:00:00Z"

algorithm: test_obs_filters

# Observation things
# ------------------
observations: [${obtype}]

crtm_coefficient_path: "$workdir/crtm/"

# Naming conventions for observational files
atmosphere_obsdatain_path: "$workdir"
atmosphere_obsdatain_prefix: "$OPREFIX."
atmosphere_obsdatain_suffix: ".tm00.nc"

atmosphere_obsdataout_path: "$workdir"
atmosphere_obsdataout_prefix: diag_
atmosphere_obsdataout_suffix: "_${cycle}.nc"

# Naming conventions for bias correction files
atmosphere_obsbiasin_path: "$workdir"
atmosphere_obsbiasin_prefix: "$GPREFIX."
atmosphere_obsbiasin_suffix: ".satbias.nc"
atmosphere_obstlapsein_prefix: "$GPREFIX."
atmosphere_obstlapsein_suffix: ".tlapse.txt"
atmosphere_obsbiascovin_prefix: "$GPREFIX."
atmosphere_obsbiascovin_suffix: ".satbias_cov.nc"

atmosphere_obsbiasout_path: "$workdir"
atmosphere_obsbiasout_prefix: "$APREFIX."
atmosphere_obsbiasout_suffix: ".satbias.nc"
atmosphere_obsbiascovout_prefix: "$APREFIX."
atmosphere_obsbiascovout_suffix: ".satbias_cov.nc"
EOF
# jcb render dictionary_of_templates.yaml jedi_config.yaml
echo "Calling JCB Render"
jcb render $workdir/temp.yaml $workdir/${obtype}_${cycle}.yaml
echo "Called JCB Render"

if [ $? -ne 0 ]; then
   echo "YAML creation failed"
   exit 1
fi

echo "Running executable"

# Run executable
cd $workdir
./$exename ${obtype}_${cycle}.yaml

if [ $? -ne 0 ]; then
   echo "*************** Running UFO failed ****************"
   RC=1
   if [ $run_eva == YES ]; then
       echo "Running EVA for diagnostic purposes"
   else
       exit 1
   fi
else
   RC=0
   if [ $run_eva == YES ]; then
       echo "Running EVA"
   else
       exit 0
   fi
fi

# Load EVA modules
module load EVA/$machine

# Generate EVA YAML
if [ $radiance = "YES" ]; then
  if [ $eva_stats_only = "YES" ]; then
    $GDASApp/ush/eva/gen_eva_obs_yaml.py -i ./${obtype}_${cycle}.yaml -t $GDASApp/ush/eva/jedi_gsi_compare_rad_summary.yaml -o $workdir
  else 
    $GDASApp/ush/eva/gen_eva_obs_yaml.py -i ./${obtype}_${cycle}.yaml -t $GDASApp/ush/eva/jedi_gsi_compare_rad.yaml -o $workdir
  fi
else
  $GDASApp/ush/eva/gen_eva_obs_yaml.py -i ./${obtype}_${cycle}.yaml -t $GDASApp/ush/eva/jedi_gsi_compare_conv.yaml -o $workdir
fi

# Run EVA
for yaml in $(ls eva_*.yaml); do
  eva $yaml
done

if [ $? -ne 0 ]; then
   echo "EVA failed"
   exit 1
else
   exit $RC
fi
