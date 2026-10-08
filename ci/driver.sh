#!/bin/bash --login
set -euo pipefail

echo "Starting automated testing at $(date)"

my_dir="$( cd "$( dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd )"
echo "Set my_dir ${my_dir}"

# ==============================================================================
die() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  set +x
  local status=${1:-1}
  echo
  echo "Usage: $0 [-t <target>] [-w] [-h]"
  echo
  echo "  -t  target/machine script is running on    DEFAULT: $(hostname)"
  echo "  -w  test GDASApp inside the Global Workflow (workflow tests)"
  echo "  -h  display this message and quit"
  echo
  exit "$status"
}

# ==============================================================================
# First, set up runtime environment

export TARGET="$(hostname)"

TEST_WORKFLOW=0
while getopts ":t:hw" opt; do
  case $opt in
    t)
      TARGET=$OPTARG
      ;;
    w)
      TEST_WORKFLOW=1
      ;;
    h)
      usage 0
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      usage 1
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      usage 1
      ;;
  esac
done

echo "Running automated testing on $TARGET"

case ${TARGET} in
  hera | ursa | orion | hercules)
    source "$MODULESHOME/init/sh" || die "could not source $MODULESHOME/init/sh"
    source "$my_dir/${TARGET}.sh" || die "could not source $my_dir/${TARGET}.sh"
    module purge
    module use "$GDAS_MODULE_USE"
    module load "GDAS/$TARGET" || die "could not load module GDAS/$TARGET"
    module list
    ;;
  gaeac6)
    source "$my_dir/${TARGET}.sh" || die "could not source $my_dir/${TARGET}.sh"
    if ( ! eval module help > /dev/null 2>&1 ) ; then
        source /etc/profile
    fi
    module reset
    module use "$GDAS_MODULE_USE"
    module load "GDAS/$TARGET" || die "could not load module GDAS/$TARGET"
    module list
    ;;
  *)
    echo "Unsupported platform. Exiting with error."
    exit 1
    ;;
esac

# Variables that must be provided by the target-specific script
for required_var in GDAS_CI_ROOT GDAS_CI_HOST AUTHORIZED_USERS_FILE; do
  [[ -n "${!required_var:-}" ]] || die "$required_var is not set by ${TARGET}.sh"
done
[[ -r "$AUTHORIZED_USERS_FILE" ]] || die "AUTHORIZED_USERS_FILE '$AUTHORIZED_USERS_FILE' is missing or unreadable"

# ==============================================================================
# set list of available CI tests to run on the Global Workflow
source "$my_dir/ci_tests.sh" || die "could not source $my_dir/ci_tests.sh"

# ==============================================================================
# set things that depend on whether running workflow tests or not

# Upstream repositories. These (not fork URLs) are used for every `gh --repo`
# call so that PR numbers, comments and labels always refer to the upstream PR.
gdasapp_repo="NOAA-EMC/GDASApp"
workflow_repo="NOAA-EMC/global-workflow"
UPSTREAM_REPO="${UPSTREAM_REPO:-$gdasapp_repo}"

if [[ $TEST_WORKFLOW == 1 ]]; then
  echo "Testing GDASApp inside the Global Workflow"

  CI_LABEL="${GDAS_CI_HOST}-GW-RT"
  OPEN_PR_LIST_DIR=$GDAS_CI_ROOT/open_pr_list_gw
  PR_TEST_DIR=$GDAS_CI_ROOT/workflow/PR
  BASE_REPO=global-workflow
else
  echo "Testing stand-alone GDASApp"

  CI_LABEL="${GDAS_CI_HOST}-RT"
  OPEN_PR_LIST_DIR=$GDAS_CI_ROOT/open_pr_list
  PR_TEST_DIR=$GDAS_CI_ROOT/PR
  BASE_REPO=GDASApp
fi

# ==============================================================================
# Helper functions

