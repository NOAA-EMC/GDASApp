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

gdasdir=${1:-${my_dir}/../../}

for r in $repos; do
  echo "Updating ${gdasdir}/sorc/${r}"
  cd ${gdasdir}/sorc/${r}
  git submodule update --remote --merge
done

datarepos="
ufo-data
ioda-data
fv3-jedi-data
"

for r in $datarepos; do
  echo "Updating ${gdasdir}/test/jcsda/${r}"
  cd ${gdasdir}/test/jcsda/${r}
  git submodule update --remote --merge
done
