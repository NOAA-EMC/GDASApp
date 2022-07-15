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

################################################################################
# runtime environment variables, create directories

# get runtime environment variables


comout = os.getenv('COMOUT')
comin_obs = os.getenv('COMIN_OBS')
staticsoca_dir = os.getenv('SOCA_INPUT_FIX_DIR')

# create analysis directory for files
anl_dir = os.path.join(comout, 'analysis')
ufsda.mkdir(anl_dir)

# create output directory for obs
diags = os.path.join(comout, 'analysis', 'diags')
ufsda.mkdir(diags)

# create output directory for soca DA
ufsda.mkdir(os.path.join(comout, 'analysis', 'Data'))

################################################################################
# fetch observations

# setup the archive, local and shared R2D2 databases
ufsda.r2d2.setup(r2d2_config_yaml='r2d2_config.yaml', shared_root=comin_obs)

# create config dict from runtime env
envconfig = ufsda.misc_utils.get_env_config(component='notatm')
os.environ['OBS_DATE'] = envconfig['OBS_DATE']
os.environ['OBS_DIR'] = envconfig['OBS_DIR']
os.environ['OBS_PREFIX'] = envconfig['OBS_PREFIX']
os.environ['DIAG_DIR'] = diags
stage_cfg = ufsda.parse_config(templateyaml=os.path.join(gdas_home,
                                                         'parm',
                                                         'templates',
                                                         'stage.yaml'), clean=True)

# stage observations from R2D2 to COMIN_OBS and then link to analysis subdir
ufsda.stage.obs(stage_cfg)

################################################################################
# stage backgrounds from COMIN_GES to analysis subdir
ufsda.stage.background(stage_cfg)

################################################################################
# stage static files
ufsda.stage.soca_fix(stage_cfg)

################################################################################
# prepare JEDI yamls

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
config = {}
ufsda.yamltools.genYAML(config, output=berr_yaml, template=berr_yaml_template)

# link yaml for decorrelation length scales
corscales_yaml = os.path.join(gdas_home,
                              'parm',
                              'soca',
                              'berror',
                              'soca_setcorscales.yaml')
ufsda.disk_utils.symlink(corscales_yaml,
                         os.path.join(stage_cfg['stage_dir'], 'soca_setcorscales.yaml'))

# generate yaml for bump C
# TODO (Guillaume): move the possible vars somewhere else
vars3d = ['tocn', 'socn', 'uocn', 'vocn', 'chl', 'biop']
vars2d = ['ssh', 'cicen', 'hicen', 'hsnon', 'swh',
          'sw', 'lw', 'lw_rad', 'lhf', 'shf', 'us']

# TODO (Guillaume): good enough for now but should be read from config.
vars = ['ssh', 'tocn', 'socn']
for v in vars:
    if v in vars2d:
        dim = '2d'
    else:
        dim = '3d'
    bumpC_yaml = os.path.join(anl_dir, 'soca_bump'+dim+'_C_'+v+'.yaml')
    bumpC_yaml_template = os.path.join(gdas_home,
                                       'parm',
                                       'soca',
                                       'berror',
                                       'soca_bump_C_split.yaml')
    bumpdir = 'bump'+dim+'_'+v
    ufsda.disk_utils.mkdir(os.path.join(anl_dir, bumpdir))
    config = {'datadir': bumpdir}
    os.environ['CVAR'] = v
    ufsda.yamltools.genYAML(config, output=bumpC_yaml, template=bumpC_yaml_template)

# generate yaml for soca_var
var_yaml = os.path.join(anl_dir, 'var.yaml')
var_yaml_template = os.path.join(gdas_home,
                                 'parm',
                                 'soca',
                                 'variational',
                                 '3dvarfgat.yaml')
gen_bkg_list(bkg_path=os.path.join(anl_dir, 'bkg'), yaml_name='bkg_list.yaml')
config = {
    'OBS_DATE': os.getenv('PDY')+os.getenv('cyc'),
    'BKG_LIST': 'bkg_list.yaml',
    'COVARIANCE_MODEL': 'SABER',
    'NINNER': '3',
    'SABER_BLOCKS_YAML': os.path.join(gdas_home, 'parm', 'soca', 'berror', 'saber_blocks.yaml')}
ufsda.yamltools.genYAML(config, output=var_yaml, template=var_yaml_template)
