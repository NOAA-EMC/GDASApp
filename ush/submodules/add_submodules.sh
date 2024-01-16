#!/bin/bash
# add_submodules.sh
# add submodules to the git commit

my_dir="$( cd "$( dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd )"

gdasdir=${1:-${my_dir}/../../}

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

for r in $repos; do
  echo "Adding ${gdasdir}/sorc/${r}"
  cd ${gdasdir}/sorc
  git add ${r}
done
