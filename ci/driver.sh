#!/bin/bash --login
set -euo pipefail

echo "Starting automated testing at $(date)"

my_dir="$( cd "$( dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd )"
echo "Set my_dir ${my_dir}"

# Validate required environment variables
: "${GDAS_CI_ROOT:?Error: GDAS_CI_ROOT environment variable is not set}"
: "${GDAS_CI_HOST:?Error: GDAS_CI_HOST environment variable is not set}"
: "${GITHUB_RUN_ID:?Error: GITHUB_RUN_ID environment variable is not set. This script expects to run in a GitHub Actions environment.}"

# Upstream repository constant for gh CLI operations
UPSTREAM_REPO="NOAA-EMC/GDASApp"

# ==============================================================================
usage() {
  set +x
  echo
  echo "Usage: $0 [-t target] [-w] [-h]"
  echo
  echo "  -t  target/machine script is running on    DEFAULT: $(hostname)"
  echo "  -w  run workflow tests on $(hostname)"
  echo "  -h  display this message and quit"
  echo
  exit 1
}

# ==============================================================================
# First, set up runtime environment

export TARGET="$(hostname)"

TEST_WORKFLOW=0
while getopts "t:hw" opt; do
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
  hera | ursa | orion | hercules)
    source $MODULESHOME/init/sh
    source "$my_dir/${TARGET}.sh"
    module purge
    module use "$GDAS_MODULE_USE"
    module load "GDAS/$TARGET"
    module list
    ;;
  gaeac6)
    source "$my_dir/${TARGET}.sh"
    if ! module help >/dev/null 2>&1; then
        source /etc/profile
    fi
    module reset
    module use "$GDAS_MODULE_USE"
    module load "GDAS/$TARGET"
    module list
    ;;
  *)
    echo "Unsupported platform. Exiting with error."
    exit 1
    ;;
esac

# ==============================================================================
# set list of available CI tests to run on the Global Workflow
source "$my_dir/ci_tests.sh"

# ==============================================================================
# set things that depend on whether running workflow tests or not
gdasapp_url="https://github.com/${UPSTREAM_REPO}.git"
if [[ $TEST_WORKFLOW == 1 ]]; then
  echo "Testing GDASApp inside the Global Workflow"

  CI_LABEL="${GDAS_CI_HOST}-GW-RT"
  OPEN_PR_LIST_FILE="$GDAS_CI_ROOT/open_pr_list_gw"
  PR_TEST_DIR="$GDAS_CI_ROOT/workflow/PR"
  BASE_REPO=global-workflow

  # Default Global Workflow repo and branch if no companion PR found
  workflow_url="https://github.com/NOAA-EMC/global-workflow.git"
  workflow_branch="develop"
else
  echo "Testing stand-alone GDASApp"

  CI_LABEL="${GDAS_CI_HOST}-RT"
  OPEN_PR_LIST_FILE="$GDAS_CI_ROOT/open_pr_list"
  PR_TEST_DIR="$GDAS_CI_ROOT/PR"
  BASE_REPO=GDASApp
fi

# ==============================================================================
# pull on the repo and get list of open PRs

cd "$GDAS_CI_ROOT/repo" || exit 1

mkdir -p "$(dirname "$OPEN_PR_LIST_FILE")"
gh pr list --repo "$UPSTREAM_REPO" --label "$CI_LABEL" --state "open" | awk '{print $1;}' > "$OPEN_PR_LIST_FILE"

open_pr=$(wc -l < "$OPEN_PR_LIST_FILE")
if (( open_pr == 0 )); then
  echo "No open PRs with ${CI_LABEL}, exit."
  echo "Finished automated testing at $(date)"
  exit 0
fi

open_pr_list=$(cat "$OPEN_PR_LIST_FILE")

