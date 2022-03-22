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
echo "Automated ${TARGET} Pull Request Testing Results:" > $outfile
echo '```' >> $outfile
echo "Start: $(date) on $(hostname)" >> $outfile
# ==============================================================================
# run build script
cd $repodir
module purge
./build.sh -t $TARGET
build_status=$?
if [ $build_status -eq 0 ]; then
  echo "Build:             *SUCCESS*" >> $outfile
  echo "Build: Completed at $(date)" >> $outfile
else
  echo "Build:             *FAILED*" >> $outfile
  echo "Build: Failed at $(date)" >> $outfile
  echo '```' >> $outfile
  exit 1
fi
# ==============================================================================
# run ctests
cd $repodir/build
echo "---------------------------------" >> $outfile
ctest --output-on-failure &>> $outfile
ctest_status=$?
echo '```' >> $outfile
exit $ctest_status
