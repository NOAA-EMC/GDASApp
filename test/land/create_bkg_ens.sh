#!/bin/bash
set -e
################################################
# 4. CREATE BACKGROUND ENSEMBLE (LETKFOI)
################################################
YYYY=2021
MM=03
DD=23
HH=18
HR=12
FILEDATE=$YYYY$MM$DD.${HH}0000

project_binary_dir=$1
project_source_dir=$2

module purge
module use $project_source_dir/modulefiles
module load GDAS/hera

RSTDIR=$GDASAPP_TESTDATA/lowres/gdas.$YYYY$MM$DD/$HR/atmos/RESTART/
DAtype=letkfoi_snow

if [[ ${DAtype} == 'letkfoi_snow' ]]; then

    B=30  # background error std for LETKFOI

    JEDI_EXEC="fv3jedi_letkf.x"

    # FOR LETKFOI, CREATE THE PSEUDO-ENSEMBLE
    for ens in 001 002
    do
        if [ -e $project_binary_dir/test/testrun/mem${ens} ]; then
                rm -r $project_binary_dir/test/testrun/mem${ens}
        fi
        mkdir $project_binary_dir/test/testrun/mem${ens}
        for tile in 1 2 3 4 5 6
        do
        cp ${RSTDIR}/${FILEDATE}.sfc_data.tile${tile}.nc  ${project_binary_dir}/test/testrun/mem${ens}/${FILEDATE}.sfc_data.tile${tile}.nc
        done
        cp ${RSTDIR}/${FILEDATE}.coupler.res ${project_binary_dir}/test/testrun/mem${ens}/${FILEDATE}.coupler.res
    done


    echo 'do_landDA: calling create ensemble'

    python ${project_source_dir}/ush/land/letkf_create_ens.py $FILEDATE $B $project_binary_dir/test/testrun
    if [[ $? != 0 ]]; then
        echo "letkf create failed"
        exit 10
    fi

fi

