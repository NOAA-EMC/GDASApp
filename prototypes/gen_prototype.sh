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
      ;;
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
    git clone https://github.com/NOAA-EMC/global-workflow.git
    cd global-workflow/sorc
    git checkout $GWHASH
    ./checkout.sh -ug
    cd gdas.cd
    git checkout $GDASHASH
    cd ../
    ./build_all.sh gfs gsi gdas
    ./link_workflow.sh
fi

# load modules to then generate experiment directory and rocoto XML
module use $dir_root/modulefiles
module load GDAS/$MACHINE

# move expdir if it exists, delete backup if it exists
if [[ -d $expdir/$PSLOT ]]; then
  [[ -d $expdir/${PSLOT}.bak ]] && rm -rf $expdir/${PSLOT}.bak
  mv $expdir/$PSLOT $expdir/${PSLOT}.bak
fi

# move rotdir if it exists, delete backup if it exists
if [[ -d $comrot/$PSLOT ]]; then
  [[ -d $comrot/${PSLOT}.bak ]] && rm -rf $comrot/${PSLOT}.bak
  mv $comrot/$PSLOT $comrot/${PSLOT}.bak
fi

# create YAML to override workflow config defaults
mkdir -p $expdir
cat > $expdir/config_${PSLOT}.yaml << EOF
base:
  ACCOUNT: "da-cpu"
  HPSS_PROJECT: "emc-da"
  HOMEDIR: "/scratch1/NCEPDEV/da/${USER}"
  DMPDIR: "${DUMPDIR}"
  DO_JEDIATMVAR: "${DO_JEDIATMVAR}"
  DO_JEDIATMENS: "${DO_JEDIATMENS}"
  DO_JEDIOCNVAR: "${DO_JEDIOCNVAR}"
  DO_JEDISNOWDA: "${DO_JEDISNOWDA}"
  DO_MERGENSST: "${DO_MERGENSST}"
EOF

# setup experiment
cd $GWDIR/global-workflow/workflow
./setup_expt.py gfs cycled --idate $idate  \
                           --edate $edate \
                           --app $app \
                           --start $starttype \
                           --gfs_cyc $gfscyc \
                           --resdetatmos $resdetatmos \
                           --resensatmos $resensatmos \
                           --nens $nens \
                           --pslot $PSLOT \
                           --configdir $GWDIR/global-workflow/parm/config/gfs \
                           --comrot $comrot \
                           --expdir $expdir \
                           --icsdir $ICSDIR \
                           --yaml $expdir/config_${PSLOT}.yaml

# setup XML for workflow
./setup_xml.py $expdir/$PSLOT

# run rocotorun one time
rocotorun -w $expdir/$PSLOT/${PSLOT}.xml -d $expdir/$PSLOT/${PSLOT}.db

# run rocotostat on the first cycle to see if things were submitted
rocotostat -w $expdir/$PSLOT/${PSLOT}.xml -d $expdir/$PSLOT/${PSLOT}.db -c ${idate}00
