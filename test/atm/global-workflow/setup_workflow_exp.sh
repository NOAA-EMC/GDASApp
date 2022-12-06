#!/bin/bash
# ctest to create an experiment directory for global-workflow
bindir=$1
srcdir=$2

# test experiment variables
idate=2021032312
edate=2021032418
app=ATM
starttype='warm'
gfscyc='4'
resdet='48'
resens='48'
nens=0
pslot='gdas_test'
configdir=$srcdir/../../parm/config
comrot=$bindir/test/atm/global-workflow/testrun/ROTDIRS
expdir=$bindir/test/atm/global-workflow/testrun/experiments

# clean previous experiment
rm -rf $comrot $expdir

# run the script
ln -sf $srcdir/../../workflow/setup_expt.py .

echo "Running global-workflow experiment generation script"
./setup_expt.py cycled --idate $idate  \
                       --edate $edate \
                       --app $app \
                       --start $starttype \
                       --gfs_cyc $gfscyc \
                       --resdet $resdet \
                       --resens $resens \
                       --nens $nens \
                       --pslot $pslot \
                       --configdir $configdir \
                       --comrot $comrot \
                       --expdir $expdir

exit $?
