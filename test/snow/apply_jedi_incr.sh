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

EXECDIR=$project_source_dir/build/bin
WORKDIR=$project_binary_dir/test/snow/apply_jedi_incr
RSTDIR=$GDASAPP_TESTDATA/lowres/gdas.$GYMD/$GHR/model/atmos/restart
INCDIR=$GDASAPP_TESTDATA/snow/C${RES}

export TPATH="$GDASAPP_TESTDATA/snow/C${RES}"
export TSTUB="C${RES}_oro_data"

if [[ -e $WORKDIR ]]; then
  rm -rf $WORKDIR
fi
mkdir -p $WORKDIR
cd $WORKDIR

if [[ -e apply_incr_nml ]]; then
  rm apply_incr_nml
fi

GFSv17=${GFSv17:-"NO"}

cat << EOF > apply_incr_nml
&noahmp_snow
 date_str=${YY}${MM}${DD}
 hour_str=$HH
 res=$RES
 frac_grid=$GFSv17
 rst_path="$WORKDIR",
 inc_path="$WORKDIR",
 orog_path="$TPATH"
 otype="$TSTUB"
/
EOF

# stage restarts
for tile in 1 2 3 4 5 6
do
  if [[ ! -e ${FILEDATE}.sfc_data.tile${tile}.nc ]]; then
    cp ${RSTDIR}/${FILEDATE}.sfc_data.tile${tile}.nc .
  fi
done

# stage increments
for tile in 1 2 3 4 5 6
do
  if [[ ! -e snowinc.${FILEDATE}.sfc_data.tile${tile}.nc ]]; then
    cp ${INCDIR}/${FILEDATE}.xainc.sfc_data.tile${tile}.nc snowinc.${FILEDATE}.sfc_data.tile${tile}.nc
  fi
done


echo 'do_snowDA: calling apply snow increment'

# (n=6) -> this is fixed, at one task per tile (with minor code change, could run on a single proc).
srun '--export=ALL' -n 6 ${EXECDIR}/apply_incr.exe ${WORKDIR}/apply_incr.log

rc=$?

exit $rc

