#!/bin/bash
set -ex
bindir=$1
srcdir=$2

# run converter python script
$srcdir/ush/convert_yaml_ewok2gdas.py $bindir/test/testinput/amsua_n19_ewok.yaml $bindir/test/testoutput/amsua_n19_gdas.yaml

# run a diff on the output and reference file
diff $bindir/test/testoutput/amsua_n19_gdas.yaml $bindir/test/testreference/amsua_n19_gdas.yaml
