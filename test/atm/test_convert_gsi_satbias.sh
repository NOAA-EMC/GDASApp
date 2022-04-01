#!/bin/bash
set -ex
# test script to run GSI to UFO sat bias converter and produce files
srcdir=$1
builddir=$2

# stage a testrun directory for this test
testrun=$builddir/test/testrun/satbias_conv
mkdir -p $testrun

# copy GSI input files
# the converter assumes a directory structure like we have for GDAS/GFS
mkdir -p $testrun/input/gdas.20220401/00/atmos

cp $builddir/test/testdata/gdas.t00z.abias* $testrun/input/gdas.20220401/00/atmos/.

# create the YAML file as input
cat > $builddir/test/testinput/run_satbias_conv.yaml << EOF
start time: 2022-04-01T00:00:00Z
end time: 2022-04-01T00:00:00Z
assim_freq: 6
dump: gdas
gsi_bc_root: $testrun/input
ufo_bc_root: $testrun/out
work_root: $testrun/work
satbias2ioda: $builddir/bin/satbias2ioda.x
EOF

# run the script
python3 $srcdir/ush/run_satbias_conv.py --config $builddir/test/testinput/run_satbias_conv.yaml

# copy output to testoutput
testout=$builddir/test/testoutput
mkdir -p $testout/satbias
cp -rf $testrun/out/* $testout/satbias/.

# clean up run directory
rm -rf $testrun
