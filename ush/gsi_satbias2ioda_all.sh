#! /usr/bin/env bash

set -ex

# Source UFSDA workflow modules
source "${HOMEgfs}/dev/ush/load_modules.sh" ufsda
status=$?
if [[ ${status} -ne 0 ]]; then
    exit "${status}"
fi


# Set variables
GDUMP="gdas"
GDATE=$(date --utc -d "${PDY} ${cyc} - ${assim_freq} hours" +%Y%m%d%H)
gcyc=${GDATE:8:2}

ABIAS=${COMOUT_ATMOS_ANALYSIS_PREV}/${GDUMP}.t${gcyc}z.abias
ABIASPC=${COMOUT_ATMOS_ANALYSIS_PREV}/${GDUMP}.t${gcyc}z.abias_pc
ABIAS_JEDI=${COMOUT_ATMOS_ANALYSIS_PREV}/${GDUMP}.t${gcyc}z.rad_varbc_params.tar

satbias2ioda_x=${HOMEgfs}/sorc/gdas.cd/build/bin/satbias2ioda.x
satbias2ioda_y=${HOMEgfs}/sorc/gdas.cd/ush/satbias_converter.yaml.tmpl


# Create work directory
gsi_run_dir=${DATA}/gsi_satbias2ioda
mkdir -p ${gsi_run_dir}
cd ${gsi_run_dir}


# Link GSI bias correction files to run directory
locdir=`pwd`
if [ ! -d ./testrun/varbc ]; then
    mkdir -p ./testrun/varbc
fi

ln -s ${ABIAS}   ./satbias_in
ln -s ${ABIASPC} ./satbias_pc
grep  -i 'NaN'  satbias_in && echo 'Stop. There are NaN in ${ABIAS}.' && exit 1


# Get instruments from satbias_in
obsclass=`grep '_' satbias_in   | awk '{print $2}' | uniq`


# Loop over instruments.  Covert GSI abias to JEDI format
for instrument in $(echo $obsclass); do
    echo ${instrument}
    /bin/cp -f ${satbias2ioda_y}  satbias_converter.yaml
    sed -i -e "s/INSTRUMENT/${instrument}/g" satbias_converter.yaml

    ${satbias2ioda_x} satbias_converter.yaml
    export err=$?
    if [[ ${err} -ne 0 ]]; then
	err_exit "satbias2iodas.x failed for ${instrument}, ABORT!"
    fi

    /bin/rm -f  testrun/varbc/*nc
    /bin/rm -f  testrun/varbc/*txt
    cd ./testrun/varbc/
    grep ${instrument}  ../../satbias_in  | awk '{print $2" "$3" "$4}' > \
          ${locdir}/gdas.t${gcyc}.${instrument}.tlapse.txt
    /bin/cp -p satbias_${instrument}.nc4  ${locdir}/gdas.t${gcyc}.${instrument}.satbias.nc
    /bin/mv  satbias_${instrument}.nc4  ${locdir}/gdas.t${gcyc}.${instrument}.satbias_cov.nc
    
    cd  ${locdir}
    /bin/rm -f satbias_converter.yaml
done
/bin/rm -f satbias_in satbias_pc
/bin/rm -rf ./testrun


# Create tarball with JEDI format radiance bias correction files
cd ${locdir}
if [[ -s ${ABIAS_JEDI} ]]; then
    rm -f ${ABIAS_JEDI}
fi
tar -cvf ${ABIAS_JEDI} ./
export err=$?
if [[ ${err} -ne 0 ]]; then
    err_exit "Creation of $ABIAS_JEDI failed, ABORT!"
fi


# Exit out cleanly
exit 0
