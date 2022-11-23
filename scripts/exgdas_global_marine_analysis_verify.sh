#!/bin/bash
# run_eva_plot_marine.sh
# This script is intended to plot a cycle of marine da analysis
# This script will:
# - Create a working directory
# - Stage fix files, obs, geovals, etc.
# - Produce an EVA YAML
# - Run EVA
#-------------------------------------------------------------
#--------------- User modified options below -----------------
cycle=2021032318
GDASApp=/scratch2/NCEPDEV/marineda/Jakir.Hossen/sandbox/GDASApp # Change this to your own branch
workdir=$PWD/$cycle
EXP_DIR=/scratch2/NCEPDEV/ocean/Guillaume.Vernieres/runs/test4jakir
machine=hera

# Load Modules for GDASApp
module use $GDASApp/modulefiles
module load GDAS/$machine
export PYTHONPATH=$GDASApp/ush:$PYTHONPATH

# Create and set up the working directory
mkdir -p $workdir
# Load EVA modules
module load EVA/$machine

# Generate EVA YAML
$GDASApp/ush/eva/gen_eva_obs_yaml.py -i ${EXP_DIR}/analysis/var.yaml -t $GDASApp/ush/eva/marine_gdas_adt.yaml -o $workdir -v absolute_dynamic_topography 
$GDASApp/ush/eva/gen_eva_obs_yaml.py -i ${EXP_DIR}/analysis/var.yaml -t $GDASApp/ush/eva/marine_gdas_sst.yaml -o $workdir -v sea_surface_temperature
#$GDASApp/ush/eva/gen_eva_obs_yaml.py -i ${EXP_DIR}/analysis/var.yaml -t $GDASApp/ush/eva/jedi_marine_mapplots.yaml -o $workdir

# Run EVA
cd $workdir
for yaml in $(ls eva_*.yaml); do
  eva $yaml
done


