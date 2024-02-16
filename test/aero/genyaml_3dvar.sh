#!/bin/bash
# generate YAML from a template
# using wxflow YAML tools
bindir=$1
srcdir=$2

# define some environment variables needed to substitue
export layout_x=1
export layout_y=1
export DATA=$bindir/test/testrun/aero/genyaml_3dvar
export BERROR_YAML=$srcdir/parm/aero/berror/staticb_identity.yaml
export OBS_LIST=$srcdir/parm/aero/obs/lists/gdas_aero_prototype.yaml
export OBS_YAML_DIR=$srcdir/parm/aero/obs/config
export LEVS=128
export CASE=C48
export CDATE=2021032118
export assim_freq=6
export OPREFIX='gdas.t18z.'

# input and output YAMLs
export YAMLin=$srcdir/parm/aero/variational/3dvar_gfs_aero.yaml
export YAMLout=$DATA/3dvar_gfs_aero.yaml

# remove and make test directory
rm -rf $DATA
mkdir -p $DATA

# run some python code to generate the YAML
python3 - <<EOF
from wxflow import AttrDict, Template, TemplateConstants, YAMLFile
from wxflow import parse_j2yaml
import os
import datetime


valid_time_obj = datetime.datetime.strptime('$CDATE','%Y%m%d%H')
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
}


config_out = parse_j2yaml('$YAMLin', {**os.environ, **cycle_dict, **exp_dict})
save_as_yaml(config_out, '$YAMLout')

EOF
