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
# check if the PR needs tier-2 testing to be activated
cd $repodir/sorc/gdas.cd
export GDAS_TIER2_TESTING="OFF"
pr_number=$(gh pr list --head "$branch_name" --json number --jq '.[0].number')
tier2_label="${GDAS_CI_HOST}-GW-RT-tier2"
do_tier2=$(gh pr view "$pr_number" --json labels --jq ".labels | map(select(.name == \"$tier2_label\")) | length > 0")
if [ "$do_tier2" == "true" ]; then
  echo "Triggering tier-2 testing"
  export GDAS_TIER2_TESTING="ON"
fi

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