# ==============================================================================
# clone, checkout, build, test, etc.
# loop through all open PRs in subshell to prevent directory drift
for pr in $open_pr_list; do
  (
    echo " "
    echo "Starting processing of pull request #${pr} at $(date)"

    # Reset PR-local state each iteration.
    gdasapp_url="https://github.com/${UPSTREAM_REPO}.git"
    if [[ $TEST_WORKFLOW == 1 ]]; then
      workflow_url="https://github.com/NOAA-EMC/global-workflow.git"
      workflow_branch="develop"
      companion_pr=""
    fi

    # get the branch name used for the PR
    gdasapp_branch=$(gh pr view "$pr" --repo "$UPSTREAM_REPO" --json headRefName -q ".headRefName")

    # get additional branch information
    gdas_branch_owner=$(gh pr view "$pr" --repo "$UPSTREAM_REPO" --json headRepositoryOwner --jq '.headRepositoryOwner.login')
    gdas_branch_name=$(gh pr view "$pr" --repo "$UPSTREAM_REPO" --json headRepository --jq '.headRepository.name')
    readarray -t pr_assignees < <(gh pr view "$pr" --repo "$UPSTREAM_REPO" --json assignees --jq '.assignees[].login')

    # check if any assignee is authorized to run CI
    rc=1
    if [[ -n "${AUTHORIZED_USERS_FILE:-}" && -f "$AUTHORIZED_USERS_FILE" ]]; then
      for str in "${pr_assignees[@]}"; do
        if grep -Fxq "$str" "$AUTHORIZED_USERS_FILE"; then
          rc=0
          echo "Authorized user $str assigned to this PR"
          break
        fi
      done
    else
      echo "Warning: AUTHORIZED_USERS_FILE is not set or file does not exist. Aborting CI check."
    fi

    # Authorized to run CI
    if (( rc == 0 )); then
      echo "CI authorized. Running CI..."

      # update PR label on upstream repository
      gh pr edit "$pr" --repo "$UPSTREAM_REPO" --remove-label "$CI_LABEL" --add-label "${CI_LABEL}-Running"

      if [[ $TEST_WORKFLOW != 1 ]] && [[ "$gdas_branch_owner" != "NOAA-EMC" ]]; then
        gdasapp_url="https://github.com/${gdas_branch_owner}/${gdas_branch_name}.git"
      fi

      echo "GDASApp URL: $gdasapp_url"
      echo "GDASApp branch Name: $gdasapp_branch"

      if [[ $TEST_WORKFLOW == 1 ]]; then
        # check for a companion PR in the global-workflow (limiting result to 1)
        companion_pr=$(gh pr list --repo "$workflow_url" --head "$gdasapp_branch" --state open --limit 1 --json number --jq '.[0].number')

        if [[ -n "$companion_pr" ]]; then
          # extract the necessary info
          gw_branch_owner=$(gh pr view "$companion_pr" --repo "$workflow_url" --json headRepositoryOwner --jq '.headRepositoryOwner.login')
          gw_branch_name=$(gh pr view "$companion_pr" --repo "$workflow_url" --json headRepository --jq '.headRepository.name')

          # Construct fork URL. Update workflow branch name
          workflow_url="https://github.com/$gw_branch_owner/$gw_branch_name.git"
          workflow_branch=$gdasapp_branch

          echo "Found companion Global Workflow PR #${companion_pr}!"
        fi

        echo "Global Workflow URL: $workflow_url"
        echo "Global Workflow branch name: $workflow_branch"
      fi

      # create PR specific directory
      rm -rf "$PR_TEST_DIR/$pr"
      mkdir -p "$PR_TEST_DIR/$pr"
      cd "$PR_TEST_DIR/$pr" || exit 1
      pwd

      # clone copy of repo
      if [[ $TEST_WORKFLOW == 1 ]]; then
        echo "Cloning Global Workflow branch $workflow_branch from $workflow_url at $(date)"
        git clone --recursive --jobs 8 --branch "$workflow_branch" "$workflow_url"
        cd global-workflow/sorc/gdas.cd || exit 1
      else
        echo "Cloning GDASApp branch $gdasapp_branch from $gdasapp_url at $(date)"
        git clone --recursive --jobs 8 --branch "$gdasapp_branch" "$gdasapp_url"
        cd GDASApp || exit 1
      fi
      pwd

      # checkout GDASApp pull request
      gh pr checkout "$pr"
      git submodule update --init --recursive

      # get commit hash
      commit=$(git log --pretty=format:'%h' -n 1)
      echo "$commit" > "$PR_TEST_DIR/$pr/commit"

      # run build and testing command via array
      echo "Running run_ci.sh for $PR_TEST_DIR/$pr/$BASE_REPO at $(date)"
      run_ci_cmd=("$my_dir/run_ci.sh" "-d" "$PR_TEST_DIR/$pr/$BASE_REPO" "-o" "$PR_TEST_DIR/$pr/output_${commit}")

      if [[ $TEST_WORKFLOW == 1 ]]; then
        # get ci tests from PR description and convert into regular expression to exclude
        branch_body=$(gh pr view "$pr" --repo "$UPSTREAM_REPO" --json body --jq '.body')
        ci_checklist=$(echo "$branch_body" | grep -i '\[x\]')
        ctest_regex_exclude=""

        for ci_test in "${CI_TESTS[@]}"; do
          if ! echo "$ci_checklist" | grep -q "$ci_test"; then
            ctest_regex_exclude+="${ctest_regex_exclude:+|}$ci_test"
          fi
        done

        # TODO - remove logic that excludes C48_ufsenkf_atmDA on MSU after required data is staged
        case ${TARGET} in
          orion | hercules)
            ci_test="C48_ufsenkf_atmDA"
            ctest_regex_exclude+="${ctest_regex_exclude:+|}$ci_test"
            ;;  
        esac
        
        # setup run_ci.sh arguments to test in the Global Workflow and exclude chosen CI tests
        run_ci_cmd+=("-w")
        if [[ -n "$ctest_regex_exclude" ]]; then
          run_ci_cmd+=("-E" "$ctest_regex_exclude")
        fi
      fi

      "${run_ci_cmd[@]}"
      ci_status=$?
      echo "Finished running run_ci.sh with ci_status ${ci_status} at $(date)"

      # Generate summary and add log URL
      LOG_FILE="$PR_TEST_DIR/$pr/output_${commit}"
      SUMMARY_FILE="$PR_TEST_DIR/$pr/summary_${commit}"
      LOG_URL="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"

      echo "### CI Run Summary for PR #${pr} (Commit: $commit)" > "$SUMMARY_FILE"
      echo "" >> "$SUMMARY_FILE"
      echo "Full logs: $LOG_URL" >> "$SUMMARY_FILE"
      echo "" >> "$SUMMARY_FILE"
      echo "#### First 10 lines of output:" >> "$SUMMARY_FILE"
      head -n 10 "$LOG_FILE" >> "$SUMMARY_FILE"
      echo "" >> "$SUMMARY_FILE"
      echo "#### Last 10 lines of output:" >> "$SUMMARY_FILE"
      tail -n 10 "$LOG_FILE" >> "$SUMMARY_FILE"
      echo "" >> "$SUMMARY_FILE"
      echo "CI Status: $([[ $ci_status -eq 0 ]] && echo "Passed" || echo "Failed")" >> "$SUMMARY_FILE"


      gh pr comment "$pr" --repo "$UPSTREAM_REPO" --body-file "$SUMMARY_FILE"
      if [[ $ci_status -eq 0 ]]; then
        gh pr edit "$pr" --repo "$UPSTREAM_REPO" --remove-label "${CI_LABEL}-Running" --add-label "${CI_LABEL}-Passed"
      else
        gh pr edit "$pr" --repo "$UPSTREAM_REPO" --remove-label "${CI_LABEL}-Running" --add-label "${CI_LABEL}-Failed"
      fi

    # Not authorized to run CI
    else
      echo "No authorized users assigned to this PR. Aborting CI..."
    fi

    echo "Finished processing Pull Request #${pr} at $(date)"
  )
done

# ==============================================================================
# scrub working directory for older PR directories
if [[ -d "$PR_TEST_DIR" ]]; then
  find "$PR_TEST_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +3 -exec rm -rf {} +
fi

echo "Finished automated testing at $(date)"
