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
    echo "Syncing NOAA-EMC forks of JCSDA repositories on $TARGET"
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

# List of repositories to sync
repos=("soca")

# Create base directory and cd into it
syncroot=$GDAS_CI_ROOT/sync
cd $syncroot

for repo_name in "${repos[@]}"; do
    # Clone fork develop branch
    repo_url="https://github.com/NOAA-EMC/${repo_name}.git"
    git clone -b develop $repo_url
    cd $repo_name

    # Fetch JCSDA remote
    git remote add jcsda https://github.com/jcsda/${repo_name}.git
    git fetch jcsda
    git checkout jcsda/develop

    # Update develop branch
    git branch -D develop
    git checkout -b develop
    git push --set-upstream origin develop

    # Update dev/emc branch
    git checkout -b dev/emc origin/dev/emc
    git merge jcsda/develop --no-edit
    git push --set-upstream origin dev/emc

    # Change directory back to sync root and delete the cloned repo
    cd ..
    rm -rf $repo_name
done
