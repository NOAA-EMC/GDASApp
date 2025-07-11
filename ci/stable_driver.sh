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
PEOPLE="Cory.R.Martin@noaa.gov David.New@noaa.gov Russ.Treadon@noaa.gov"
BODY=$stableroot/$datestr/stable_nightly  

# ==============================================================================
# run the automated testing

# Run CI testing
$my_dir/run_ci.sh -d $stableroot/$datestr/global-workflow -o $stableroot/$datestr/output -w
ci_status=$?

# Sync NOAA-EMC forks of JCSDA repositories
$my_dir/sync_forks.sh
sync_status=$?

total=0
if [ $ci_status -eq 0 ] && [ $sync_status -eq 0 ]; then
  # sync NOAA-EMC forks of JCSDA repositories
  $my_dir/sync_forks.sh
  rc=$?
  total=$(($total+$rc))
  if [ $rc -ne 0 ]; then
    echo "Unable to sync NOAA-EMC forks of JCSDA repositories" >> $stableroot/$datestr/output
  fi

  cd $gdasdir

  # checkout feature/stable-nightly
  git checkout feature/stable-nightly
  rc=$?
  total=$(($total+$rc))
  if [ $rc -ne 0 ]; then
    echo "Unable to checkout feature/stable-nightly" >> $stableroot/$datestr/output
  fi

  # merge in develop
  git merge develop
  rc=$?
  total=$(($total+$rc))
  if [ $rc -ne 0 ]; then
    echo "Unable to merge develop" >> $stableroot/$datestr/output
  fi

  # add in submodules
  $gdasdir/ush/submodules/add_submodules.sh $gdasdir
  rc=$?
  total=$(($total+$rc))
  if [ $rc -ne 0 ]; then
    echo "Unable to add updated submodules to commit" >> $stableroot/$datestr/output
  fi

  # commit the changes
  git diff-index --quiet HEAD || git commit -m "Update to new stable build on $datestr"
  rc=$?
  total=$(($total+$rc))
  if [ $rc -ne 0 ]; then
    echo "Unable to commit" >> $stableroot/$datestr/output
  fi

  # push the changes
  git push --set-upstream origin feature/stable-nightly
  rc=$?
  total=$(($total+$rc))
  if [ $rc -ne 0 ]; then
    echo "Unable to push" >> $stableroot/$datestr/output
  fi

  if [ $total -ne 0 ]; then
    SUBJECT="Problem updating feature/stable-nightly branch of GDASApp"
    cat > $BODY << EOF
Problem updating feature/stable-nightly branch of GDASApp. Please check $stableroot/$datestr/global-workflow

EOF
    echo $SUBJECT
    mail -r "Darth Vader - NOAA Affiliate <darth.vader@noaa.gov>" -s "$SUBJECT" "$PEOPLE" < $BODY
  else
    SUBJECT="Success updating feature/stable-nightly branch of GDASApp"
    cat > $BODY << EOF
feature/stable-nightly branch of GDASApp updated successfully. See $stableroot/$datestr/global-workflow for details.

EOF
    echo $SUBJECT
    mail -r "Darth Vader - NOAA Affiliate <darth.vader@noaa.gov>" -s "$SUBJECT" "$PEOPLE" < $BODY
  fi
else
  # do nothing
  if [ $ci_status -ne 0 ]; then
    SUBJECT="Testing or building of feature/stable-nightly branch of GDASApp failed"
    cat > $BODY << EOF
Testing or building of feature/stable-nightly branch of GDASApp failed. Please check $stableroot/$datestr/global-workflow.

EOF
    echo $SUBJECT
    mail -r "Darth Vader - NOAA Affiliate <darth.vader@noaa.gov>" -s "$SUBJECT" "$PEOPLE" < $BODY  
  fi
  if [ $sync_status -ne 0 ]; then
    SUBJECT="Syncing of NOAA-EMC forks of JCSDA repositories failed"
    cat > $BODY << EOF
Syncing of NOAA-EMC forks of JCSDA repositories failed. Please check $stableroot/$datestr/global-workflow.

EOF
    echo $SUBJECT
    mail -r "Darth Vader - NOAA Affiliate <darth.vader@noaa.gov>" -s "$SUBJECT" "$PEOPLE" < $BODY
  fi
fi 
# ==============================================================================
# publish some information to RZDM for quick viewing
# THIS IS A TODO FOR NOW

# ==============================================================================
# scrub working directory for older files
find $stableroot/* -maxdepth 1 -mtime +1 -exec rm -rf {} \;
