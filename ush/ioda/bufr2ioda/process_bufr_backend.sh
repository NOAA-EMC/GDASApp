#!/bin/sh -xvf

source ~eliu/modules/env_jedi.sh

set -x
ulimit -s unlimited
ulimit -a

export OOPS_TRACE=1
export OOPS_DEBUG=1

cdate=2021080100

y4=`echo $cdate | cut -c1-4`
m2=`echo $cdate | cut -c5-6`
d2=`echo $cdate | cut -c7-8`
h2=`echo $cdate | cut -c9-10`

work_dir=$PWD
src_dir=/work/noaa/da/eliu/JEDI-ioda/ioda-bundle
out_dir=${work_dir}/testoutput/$cdate/bufr_backend
in_dir=${work_dir}/testinput/$cdate

mkdir -p -m770 $out_dir

process_yaml=${work_dir}/bufr2ioda_bufr_backend_amsua.yaml

${src_dir}/build/bin/time_IodaIO.x ${process_yaml}
#gdb --args ${src_dir}/build/bin/time_IodaIO.x ${process_yaml}
