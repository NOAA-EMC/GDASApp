#!/usr/bin/env python3
################################################################################
#  UNIX Script Documentation Block
#                      .                                             .
# Script name:         exufsda_global_marine_analysis_prep.py
# Script description:  Stages files and generates YAML for UFS Global Marine Analysis
#
# Author: Guillaume Vernieres      Org: NCEP/EMC     Date: 2022-03-28
#
# Abstract: This script stages the marine observations necessary
#           to produce a UFS Global Marine Analysis.
#
# $Id$
#
# Attributes:
#   Language: Python3
#
################################################################################

# import os and sys to add ush to path
import os
import sys
import yaml
import glob
import dateutil.parser as dparser

# get absolute path of ush/ directory either from env or relative to this file
# TODO: ufsda should be installed
sys.path.append(os.path.join(os.getenv('HOMEgfs'), 'ush'))

# import UFSDA utilities
import ufsda


def gen_bkg_list(bkg_path='.', file_type='MOM', yaml_name='bkg.yaml'):
    # generate a YAML of the list the backgrounds for the pseudo model
    # TODO (Guillaume): Move somewhere else ...
    files = glob.glob(bkg_path+'/*'+file_type+'*')
    files.sort()
    bkg_list = []
    for bkg in files:
        ocn_filename = os.path.basename(bkg)
        date = dparser.parse(ocn_filename, fuzzy=True)
        bkg_dict = {'date': date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'basename': bkg_path,
                    'ocn_filename': ocn_filename,
                    'read_from_file': 1}
        bkg_list.append(bkg_dict)
    dict = {'states': bkg_list}
    f = open(yaml_name, 'w')
    yaml.dump(dict, f, sort_keys=False, default_flow_style=False)


# get runtime environment variables
comout = os.getenv('COMOUT')
comin_obs = os.getenv('COMIN_OBS')

# create analysis directory for files
anl_dir = os.path.join(comout, 'analysis')
ufsda.mkdir(anl_dir)

# setup the archive, local and shared R2D2 databases
ufsda.r2d2.setup(r2d2_config_yaml='r2d2_config.yaml', shared_root=comin_obs)

# create config dict from runtime env
stage_cfg = ufsda.parse_config(templateyaml=os.path.join(os.getenv('HOMEgfs'),
                                                         'parm',
                                                         'templates',
                                                         'stage.yaml'), clean=True)

# stage observations from R2D2 to COMIN_OBS and then link to analysis subdir
ufsda.stage.obs(stage_cfg)

# stage backgrounds from COMIN_GES to analysis subdir
ufsda.stage.background(stage_cfg)

# stage static files
# TODO (Guillaume)

# generate YAML file for soca_var
var_yaml = os.path.join(anl_dir, 'var.yaml')
var_yaml_template = os.path.join(os.getenv('HOMEgfs'),
                                 'parm',
                                 'soca',
                                 'variational',
                                 'ufsda_global_ocn_3dvarfgat.yaml')
gen_bkg_list(bkg_path=os.path.join(anl_dir, 'bkg'), yaml_name='bkg_list.yaml')
os.environ['BKG_LIST'] = 'bkg_list.yaml'
ufsda.gen_yaml(var_yaml, var_yaml_template)
