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
cycle=2021080100
obtype=amsua_n19
GDASApp=/work2/noaa/da/cmartin/GDASApp/dev/GDASApp # Change this to your own branch
workdir=/work2/noaa/da/$LOGNAME/ufoeval/$cycle/$obtype
yamlpath=$GDASApp/parm/atm/obs/testing/amsua_n19.yaml
exename=test_ObsFilters.x
machine=orion
radiance="YES"

#-------------- Do not modify below this line ----------------
# paths that should only be changed by an expert user
GeoDir=/work2/noaa/da/cmartin/UFO_eval/data/gsi_geovals_l127/nofgat_aug2021/20220816/geovals/
ObsDir=/work2/noaa/da/cmartin/UFO_eval/data/gsi_geovals_l127/nofgat_aug2021/20220816/obs/
BCDir=/work2/noaa/da/cmartin/UFO_eval/data/gsi_geovals_l127/nofgat_aug2021/20220816/bc/
FixDir=/work2/noaa/da/cmartin/GDASApp/fix/

# other variables that should not change often
export CDATE=$cycle
export assim_freq=6
export GDATE=$(date +%Y%m%d%H -d "${CDATE:0:8} ${CDATE:8:2} - ${assim_freq} hours")
export PDY=${CDATE:0:8}
export cyc=${CDATE:8:2}

# Load Modules for GDASApp
module use $GDASApp/modulefiles
module load GDAS/$machine
export PYTHONPATH=$GDASApp/ush:$PYTHONPATH

# Create and set up the working directory
mkdir -p $workdir

# Link CRTM coefficients
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

# Copy/generate YAML for test executable
# First, create the input YAMLs for the genYAML script
cat > $workdir/obslist.yaml << EOF
observations:
- $<< $yamlpath
EOF
cat > $workdir/temp.yaml << EOF
template: $GDASApp/parm/atm/hofx/hofx_ufotest.yaml
output: $workdir/${obtype}_${cycle}.yaml
config:
  atm: true
  OBS_DIR: ./
  DIAG_DIR: ./
  CRTM_COEFF_DIR: crtm
  BIAS_IN_DIR: ./
  OBS_LIST: $workdir/obslist.yaml
  BKG_DIR: ./
  OBS_DATE: '$CDATE'
  BIAS_DATE: '$GDATE'
  INTERP_METHOD: '$INTERP_METHOD'
EOF
$GDASApp/ush/genYAML --config $workdir/temp.yaml

# Run executable
cd $workdir
./$exename ${obtype}_${cycle}.yaml

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
