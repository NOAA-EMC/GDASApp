#!/bin/bash
set -x

bindir=$1
srcdir=$2

# Identify machine
if [[ -d /scratch1 ]] ; then
    machine="hera"
elif [[ -d /work ]] ; then
    machine="orion"
else
    echo "UNSUPPORTED MACHINE.  ABORT"
    exit 99
fi

# Load modules
set +x
module use ${srcdir}/modulefiles
module load GDAS/${machine}
set -x
module list

# Set machine dependent variables
if [ "$machine" = "hera" ] ; then
    cominges="/scratch1/NCEPDEV/da/Russ.Treadon/GDASApp/cases"
    partition="hera"
    gdasfix="/scratch1/NCEPDEV/da/Cory.R.Martin/GDASApp/fix"
elif [ "$machine" = "orion" ]; then
    cominges="/work2/noaa/da/rtreadon/GDASApp/cases"
    partition="debug"
    gdasfix="/work2/noaa/da/cmartin/GDASApp/fix"
fi

# Create test run directory
mkdir -p ${bindir}/test/atm/global-workflow/testrun/gdas_single_test_letkf
cd ${bindir}/test/atm/global-workflow/testrun/gdas_single_test_letkf

# Create input yaml
cat > ./letkf_example.yaml << EOF
working directory: ./
GDASApp home: ${srcdir}
GDASApp mode: letkf
template: ${srcdir}/parm/atm/lgetkf/lgetkf.yaml
config:
  obs_dir: obs
  diag_dir: diags
  crtm_coeff_dir: crtm
  bias_in_dir: obs
  bias_out_dir: bc
  obs_yaml_dir: ${srcdir}/parm/atm/obs/config
  executable: ${bindir}/bin/fv3jedi_letkf.x
  obs_list: ${srcdir}/parm/atm/obs/lists/lgetkf_prototype.yaml
  gdas_fix_root: ${gdasfix}
  atm: true
  layout_x: 3
  layout_y: 2
  atm_window_length: PT6H
  valid_time: 2021-12-21T06:00:00Z
  dump: gdas
  case: C48
  case_anl: C48
  staticb_type: gsibec
  dohybvar: no
  levs: 128
  nmem: 5
  comin_ges: ${cominges}
  interp_method: barycentric
job options:
  machine: ${machine}
  account: da-cpu
  queue: debug
  partition: ${partition}
  walltime: '30:00'
  ntasks: 36
  modulepath: ${srcdir}/modulefiles
EOF

# Execute run_jedi_exe.py
if [ -e stdout.txt ]; then
    rm -f stdout.txt
fi
${srcdir}/ush/run_jedi_exe.py -c ./letkf_example.yaml > stdout.txt 2>&1
rc=$?
if [ $rc -ne 0 ]; then
    exit $rc
fi

# Check for job submission error
error=$(grep -i "error" stdout.txt | wc -l)
if [ $error -ne 0 ]; then
    rc=$error
    exit $rc
fi

# Cancel submitted job
jobid=$(grep "Submitted" stdout.txt | awk -F' ' '{print $4}')
scancel $jobid
rc=$?
if [ $rc -ne 0 ]; then
    exit $rc
fi

# Check for valid yaml files
ylist="letkf_example.yaml gdas_letkf.yaml"
for yfile in $ylist; do
    python3 -c 'import yaml, sys; yaml.safe_load(sys.stdin)' < $yfile
    rc=$?
    if [ $rc -ne 0 ]; then
	exit $rc
    fi
done

exit $rc
