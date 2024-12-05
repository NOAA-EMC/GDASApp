#!/bin/bash --login

echo "Starting automated testing at $(date)"

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
  echo "  -w  run workflow tests on $(hostname)"
  echo
  exit 1
}

# ==============================================================================
# First, set up runtime environment

export TARGET="$(hostname)"

TEST_WORKFLOW=0
while getopts "t:h:w" opt; do
  case $opt in
    t)
      TARGET=$OPTARG
      ;;
    h|\?|:)
      usage
      ;;
    w)
      TEST_WORKFLOW=1
      ;;  
  esac
done

echo "Running automated testing on $TARGET"

case ${TARGET} in
  hera | orion | hercules)
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
# set list of available CI tests to run on the Global Workflow
source $my_dir/ci_tests.sh

# ==============================================================================
# set things that depend on whether running workflow tests or not
gdasapp_url="https://github.com/NOAA-EMC/GDASApp.git"
if [[ $TEST_WORKFLOW == 1 ]]; then
  echo "Testing GDASApp inside the Global Workflow"
    
  CI_LABEL="${GDAS_CI_HOST}-GW-RT"
  OPEN_PR_LIST_DIR=$GDAS_CI_ROOT/open_pr_list_gw
  PR_TEST_DIR=$GDAS_CI_ROOT/workflow/PR
  BASE_REPO=global-workflow

  # Default Global Workflow repo and branch if no companion PR found
  workflow_url="https://github.com/NOAA-EMC/global-workflow.git"
  workflow_branch="develop"
else
  echo "Testing stand-alone GDASApp"
    
  CI_LABEL="${GDAS_CI_HOST}-RT"
  OPEN_PR_LIST_DIR=$GDAS_CI_ROOT/open_pr_list
  PR_TEST_DIR=$GDAS_CI_ROOT/PR
  BASE_REPO=GDASApp
fi

# ==============================================================================
# pull on the repo and get list of open PRs

cd $GDAS_CI_ROOT/repo

gh pr list --label "$CI_LABEL" --state "open" | awk '{print $1;}' > $OPEN_PR_LIST_DIR

open_pr=`cat $OPEN_PR_LIST_DIR | wc -l`
if (( $open_pr == 0 )); then
  echo "No open PRs with ${CI_LABEL}, exit."
  echo "Finished automated testing at $(date)"    
  exit
fi

open_pr_list=$(cat $OPEN_PR_LIST_DIR)

# ==============================================================================
# clone, checkout, build, test, etc.
# loop through all open PRs
for pr in $open_pr_list; do
  echo " "
  echo "Starting processing of pull request #${pr} at $(date)"

  # get the branch name used for the PR
  gdasapp_branch=$(gh pr view $pr --json headRefName -q ".headRefName")

  # get additional branch informatio
  branch_owner=$(gh pr view $pr --repo ${gdasapp_url} --json headRepositoryOwner --jq '.headRepositoryOwner.login')
  branch_name=$(gh pr view $pr --repo ${gdasapp_url} --json headRepository --jq '.headRepository.name')
  pr_assignees=$(gh pr view $pr --repo ${gdasapp_url} --json assignees --jq '.assignees[].login')
  
  # check if any assignee is authorized to run CI
  rc=1
  for str in ${pr_assignees[@]}; do
    grep $str $AUTHORIZED_USERS_FILE > /dev/null
    if (( rc != 0 )); then
	rc=$?
    fi	
    if (( rc == 0 )); then
      echo "Authorized user $str assigned to this PR"
    fi
  done

  # Authorized to run CI
  if (( rc == 0 )); then
    echo "CI authorized. Running CI..."

    # update PR label
    gh pr edit $pr --remove-label $CI_LABEL --add-label ${CI_LABEL}-Running

    echo "GDASApp URL: $gdasapp_url"
    echo "GDASApp branch Name: $gdasapp_branch"
    
    if [[ $TEST_WORKFLOW == 1 ]]; then
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

      echo "Found companion Global Workflow PR #${companion_pr}!"
      echo "Global Workflow URL: $workflow_url"
      echo "Global Workflow branch name: $workflow_branch"      
    fi

    # create PR specific directory    
    if [ -d $PR_TEST_DIR/$pr ]; then
        rm -rf $PR_TEST_DIR/$pr
    fi
    mkdir -p $PR_TEST_DIR/$pr
    cd $PR_TEST_DIR/$pr        
    pwd

    # clone copy of repo
    if [[ $TEST_WORKFLOW == 1 ]]; then
      echo "Cloning Global Workflow branch $workflow_branch from $workflow_url at $(date)"
      git clone --recursive --jobs 8 --branch $workflow_branch $workflow_url
      cd global-workflow/sorc/gdas.cd
    else
      echo "Cloning GDASApp branch $workflow_branch at $(date)"	
      git clone --recursive --jobs 8 --branch $gdasapp_branch $gdasapp_url
      cd GDASApp
    fi
    pwd

    # checkout GDASApp pull request
    gh pr checkout $pr
    git submodule update --init --recursive

    # get commit hash
    commit=$(git log --pretty=format:'%h' -n 1)
    echo "$commit" > $PR_TEST_DIR/$pr/commit

    # run build and testing command
    echo "Running run_ci.sh for $PR_TEST_DIR/$pr/$BASE_REPO at $(date)"
    run_ci_cmd="$my_dir/run_ci.sh -d $PR_TEST_DIR/$pr/$BASE_REPO -o $PR_TEST_DIR/$pr/output_${commit}"
    if [[ $TEST_WORKFLOW == 1 ]]; then
      # get ci tests from PR description and convert into a regular expressions to be excluded
      branch_body=$(gh pr view $pr --repo ${gdasapp_url} --json body --jq '.body')
      ci_checklist=$(echo "$branch_body" | grep '\[x\]')
      ctest_regex_exclude=""  
      for ci_test in ${CI_TESTS[@]}; do
        if ! echo "$ci_checklist" | grep -q "$ci_test"; then
	  ctest_regex_exclude+="${ctest_regex_exclude:+|}$ci_test"
	fi      
      done

      # setup run_ci.sh arguments to test in the Global Workflow and exclude chosen CI tests
      run_ci_cmd+=" -w"
      if [ -n "$ctest_regex_exclude" ]; then
        run_ci_cmd+=" -E $ctest_regex_exclude"
      fi
    fi
    $run_ci_cmd
    ci_status=$?
    echo "Finished running run_ci.sh with ci_status ${ci_status} at $(date)"
    
    gh pr comment $pr --repo ${gdasapp_url} --body-file $PR_TEST_DIR/$pr/output_${commit}
    if [ $ci_status -eq 0 ]; then
      gh pr edit $pr --repo ${gdasapp_url} --remove-label ${CI_LABEL}-Running --add-label ${CI_LABEL}-Passed
    else
      gh pr edit $pr --repo ${gdasapp_url} --remove-label ${CI_LABEL}-Running --add-label ${CI_LABEL}-Failed
    fi

  # Not authorized to run CI
  else
    echo "No authorized users assigned to this PR. Aborting CI..."
  fi

  echo "Finished processing Pull Request #${pr} at $(date)"
done

# ==============================================================================
# scrub working directory for older files
find $PR_TEST_DIR/* -maxdepth 1 -mtime +3 -exec rm -rf {} \;
echo "Finished automated testing at $(date)"
