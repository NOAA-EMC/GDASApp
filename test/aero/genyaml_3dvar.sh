#!/bin/bash
# generate YAML from a template
# using wxflow YAML tools
bindir=$1
srcdir=$2

# define some environment variables needed to substitue
export layout_x=1
export layout_y=1
export DATA=$bindir/test/testrun/aero/genyaml_3dvar
export BERROR_YAML=$srcdir/parm/aero/berror/staticb_identity.yaml.j2
export OBS_LIST=$srcdir/parm/aero/obs/lists/gdas_aero.yaml.j2
export LEVS=128
export CASE=C48
export PDY=20210321
export cyc=18
export assim_freq=6
export OPREFIX='gdas.t18z.'

# input and output YAMLs
export YAMLin=$srcdir/test/testinput/3dvar_gfs_aero.yaml.j2
export YAMLout=$DATA/3dvar_gfs_aero.yaml

# remove and make test directory
rm -rf $DATA
mkdir -p $DATA

# Set g-w HOMEgfs
topdir=$(cd "$(dirname "$(readlink -f -n "${bindir}" )" )/../../.." && pwd -P)
export HOMEgfs=$topdir

# Detect machine
source "${HOMEgfs}/ush/detect_machine.sh"

# Set up the PYTHONPATH to include wxflow from HOMEgfs
if [[ -d "${HOMEgfs}/sorc/wxflow/src" ]]; then
  PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${HOMEgfs}/sorc/wxflow/src"
fi

# Set python path for workflow utilities and tasks
wxflowPATH="${HOMEgfs}/ush/python"
PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${wxflowPATH}"
export PYTHONPATH

# run some python code to generate the YAML
python3 - <<EOF
from wxflow import parse_j2yaml
import datetime

valid_time_obj = datetime.datetime.strptime('$PDY$cyc','%Y%m%d%H')
winlen = $assim_freq
win_begin = valid_time_obj - datetime.timedelta(hours=int(winlen)/2)
case = int('$CASE'[1:])
levs = int('$LEVS')
npx = case + 1
npy = case + 1
npz = levs - 1

cycle_dict = {
    'AERO_WINDOW_BEGIN': win_begin,
    'current_cycle': valid_time_obj,
}

exp_dict = {
    'AERO_WINDOW_LENGTH': 'PT${assim_freq}H',
    'npx_ges': npx,
    'npy_ges': npy,
    'npz_ges': npz,
    'npx_anl': npx,
    'npy_anl': npy,
    'npz_anl': npz,
    'layout_x': 1,
    'layout_y': 1,
    'OPREFIX': '${OPREFIX}'
}

context = dict(cycle_dict, **exp_dict)
config = parse_j2yaml('$YAMLin', context, searchpath='$srcdir/parm')

config.save('$YAMLout')
EOF