# Remove PR test directories that have not been touched for more than 3 days.
scrub_old_pr_dirs() {
  if [[ -n "$PR_TEST_DIR" && -d "$PR_TEST_DIR" ]]; then
    find "$PR_TEST_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +3 -exec rm -rf {} +
  fi
}

# Runs on every exit path (including the "no open PRs" early exit).
finish() {
  scrub_old_pr_dirs
  echo "Finished automated testing at $(date)"
}

# Return 0 if GitHub login $1 is listed in AUTHORIZED_USERS_FILE.
# GitHub logins are case-insensitive; tolerate CRLF line endings and
# leading/trailing whitespace in the file. Exact (whole-line) match only.
is_authorized() {
  local user="${1,,}" line
  [[ -n "$user" ]] || return 1
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    if [[ -n "$line" && "${line,,}" == "$user" ]]; then
      return 0
    fi
  done < "$AUTHORIZED_USERS_FILE"
  return 1
}

# Return 0 if any assignee of PR $2 in repo $1 is authorized to run CI.
# Sets AUTHORIZED_USER to the matching login.
assignees_authorized() {
  local repo=$1 num=$2 login
  AUTHORIZED_USER=""
  while IFS= read -r login; do
    [[ -n "$login" ]] || continue
    if is_authorized "$login"; then
      AUTHORIZED_USER=$login
      return 0
    fi
  done < <(gh pr view "$num" --repo "$repo" --json assignees --jq '.assignees[].login')
  return 1
}

# Value sanity checks for data that ends up in URLs / jq expressions.
valid_owner() { [[ "$1" =~ ^[A-Za-z0-9-]+$ && "$1" != "null" ]]; }
valid_repo()  { [[ "$1" =~ ^[A-Za-z0-9._-]+$ && "$1" != "null" ]]; }

# Mark PR $1 as failed for an infrastructure reason described by $2.
# Safe to call after the PR was labelled "-Running".
fail_pr() {
  local num=$1 msg=$2
  echo "ERROR (PR #${num}): ${msg}"
  gh pr comment "$num" --repo "$gdasapp_repo" --body "CI could not complete: ${msg}"
  gh pr edit "$num" --repo "$gdasapp_repo" \
    --remove-label "${CI_LABEL}-Running" --add-label "${CI_LABEL}-Failed"
}

