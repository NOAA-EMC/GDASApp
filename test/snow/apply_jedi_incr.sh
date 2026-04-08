#!/bin/bash
set -e
################################################
YY=2021
MM=03
DD=23
HH=18
FILEDATE=$YY$MM$DD.${HH}0000
RES=48

project_binary_dir=$1
project_source_dir=$2

GYMD=$(date +%Y%m%d -d "$YY$MM$DD $HH - 6 hours")
GHR=$(date +%H -d "$YY$MM$DD $HH - 6 hours")

EXECDIR=$project_source_dir/build/bin
WORKDIR=$project_binary_dir/test/snow/apply_jedi_incr
RSTDIR=$GDASAPP_TESTDATA/lowres/gdas.$GYMD/$GHR/model/atmos/restart
INCDIR=$GDASAPP_TESTDATA/snow/C${RES}
HOMEglobal=$project_source_dir/../../

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

export TPATH="$GDASAPP_TESTDATA/snow/C${RES}"
export TSTUB="C${RES}_oro_data"

if [[ -e $WORKDIR ]]; then
  rm -rf $WORKDIR
fi
mkdir -p $WORKDIR
cd $WORKDIR

if [[ -e apply_incr_nml ]]; then
  rm apply_incr_nml
fi

GFSv17=${GFSv17:-"NO"}

frac_grid=.false.
if [[ $GFSv17 == "YES" ]]; then
    frac_grid=.true.
fi

cat << EOF > apply_incr_nml
&noahmp_snow
 date_str=${YY}${MM}${DD}
 hour_str=$HH
 res=$RES
 frac_grid=$frac_grid
 rst_path="$WORKDIR",
 inc_path="$WORKDIR",
 orog_path="$TPATH"
 otype="$TSTUB"
 ntiles=6,
 ens_size=1,
 noincr_threshold=999999.9,
 print_summary=.true.,
 print_debug=.false.,
 truncate=.true.
/
EOF

# stage restarts
for tile in 1 2 3 4 5 6
do
  if [[ ! -e ${FILEDATE}.sfc_data.tile${tile}.nc ]]; then
    cp ${RSTDIR}/${FILEDATE}.sfc_data.tile${tile}.nc .
  fi
done

# stage increments
for tile in 1 2 3 4 5 6
do
  if [[ ! -e snowinc.${FILEDATE}.sfc_data.tile${tile}.nc ]]; then
    cp ${INCDIR}/${FILEDATE}.xainc.sfc_data.tile${tile}.nc snowinc.${FILEDATE}.sfc_data.tile${tile}.nc
  fi
done


echo 'do_snowDA: calling apply snow increment'

# Create script to run executable
runsh="./apply_incr.sh"
cat <<EOF > $runsh
#!/bin/bash
set -ex
# Set APRUN for machine
APRUN="srun -n 6"
if [[ ${MACHINE_ID} == 'wcoss2' ]]; then
   APRUN="mpiexec -n 6"
fi

# Run executable
\${APRUN} ${EXECDIR}/apply_incr.exe ${WORKDIR}/apply_incr.log
EOF
chmod 755 $runsh

# Create yaml with job configuration
memory="8Gb"
if [[ ${MACHINE_ID} == "gaeac6" ]]; then
    memory=0
fi
submitsh="./submit.sh"
config_yaml="./config.yaml"
cat <<EOF > ${config_yaml}
machine: ${MACHINE_ID}
homegfs: ${HOMEglobal}
job_name: apply_jedi_incr
walltime: "00:30:00"
nodes: 1
ntasks_per_node: 6
threads_per_task: 1
memory: ${memory}
command: ${runsh}
filename: ${submitsh}
EOF


# Create submission script
$HOMEglobal/sorc/gdas.cd/test/workflow/generate_job_script.py ${config_yaml}
SCHEDULER=$(echo `grep SCHEDULER ${HOMEglobal}/sorc/gdas.cd/test/workflow/hosts/${MACHINE_ID}.yaml | cut -d":" -f2` | tr -d ' ')

# Submit script
if [[ $SCHEDULER = 'slurm' ]]; then
    sbatch --export=ALL --wait ${submitsh}
elif [[ $SCHEDULER = 'pbspro' ]]; then
    qsub -V -W block=true ${submitsh}
else
    echo "UNKOWN SCHEDULER $SCHEDULER"
fi
rc=$?

exit $rc

