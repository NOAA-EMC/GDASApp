#!/bin/bash
set -e
################################################
YY=2021
MM=03
DD=23
HH=18
FILEDATE=$YY$MM$DD.${HH}0000
RES=48

project_binary_dir=$1
project_source_dir=$2

GYMD=$(date +%Y%m%d -d "$YY$MM$DD $HH - 6 hours")
GHR=$(date +%H -d "$YY$MM$DD $HH - 6 hours")
DOY=$(date +%j -d "$YY$MM$DD + 1 day")

EXECDIR=$project_source_dir/build/bin
WORKDIR=$project_binary_dir/test/snow/ims_proc
RSTDIR=$GDASAPP_TESTDATA/lowres/gdas.$GYMD/$GHR/model/atmos/restart

export OBSDIR=$GDASAPP_TESTDATA/snow/snow_ice_cover
export TSTUB="oro_C${RES}.mx100"

if [[ -e $WORKDIR ]]; then
  rm -rf $WORKDIR
fi
mkdir -p $WORKDIR
cd $WORKDIR

if [[ -e fims.nml ]]; then
  rm fims.nml
fi

cat >> fims.nml << EOF
 &fIMS_nml
  idim=$RES, jdim=$RES,
  otype=${TSTUB},
  jdate=$YY$DOY,
  yyyymmddhh=$YY$MM$DD.18,
  imsformat=2,
  imsversion=1.3,
  IMS_OBS_PATH="${OBSDIR}/IMS/$YY/",
  IMS_IND_PATH="${OBSDIR}/IMS/index_files/"
  /
EOF

# stage restarts
for tile in 1 2 3 4 5 6
do
  if [[ ! -e ${FILEDATE}.sfc_data.tile${tile}.nc ]]; then
    ln -s ${RSTDIR}/${FILEDATE}.sfc_data.tile${tile}.nc .
  fi
done

ulimit -Ss unlimited
${EXECDIR}/calcfIMS.exe

export PYTHONPATH=$PYTHONPATH:${project_source_dir}/iodaconv/src/:${project_source_dir}/build/lib/python${Python3_VERSION_MAJOR}.${Python3_VERSION_MINOR}
IMS_IODA=${EXECDIR}/imsfv3_scf2ioda.py

echo 'do_snowDA: calling ioda converter'
python ${IMS_IODA} -i IMSscf.${YY}${MM}${DD}.${TSTUB}.nc -o ioda.IMSscf.${YY}${MM}${DD}.${TSTUB}.nc

rc=$?

exit $rc

