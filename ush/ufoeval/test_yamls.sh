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

# Process tests wiht QC
for file in `find ../../parm/jcb-gdas/observations/atmosphere -type f`; do
   basefile=${file##*/}
   obtype="${basefile%.*}"
   ./run_ufo_hofx_test.sh -x $obtype > $WORKDIR/$obtype.log 2> $WORKDIR/$obtype.err
   if [ $? == 0 ]; then
     echo $basefile Passes \(yay!\)
   else
     echo $basefile Fails \(boo!\)
   fi
done

# Process tests without QC (HofX + Observation error assignment)
for file in `find ../../parm/jcb-gdas/observations/atmosphere -type f`; do
   basefile=${file##*/}
   obtype="${basefile%_noqc.*}"
   ./run_ufo_hofx_test.sh -x -q $obtype > $WORKDIR/${obtype}_noqc.log 2> $WORKDIR/${obtype}_noqc.err
   if [ $? == 0 ]; then
     echo $basefile Passes \(yay!\)
   else
     echo $basefile Fails \(boo!\)
   fi
done

exit 0
