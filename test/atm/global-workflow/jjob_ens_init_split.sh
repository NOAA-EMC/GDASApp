#! /usr/bin/env bash

set -x
bindir=$1
srcdir=$2

type="jjob_ens_init_split"

# Set g-w HOMEglobal
topdir=$(cd "$(dirname "$(readlink -f -n "${bindir}" )" )/../../.." && pwd -P)
export HOMEglobal=$topdir

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
oprefix=$GDUMP.t${cyc}z

# Generate COM variables from templates
declare -rx COMIN_OBS="${ROTDIR}/${GDUMP}.${PDY}/${cyc}/obs"
declare -rx COMIN_ATMOS_ANALYSIS_PREV="${ROTDIR}/${GDUMP}.${gPDY}/${gcyc}/analysis/atmos"

# Link observations
dpath=gdas.$PDY/$cyc/obs
mkdir -p $COMIN_OBS/atmos
flist="radiance_amsua_n19 sondes"
for file in $flist; do
   ln -fs $GDASAPP_TESTDATA/lowres/$dpath/${oprefix}.${file}.${PDY}${cyc}.nc $COMIN_OBS/atmos/${oprefix}.${file}.nc
done

# Link radiance bias correction files
dpath=gdas.$gPDY/$gcyc/analysis/atmos
mkdir -p $COMIN_ATMOS_ANALYSIS_PREV
flist="radiance_amsua_n19.satbias radiance_amsua_n19.satbias_cov"
for file in $flist; do
   ln -fs $GDASAPP_TESTDATA/lowres/$dpath/$gprefix.${file}.nc $COMIN_ATMOS_ANALYSIS_PREV/$gprefix.${file}.nc
done
flist="radiance_amsua_n19.tlapse.txt"
for file in $flist; do
   ln -fs $GDASAPP_TESTDATA/lowres/$dpath/$gprefix.$file $COMIN_ATMOS_ANALYSIS_PREV/$gprefix.$file
done

# Link member atmospheric background on tiles and atmf006
dpath=enkfgdas.$gPDY/$gcyc
for imem in $(seq 1 $NMEM_ENS); do
    memchar="mem"$(printf %03i $imem)

    declare -x COMIN_ATMOS_HISTORY_PREV_ENS="${ROTDIR}/${RUN}.${gPDY}/${gcyc}/${memchar}/model/atmos/history"    

    source=$GDASAPP_TESTDATA/lowres/$dpath/$memchar/model/atmos/history
    target=$COMIN_ATMOS_HISTORY_PREV_ENS
    mkdir -p $target
    file=atmf006.nc
    rm -rf $target/enkf${gprefix}.${file}
    ln -fs $source/enkf${gprefix}.${file} $target/enkf${gprefix}.${file}

    source=$GDASAPP_TESTDATA/lowres/$dpath/$memchar/model/atmos/history
    target=$COMIN_ATMOS_HISTORY_PREV_ENS
    flist=("csg_atm.f006.nc" "csg_sfc.f006.nc")
    for file in "${flist[@]}"; do
	rm -rf $target/enkf${gprefix}.${file}
        ln -fs $source/enkf${gprefix}.${file} $target/enkf${gprefix}.${file}
    done
done

# Set DO_JEDIATMENS_SPLIT_OBSSOL to run letkf as separate observer and solver jobs
# NOTE:  atmensanlinit creates input yaml for atmensanlobs and atmensanlsol jobs
cp $EXPDIR/config.base_split_obssol_true $EXPDIR/config.base

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
command: ${HOMEglobal}/dev/jobs/JGLOBAL_ATMENS_ANALYSIS_INITIALIZE
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
    ${HOMEglobal}/dev/jobs/JGLOBAL_ATMENS_ANALYSIS_INITIALIZE
fi
