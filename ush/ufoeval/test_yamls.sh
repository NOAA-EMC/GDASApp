#!/bin/bash
# test_yamls.sh 
# This scripts runs run_ufo_hofx_test.sh for the input YAMLs in ../../parm/atm/obs/testing
# and outputs pass/fail information

# Work directory
WORKDIR=$STMP/test_yamls  # Change to suitable path

mkdir -p $WORKDIR

if [ $? -ne 0 ]; then
  echo cannot make $WORKDIR
  exit 1
fi

for file in `ls ../../parm/atm/obs/testing/*yaml`; do
   basefile=${file##*/}
   inst="${basefile%.*}"
   ./run_ufo_hofx_test.sh -x $inst > $WORKDIR/$inst.log 2> $WORKDIR/$inst.err
   if [ $? == 0 ]; then
     echo $basefile Passes \(yay!\)
   else
     echo $basefile Fails \(boo!\)
   fi
done

exit 0
