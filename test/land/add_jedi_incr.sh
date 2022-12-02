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
module purge
module use $project_source_dir/modulefiles
module load GDAS/hera

GYMD=$(date +%Y%m%d -d "$YY$MM$DD $HH - 6 hours")
GHR=$(date +%H -d "$YY$MM$DD $HH - 6 hours")

EXECDIR=$project_source_dir/build/bin/
WORKDIR=$project_binary_dir/test/testrun
RSTDIR=$GDASAPP_TESTDATA/lowres/gdas.$GYMD/$GHR/atmos/RESTART/

#export TPATH="/scratch2/BMC/gsienkf/Clara.Draper/data_RnR/orog_files_Mike/"
export TPATH="/scratch1/NCEPDEV/global/glopara/fix/orog/20220805/C${RES}/"
export TSTUB="C${RES}_oro_data"

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

echo 'do_landDA: calling apply snow increment'

# (n=6) -> this is fixed, at one task per tile (with minor code change, could run on a single proc).
srun '--export=ALL' -A fv3-cpu -n 6 ${EXECDIR}/apply_incr ${WORKDIR}/apply_incr.log
if [[ $? != 0 ]]; then
    echo "apply snow increment failed"
    exit 10
fi

