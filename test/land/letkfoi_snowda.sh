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
WORKDIR=$project_binary_dir/test/land/letkfoi_snowda
RSTDIR=$GDASAPP_TESTDATA/lowres/gdas.$GYMD/$GHR/model_data/atmos/restart
export OBSDIR=$GDASAPP_TESTDATA/land

GFSv17=${GFSv17:-"NO"}
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

    JEDI_EXEC="fv3jedi_letkf.x"

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


    echo 'do_landDA: calling create ensemble'

    python ${project_source_dir}/ush/land/letkf_create_ens.py $FILEDATE $SNOWDEPTHVAR $B $WORKDIR

fi
############################################
# Prepare and Run JEDI
############################################
mkdir -p Data diags
ln -s ${project_binary_dir}/fv3-jedi/test/Data/fieldmetadata Data/fieldmetadata
ln -s ${project_binary_dir}/fv3-jedi/test/Data/fv3files Data/fv3files
ln -s ${project_source_dir}/ush/land/genYAML_output_letkfoi.yaml letkf_land.yaml
ln -s ${OBSDIR}/snow_depth/GTS/202103/adpsfc_snow_2021032318.nc4 adpsfc_snow.nc4
ln -s ${OBSDIR} Data/land
echo 'do_landDA: calling fv3-jedi'

srun '--export=ALL' -n 6 ${EXECDIR}/${JEDI_EXEC} letkf_land.yaml

rc=$?

exit $rc

