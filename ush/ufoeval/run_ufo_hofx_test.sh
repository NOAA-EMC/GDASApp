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
obtype=sondes_ps
workdir=/work2/noaa/da/$LOGNAME/ufoeval/$cycle/$obtype
yamlpath=/work2/noaa/da/cmartin/UFO_eval/geovals/yamls/sondes_ps.yaml
GDASApp=/work2/noaa/da/cmartin/GDASApp/dev/GDASApp
exename=test_ObsOperator.x
machine=orion

#-------------- Do not modify below this line ----------------
# paths that should only be changed by an expert user
GeoDir=/work2/noaa/da/cmartin/UFO_eval/data/gsi_geovals_l127/nofgat_aug2021/20220806/geovals/
ObsDir=/work2/noaa/da/cmartin/UFO_eval/data/gsi_geovals_l127/nofgat_aug2021/20220806/obs/
FixDir=/work2/noaa/da/cmartin/GDASApp/fix/

# Load Modules for GDASApp
module use $GDASApp/modulefiles
module load GDAS/$machine

# Create and set up the working directory
mkdir -p $workdir

# Link CRTM coefficients
ln -sf $FixDir/crtm/2.3.0 $workdir/crtm

# Copy obs and geovals
cp -rf $GeoDir/${obtype}_geoval_${cycle}.nc4 $workdir/.
cp -rf $ObsDir/${obtype}_obs_${cycle}.nc4 $workdir/.

# Link executable
ln -sf $GDASApp/build/bin/$exename $workdir/.

# Copy/generate YAML for test executable
# First, create the input YAML for the genYAML script

# Run executable
cd $workdir
./$exename ${obtype}_${cycle}.yaml

# Load EVA modules
module load EVA/$machine

# Generate EVA YAML

# Run EVA
