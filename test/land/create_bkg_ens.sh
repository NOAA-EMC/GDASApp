#!/bin/bash -e
################################################
# 4. CREATE BACKGROUND ENSEMBLE (LETKFOI)
################################################
YYYY=2021
MM=03
DD=23
HH=18

WORKDIR=./
SORCDIR=/scratch2/NCEPDEV/stmp1/Jiarui.Dong/gdasapp/gdasapp.3
FILEDATE=$YYYY$MM$DD.${HH}0000

MODDIR=/scratch1/NCEPDEV/global/Jiarui.Dong/JEDI/GDASWork/GDASApp/ush/land/modules
RSTDIR=/scratch1/NCEPDEV/da/Cory.R.Martin/CI/GDASApp/data/lowres/gdas.$YYYY$MM$DD/12/atmos/RESTART/
DAtype=letkfoi_snow_gts

if [[ ${DAtype} == 'letkfoi_snow_gts' ]]; then

    B=30  # back ground error std for LETKFOI

    JEDI_EXEC="fv3jedi_letkf.x"

    # FOR LETKFOI, CREATE THE PSEUDO-ENSEMBLE
    for ens in 001 002
    do
        if [ -e $WORKDIR/mem${ens} ]; then
                rm -r $WORKDIR/mem${ens}
        fi
        mkdir $WORKDIR/mem${ens}
        for tile in 1 2 3 4 5 6
        do
        cp ${RSTDIR}/${FILEDATE}.sfc_data.tile${tile}.nc  ${WORKDIR}/mem${ens}/${FILEDATE}.sfc_data.tile${tile}.nc
        done
        cp ${RSTDIR}/${FILEDATE}.coupler.res ${WORKDIR}/mem${ens}/${FILEDATE}.coupler.res
    done


    echo 'do_landDA: calling create ensemble'

    # using ioda mods to get a python version with netCDF4
#    source ${WORKDIR}/ioda_mods_hera
    source ${MODDIR}/gdasapp_mods

    python ${SORCDIR}/ush/land/letkf_create_ens.py $FILEDATE $B
    if [[ $? != 0 ]]; then
        echo "letkf create failed"
        exit 10
    fi

fi

