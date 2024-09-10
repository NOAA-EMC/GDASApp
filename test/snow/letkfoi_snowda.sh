#!/bin/bash
set -xe
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
WORKDIR=$project_binary_dir/test/snow/letkfoi_snowda
RSTDIR=$GDASAPP_TESTDATA/lowres/gdas.$GYMD/$GHR/model/atmos/restart
export OBSDIR=$GDASAPP_TESTDATA/snow

GFSv17=${GFSv17:-"YES"}
DAtype=letkfoi_snow

if [ $GFSv17 == "YES" ]; then
    SNOWDEPTHVAR="snodl"
else
    SNOWDEPTHVAR="snwdph"
fi

if [[ -e $WORKDIR ]]; then
  rm -rf $WORKDIR
fi
mkdir -p $WORKDIR
cd $WORKDIR

if [[ ${DAtype} == 'letkfoi_snow' ]]; then

    B=30  # background error std for LETKFOI

    JEDI_EXEC="gdas.x fv3jedi localensembleda"

    # FOR LETKFOI, CREATE THE PSEUDO-ENSEMBLE
    for ens in 001 002
    do
        if [ -e $WORKDIR/mem${ens} ]; then
                rm -rf $WORKDIR/mem${ens}
        fi
        mkdir -p $WORKDIR/mem${ens}
        for tile in 1 2 3 4 5 6
        do
            cp ${RSTDIR}/${FILEDATE}.sfc_data.tile${tile}.nc  ${WORKDIR}/mem${ens}/${FILEDATE}.sfc_data.tile${tile}.nc
        done
        cp ${RSTDIR}/${FILEDATE}.coupler.res ${WORKDIR}/mem${ens}/${FILEDATE}.coupler.res
    done


    echo 'do_snowDA: calling create ensemble'

    python ${project_source_dir}/ush/snow/letkf_create_ens.py $FILEDATE $SNOWDEPTHVAR $B $WORKDIR

fi
############################################
# Prepare and Run JEDI
############################################
mkdir -p Data diags
mkdir -p Data/fieldmetadata
ln -s ${project_source_dir}/parm/io/fv3jedi_fieldmetadata_restart.yaml Data/fieldmetadata/.
ln -s ${project_source_dir}/sorc/fv3-jedi/test/Data/fv3files Data/fv3files
ln -s ${project_source_dir}/test/snow/letkfoi_snow.yaml letkf_snow.yaml
ln -s ${OBSDIR}/snow_depth/GTS/202103/adpsfc_snow_2021032318.nc4 adpsfc_snow.nc4
ln -s ${OBSDIR} Data/snow
echo 'do_snowDA: calling fv3-jedi'

srun '--export=ALL' -n 6 ${EXECDIR}/${JEDI_EXEC} letkf_snow.yaml

rc=$?

exit $rc

