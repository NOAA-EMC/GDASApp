#!/bin/bash --login

echo "Start at $(date)"

my_dir="$( cd "$( dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd )"
echo "Set my_dir ${my_dir}"

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
    echo "Running Automated GW Testing on $TARGET"
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
# pull on the repo and get list of open PRs
cd $GDAS_CI_ROOT/repo
CI_LABEL="${GDAS_CI_HOST}-GW-RT"
gh pr list --label "$CI_LABEL" --state "open" | awk '{print $1;}' > $GDAS_CI_ROOT/open_pr_list_gw

open_pr=`cat $GDAS_CI_ROOT/open_pr_list_gw | wc -l`
if (( $open_pr == 0 )); then
  echo "No open PRs with ${CI_LABEL}, exit."
  echo "Finish at $(date)"    
  exit
fi

open_pr_list=$(cat $GDAS_CI_ROOT/open_pr_list_gw)

# ==============================================================================
# clone, checkout, build, test, etc.
repo_url="https://github.com/NOAA-EMC/GDASApp.git"
workflow_url="https://github.com/NOAA-EMC/global-workflow.git"
workflow_branch="develop"
# loop through all open PRs
for pr in $open_pr_list; do
  echo " "
  echo "Start processing Pull Request #${pr} at $(date)"

  # get the branch name used for the PR
  gdasapp_branch=$(gh pr view $pr --json headRefName -q ".headRefName")

  # get additional branch information
  branch_owner=$(gh pr view $pr --repo ${repo_url} --json headRepositoryOwner --jq '.headRepositoryOwner.login')
  branch_name=$(gh pr view $pr --repo ${repo_url} --json headRepository --jq '.headRepository.name')
  pr_assignees=$(gh pr view $pr --repo ${repo_url} --json assignees --jq '.assignees[].login')

  # check if any assignee is authorized to run CI
  authorized_by=""
  for str in ${pr_assignees[@]}; do
    grep $str /scratch1/NCEPDEV/da/role.jedipara/CI/GDASApp/authorized_users
    rc=$?
    if (( rc == 0 )); then
      authorized_by=${str}
      echo "FOUND MATCH $str, rc $rc"
      break
    fi
  done

  # Authorized to run CI
  if (( rc == 0 )); then
    echo "Run CI"

    # update PR label
    gh pr edit $pr --remove-label $CI_LABEL --add-label ${CI_LABEL}-Running

    # check for a companion PR in the global-workflow
    companion_pr_exists=$(gh pr list --repo ${workflow_url} --head ${gdasapp_branch} --state open)
    if [ -n "$companion_pr_exists" ]; then
      # get the PR number
      companion_pr=$(echo "$companion_pr_exists" | awk '{print $1;}')

      # extract the necessary info
      branch_owner=$(gh pr view $companion_pr --repo $workflow_url --json headRepositoryOwner --jq '.headRepositoryOwner.login')
      branch_name=$(gh pr view $companion_pr --repo $workflow_url --json headRepository --jq '.headRepository.name')

      # Construct fork URL. Update workflow branch name
      workflow_url="https://github.com/$branch_owner/$branch_name.git"
      workflow_branch=$gdasapp_branch

    fi
    
    echo "Workflow URL: $workflow_url"
    echo "Workflow branch name: $workflow_branch"
    echo "GDASApp branch name: $gdasapp_branch"
    echo "CI authorized by $authorized_by at $(date)"

    # create PR specific directory
    if [ -d $GDAS_CI_ROOT/workflow/PR/$pr ]; then
        rm -rf $GDAS_CI_ROOT/workflow/PR/$pr
    fi
    mkdir -p $GDAS_CI_ROOT/workflow/PR/$pr
    cd $GDAS_CI_ROOT/workflow/PR/$pr
    pwd
  
    # clone global workflow develop branch
    git clone --recursive --jobs 8 --branch $workflow_branch $workflow_url

    # checkout GDASApp pull request
    cd $GDAS_CI_ROOT/workflow/PR/$pr/global-workflow/sorc/gdas.cd
    git pull
    gh pr checkout $pr
    git submodule update --init --recursive

    # get commit hash
    commit=$(git log --pretty=format:'%h' -n 1)
    echo "$commit" > $GDAS_CI_ROOT/workflow/PR/$pr/commit

    # run build and testing command
    echo "Execute $my_dir/run_gw_ci.sh for $GDAS_CI_ROOT/PR/workflow/PR/$pr/global-workflow at $(date)"
    $my_dir/run_gw_ci.sh -d $GDAS_CI_ROOT/workflow/PR/$pr/global-workflow -o $GDAS_CI_ROOT/workflow/PR/$pr/output_${commit}
    ci_status=$?
    echo "After run_gw_ci.sh with ci_status ${ci_status} at $(date)"
    gh pr comment $pr --body-file $GDAS_CI_ROOT/workflow/PR/$pr/output_${commit}
    if [ $ci_status -eq 0 ]; then
      gh pr edit $pr --remove-label ${CI_LABEL}-Running --add-label ${CI_LABEL}-Passed
    else
      gh pr edit $pr --remove-label ${CI_LABEL}-Running --add-label ${CI_LABEL}-Failed
    fi

  # Not authorized to run CI
  else
    echo "Do NOT run CI"
  fi

  echo "Finish processing Pull Request #{pr} at $(date)"
done

# ==============================================================================
# scrub working directory for older files
find $GDAS_CI_ROOT/workflow/PR/* -maxdepth 1 -mtime +3 -exec rm -rf {} \;
echo "Finish at $(date)"