# ==============================================================================
# Process one pull request
process_pr() {
  local pr=$1
  local gdasapp_branch head_owner head_repo head_sha
  local gdasapp_clone_url="https://github.com/${gdasapp_repo}.git"
  local workflow_clone_url="https://github.com/${workflow_repo}.git"
  local workflow_branch="develop"
  local companion_pr="" companion_repo="" companion_sha=""
  local branch_body ci_checklist ctest_regex_exclude ci_test n_selected
  local commit current_sha ci_status output_file
  local -a run_ci_cmd

  # Always start from a known directory so nothing depends on the previous PR.
  cd "$GDAS_CI_ROOT/repo" || { echo "ERROR: cannot cd to $GDAS_CI_ROOT/repo"; return 1; }

  if [[ ! "$pr" =~ ^[0-9]+$ ]]; then
    echo "Skipping invalid PR identifier '${pr}'"
    return 1
  fi

  # --------------------------------------------------------------------------
  # Gather PR information (all queries are against the upstream repo)
  gdasapp_branch=$(gh pr view "$pr" --repo "$gdasapp_repo" --json headRefName --jq '.headRefName // empty') \
    || { echo "ERROR: gh failed to read PR #${pr}; will retry next cycle"; return 1; }
  head_owner=$(gh pr view "$pr" --repo "$gdasapp_repo" --json headRepositoryOwner --jq '.headRepositoryOwner.login // empty')
  head_repo=$(gh pr view "$pr" --repo "$gdasapp_repo" --json headRepository --jq '.headRepository.name // empty')
  head_sha=$(gh pr view "$pr" --repo "$gdasapp_repo" --json headRefOid --jq '.headRefOid // empty')

  if [[ -z "$gdasapp_branch" || -z "$head_sha" ]]; then
    echo "ERROR: could not determine head branch/commit of PR #${pr}; will retry next cycle"
    return 1
  fi

  # --------------------------------------------------------------------------
  # Check if any assignee is authorized to run CI
  if ! assignees_authorized "$gdasapp_repo" "$pr"; then
    echo "No authorized users assigned to this PR. Aborting CI..."
    return 0
  fi
  echo "Authorized user $AUTHORIZED_USER assigned to this PR"
  echo "CI authorized. Running CI..."

  # --------------------------------------------------------------------------
  # update PR label; if this fails do not run CI (it would be re-run every cycle)
  if ! gh pr edit "$pr" --repo "$gdasapp_repo" --remove-label "$CI_LABEL" --add-label "${CI_LABEL}-Running"; then
    echo "ERROR: could not update labels on PR #${pr}; skipping"
    return 1
  fi

  # From here on, every failure must end in fail_pr so the PR is not left "-Running".
  if ! valid_owner "$head_owner" || ! valid_repo "$head_repo"; then
    fail_pr "$pr" "head repository of this PR is unavailable (deleted fork?)"
    return 1
  fi

  # Standalone mode: PRs from forks are cloned from the fork, not from upstream.
  if [[ $TEST_WORKFLOW != 1 && "${head_owner,,}" != "noaa-emc" ]]; then
    gdasapp_clone_url="https://github.com/${head_owner}/${head_repo}.git"
  fi

  echo "GDASApp clone URL: $gdasapp_clone_url"
  echo "GDASApp branch Name: $gdasapp_branch"

  # --------------------------------------------------------------------------
  # Workflow mode: look for a companion PR in the global-workflow
  if [[ $TEST_WORKFLOW == 1 ]]; then
    # Only accept a companion PR whose head branch has the same name AND comes
    # from the same owner as the GDASApp PR (head_owner was validated above, so
    # it is safe to embed in the jq expression).
    companion_pr=$(gh pr list --repo "$workflow_repo" --head "$gdasapp_branch" --state open \
      --json number,headRepositoryOwner \
      --jq "[.[] | select(.headRepositoryOwner.login == \"${head_owner}\")][0].number // empty")

    if [[ -n "$companion_pr" ]]; then
      if [[ ! "$companion_pr" =~ ^[0-9]+$ ]]; then
        fail_pr "$pr" "unexpected companion PR identifier '${companion_pr}'"
        return 1
      fi

      # The companion PR's code will be built and run, so it needs the same
      # authorization as the GDASApp PR.
      if ! assignees_authorized "$workflow_repo" "$companion_pr"; then
        fail_pr "$pr" "companion Global Workflow PR #${companion_pr} has no authorized assignee"
        return 1
      fi

      companion_repo=$(gh pr view "$companion_pr" --repo "$workflow_repo" --json headRepository --jq '.headRepository.name // empty')
      companion_sha=$(gh pr view "$companion_pr" --repo "$workflow_repo" --json headRefOid --jq '.headRefOid // empty')
      if ! valid_repo "$companion_repo" || [[ -z "$companion_sha" ]]; then
        fail_pr "$pr" "could not read head repository of companion PR #${companion_pr}"
        return 1
      fi

      # Construct fork URL. Update workflow branch name
      workflow_clone_url="https://github.com/${head_owner}/${companion_repo}.git"
      workflow_branch=$gdasapp_branch

      echo "Found companion Global Workflow PR #${companion_pr}!"
    fi

    echo "Global Workflow clone URL: $workflow_clone_url"
    echo "Global Workflow branch name: $workflow_branch"
  fi

  # --------------------------------------------------------------------------
  # create PR specific directory
  rm -rf -- "${PR_TEST_DIR:?}/$pr"
  mkdir -p "$PR_TEST_DIR/$pr" && cd "$PR_TEST_DIR/$pr" \
    || { fail_pr "$pr" "could not create working directory $PR_TEST_DIR/$pr"; return 1; }
  pwd

  # clone copy of repo (explicit target directory names so a renamed fork still works)
  if [[ $TEST_WORKFLOW == 1 ]]; then
    echo "Cloning Global Workflow branch $workflow_branch from $workflow_clone_url at $(date)"
    git clone --recursive --jobs 8 --branch "$workflow_branch" -- "$workflow_clone_url" global-workflow \
      || { fail_pr "$pr" "git clone of Global Workflow failed"; return 1; }

    if [[ -n "$companion_sha" ]]; then
      current_sha=$(git -C global-workflow rev-parse HEAD)
      if [[ "$current_sha" != "$companion_sha" ]]; then
        fail_pr "$pr" "companion PR #${companion_pr} changed after authorization (expected ${companion_sha:0:8}, got ${current_sha:0:8}); re-add the CI label to retry"
        return 1
      fi
    fi

    cd global-workflow/sorc/gdas.cd || { fail_pr "$pr" "global-workflow/sorc/gdas.cd not found"; return 1; }
  else
    echo "Cloning GDASApp branch $gdasapp_branch from $gdasapp_clone_url at $(date)"
    git clone --recursive --jobs 8 --branch "$gdasapp_branch" -- "$gdasapp_clone_url" GDASApp \
      || { fail_pr "$pr" "git clone of GDASApp failed"; return 1; }
    cd GDASApp || { fail_pr "$pr" "GDASApp directory not found after clone"; return 1; }
  fi
  pwd

  # checkout GDASApp pull request
  gh pr checkout "$pr" --repo "$gdasapp_repo" \
    || { fail_pr "$pr" "gh pr checkout failed"; return 1; }
  git submodule update --init --recursive \
    || { fail_pr "$pr" "git submodule update failed"; return 1; }

  # make sure we are testing exactly the commit that was authorized
  current_sha=$(git rev-parse HEAD)
  if [[ "$current_sha" != "$head_sha" ]]; then
    fail_pr "$pr" "PR head changed after authorization (expected ${head_sha:0:8}, got ${current_sha:0:8}); re-add the CI label to retry"
    return 1
  fi

  # get commit hash
  commit=$(git log --pretty=format:'%h' -n 1)
  echo "$commit" > "$PR_TEST_DIR/$pr/commit"

  # --------------------------------------------------------------------------
  # run build and testing command
  echo "Running run_ci.sh for $PR_TEST_DIR/$pr/$BASE_REPO at $(date)"
  run_ci_cmd=("$my_dir/run_ci.sh" -d "$PR_TEST_DIR/$pr/$BASE_REPO" -o "$PR_TEST_DIR/$pr/output_${commit}")
  if [[ $TEST_WORKFLOW == 1 ]]; then
    # get ci tests from PR description and convert into a regular expressions to be excluded
    branch_body=$(gh pr view "$pr" --repo "$gdasapp_repo" --json body --jq '.body')
    ci_checklist=$(printf '%s\n' "$branch_body" | grep -i '\[x\]')
    ctest_regex_exclude=""
    n_selected=0

    for ci_test in "${CI_TESTS[@]}"; do
      # -F: literal match, -w: whole word only (C48_foo must not match C48_foo_bar)
      if grep -qFw -- "$ci_test" <<< "$ci_checklist"; then
        n_selected=$((n_selected + 1))
      else
        ctest_regex_exclude+="${ctest_regex_exclude:+|}$ci_test"
      fi
    done

    # Excluding every test would run nothing and could be reported as "Passed".
    if (( n_selected == 0 )); then
      fail_pr "$pr" "no CI tests are checked in the PR description; check at least one test and re-add the CI label"
      return 1
    fi

    #TODO - remove logic that excludes C48_ufsenkf_atmDA on MSU after required data is staged
    case ${TARGET} in
      orion | hercules)
        ci_test="C48_ufsenkf_atmDA"
        ctest_regex_exclude+="${ctest_regex_exclude:+|}$ci_test"
        ;;
    esac

    # setup run_ci.sh arguments to test in the Global Workflow and exclude chosen CI tests
    run_ci_cmd+=(-w)
    if [[ -n "$ctest_regex_exclude" ]]; then
      run_ci_cmd+=(-E "$ctest_regex_exclude")
    fi
  fi
  "${run_ci_cmd[@]}"
  ci_status=$?
  echo "Finished running run_ci.sh with ci_status ${ci_status} at $(date)"

  # Generate summary and add log URL
  LOG_FILE="$PR_TEST_DIR/$pr/output_${commit}"
  SUMMARY_FILE="$PR_TEST_DIR/$pr/summary_${commit}"

  # Set defaults for GitHub environment variables when running under cron
  server_url="${GITHUB_SERVER_URL:-https://github.com}"
  repo_name="${GITHUB_REPOSITORY:-$gdasapp_repo}"

  # Construct LOG_URL depending on whether running in GH Actions or local cron
  if [[ -n "${GITHUB_RUN_ID:-}" ]]; then
    LOG_URL="${server_url}/${repo_name}/actions/runs/${GITHUB_RUN_ID}"
  else
    LOG_URL="${server_url}/${repo_name}/pull/${pr}"
  fi
  
  echo "### CI Run Summary for PR #${pr} (Commit: $commit)" > "$SUMMARY_FILE"
  echo "" >> "$SUMMARY_FILE"
  cat "$LOG_FILE" >> "$SUMMARY_FILE"
  echo "" >> "$SUMMARY_FILE"
  echo "CI Status: $([[ $ci_status -eq 0 ]] && echo "Passed" || echo "Failed")" >> "$SUMMARY_FILE"

  gh pr comment "$pr" --repo "${UPSTREAM_REPO:-$gdasapp_repo}" --body-file "$SUMMARY_FILE"  
  if [ "$ci_status" -eq 0 ]; then
    gh pr edit "$pr" --repo "$gdasapp_repo" --remove-label "${CI_LABEL}-Running" --add-label "${CI_LABEL}-Passed"
  else
    gh pr edit "$pr" --repo "$gdasapp_repo" --remove-label "${CI_LABEL}-Running" --add-label "${CI_LABEL}-Failed"
  fi
}

