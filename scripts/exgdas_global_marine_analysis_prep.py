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
import f90nml
import shutil
import logging
import subprocess
from datetime import datetime, timedelta
from netCDF4 import Dataset
import xarray as xr
import numpy as np


# set up logger
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

# get absolute path of ush/ directory either from env or relative to this file
my_dir = os.path.dirname(__file__)
my_home = os.path.dirname(os.path.dirname(my_dir))
gdas_home = os.path.join(os.getenv('HOMEgfs'), 'sorc', 'gdas.cd')
sys.path.append(os.path.join(os.getenv('HOMEgfs', my_home), 'ush'))
print(f"sys.path={sys.path}")


# import UFSDA utilities
import ufsda

def agg_seaice(fname_in, fname_out):
    """
    Aggregates seaice variables from fname_in and save in fname_out.
    """

    soca2cice_vars = {'aicen': 'aicen',
                      'hicen': 'vicen',
                      'hsnon': 'vsnon'}

    # read CICE restart
    ds = xr.open_dataset(fname_in)
    nj = np.shape(ds['aicen'])[1]
    ni = np.shape(ds['aicen'])[2]

    # populate xarray with aggregated quantities
    aggds = xr.merge([xr.DataArray(
                         name = varname,
                         data = np.reshape(np.sum(ds[soca2cice_vars[varname]].values, axis=0), (1, nj,ni)),
                         dims = ['time','yaxis_1','xaxis_1']
                                  ) for varname in soca2cice_vars.keys()])

    # remove fill value
    encoding = {varname: {'_FillValue': False} for varname in soca2cice_vars.keys()}

    # save datasets
    aggds.to_netcdf(fname_out, format='NETCDF4', unlimited_dims='time', encoding=encoding)

    # xarray doesn't allow variables and dim that have the same name, switch to netCDF4
    ncf = Dataset(fname_out,'a')
    t = ncf.createVariable('time','f8',('time'))
    t[:] = 1.0
    ncf.close()

def test_hist_date(histfile, ref_date):
    """
    Check that the date in the MOM6 history file is the expected one for the cycle.
    TODO: Implement the same for seaice
    """

    ncf = Dataset(histfile, 'r')
    hist_date = dparser.parse(ncf.variables['time'].units, fuzzy=True) + timedelta(hours=int(ncf.variables['time'][0]))
    ncf.close()
    logging.info(f"*** history file date: {hist_date} expected date: {ref_date}")
    assert hist_date == ref_date, 'Inconsistent bkg date'


def gen_bkg_list(window_begin=' ', bkg_path='.', file_type='gdas.t*.ocnf00[3-9]', yaml_name='bkg.yaml'):
    """
    Generate a YAML of the list of backgrounds for the pseudo model
    TODO: [3-9] shouldn't be hard-coded. Instead construct the list of background dates for the cycle
                and grab the files that correspond to the dates.
    """

    # Create yaml of list of backgrounds
    bkg_list = []
    bkg_date = window_begin
    files = glob.glob(bkg_path+'/*'+file_type+'*')
    files.sort()
    ocn_filename_ic = os.path.splitext(os.path.basename(files[0]))[0]+'.nc'
    test_hist_date(os.path.join(bkg_path, ocn_filename_ic), bkg_date)  # assert date of the history file is correct

    for bkg in files:
        test_hist_date(bkg, bkg_date)  # assert date of the history file is correct
        ocn_filename = os.path.splitext(os.path.basename(bkg))[0]+'.nc'
        ice_filename = ocn_filename.replace("ocn", "ice")
        agg_ice_filename = ocn_filename.replace("ocn", "agg_ice")
        agg_seaice(os.path.join(bkg_path, ice_filename),
                   os.path.join(bkg_path, agg_ice_filename)) # aggregate seaice variables
        bkg_dict = {'date': bkg_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'basename': bkg_path+'/',
                    'ocn_filename': ocn_filename,
                    'ice_filename': agg_ice_filename,
                    'read_from_file': 1,
                    'remap_filename': os.path.join(bkg_path, ocn_filename_ic)}
        bkg_date = bkg_date + timedelta(hours=1)  # TODO: make the bkg interval a configurable
        bkg_list.append(bkg_dict)
    dict = {'states': bkg_list}
    f = open(yaml_name, 'w')
    yaml.dump(dict, f, sort_keys=False, default_flow_style=False)

