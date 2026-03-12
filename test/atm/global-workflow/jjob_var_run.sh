#! /usr/bin/env bash

set -x

bindir=$1
srcdir=$2

type="jjob_var_run"

# Set g-w HOMEglobal
topdir=$(cd "$(dirname "$(readlink -f -n "${bindir}" )" )/../../.." && pwd -P)
export HOMEglobal=$topdir

# Set variables for ctest
export PSLOT=gdas_test
export EXPDIR=$bindir/test/atm/global-workflow/testrun/experiments/$PSLOT
export PDY=20210323
export cyc=18
export gPDY=20210323
export gcyc=12
export ROTDIR=$bindir/test/atm/global-workflow/testrun/ROTDIRS/$PSLOT
export RUN=gdas
export CDUMP=gdas
export DATAROOT=$bindir/test/atm/global-workflow/testrun/RUNDIRS/$PSLOT
export COMIN_GES=${bindir}/test/atm/bkg
export pid=${pid:-$$}
export jobid=$pid
export COMROOT=$DATAROOT
export NMEM_ENS=0
export ACCOUNT=da-cpu

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

# Create yaml with job configuration
memory="96Gb"
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
ntasks_per_node: 6
threads_per_task: 1
memory: ${memory}
command: ${HOMEglobal}/dev/jobs/JGLOBAL_ATM_ANALYSIS_VARIATIONAL
filename: submit_${type}.sh
EOF

# Create script to execute j-job. Set job scheduler
${HOMEglobal}/sorc/gdas.cd/test/workflow/generate_job_script.py ${config_yaml}
SCHEDULER=$(echo `grep SCHEDULER ${HOMEglobal}/sorc/gdas.cd/test/workflow/hosts/${MACHINE_ID}.yaml | cut -d":" -f2` | tr -d ' ')

# Submit script to execute j-job
if [[ $SCHEDULER = 'slurm' ]]; then
    sbatch --export=ALL --wait submit_${type}.sh
elif [[ $SCHEDULER = 'pbspro' ]]; then
    qsub -V -W block=true submit_${type}.sh
else
    ${HOMEglobal}/dev/jobs/JGLOBAL_ATM_ANALYSIS_VARIATIONAL
fi
