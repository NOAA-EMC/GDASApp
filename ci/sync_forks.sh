#!/bin/bash --login

# List of forked repositories
fork_repos=("soca")

# Make sure certain environment variables are set (these should be set by stable_driver.sh)
[ ! -z "${GDAS_CI_ROOT}" ] || { echo "Error: variable GDAS_CI_ROOT not set"; exit 1; }
[ ! -z "${TARGET}" ] || { echo "Error: variable TARGET not set"; exit 1; }

# Create base directory and cd into it
syncroot=$GDAS_CI_ROOT/sync
mkdir -p "$syncroot" # make sure the directory exists
cd "$syncroot"

for repo_name in "${fork_repos[@]}"; do
    # Clone fork develop branch
    [ -d "$syncroot/$repo_name" ] && rm -rf "$syncroot/$repo_name" # delete repo directory if it already exists
    repo_url="https://github.com/NOAA-EMC/${repo_name}.git"
    git clone -b develop $repo_url || { echo "Failed to clone $repo_name develop branch"; exit 1; }
    mkdir -p "$syncroot/$repo_name" # make sure the directory exists
    cd "$syncroot/$repo_name"

    # Fetch JCSDA remote
    git remote add jcsda https://github.com/jcsda/${repo_name}.git || { echo "$repo_name: Failed to add remote jcsda"; exit 1; }
    git fetch jcsda || { echo "$repo_name: Failed to fetch from jcsda"; exit 1; }
    git checkout jcsda/develop || { echo "$repo_name: Failed to checkout jcsda/develop"; exit 1; }

    # Update develop branch
    git branch -D develop || { echo "$repo_name: Failed to delete develop branch"; exit 1; }
    git checkout -b develop || { echo "$repo_name: Failed to create develop branch"; exit 1; }
    #git push --set-upstream origin develop || { echo "$repo_name: Failed to push develop branch"; exit 1; }

    # Update dev/emc branch
    git checkout -b dev/emc origin/dev/emc || { echo "$repo_name: Failed to create dev/emc branch"; exit 1; }
    git merge jcsda/develop --no-edit || {
        # Try to resolve deleted submodule conflicts automatically
        git status --porcelain | grep '^DU ' | awk '{print $2}' | xargs -r git rm -f

        # Try to complete the merge
        git commit --no-edit 2>/dev/null || git merge --continue 2>/dev/null

        # If merge is still in progress (conflicts remain), then fail
        if git merge --abort 2>/dev/null; then
            echo "$repo_name: Failed to merge jcsda/develop into dev/emc"
            exit 1
        fi
    }
    #git push --set-upstream origin dev/emc || { echo "$repo_name: Failed to push dev/emc branch"; exit 1; }

    # Change directory back to sync root and delete the cloned repo
    cd "$syncroot"
    rm -rf "$syncroot/$repo_name"
done
