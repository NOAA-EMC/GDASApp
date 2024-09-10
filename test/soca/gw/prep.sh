#!/bin/bash
set -e

project_binary_dir=$1
project_source_dir=$2

# Get low res static files from the soca sandbox
${project_source_dir}/test/soca/gw/static.sh $project_binary_dir $project_source_dir

# Stage history and restart files following the "COM" structure

COM=${project_binary_dir}/test/soca/gw/COM/gdas.20180415

mkdir -p ${COM}/06/model/ice/history
mkdir -p ${COM}/06/model/ice/restart
mkdir -p ${COM}/06/model/ocean/history
mkdir -p ${COM}/06/model/atmos/analysis

# copy CICE6 restart
ice_rst=${project_binary_dir}/test/testdata/iced.2019-04-15-43200.nc
hist_icef=${project_binary_dir}/test/testdata/cice_hist.nc

cp ${ice_rst} ${COM}/06/model/ice/restart/20180415.120000.cice_model.res.nc

# invent MOM6 and CICE6 history files
i=3
lof=`ls ${project_binary_dir}/test/testdata/ocn_da_*`
for ocnf in $lof; do
  cp $ocnf ${COM}/06/model/ocean/history/gdas.ocean.t06z.inst.f00$i.nc
  cp $hist_icef ${COM}/06/model/ice/history/gdas.ice.t06z.inst.f00$i.nc
  i=$(($i+1))
done

# invent background error
for day in $(seq 1 2 9); do
    cp ${COM}/06/model/ocean/history/gdas.ocean.t06z.inst.f003.nc \
       ${project_binary_dir}/soca_static/bkgerr/stddev/ocn.ensstddev.fc.2019-04-0${day}T00:00:00Z.PT0S.nc
    cp ${project_source_dir}/sorc/soca/test/Data/72x35x25/ice.bkgerror.nc \
       ${project_binary_dir}/soca_static/bkgerr/stddev/ice.ensstddev.fc.2019-04-0${day}T00:00:00Z.PT0S.nc
done

# invent static ensemble
clim_ens_dir=${project_binary_dir}/soca_static/bkgerr/ens/2019-07-10T00Z
mkdir -p ${clim_ens_dir}
for domain in "ocean" "ice"; do
    list_of_ocn_fcst=$(ls ${COM}/06/model/${domain}/history/gdas.${domain}.t06z.inst.f*.nc)
    counter=1
    for file in ${list_of_ocn_fcst}; do
        file_name=${domain}.${counter}.nc
        cp ${file} ${clim_ens_dir}/${file_name}
        ((counter++))
    done
done

ice_files=$(ls ${clim_ens_dir}/ice.*.nc)
for ice_file in ${ice_files}; do
    ncrename -O -d ni,xaxis_1 -d nj,yaxis_1 -v aice_h,aicen -v hi_h,hicen -v hs_h,hsnon ${ice_file}
done

# Invent ensemble forecast for f009
fake_ocean_members=`ls`
fake_ice_members=`ls ${clim_ens_dir/ice.*.nc}`
COMENS=${project_binary_dir}/test/soca/gw/COM/enkfgdas.20180415
for mem in  {1..4}
do
    echo "member: $mem"
    # ocean member
    oceandir=${COMENS}/06/mem00${mem}/model/ocean/history
    mkdir -p $oceandir
    cp ${clim_ens_dir}/ocean.${mem}.nc $oceandir/enkfgdas.ocean.t06z.inst.f009.nc
    cp ${clim_ens_dir}/ocean.${mem}.nc $oceandir/enkfgdas.ocean.t06z.inst.f006.nc

    # ice member
    icedir=${COMENS}/06/mem00${mem}/model/ice/history
    mkdir -p $icedir
    cp ${clim_ens_dir}/ice.${mem}.nc $icedir/enkfgdas.ice.t06z.inst.f009.nc
    cp ${clim_ens_dir}/ice.${mem}.nc $icedir/enkfgdas.ice.t06z.inst.f006.nc
done
