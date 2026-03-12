#! /usr/bin/env bash

set -x
bindir=$1
srcdir=$2

# Set g-w HOMEglobal
topdir=$(cd "$(dirname "$(readlink -f -n "${bindir}" )" )/../../.." && pwd -P)
export HOMEglobal=$topdir

# Set variables for ctest
export PSLOT=gdas_test
export EXPDIR=$bindir/test/aero/global-workflow/testrun/experiments/$PSLOT
export PDY=20210323
export cyc=18
export ROTDIR=$bindir/test/aero/global-workflow/testrun/ROTDIRS/$PSLOT
export RUN=gdas
export CDUMP=gdas
export DATAROOT=$bindir/test/aero/global-workflow/testrun/RUNDIRS/$PSLOT
export COMIN_GES=${bindir}/test/aero/bkg
export pid=${pid:-$$}
export jobid=$pid
export COMROOT=$DATAROOT
export NMEM_ENS=0
export COM_TOP=$ROTDIR

# Set GFS COM paths
source "${HOMEglobal}/ush/preamble.sh"
source "${HOMEglobal}/dev/parm/config/gfs/config.com"

# Detect machine
source "${HOMEglobal}/ush/detect_machine.sh"

# Set up the PYTHONPATH to include wxflow from HOMEglobal
if [[ -d "${HOMEglobal}/sorc/wxflow/src" ]]; then
  PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${HOMEglobal}/sorc/wxflow/src"
fi

# Set python path for workflow utilities and tasks
wxflowPATH="${HOMEglobal}/ush/python"
PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${wxflowPATH}"
export PYTHONPATH

# Export library path
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:${HOMEglobal}/lib"

# Set date variables for previous cycle
gPDY=$(date +%Y%m%d -d "${PDY} ${cyc} - 6 hours")
gcyc=$(date +%H -d "${PDY} ${cyc} - 6 hours")
GDUMP="gdas"

# Set file prefixes
gprefix=$GDUMP.t${gcyc}z
oprefix=$CDUMP.t${cyc}z

# Generate COM variables from templates
declare -rx COMIN_OBS="${ROTDIR}/${RUN}.${PDY}/${cyc}/obs"
declare -rx COMIN_ATMOS_RESTART_PREV="${ROTDIR}/${GDUMP}.${gPDY}/${gcyc}/model/atmos/restart"

# Link observations
dpath=gdas.$PDY/$cyc/obs
mkdir -p $COMIN_OBS
flist="viirs_npp.${PDY}${cyc}.nc4"
for file in $flist; do
   ln -fs $GDASAPP_TESTDATA/lowres/$dpath/${oprefix}.$file $COMIN_OBS/
done


# Copy model bacgkround on tiles
dpath=gdas.$gPDY/$gcyc/model/atmos
COMIN_ATMOS_RESTART_PREV_DIRNAME=$(dirname $COMIN_ATMOS_RESTART_PREV)
if [ -d $COMIN_ATMOS_RESTART_PREV_DIRNAME/restart ]; then
    rm -rf $COMIN_ATMOS_RESTART_PREV_DIRNAME/restart
fi
mkdir -p $COMIN_ATMOS_RESTART_PREV_DIRNAME/restart
flist="restart/*"
for file in $flist; do
   cp $GDASAPP_TESTDATA/lowres/$dpath/$file $COMIN_ATMOS_RESTART_PREV_DIRNAME/restart/
done

# Create yaml with job configuration
memory="8Gb"
if [[ ${MACHINE_ID} == "gaeac6" ]]; then
    memory=0
fi
config_yaml="./config_${type}.yaml"
cat <<EOF > ${config_yaml}
machine: ${MACHINE_ID}
homegfs: ${HOMEglobal}
job_name: ${type}
walltime: "00:30:00"
nodes: 1
ntasks_per_node: 1
threads_per_task: 1
memory: ${memory}
command: ${HOMEglobal}/dev/jobs/JGLOBAL_AERO_ANALYSIS_INITIALIZE
filename: submit_${type}.sh
EOF

# Create script to execute j-job
$HOMEglobal/sorc/gdas.cd/test/workflow/generate_job_script.py ${config_yaml}
SCHEDULER=$(echo `grep SCHEDULER ${HOMEglobal}/sorc/gdas.cd/test/workflow/hosts/${MACHINE_ID}.yaml | cut -d":" -f2` | tr -d ' ')

# Submit script to execute j-job
if [[ $SCHEDULER = 'slurm' ]]; then
    sbatch --export=ALL --wait submit_${type}.sh
elif [[ $SCHEDULER = 'pbspro' ]]; then
    qsub -V -W block=true submit_${type}.sh
else
    ${HOMEglobal}/dev/jobs/JGLOBAL_AERO_ANALYSIS_INITIALIZE
fi
