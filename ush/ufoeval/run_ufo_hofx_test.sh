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
#--------------- User modified options below -----------------
obtype=$1
cycle=${2:-2021080100}

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
   echo "Incorrect number of arguments"
   echo "Usage:"
   echo $0 instrument [cycle]
   exit 1
fi

machine=hera
#GDASApp=/work2/noaa/da/cmartin/GDASApp/dev/GDASApp # Change this to your own branch
GDASApp=/scratch1/NCEPDEV/da/Andrew.Collard/git/GDASApp_sprint-ioda-converters/ # Change this to your own branch

if [ $machine = orion ]; then
   workdir=/work2/noaa/da/$LOGNAME/ufoeval/$cycle/$obtype
elif [ $machine = hera ]; then
   workdir=/scratch1/NCEPDEV/stmp2/$LOGNAME/ufoeval/$cycle/$obtype
else
   echo "Machine " $machine "not found"
   exit
fi

yamlpath=$GDASApp/parm/atm/obs/testing/${obtype}.yaml
exename=test_ObsFilters.x

#-------------- Do not modify below this line ----------------
# paths that should only be changed by an expert user

obtype_short=${obtype:0:4}
if [ $obtype_short = "cris" ] || [ $obtype_short = "iasi" ] || [ $obtype_short = "hirs" ] || [ $obtype_short = "sevi" ] || \
   [ $obtype_short = "avhr" ] || [ $obtype_short = "mhs_" ] || [ $obtype_short = "ssmi" ]; then
   radiance="YES"
else 
   radiance="NO"
fi

if [ $machine = orion ]; then
    export Datapath='/work2/noaa/da/cmartin/UFO_eval/data/gsi_geovals_l127/nofgat_aug2021/20220816' 
    FixDir=/work2/noaa/da/cmartin/GDASApp/fix
elif [ $machine = hera ]; then
    export Datapath='/scratch1/NCEPDEV/da/Cory.R.Martin/UFO_eval/data/gsi_geovals_l127/nofgat_aug2021/20230126'
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
export GDATE=$(date +%Y%m%d%H -d "${CDATE:0:8} ${CDATE:8:2} - ${assim_freq} hours")
export PDY=${CDATE:0:8}
export cyc=${CDATE:8:2}
export gPDY=${GDATE:0:8}
export gcyc=${GDATE:8:2}
export CASE="C768"
export CASE_ENKF="C384"
export LEVS="128"

# Load Modules for GDASApp
module use $GDASApp/modulefiles
module load GDAS/$machine
export PYTHONPATH=$GDASApp/ush:$PYTHONPATH

# Create and set up the working directory
mkdir -p $workdir

# Link CRTM coefficients
rm -rf $workdir/crtm
ln -sf $FixDir/crtm/2.3.0 $workdir/crtm

# copy BC files
if [ $radiance = "YES" ]; then
  cp -rf $BCDir/${obtype}*${GDATE}* $workdir/.
fi

# Copy obs and geovals
cp -rf $GeoDir/${obtype}_geoval_${cycle}.nc4 $workdir/.
cp -rf $ObsDir/${obtype}_obs_${cycle}.nc4 $workdir/.

# Link executable
ln -sf $GDASApp/build/bin/$exename $workdir/.

echo "Generating YAML"

# Copy/generate YAML for test executable
# First, create the input YAMLs for the genYAML script
cat > $workdir/obslist.yaml << EOF
- !INC $yamlpath
EOF
cat > $workdir/temp.yaml << EOF
template: $GDASApp/parm/atm/hofx/hofx_ufotest.yaml
output: $workdir/${obtype}_${cycle}.yaml
config:
  COMPONENT: atmos
  OBS_LIST: $workdir/obslist.yaml
  DATA: ./
  OPREFIX: gdas.t${cyc}z
  APREFIX: gdas.t${cyc}z
  GPREFIX: gdas.t${gcyc}z
EOF
$GDASApp/ush/genYAML --config $workdir/temp.yaml

echo "Running executable"

# Run executable
cd $workdir
./$exename ${obtype}_${cycle}.yaml

echo "Running EVA"

# Load EVA modules
module load EVA/$machine

# Generate EVA YAML
if [ $radiance = "YES" ]; then
  $GDASApp/ush/eva/gen_eva_obs_yaml.py -i ./${obtype}_${cycle}.yaml -t $GDASApp/ush/eva/jedi_gsi_compare_rad.yaml -o $workdir
else
  $GDASApp/ush/eva/gen_eva_obs_yaml.py -i ./${obtype}_${cycle}.yaml -t $GDASApp/ush/eva/jedi_gsi_compare_conv.yaml -o $workdir
fi

# Run EVA
for yaml in $(ls eva_*.yaml); do
  eva $yaml
done