# ==============================================================================
# Prevent overlapping driver runs (e.g. from cron) for the same CI label
if command -v flock > /dev/null 2>&1; then
  exec 9> "$GDAS_CI_ROOT/.driver_${CI_LABEL}.lock" || die "cannot open lock file in $GDAS_CI_ROOT"
  if ! flock -n 9; then
    echo "Another driver instance for ${CI_LABEL} is already running. Exiting."
    exit 0
  fi
else
  echo "WARNING: flock not found; cannot guard against overlapping driver runs"
fi

# From here on, clean up old PR directories and log completion on any exit.
trap finish EXIT

# ==============================================================================
# pull on the repo and get list of open PRs

cd "$GDAS_CI_ROOT/repo" || die "cannot cd to $GDAS_CI_ROOT/repo"

open_pr_list=$(gh pr list --repo "$gdasapp_repo" --label "$CI_LABEL" --state "open" --limit 100 \
                 --json number --jq '.[].number') \
  || die "gh pr list failed"
printf '%s\n' "$open_pr_list" | sed '/^$/d' > "$OPEN_PR_LIST_DIR"

if [[ -z "$open_pr_list" ]]; then
  echo "No open PRs with ${CI_LABEL}, exit."
  exit 0
fi

# ==============================================================================
# clone, checkout, build, test, etc.
# loop through all open PRs
for pr in $open_pr_list; do
  echo " "
  echo "Starting processing of pull request #${pr} at $(date)"
  process_pr "$pr"
  echo "Finished processing Pull Request #${pr} at $(date)"
done

# Old PR directories are scrubbed (and the finish message printed) by the EXIT trap.
