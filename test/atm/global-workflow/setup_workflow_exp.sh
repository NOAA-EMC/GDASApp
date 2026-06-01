#!/bin/bash
set -x
# ctest to create an experiment directory for global-workflow
bindir=$1
srcdir=$2

# Set g-w HOMEglobal
topdir=$(cd "$(dirname "$(readlink -f -n "${bindir}" )" )/../../.." && pwd -P)
export HOMEglobal=$topdir

# test experiment variables
idate=2021032312
edate=2021032318
app=ATM
starttype='warm'
interval='6'
resdetatmos='48'
resensatmos='48'
nens=3
pslot='gdas_test'
configdir=$srcdir/../../dev/parm/config/gfs
comroot=$bindir/test/atm/global-workflow/testrun/ROTDIRS
expdir=$bindir/test/atm/global-workflow/testrun/experiments

# clean previous experiment
rm -rf $comroot $expdir config

# copy config.yaml to local config
cp $srcdir/test/atm/global-workflow/config.yaml .

# update paths in config.yaml
sed -i -e "s~@topdir@~${topdir}~g" config.yaml
sed -i -e "s~@bindir@~${bindir}~g" config.yaml
sed -i -e "s~@srcdir@~${srcdir}~g" config.yaml
sed -i -e "s~@dumpdir@~${GDASAPP_TESTDATA}/lowres~g" config.yaml

# Detect machine
source "${HOMEglobal}/ush/detect_machine.sh"

# Set up the PYTHONPATH to include wxflow from HOMEglobal
if [[ -d "${HOMEglobal}/sorc/wxflow/src" ]]; then
  PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${HOMEglobal}/sorc/wxflow/src"
fi

# Set python path for workflow utilities and tasks
wxflowPATH="${HOMEglobal}/ush/python"
PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${wxflowPATH}"
export PYTHONPATH

# run the script
echo "Running global-workflow experiment generation script"
$srcdir/../../dev/workflow/setup_expt.py gfs cycled --idate $idate  \
                       --edate $edate \
                       --app $app \
                       --start $starttype \
                       --interval $interval \
                       --resdetatmos $resdetatmos \
                       --resensatmos $resensatmos \
                       --nens $nens \
                       --pslot $pslot \
                       --configdir $configdir \
                       --comroot $comroot \
                       --expdir $expdir \
                       --yaml $expdir/../config.yaml

echo " "
echo "$expdir/../config.yaml is"
cat $expdir/../config.yaml

# config.base contains with lobsdiag_forenkf=.true.  Create config.base with lobsdiag_forenkf=.false. for jjob_ens_letkf.sh
EXPDIR=$expdir/$pslot
cp $EXPDIR/config.base $EXPDIR/config.base_lobsdiag_forenkf_true
sed 's/export lobsdiag_forenkf=".true."/export lobsdiag_forenkf=".false."/' $EXPDIR/config.base > $EXPDIR/config.base_lobsdiag_forenkf_false

exit $?