################################################################################
# runtime environment variables, create directories


logging.info(f"---------------- Setup runtime environement")

comout = os.getenv('COMOUT')
comin_obs = os.getenv('COMIN_OBS')
anl_dir = os.getenv('DATA')
staticsoca_dir = os.getenv('SOCA_INPUT_FIX_DIR')

# create analysis directory for files
ufsda.mkdir(anl_dir)

# create output directory for obs
diags = os.path.join(anl_dir, 'diags')
ufsda.mkdir(diags)

# create output directory for soca DA
anl_out = os.path.join(comout, 'ocnanal_'+os.getenv('CDATE'), 'Data')
ufsda.mkdir(anl_out)
ufsda.symlink(os.path.join(anl_dir, 'Data'), anl_out, remove=False)


################################################################################
# fetch observations

logging.info(f"---------------- Stage observations")

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
logging.info(f"---------------- Stage backgrounds")

stage_cfg['background_dir'] = os.getenv('COMIN_GES')
ufsda.stage.background(stage_cfg)

################################################################################
# stage static files
logging.info(f"---------------- Stage static files")
ufsda.stage.soca_fix(stage_cfg)

################################################################################
# prepare JEDI yamls
logging.info(f"---------------- Generate JEDI yaml files")

# get list of DA variables
soca_vars = os.environ.get("SOCA_VARS").split(",")

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

for v in soca_vars:
    logging.info(f"creating the yaml to initialize bump for {v}")
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
half_assim_freq = timedelta(hours=int(os.getenv('assim_freq'))/2)
window_begin = datetime.strptime(os.getenv('CDATE'), '%Y%m%d%H') - half_assim_freq
gen_bkg_list(window_begin=window_begin, bkg_path=os.getenv('COMIN_GES'), yaml_name='bkg_list.yaml')
soca_ninner = os.getenv('SOCA_NINNER')
config = {
    'OBS_DATE': os.getenv('PDY')+os.getenv('cyc'),
    'BKG_LIST': 'bkg_list.yaml',
    'COVARIANCE_MODEL': 'SABER',
    'NINNER': soca_ninner,
    'SABER_BLOCKS_YAML': os.path.join(gdas_home, 'parm', 'soca', 'berror', 'saber_blocks.yaml')}
logging.info(f"{config}")
ufsda.yamltools.genYAML(config, output=var_yaml, template=var_yaml_template)

# link of convenience
mom_ic = glob.glob(os.path.join(os.getenv('COMIN_GES'), 'gdas.*.ocnf003.nc'))[0]
ufsda.disk_utils.symlink(mom_ic, os.path.join(anl_dir, 'INPUT', 'MOM.res.nc'))

cice_ic = glob.glob(os.path.join(os.getenv('COMIN_GES'), 'gdas.*.agg_icef003.nc'))[0]
ufsda.disk_utils.symlink(cice_ic, os.path.join(anl_dir, 'INPUT', 'cice.res.nc'))

# prepare input.nml
mom_input_nml_src = os.path.join(gdas_home, 'parm', 'soca', 'fms', 'input.nml')
mom_input_nml_tmpl = os.path.join(stage_cfg['stage_dir'], 'mom_input.nml.tmpl')
mom_input_nml = os.path.join(stage_cfg['stage_dir'], 'mom_input.nml')
ufsda.disk_utils.copyfile(mom_input_nml_src, mom_input_nml_tmpl)
domain_stack_size = os.getenv('DOMAIN_STACK_SIZE')

ymdhms = [int(s) for s in window_begin.strftime('%Y,%m,%d,%H,%M,%S').split(',')]
with open(mom_input_nml_tmpl, 'r') as nml_file:
    nml = f90nml.read(nml_file)
    nml['ocean_solo_nml']['date_init'] = ymdhms
    nml['fms_nml']['domains_stack_size'] = int(domain_stack_size)
    ufsda.disk_utils.removefile(mom_input_nml)
    nml.write(mom_input_nml)
