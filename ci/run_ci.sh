#!/bin/bash
set -u

# ==============================================================================
usage() {
  set +x
  echo
  echo "Usage: $0 -d <directory> -o <output> -h"
  echo
  echo "  -d  Run build and ctest for clone in <directory>"
  echo "  -o  Path to output message detailing results of CI tests"
  echo "  -w  Test GDASApp within the Global Workflow"
  echo "  -E  Regular expression of CTests to exclude"
  echo "  -h  display this message and quit"
  echo
  exit 1
}

# ==============================================================================
TEST_WORKFLOW=0
ctest_regex_exclude=""
while getopts "d:o:h:E:w" opt; do
  case $opt in
    d)
      repodir=$OPTARG
      ;;
    o)
      outfile=$OPTARG
      ;;
    E)
      ctest_regex_exclude+=$OPTARG
      ;;
    w)
      TEST_WORKFLOW=1
      ;;    
    h|\?|:)
      usage
      ;;
  esac
done

if [[ $TEST_WORKFLOW == 1 ]]; then
    export WORKFLOW_BUILD="ON"
    export WORKFLOW_TESTS="ON"

    workflow_dir=$repodir
    gdasapp_dir=$workflow_dir/sorc/gdas.cd

    build_cmd_dir=$workflow_dir/sorc
    sed -i 's/\(WORKFLOW_TESTS=.*:-"\)OFF\("\)/\1ON\2/' ${build_cmd_dir}/build_gdas.sh
    build_cmd="./build_compute.sh -A ${SLURM_ACCOUNT} gfs gcafs gsi gdas"
    build_dir=$workflow_dir/build
else
    export BUILD_JOBS=8

    gdasapp_dir=$repodir

    build_cmd_dir=$gdasapp_dir
    build_cmd="./build.sh -t $TARGET"
    build_dir=$gdasapp_dir/build
fi

# ==============================================================================
# start output file
if [[ $TEST_WORKFLOW == 1 ]]; then
  echo "Automated GW-GDASApp Testing Results:" > $outfile
else
  echo "Automated GDASApp Testing Results:" > $outfile
fi
echo "Machine: ${TARGET}" >> $outfile
echo '```' >> $outfile
echo "Start: $(date) on $(hostname)" >> $outfile
echo "---------------------------------------------------" >> $outfile
# ==============================================================================
# run build script
cd $build_cmd_dir
if [[ "${TARGET}" == "gaeac6" ]]; then
    if ( ! eval module help > /dev/null 2>&1 ) ; then
        source /etc/profile
    fi
    module reset
else
    module purge
fi
rm -rf log.build
$build_cmd &>> log.build
build_status=$?
if [ $build_status -eq 0 ]; then
  echo "Build:                                 *SUCCESS*" >> $outfile
  echo "Build: Completed at $(date)" >> $outfile
else
  echo "Build:                                  *FAILED*" >> $outfile
  echo "Build: Failed at $(date)" >> $outfile
  echo "Build: see output at $build_cmd_dir/log.build" >> $outfile
  echo '```' >> $outfile
  exit $build_status
fi
if [[ $TEST_WORKFLOW == 1 ]]; then
  ./link_workflow.sh
fi
# ==============================================================================
# run ctests

# PATCH START
# Hera and Ursa role.jedipara can not use /scratch3/NCEPDEV/global.
# MSU role-da can not use /work2/noaa/global. The logic below modifies the paths so
# role.jedipara and role-da can run g-w based ctests.
if [[ $TEST_WORKFLOW == 1 ]]; then
  if [[ "${TARGET}" = "hera" || "${TARGET}" = "ursa" ]]; then
    echo "***WARNING*** apply ${TARGET} global-->da patch to $workflow_dir/dev/workflow/hosts/${TARGET}.yaml"
    sed -i "s|/scratch3/NCEPDEV/global/\${USER}|/scratch3/NCEPDEV/da/\${USER}|g" $workflow_dir/dev/workflow/hosts/${TARGET}.yaml
  fi
  if [[ "${TARGET}" = "orion" || "${TARGET}" = "hercules" ]]; then
    echo "***WARNING*** apply MSU stmp patch to $workflow_dir/dev/workflow/hosts/${TARGET}.yaml"
    sed -i "s|/work2/noaa/global/\${USER}|/work2/noaa/da/\${USER}|g" $workflow_dir/dev/workflow/hosts/${TARGET}.yaml
  fi
fi
# PATCH END

cd $gdasapp_dir/build
module use $gdasapp_dir/modulefiles
module load GDAS/$TARGET
echo "---------------------------------------------------" >> $outfile
rm -rf log.ctest
ctest_cmd="ctest -j${NTASKS_TESTS} -R gdasapp"
if [ -n "$ctest_regex_exclude" ]; then
  ctest_cmd+=" -E $ctest_regex_exclude"
fi
pwd
echo "Tests: $ctest_cmd" >> $outfile
$ctest_cmd --timeout 43200 --output-on-failure &>> log.ctest
ctest_status=$?
npassed=$(cat log.ctest | grep "tests passed")
if [ $ctest_status -eq 0 ]; then
  echo "Tests:                                 *SUCCESS*" >> $outfile
  echo "Tests: Completed at $(date)" >> $outfile
  echo "Tests: $npassed" >> $outfile
else
  echo "Tests:                                  *Failed*" >> $outfile
  echo "Tests: Failed at $(date)" >> $outfile
  echo "Tests: $npassed" >> $outfile
  cat log.ctest | grep "(Failed)" >> $outfile
  cat log.ctest | grep "(Timeout)" >> $outfile  
  echo "Tests: see output at $gdasapp_dir/build/log.ctest" >> $outfile
fi
echo '```' >> $outfile
exit $ctest_status
