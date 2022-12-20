#!/bin/bash
# ctest to create an experiment directory for global-workflow
bindir=$1
srcdir=$2

# export env. var.
source "${srcdir}/test/soca/gw/runtime_vars.sh" "${bindir}" "${srcdir}"

# test experiment variables
idate=${PDY}${cyc}
edate=${PDY}${cyc}
app=ATM # NOTE make this S2SWA soon
starttype='warm'
gfscyc='4'
resdet='48'
resens='24'
nens=0
configdir=${srcdir}/../../parm/config

# clean previous experiment
rm -rf "${ROTDIR}" "${EXPDIRS}"

# run the script
ln -sf "${srcdir}/../../workflow/setup_expt.py" .

# make a copy of parm/configdir
# TODO: remove when all the config.* that need to have variables substituted have been
#       updated in the g-w
cp -r "${configdir}" config

# edit config.yaml
cp "${srcdir}/test/soca/gw/config.yaml" .
soca_input_fix_dir="${bindir}/soca_static"
comin_obs="${bindir}/test/soca/obs/r2d2-shared"
soca_ninner=1
sed -i -e "s~@SOCA_INPUT_FIX_DIR@~${soca_input_fix_dir}~g" config.yaml
sed -i -e "s~@COMIN_OBS@~${comin_obs}~g" config.yaml
sed -i -e "s~@SOCA_NINNER@~${soca_ninner}~g" config.yaml
echo "Running global-workflow experiment generation script"
./setup_expt.py cycled --idate "${idate}"  \
                       --edate "${edate}" \
                       --app "${app}" \
                       --start "${starttype}" \
                       --gfs_cyc "${gfscyc}" \
                       --resdet "${resdet}" \
                       --resens "${resens}" \
                       --nens "${nens}" \
                       --pslot "${PSLOT}" \
                       --configdir config \
                       --comrot "${ROTDIR}" \
                       --expdir "${EXPDIRS}" \
                       --yaml config.yaml

# get the machine name from config.base
machine="$(echo "$(grep "export machine=" "${EXPDIRS}/${PSLOT}/config.base")" | cut -d "=" -f2)"
machine=$(echo "${machine}" | sed 's/[^0-9A-Z]*//g')

# over-write config.base
cp "${srcdir}/test/soca/gw/config.base" "${EXPDIRS}/${PSLOT}/"
HOMEgfs=$(readlink -f "${srcdir}/../..")
STMP="${bindir}/test/soca/gw/testrun"
sed -i -e "s~@MACHINE@~${machine}~g" "${EXPDIRS}/${PSLOT}/config.base"
sed -i -e "s~@HOMEgfs@~${HOMEgfs}~g" "${EXPDIRS}/${PSLOT}/config.base"
sed -i -e "s~@STMP@~${STMP}~g" "${EXPDIRS}/${PSLOT}/config.base"
sed -i -e "s~@ROTDIRS@~${ROTDIR}~g" "${EXPDIRS}/${PSLOT}/config.base"
sed -i -e "s~@EXPDIRS@~${EXPDIRS}~g" "${EXPDIRS}/${PSLOT}/config.base"

exit $?
