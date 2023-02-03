#!/bin/bash
set -x

bindir=$1
srcdir=$2

if [[ -d /scratch1 ]] ; then
    machine="hera"
elif [[ -d /work ]] ; then
    machine="orion"
else
    echo "UNSUPPORTED MACHINE.  ABORT"
    exit 99
fi

set +x
module use ${srcdir}/modulefiles
module load GDAS/${machine}
set -x
module list

mkdir -p ${bindir}/test/atm/global-workflow/testrun/gdas_single_test_hofx3d
cd ${bindir}/test/atm/global-workflow/testrun/gdas_single_test_hofx3d

cat > ./3dhofx_example.yaml << EOF
working directory: ./
GDASApp home: ${srcdir}
GDASApp mode: hofx
template: ${srcdir}/parm/atm/hofx/hofx_nomodel.yaml
config:
  obs_yaml_dir: ${srcdir}/parm/atm/obs/config
  executable: ${bindir}/bin/fv3jedi_hofx_nomodel.x
  obs_list: ${srcdir}/parm/atm/obs/lists/gdas_prototype_3d.yaml
  gdas_fix_root: /scratch1/NCEPDEV/da/Cory.R.Martin/GDASApp/fix
  atm: true
  layout_x: 1
  layout_y: 1
  atm_window_length: PT6H
  valid_time: 2021-08-01T00:00:00Z
  dump: gdas
  case: C768
  levs: 128
  interp_method: barycentric
job options:
  machine: ${machine}
  account: da-cpu
  queue: debug
  partition: hera
  walltime: '30:00'
  ntasks: 6
  ntasks-per-node: 2
  modulepath: ${srcdir}/modulefiles
EOF

rm stdout.txt
${srcdir}/ush/run_jedi_exe.py -c ./3dhofx_example.yaml > stdout.txt
rc=$?
if [ $rc -ne 0 ]; then
    exit $rc
fi

jobid=$(grep "Submitted" stdout.txt | awk -F' ' '{print $4}')
echo "jobid is $jobid"

nloop=100
n=1
while [ $n -le $nloop ]; do
    if [ -s GDASApp.o$jobid ]; then
	break
    fi
    sleep 10
    n=$((n+1))
done

rc=1
n=1
while [ $n -le $nloop ]; do
    count=$(cat GDASApp.o$jobid | grep "OOPS_STATS Run end" | wc -l)
    echo "n = $n   count = $count"
    if [ $count -gt 0 ]; then
	rc=0
	break
    fi
    sleep 10
    n=$((n+1))
done

exit $rc
