#!/usr/bin/env python3
################################################################################
#  UNIX Script Documentation Block
#                      .                                             .
# Script name:         exufsda_global_marine_analysis_prep.py
# Script description:  Stages files and generates YAML for UFS Global Marine Analysis
#
# Author: Guillaume Vernieres      Org: NCEP/EMC     Date: 2022-03-28
#
# Abstract: This script stages the marine observations, backgrounds and prepares
#           the variational yaml necessary to produce a UFS Global Marine Analysis.
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
my_dir = os.path.dirname(__file__)
my_home = os.path.dirname(os.path.dirname(my_dir))
gdas_home = os.path.join(os.getenv('HOMEgfs'), 'sorc', 'gdas.cd')
sys.path.append(os.path.join(os.getenv('HOMEgfs', my_home), 'ush'))
print(f"sys.path={sys.path}")


# import UFSDA utilities
import ufsda


def gen_bkg_list(bkg_path='.', file_type='MOM', yaml_name='bkg.yaml'):
    """
    Generate a YAML of the list of backgrounds for the pseudo model
    """
    files = glob.glob(bkg_path+'/*'+file_type+'*')
    files.sort()
    bkg_list = []
    for bkg in files:
        ocn_filename = os.path.basename(bkg)
        date = dparser.parse(ocn_filename, fuzzy=True)
        bkg_dict = {'date': date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'basename': bkg_path+'/',
                    'ocn_filename': ocn_filename,
                    'read_from_file': 1}
        bkg_list.append(bkg_dict)
    dict = {'states': bkg_list}
    f = open(yaml_name, 'w')
    yaml.dump(dict, f, sort_keys=False, default_flow_style=False)


# get runtime environment variables
comout = os.getenv('COMOUT')
comin_obs = os.getenv('COMIN_OBS')
staticsoca_dir = os.getenv('SOCA_INPUT_FIX_DIR')

# create analysis directory for files
anl_dir = os.path.join(comout, 'analysis')
ufsda.mkdir(anl_dir)

# create output directory for obs
ufsda.mkdir(os.path.join(comout, 'analysis', 'obs_out'))

# create output directory for soca DA
ufsda.mkdir(os.path.join(comout, 'analysis', 'Data'))

# setup the archive, local and shared R2D2 databases
ufsda.r2d2.setup(r2d2_config_yaml='r2d2_config.yaml', shared_root=comin_obs)

# create config dict from runtime env
stage_cfg = ufsda.parse_config(templateyaml=os.path.join(gdas_home,
                                                         'parm',
                                                         'templates',
                                                         'stage.yaml'), clean=True)

# stage observations from R2D2 to COMIN_OBS and then link to analysis subdir
ufsda.stage.obs(stage_cfg)

# stage backgrounds from COMIN_GES to analysis subdir
ufsda.stage.background(stage_cfg)

# stage static files
ufsda.stage.soca_fix(stage_cfg)

# link yaml for grid generation
gridgen_yaml = os.path.join(gdas_home,
                            'parm',
                            'soca',
                            'gridgen',
                            'gridgen.yaml')
ufsda.disk_utils.symlink(gridgen_yaml,
                         os.path.join(stage_cfg['stage_dir'], 'gridgen.yaml'))

# generate YAML file for parametric diag of B
berr_yaml = os.path.join(anl_dir, 'parametric_stddev_b.yaml')
berr_yaml_template = os.path.join(gdas_home,
                                 'parm',
                                 'soca',
                                 'berror',
                                 'parametric_stddev_b.yaml')
config = {'atm': 'false'}
ufsda.yamltools.genYAML(config, output=berr_yaml, template=berr_yaml_template)

# generate YAML file for soca_var
var_yaml = os.path.join(anl_dir, 'var.yaml')
var_yaml_template = os.path.join(gdas_home,
                                 'parm',
                                 'soca',
                                 'variational',
                                 '3dvarfgat.yaml')
gen_bkg_list(bkg_path=os.path.join(anl_dir, 'bkg'), yaml_name='bkg_list.yaml')
config = {
    'atm': 'false',
    'OBS_DATE': os.getenv('PDY')+os.getenv('cyc'),
    'BKG_LIST': 'bkg_list.yaml',
    'COVARIANCE_MODEL': 'SABER',
    'SABER_BLOCKS_YAML': os.path.join(gdas_home, 'parm', 'soca', 'berror', 'saber_block_identity.yaml')}
ufsda.yamltools.genYAML(config, output=var_yaml, template=var_yaml_template)
