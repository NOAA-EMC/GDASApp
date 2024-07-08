#!/bin/bash
#set -eu

# ==============================================================================
usage() {
  set +x
  echo
  echo "Usage: $0 -d <directory> -o <output> -h"
  echo
  echo "  -d  Run build and ctest for clone in <directory>"
  echo "  -o  Path to output message detailing results of CI tests"
  echo "  -t  run the tier-2 testing, default is OFF"
  echo "  -h  display this message and quit"
  echo
  exit 1
}

# ==============================================================================
while getopts "d:o:h" opt; do
  case $opt in
    d)
      repodir=$OPTARG
      ;;
    o)
      outfile=$OPTARG
      ;;
    t)
      do_tier2=${OPTARG:-false}
      ;;
    h|\?|:)
      usage
      ;;
  esac
done

# ==============================================================================
# start output file
echo "Automated Global-Workflow GDASApp Testing Results:" > $outfile
echo "Machine: ${TARGET}" >> $outfile
echo '```' >> $outfile
echo "Start: $(date) on $(hostname)" >> $outfile
echo "---------------------------------------------------" >> $outfile
# ==============================================================================
# run build and link as part of the workflow
export WORKFLOW_BUILD="ON"
cd $repodir/sorc
module purge
rm -rf log.build
./build_all.sh -u &>> log.build
build_status=$?
if [ $build_status -eq 0 ]; then
  echo "Build:                                 *SUCCESS*" >> $outfile
  echo "Build: Completed at $(date)" >> $outfile
else
  echo "Build:                                  *FAILED*" >> $outfile
  echo "Build: Failed at $(date)" >> $outfile
  echo "Build: see output at $repodir/sorc/log.build" >> $outfile
  echo '```' >> $outfile
  exit $build_status
fi
./link_workflow.sh
# ==============================================================================
# run ctests
cd $repodir/sorc/gdas.cd/build
module use $repodir/sorc/gdas.cd/modulefiles
module load GDAS/$TARGET
echo "---------------------------------------------------" >> $outfile
# Reconfigure if the tier-2 testing is required
# TODO: Not the most efficient, but even when exported, the variable is out of scope
#       when running build.sh
if [ $do_tier2 == "true" ]; then
  echo "Tier-2 Testing: Activated" >> $outfile
  cmake -DGDAS_TIER2_TESTING=ON . >> log.cmake_tier2
fi
(cd gdas && ctest -N) >> log.gdasapp_tests

rm -rf log.ctest
ctest -R gdasapp --output-on-failure &>> log.ctest
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
  echo "Tests: see output at $repodir/sorc/gdas.cd/build/log.ctest" >> $outfile
fi
echo '```' >> $outfile
exit $ctest_status
