#!/bin/bash
set -e
################################################
# 4. CREATE BACKGROUND ENSEMBLE (LETKFOI)
################################################
YY=2021
MM=03
DD=23
HH=18
HR=12
FILEDATE=$YY$MM$DD.${HH}0000

project_binary_dir=$1
project_source_dir=$2

GYMD=$(date +%Y%m%d -d "$YY$MM$DD $HH - 6 hours")
GHR=$(date +%H -d "$YY$MM$DD $HH - 6 hours")

WORKDIR=$project_binary_dir/test/land/create_jedi_ens
RSTDIR=$GDASAPP_TESTDATA/lowres/gdas.$GYMD/$GHR/atmos/RESTART
DAtype=letkfoi_snow

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

    python ${project_source_dir}/ush/land/letkf_create_ens.py $FILEDATE $B $WORKDIR

    rc=$?

    exit $rc

fi

