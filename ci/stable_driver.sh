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
# clone a fresh copy of the develop branch
datestr="$(date +%Y%m%d)"
repo_url="https://github.com/NOAA-EMC/GDASApp.git"
stableroot=$GDAS_CI_ROOT/stable

mkdir -p $stableroot/$datestr
cd $stableroot/$datestr
git clone $repo_url
cd GDASApp

# ==============================================================================
# run ecbuild to get the repos cloned
mkdir -p build
cd build
ecbuild ../
cd ..
rm -rf build

# ==============================================================================
# update the hashes to the most recent
$my_dir/stable_mark.sh $stableroot/$datestr/GDASApp

# ==============================================================================
# run the automated testing
$my_dir/run_ci.sh -d $stableroot/$datestr/GDASApp -o $stableroot/$datestr/output
ci_status=$?
total=0
if [ $ci_status -eq 0 ]; then
  # copy the CMakeLists file for safe keeping
  cp $stableroot/$datestr/GDASApp/CMakeLists.txt $stableroot/$datestr/GDASApp/CMakeLists.txt.new
  total=$(($total+$?))
  if [ $total -ne 0 ]; then
    echo "Unable to cp CMakeLists" >> $stableroot/$datestr/output
  fi
  # checkout feature/stable-nightly
  git stash
  total=$(($total+$?))
  if [ $total -ne 0 ]; then
    echo "Unable to cp CMakeLists" >> $stableroot/$datestr/output
  fi
  git checkout feature/stable-nightly
  total=$(($total+$?))
  if [ $total -ne 0 ]; then
    echo "Unable to cp CMakeLists" >> $stableroot/$datestr/output
  fi
  # merge in develop
  git merge develop
  total=$(($total+$?))
  if [ $total -ne 0 ]; then
    echo "Unable to merge develop" >> $stableroot/$datestr/output
  fi
  # force move the copy to the original path of CMakeLists.txt
  /bin/mv -f $stableroot/$datestr/GDASApp/CMakeLists.txt.new $stableroot/$datestr/GDASApp/CMakeLists.txt
  total=$(($total+$?))
  if [ $total -ne 0 ]; then
    echo "Unable to mv CMakeLists" >> $stableroot/$datestr/output
  fi
  # commit this change and push
  git add CMakeLists.txt
  total=$(($total+$?))
  if [ $total -ne 0 ]; then
    echo "Unable to add CMakeLists to commit" >> $stableroot/$datestr/output
  fi
  git commit -m "Update to new stable build on $datestr"
  total=$(($total+$?))
  caution=""
  if [ $total -ne 0 ]; then
    echo "Unable to commit" >> $stableroot/$datestr/output
    caution="There probably was just no update to commit today. Git returns exit code 1 in this case. I should blow up their planet..." 
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

$caution
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
