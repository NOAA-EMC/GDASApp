#!/bin/bash
set -x
# ctest to create an experiment directory for global-workflow
bindir=$1
srcdir=$2
topdir=$(cd "$(dirname "$(readlink -f -n "${bindir}" )" )/../../.." && pwd -P)

# test experiment variables
idate=2021032312
edate=2021032318
app=ATM
starttype='warm'
gfscyc='4'
resdetatmos='48'
resensatmos='48'
nens=3
pslot='gdas_test'
configdir=$srcdir/../../parm/config/gfs
comroot=$bindir/test/atm/global-workflow/testrun/ROTDIRS
expdir=$bindir/test/atm/global-workflow/testrun/experiments

# clean previous experiment
rm -rf $comroot $expdir config

# copy config.yaml to local config
cp -r $configdir config
cp $srcdir/test/atm/global-workflow/config.atmanl       config/
cp $srcdir/test/atm/global-workflow/config.yaml .

# update paths in config.yaml
sed -i -e "s~@topdir@~${topdir}~g" config.yaml
sed -i -e "s~@bindir@~${bindir}~g" config.yaml
sed -i -e "s~@srcdir@~${srcdir}~g" config.yaml
sed -i -e "s~@dumpdir@~${GDASAPP_TESTDATA}/lowres~g" config.yaml

# run the script
echo "Running global-workflow experiment generation script"
$srcdir/../../workflow/setup_expt.py gfs cycled --idate $idate  \
                       --edate $edate \
                       --app $app \
                       --start $starttype \
                       --gfs_cyc $gfscyc \
                       --resdetatmos $resdetatmos \
                       --resensatmos $resensatmos \
                       --nens $nens \
                       --pslot $pslot \
                       --configdir $expdir/../config \
                       --comroot $comroot \
                       --expdir $expdir \
                       --yaml $expdir/../config.yaml

echo " "
echo "$expdir/../config.yaml is"
cat $expdir/../config.yaml

exit $?
