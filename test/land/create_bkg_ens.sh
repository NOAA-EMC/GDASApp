#!/bin/bash -e
################################################
# 4. CREATE BACKGROUND ENSEMBLE (LETKFOI)
################################################
YYYY=2021
MM=03
DD=23
HH=18
FILEDATE=$YYYY$MM$DD.${HH}0000

WORKDIR=$1
SORCDIR=$2
echo "START CREATE BACKGROUND ENSEMBLE"
echo "WORKDIR: $WORKDIR"
echo "SORCDIR: $SORCDIR"
module use $SORCDIR/modulefiles
module load GDAS/hera
echo "GDASAPP_TESTDATA: $GDASAPP_TESTDATA"

RSTDIR=$GDASAPP_TESTDATA/lowres/gdas.$YYYY$MM$DD/12/atmos/RESTART/
echo "RSTDIR1: $RSTDIR"
RSTDIR=/scratch1/NCEPDEV/da/Cory.R.Martin/CI/GDASApp/data/lowres/gdas.$YYYY$MM$DD/12/atmos/RESTART/
echo "RSTDIR2: $RSTDIR"
DAtype=letkfoi_snow

if [[ ${DAtype} == 'letkfoi_snow' ]]; then

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

    python ${SORCDIR}/ush/land/letkf_create_ens.py $FILEDATE $B
    if [[ $? != 0 ]]; then
        echo "letkf create failed"
        exit 10
    fi

fi

