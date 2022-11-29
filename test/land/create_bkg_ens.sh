#!/bin/bash
set -e
################################################
# 4. CREATE BACKGROUND ENSEMBLE (LETKFOI)
################################################
YYYY=2021
MM=03
DD=23
HH=18
FILEDATE=$YYYY$MM$DD.${HH}0000

project_binary_dir=$1
project_source_dir=$2

echo "project_binary_dir: $project_binary_dir"
echo "project_source_dir: $project_source_dir"

##module use $project_source_dir/modulefiles
##module load GDAS/hera
echo "GDASAPP_TESTDATA: $GDASAPP_TESTDATA"

RSTDIR=$GDASAPP_TESTDATA/lowres/gdas.$YYYY$MM$DD/12/atmos/RESTART/
echo "RSTDIR: $RSTDIR"
##RSTDIR=/scratch1/NCEPDEV/da/Cory.R.Martin/CI/GDASApp/data/lowres/gdas.$YYYY$MM$DD/12/atmos/RESTART/
##echo "RSTDIR2: $RSTDIR"
DAtype=letkfoi_snow

if [[ ${DAtype} == 'letkfoi_snow' ]]; then

    B=30  # back ground error std for LETKFOI

    JEDI_EXEC="fv3jedi_letkf.x"

    # FOR LETKFOI, CREATE THE PSEUDO-ENSEMBLE
    for ens in 001 002
    do
        if [ -e $project_binary_dir/mem${ens} ]; then
                rm -r $project_binary_dir/mem${ens}
        fi
        mkdir $project_binary_dir/mem${ens}
        for tile in 1 2 3 4 5 6
        do
        cp ${RSTDIR}/${FILEDATE}.sfc_data.tile${tile}.nc  ${project_binary_dir}/mem${ens}/${FILEDATE}.sfc_data.tile${tile}.nc
        done
        cp ${RSTDIR}/${FILEDATE}.coupler.res ${project_binary_dir}/mem${ens}/${FILEDATE}.coupler.res
    done


    echo 'do_landDA: calling create ensemble'

    python ${project_source_dir}/ush/land/letkf_create_ens.py $FILEDATE $B $project_binary_dir
    if [[ $? != 0 ]]; then
        echo "letkf create failed"
        exit 10
    fi

fi

