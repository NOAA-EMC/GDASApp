#!/bin/bash
# ctest to create an experiment directory for global-workflow
bindir=$1
srcdir=$2

# test experiment variables
idate=2021032318
edate=2021032418
app=ATM # NOTE make this S2SWA soon
starttype='warm'
gfscyc='4'
resdet='48'
resens='24'
nens=0
pslot='gdas_test'
configdir=$srcdir/../../parm/config
comrot=$bindir/test/soca/gw/testrun/ROTDIRS
expdir=$bindir/test/soca/gw/testrun/experiments

# clean previous experiment
rm -rf $comrot $expdir

# run the script
ln -sf $srcdir/../../workflow/setup_expt.py .

# edit config.yaml
cp $srcdir/test/soca/gw/config.yaml .
soca_input_fix_dir="${bindir}/soca_static"
comin_obs="${bindir}/test/soca/obs/r2d2-shared"
sed -i -e "s~@SOCA_INPUT_FIX_DIR@~${soca_input_fix_dir}~g" config.yaml
sed -i -e "s~@COMIN_OBS@~${comin_obs}~g" config.yaml

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
                       --expdir $expdir \
                       --yaml config.yaml

# over-write config.base
cp $srcdir/test/soca/gw/config.base ${expdir}/${pslot}/
HOMEgfs=$(readlink -f ${srcdir}/../..)
STMP=$bindir/test/soca/gw/testrun
sed -i -e "s~@HOMEgfs@~${HOMEgfs}~g" ${expdir}/${pslot}/config.base
sed -i -e "s~@STMP@~${STMP}~g" ${expdir}/${pslot}/config.base
sed -i -e "s~@ROTDIRS@~${comrot}~g" ${expdir}/${pslot}/config.base
sed -i -e "s~@EXPDIRS@~${expdir}~g" ${expdir}/${pslot}/config.base

exit $?
