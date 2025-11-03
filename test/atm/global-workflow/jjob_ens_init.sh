#! /usr/bin/env bash

set -x
bindir=$1
srcdir=$2

type="jjob_ens_init"

# Set g-w HOMEgfs
topdir=$(cd "$(dirname "$(readlink -f -n "${bindir}" )" )/../../.." && pwd -P)
export HOMEgfs=$topdir

# Set variables for ctest
export PSLOT=gdas_test
export EXPDIR=$bindir/test/atm/global-workflow/testrun/experiments/$PSLOT
export PDY=20210323
export cyc=18
export ROTDIR=$bindir/test/atm/global-workflow/testrun/ROTDIRS/$PSLOT
export RUN=enkfgdas
export CDUMP=enkfgdas
export DATAROOT=$bindir/test/atm/global-workflow/testrun/RUNDIRS/$PSLOT
export pid=${pid:-$$}
export jobid=$pid
export COMROOT=$DATAROOT
export NMEM_ENS=3
export ACCOUNT=da-cpu

# Set GFS COM paths
export STRICT="NO"
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
oprefix=$GDUMP.t${cyc}z

# Generate COM variables from templates
RUN=${GDUMP} YMD=${PDY} HH=${cyc} declare_from_tmpl -rx \
    COMIN_OBS:COM_OBS_TMPL
RUN=${GDUMP} YMD=${gPDY} HH=${gcyc} declare_from_tmpl -rx \
    COMIN_ATMOS_ANALYSIS_PREV:COM_ATMOS_ANALYSIS_TMPL \

# Link observations
dpath=gdas.$PDY/$cyc/obs
mkdir -p $COMIN_OBS
flist="amsua_n19 sondes"
for file in $flist; do
   ln -fs $GDASAPP_TESTDATA/lowres/$dpath/${oprefix}.${file}.${PDY}${cyc}.nc4 $COMIN_OBS/${oprefix}.${file}.nc
done

# Link radiance bias correction tarball
dpath=gdas.$gPDY/$gcyc/analysis/atmos
mkdir -p $COMIN_ATMOS_ANALYSIS_PREV
flist="rad_varbc_params.tar"
for file in $flist; do
   ln -fs $GDASAPP_TESTDATA/lowres/$dpath/$gprefix.${file} $COMIN_ATMOS_ANALYSIS_PREV/$gprefix.${file}
done

# Link member atmospheric background on tiles and atmf006
dpath=enkfgdas.$gPDY/$gcyc
for imem in $(seq 1 $NMEM_ENS); do
    memchar="mem"$(printf %03i $imem)

    MEMDIR=${memchar} RUN=${RUN} YMD=${gPDY} HH=${gcyc} declare_from_tmpl -x \
	COMIN_ATMOS_HISTORY_PREV_ENS:COM_ATMOS_HISTORY_TMPL \
	COMIN_ATMOS_RESTART_PREV_ENS:COM_ATMOS_RESTART_TMPL
    COMIN_ATMOS_RESTART_PREV_DIRNAME_ENS=$(dirname $COMIN_ATMOS_RESTART_PREV_ENS)

    source=$GDASAPP_TESTDATA/lowres/$dpath/$memchar/model/atmos/history
    target=$COMIN_ATMOS_HISTORY_PREV_ENS
    mkdir -p $target
    rm -rf $target/enkfgdas.t${gcyc}z.atmf006.nc
    ln -fs $source/enkfgdas.t${gcyc}z.atmf006.nc $target/

    source=$GDASAPP_TESTDATA/lowres/$dpath/$memchar/model/atmos/history
    target=$COMIN_ATMOS_HISTORY_PREV_ENS
    flist=("csg_atm.f006.nc" "csg_sfc.f006.nc")
    for file in "${flist[@]}"; do
	rm -rf $target/enkf${gprefix}.${file}
        ln -fs $source/enkf${gprefix}.${file} $target/
    done
done

# Set lobsdiag_forenkf=.false. to run letkf as single observer and solver job
# NOTE:  atmensanlinit creates input yaml for atmensanlletkf job
cp $EXPDIR/config.base_lobsdiag_forenkf_false $EXPDIR/config.base

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
command: ${HOMEgfs}/jobs/JGLOBAL_ATMENS_ANALYSIS_INITIALIZE
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
    ${HOMEgfs}/jobs/JGLOBAL_ATM_ANALYSIS_INITIALIZE
fi
