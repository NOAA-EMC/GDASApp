#! /usr/bin/env bash

set -x
bindir=$1
srcdir=$2

# Set g-w HOMEgfs
topdir=$(cd "$(dirname "$(readlink -f -n "${bindir}" )" )/../../.." && pwd -P)
export HOMEgfs=$topdir

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
source "${HOMEgfs}/ush/preamble.sh"
source "${HOMEgfs}/dev/parm/config/gfs/config.com"

# Detect machine
source "${HOMEgfs}/ush/detect_machine.sh"

# Set up the PYTHONPATH to include wxflow from HOMEgfs
if [[ -d "${HOMEgfs}/sorc/wxflow/src" ]]; then
  PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${HOMEgfs}/sorc/wxflow/src"
fi

# Set python path for workflow utilities and tasks
wxflowPATH="${HOMEgfs}/ush/python"
PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${wxflowPATH}"
export PYTHONPATH

# Export library path
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:${HOMEgfs}/lib"

# Set date variables for previous cycle
gPDY=$(date +%Y%m%d -d "${PDY} ${cyc} - 6 hours")
gcyc=$(date +%H -d "${PDY} ${cyc} - 6 hours")
GDUMP="gdas"

# Set file prefixes
gprefix=$GDUMP.t${gcyc}z
oprefix=$CDUMP.t${cyc}z

# Generate COM variables from templates
YMD=${PDY} HH=${cyc} declare_from_tmpl -rx \
    COMIN_OBS:COM_OBS_TMPL

RUN=${GDUMP} YMD=${gPDY} HH=${gcyc} declare_from_tmpl -rx \
    COMIN_ATMOS_RESTART_PREV:COM_ATMOS_RESTART_TMPL

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
homegfs: ${HOMEgfs}
job_name: ${type}
walltime: "00:30:00"
nodes: 1
ntasks_per_node: 1
threads_per_task: 1
memory: ${memory}
command: ${HOMEgfs}/dev/jobs/JGLOBAL_AERO_ANALYSIS_INITIALIZE
filename: submit_${type}.sh
EOF

# Create script to execute j-job
$HOMEgfs/sorc/gdas.cd/test/workflow/generate_job_script.py ${config_yaml}
SCHEDULER=$(echo `grep SCHEDULER ${HOMEgfs}/sorc/gdas.cd/test/workflow/hosts/${MACHINE_ID}.yaml | cut -d":" -f2` | tr -d ' ')

# Submit script to execute j-job
if [[ $SCHEDULER = 'slurm' ]]; then
    sbatch --export=ALL --wait submit_${type}.sh
elif [[ $SCHEDULER = 'pbspro' ]]; then
    qsub -V -W block=true submit_${type}.sh
else
    ${HOMEgfs}/dev/jobs/JGLOBAL_AERO_ANALYSIS_INITIALIZE
fi
