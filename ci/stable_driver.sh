#!/bin/bash --login

my_dir="$( cd "$( dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd )"

# ==============================================================================
usage() {
  set +x
  echo
  echo "Usage: $0 -t <target> -h"
  echo
  echo "  -t  target/machine script is running on    DEFAULT: $(hostname)"
  echo "  -h  display this message and quit"
  echo
  exit 1
}

# ==============================================================================
# First, set up runtime environment

export TARGET="$(hostname)"

while getopts "t:h" opt; do
  case $opt in
    t)
      TARGET=$OPTARG
      ;;
    h|\?|:)
      usage
      ;;
  esac
done

case ${TARGET} in
  hera | orion)
    echo "Running stability check on $TARGET"
    source $MODULESHOME/init/sh
    source $my_dir/${TARGET}.sh
    module purge
    module use $GDAS_MODULE_USE
    module load GDAS/$TARGET
    module list
    ;;
  *)
    echo "Unsupported platform. Exiting with error."
    exit 1
    ;;
esac

# ==============================================================================
datestr="$(date +%Y%m%d)"
repo_url="https://github.com/NOAA-EMC/GDASApp.git"
workflow_url="https://github.com/NOAA-EMC/global-workflow.git"
stableroot=$GDAS_CI_ROOT/stable

mkdir -p $stableroot/$datestr
cd $stableroot/$datestr

# clone global workflow develop branch
git clone $workflow_url

# run checkout script for all other components
cd $stableroot/$datestr/global-workflow/sorc
./checkout.sh -u

# checkout develop
cd gdas.cd
git checkout develop
git pull

# ==============================================================================
# update the hashes to the most recent
gdasdir=$stableroot/$datestr/global-workflow/sorc/gdas.cd
$my_dir/../ush/submodules/update_develop.sh $gdasdir

# ==============================================================================
# run the automated testing
$my_dir/run_gw_ci.sh -d $stableroot/$datestr/global-workflow -o $stableroot/$datestr/output
ci_status=$?
total=0
if [ $ci_status -eq 0 ]; then
  cd $gdasdir
  # checkout feature/stable-nightly
  git stash
  total=$(($total+$?))
  if [ $total -ne 0 ]; then
    echo "Unable to git stash" >> $stableroot/$datestr/output
  fi
  git checkout feature/stable-nightly
  total=$(($total+$?))
  if [ $total -ne 0 ]; then
    echo "Unable to checkout feature/stable-nightly" >> $stableroot/$datestr/output
  fi
  # merge in develop
  git merge develop
  total=$(($total+$?))
  if [ $total -ne 0 ]; then
    echo "Unable to merge develop" >> $stableroot/$datestr/output
  fi
  # add in submodules
  git stash pop
  total=$(($total+$?))
  if [ $total -ne 0 ]; then
    echo "Unable to git stash pop" >> $stableroot/$datestr/output
  fi
  $my_dir/../ush/submodules/add_submodules.sh $gdasdir
  total=$(($total+$?))
  if [ $total -ne 0 ]; then
    echo "Unable to add updated submodules to commit" >> $stableroot/$datestr/output
  fi
  git diff-index --quiet HEAD || git commit -m "Update to new stable build on $datestr"
  total=$(($total+$?))
  caution=""
  if [ $total -ne 0 ]; then
    echo "Unable to commit" >> $stableroot/$datestr/output
  fi
  git push --set-upstream origin feature/stable-nightly
  total=$(($total+$?))
  if [ $total -ne 0 ]; then
    echo "Unable to push" >> $stableroot/$datestr/output
  fi
  if [ $total -ne 0 ]; then
    echo "Issue merging with develop. please manually fix"
    PEOPLE="Cory.R.Martin@noaa.gov Russ.Treadon@noaa.gov Guillaume.Vernieres@noaa.gov"
    SUBJECT="Problem updating feature/stable-nightly branch of GDASApp"
    BODY=$stableroot/$datestr/output_stable_nightly
    cat > $BODY << EOF
Problem updating feature/stable-nightly branch of GDASApp. Please check $stableroot/$datestr/GDASApp

EOF
    mail -r "Darth Vader - NOAA Affiliate <darth.vader@noaa.gov>" -s "$SUBJECT" "$PEOPLE" < $BODY
  else
    echo "Stable branch updated"
  fi
else
  # do nothing
  echo "Testing failed, stable branch will not be updated"
fi
# ==============================================================================
# publish some information to RZDM for quick viewing
# THIS IS A TODO FOR NOW

# ==============================================================================
# scrub working directory for older files
find $stableroot/* -maxdepth 1 -mtime +3 -exec rm -rf {} \;
