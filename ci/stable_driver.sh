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

set -x
# ==============================================================================
datestr="$(date +%Y%m%d)"
repo_url="https://github.com/NOAA-EMC/GDASApp.git"
workflow_url="https://github.com/NOAA-EMC/global-workflow.git"
stableroot=$GDAS_CI_ROOT/stable

[[ -d $stableroot/$datestr ]] && rm -rf $stableroot/$datestr
mkdir -p $stableroot/$datestr
cd $stableroot/$datestr

# clone global workflow develop branch
git clone --recursive $workflow_url

# checkout develop
cd $stableroot/$datestr/global-workflow/sorc/gdas.cd
git checkout develop
git pull
git submodule update --init --recursive

# ==============================================================================
# update the hashes to the most recent
gdasdir=$stableroot/$datestr/global-workflow/sorc/gdas.cd
$gdasdir/ush/submodules/update_develop.sh $gdasdir

# ==============================================================================
# email information
PEOPLE="Cory.R.Martin@noaa.gov Russ.Treadon@noaa.gov Guillaume.Vernieres@noaa.gov David.New@noaa.gov"
BODY=$stableroot/$datestr/stable_nightly  

# ==============================================================================
# run the automated testing
$my_dir/run_ci.sh -d $stableroot/$datestr/global-workflow -o $stableroot/$datestr/output -w
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
  if [ $total -ne 0 ]; then
    echo "Unable to commit" >> $stableroot/$datestr/output
  fi
  git push --set-upstream origin feature/stable-nightly
  total=$(($total+$?))
  if [ $total -ne 0 ]; then
    echo "Unable to push" >> $stableroot/$datestr/output
  fi
  if [ $total -ne 0 ]; then
    SUBJECT="Problem updating feature/stable-nightly branch of GDASApp"
    cat > $BODY << EOF
Problem updating feature/stable-nightly branch of GDASApp. Please check $stableroot/$datestr/global-workflow

EOF

  else
    SUBJECT="Success updating feature/stable-nightly branch of GDASApp"
    cat > $BODY << EOF
feature/stable-nightly branch of GDASApp updated successfully. See $stableroot/$datestr/global-workflow for details.

EOF

  fi
else
  # do nothing
  SUBJECT="Testing or building of feature/stable-nightly branch of GDASApp failed"
  cat > $BODY << EOF
Testing or building of feature/stable-nightly branch of GDASApp failed. Please check $stableroot/$datestr/global-workflow.

EOF
fi
echo $SUBJECT
mail -r "Darth Vader - NOAA Affiliate <darth.vader@noaa.gov>" -s "$SUBJECT" "$PEOPLE" < $BODY  
# ==============================================================================
# publish some information to RZDM for quick viewing
# THIS IS A TODO FOR NOW

# ==============================================================================
# scrub working directory for older files
find $stableroot/* -maxdepth 1 -mtime +3 -exec rm -rf {} \;
