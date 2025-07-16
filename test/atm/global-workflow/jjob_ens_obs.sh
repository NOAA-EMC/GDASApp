#! /usr/bin/env bash

set -x
bindir=$1
srcdir=$2

type="jjob_ens_obs"

# Set g-w HOMEgfs
topdir=$(cd "$(dirname "$(readlink -f -n "${bindir}" )" )/../../.." && pwd -P)
export HOMEgfs=$topdir

# Set variables for ctest
export PSLOT=gdas_test
export EXPDIR=$bindir/test/atm/global-workflow/testrun/experiments/$PSLOT
export PDY=20210323
export cyc=18
export gPDY=20210323
export gcyc=12
export ROTDIR=$bindir/test/atm/global-workflow/testrun/ROTDIRS/$PSLOT
export RUN=enkfgdas
export CDUMP=enkfgdas
export DATAROOT=$bindir/test/atm/global-workflow/testrun/RUNDIRS/$PSLOT
export COMIN_GES=${bindir}/test/atm/bkg
export pid=${pid:-$$}
export jobid=$pid
export COMROOT=$DATAROOT
export NMEM_ENS=3
export ACCOUNT=da-cpu

# Detect machine
source "${HOMEgfs}/ush/detect_machine.sh"

# Set python path for workflow utilities and tasks
wxflowPATH="${HOMEgfs}/ush/python"
PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${wxflowPATH}"
export PYTHONPATH

# Export library path
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:${HOMEgfs}/lib"

# Set lobsdiag_forenkf=.true. to run letkf as stand-alone observer job
cp $EXPDIR/config.base_lobsdiag_forenkf_true $EXPDIR/config.base

# Create yaml with job configuration
memory="32Gb"
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
ntasks_per_node: 6
threads_per_task: 1
memory: ${memory}
command: ${HOMEgfs}/jobs/JGLOBAL_ATMENS_ANALYSIS_OBS
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
    ${HOMEgfs}/jobs/JGLOBAL_ATMENS_ANALYSIS_OBS
fi
