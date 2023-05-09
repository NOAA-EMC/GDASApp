#!/bin/bash
set -e

# ==============================================================================
usage() {
  set +x
  echo
  echo "Usage: $0 -c <config> -t <target> -h"
  echo
  echo "  -c  Configuration for prototype defined in shell script <config>"
  echo "  -t  Supported platform script is running on <Hera|Orion>"
  echo "  -h  display this message and quit"
  echo
  exit 1
}

# ==============================================================================
while getopts "c:t:h" opt; do
  case $opt in
    c)
      config=$OPTARG
      ;;
    t)
      MACHINE=${MACHINE:-$OPTARG}
    h|\?|:)
      usage
      ;;
  esac
done

dir_root="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/../ >/dev/null 2>&1 && pwd )"

# source the input configuration
source $config

# create directories
mkdir -p $PROTOROOT/$PSLOT

# clone/build/link workflow and GDASApp
if [[ $BUILD == 'YES' ]]; then
    cd $GWDIR
    git clone -b $GWHASH https://github.com/NOAA-EMC/global-workflow.git
    cd global-workflow/sorc
    ./checkout.sh -ug
    cd gdas.cd
    git checkout $GDASHASH
    cd ..
    ./build_all.sh
    ./link_workflow.sh
fi

# load modules to then generate experiment directory and rocoto XML
module use $dir_root/modulefiles
module load GDAS/$MACHINE

# move expdir if it exists, delete backup if it exists
if [[ -d $expdir/$PSLOT ]]; then
  [[ -d $expdir/${PSLOT}.bak]] && rm -rf $expdir/${PSLOT}.bak
  mv $expdir/$PSLOT $expdir/${PSLOT}.bak
fi

# create YAML to override workflow config defaults
cat > $expdir/config_${PSLOT}.yaml << EOF
base:
  ACCOUNT: da-cpu
  HPSS_PROJECT: emc-da
  HOMEDIR: "/scratch1/NCEPDEV/da/${USER}"
EOF



# setup experiment
cd $GWDIR/workflow
./setup_expt.py cycled --idate $idate  \
                       --edate $edate \
                       --app $app \
                       --start $starttype \
                       --gfs_cyc $gfscyc \
                       --resdet $resdet \
                       --resens $resens \
                       --nens $nens \
                       --pslot $pslot \
                       --configdir $GWDIR/parm/config \
                       --comrot $comrot \
                       --expdir $expdir \
                       --yaml $expdir/config_${PSLOT}.yaml
