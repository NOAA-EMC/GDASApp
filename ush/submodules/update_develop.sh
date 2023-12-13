#!/bin/bash
# update_develop.sh
# update specified repositories to most recent develop hash

repos="
oops
vader
saber
ioda
ufo
fv3-jedi
soca
iodaconv
"

my_dir="$( cd "$( dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd )"

sorcdir=${1:-${my_dir}/../../sorc}

for r in $repos; do
  echo "Updating ${sorcdir}/${r}"
  git submodule update --remote --merge
done
