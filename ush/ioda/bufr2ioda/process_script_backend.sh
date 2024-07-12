#!/bin/sh -xvf

#source ~eliu/modules/env_jedi.sh

set -x
ulimit -s unlimited
ulimit -a

export OOPS_TRACE=1
export OOPS_DEBUG=1
#export LD_LIBRARY_PATH=/work/noaa/da/eliu/EMC-bufr-query/bufr-query/build/lib:${LD_LIBRARY_PATH}
export PYTHONPATH=$PYTHONPATH:/work/noaa/da/eliu/EMC-bufr-query/bufr-query/build/lib/python3.10
export PYTHONPATH=$PYTHONPATH:/work/noaa/da/eliu/JEDI-ioda/ioda-bundle/build/lib/python3.10

cdate=2021080100

y4=`echo $cdate | cut -c1-4`
m2=`echo $cdate | cut -c5-6`
d2=`echo $cdate | cut -c7-8`
h2=`echo $cdate | cut -c9-10`

work_dir=$PWD
src_dir=/work/noaa/da/eliu/JEDI-ioda/ioda-bundle
out_dir=${work_dir}/testoutput/$cdate/script_backend
in_dir=${work_dir}/testinput/$cdate

mkdir -p -m770 $out_dir

process_yaml=${work_dir}/bufr2ioda_script_backend_amsua.yaml

${src_dir}/build/bin/time_IodaIO.x ${process_yaml}

