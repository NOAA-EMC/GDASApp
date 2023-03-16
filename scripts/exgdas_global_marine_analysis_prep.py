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
import pytz
from netCDF4 import Dataset
import xarray as xr
import numpy as np
from pygw.attrdict import AttrDict
from pygw.template import Template, TemplateConstants
from pygw.yaml_file import YAMLFile


# set up logger
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

# get absolute path of ush/ directory either from env or relative to this file
my_dir = os.path.dirname(__file__)
my_home = os.path.dirname(os.path.dirname(my_dir))
gdas_home = os.path.join(os.getenv('HOMEgfs'), 'sorc', 'gdas.cd')

# import UFSDA utilities
import ufsda
from ufsda.stage import obs, soca_fix


def agg_seaice(fname_in, fname_out):
    """
    Aggregates seaice variables from a CICE restart fname_in and save in fname_out.
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
                      name=varname,
                      data=np.reshape(np.sum(ds[soca2cice_vars[varname]].values, axis=0), (1, nj, ni)),
                      dims=['time', 'yaxis_1', 'xaxis_1']) for varname in soca2cice_vars.keys()])

    # remove fill value
    encoding = {varname: {'_FillValue': False} for varname in soca2cice_vars.keys()}

    # save datasets
    aggds.to_netcdf(fname_out, format='NETCDF4', unlimited_dims='time', encoding=encoding)

    # xarray doesn't allow variables and dim that have the same name, switch to netCDF4
    ncf = Dataset(fname_out, 'a')
    t = ncf.createVariable('time', 'f8', ('time'))
    t[:] = 1.0
    ncf.close()


def cice_hist2fms(input_filename, output_filename):
    """
    Simple reformatting utility to allow soca/fms to read CICE's history
    """

    # open the CICE history file
    ds = xr.open_dataset(input_filename)

    # rename the dimensions to xaxis_1 and yaxis_1
    ds = ds.rename({'ni': 'xaxis_1', 'nj': 'yaxis_1'})

    # rename the variables
    ds = ds.rename({'aice_h': 'aicen', 'hi_h': 'hicen', 'hs_h': 'hsnon'})

    # Save the new netCDF file
    ds.to_netcdf(output_filename, mode='w')


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


def gen_bkg_list(bkg_path, out_path, window_begin=' ', yaml_name='bkg.yaml', ice_rst=False):
    """
    Generate a YAML of the list of backgrounds for the pseudo model
    """

    # Pseudo model parameters (time step, start date)
    # TODO: make this a parameter
    dt_pseudo = 3
    bkg_date = window_begin

    # Construct list of background file names
    cdump = os.getenv('CDUMP')
    cyc = str(os.getenv('cyc')).zfill(2)
    gcyc = str((int(cyc) - 6) % 24).zfill(2)  # previous cycle
    fcst_hrs = list(range(3, 10, dt_pseudo))
    files = []
    for fcst_hr in fcst_hrs:
        files.append(os.path.join(bkg_path, cdump+'.t'+gcyc+'z.ocnf'+str(fcst_hr).zfill(3)+'.nc'))

    # Identify the ocean background that will be used for the  vertical coordinate remapping
    ocn_filename_ic = os.path.splitext(os.path.basename(files[0]))[0]+'.nc'
    test_hist_date(os.path.join(bkg_path, ocn_filename_ic), bkg_date)  # assert date of the history file is correct

    # Copy/process backgrounds and generate background yaml list
    bkg_list = []
    for bkg in files:

        # assert validity of the ocean bkg date, remove basename
        test_hist_date(bkg, bkg_date)
        ocn_filename = os.path.splitext(os.path.basename(bkg))[0]+'.nc'

        # prepare the seaice background, aggregate if the backgrounds are CICE restarts
        ice_filename = ocn_filename.replace("ocn", "ice")
        agg_ice_filename = ocn_filename.replace("ocn", "agg_ice")
        if ice_rst:
            # if this is a CICE restart, aggregate seaice variables and dump
            # aggregated ice bkg in out_path
            # TODO: This option is turned off for now, figure out what to do with it.
            agg_seaice(os.path.join(bkg_path, ice_filename),
                       os.path.join(out_path, agg_ice_filename))
        else:
            # Process the CICE history file so they can be read by soca/fms
            # TODO: Add date check of the cice history
            # TODO: bkg_path should be 1 level up
            cice_hist2fms(os.path.join(bkg_path, '..', 'ice', ice_filename),
                          os.path.join(out_path, agg_ice_filename))

        # copy ocean bkg to out_path
        ufsda.disk_utils.copyfile(os.path.join(bkg_path, ocn_filename),
                                  os.path.join(out_path, ocn_filename))

        bkg_dict = {'date': bkg_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'basename': './bkg/',
                    'ocn_filename': ocn_filename,
                    'ice_filename': agg_ice_filename,
                    'read_from_file': 1,
                    'remap_filename': './bkg/'+ocn_filename_ic}
        bkg_date = bkg_date + timedelta(hours=dt_pseudo)  # TODO: make the bkg interval a configurable
        bkg_list.append(bkg_dict)
    f = open(yaml_name, 'w')
    yaml.dump(bkg_list, f, sort_keys=False, default_flow_style=False)


def find_bkgerr(input_date, domain):
    """
    Find the std. dev. files that are the closest to the DA window
    """
    bkgerror_dir = os.path.join(os.getenv('SOCA_INPUT_FIX_DIR'), 'bkgerr', 'stddev')
    files = glob.glob(os.path.join(bkgerror_dir, domain+'.ensstddev.fc.*.nc'))
    closest_file = ""
    closest_diff = float("inf")
    for file in files:
        file_date = dparser.parse(os.path.basename(file), fuzzy=True)
        file_date = file_date.replace(year=input_date.year)
        diff = abs((file_date - input_date).total_seconds())
        if diff < closest_diff:
            closest_file = file
            closest_diff = diff
    return closest_file


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

# create output directory for obs
bkg_dir = os.path.join(anl_dir, 'bkg')
ufsda.mkdir(bkg_dir)

# create output directory for soca DA
anl_out = os.path.join(anl_dir, 'Data')
ufsda.mkdir(anl_out)

# Variables of convenience
half_assim_freq = timedelta(hours=int(os.getenv('assim_freq'))/2)
assim_freq = timedelta(hours=int(os.getenv('assim_freq')))
window_begin = datetime.strptime(os.getenv('PDY')+os.getenv('cyc'), '%Y%m%d%H') - half_assim_freq
window_begin_iso = window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')
fcst_begin = datetime.strptime(os.getenv('PDY')+os.getenv('cyc'), '%Y%m%d%H') - assim_freq

################################################################################
# fetch observations

logging.info(f"---------------- Stage observations")

# setup the archive, local and shared R2D2 databases
ufsda.r2d2.setup(r2d2_config_yaml=os.path.join(anl_dir, 'r2d2_config.yaml'), shared_root=comin_obs)

# create config dict from runtime env
envconfig = ufsda.misc_utils.get_env_config(component='soca')
stage_cfg = YAMLFile(path=os.path.join(gdas_home,
                                       'parm',
                                       'templates',
                                       'stage.yaml'))
stage_cfg = Template.substitute_structure(stage_cfg, TemplateConstants.DOUBLE_CURLY_BRACES, envconfig.get)
stage_cfg = Template.substitute_structure(stage_cfg, TemplateConstants.DOLLAR_PARENTHESES, envconfig.get)

# stage observations from R2D2 to COMIN_OBS and then link to analysis subdir
ufsda.stage.obs(stage_cfg)

################################################################################
# stage static files

logging.info(f"---------------- Stage static files")
ufsda.stage.soca_fix(stage_cfg)

################################################################################
# stage background error files

logging.info(f"---------------- Stage static files")
for domain in ['ocn', 'ice']:
    fname_stddev = find_bkgerr(pytz.utc.localize(window_begin, is_dst=None), domain=domain)
    fname_out = domain+'.bkgerr_stddev.incr.'+window_begin_iso+'.nc'
    ufsda.disk_utils.copyfile(fname_stddev, os.path.join(stage_cfg['stage_dir'], fname_out))

################################################################################
# prepare JEDI yamls

logging.info(f"---------------- Generate JEDI yaml files")

################################################################################
# link yaml for grid generation

gridgen_yaml = os.path.join(gdas_home,
                            'parm',
                            'soca',
                            'gridgen',
                            'gridgen.yaml')
ufsda.disk_utils.symlink(gridgen_yaml,
                         os.path.join(stage_cfg['stage_dir'], 'gridgen.yaml'))

################################################################################
# generate YAML file for parametric diag of B

berr_yaml = os.path.join(anl_dir, 'parametric_stddev_b.yaml')
berr_yaml_template = os.path.join(gdas_home,
                                  'parm',
                                  'soca',
                                  'berror',
                                  'parametric_stddev_b.yaml')
config = YAMLFile(path=berr_yaml_template)
config = Template.substitute_structure(config, TemplateConstants.DOUBLE_CURLY_BRACES, envconfig.get)
config = Template.substitute_structure(config, TemplateConstants.DOLLAR_PARENTHESES, envconfig.get)
config.save(berr_yaml)

################################################################################
# link yaml for decorrelation length scales

corscales_yaml = os.path.join(gdas_home,
                              'parm',
                              'soca',
                              'berror',
                              'soca_setcorscales.yaml')
ufsda.disk_utils.symlink(corscales_yaml,
                         os.path.join(stage_cfg['stage_dir'], 'soca_setcorscales.yaml'))

################################################################################
# generate yaml for bump/nicas (used for correlation and/or localization)

# TODO (Guillaume): move the possible vars somewhere else
vars3d = ['tocn', 'socn', 'uocn', 'vocn', 'chl', 'biop']
vars2d = ['ssh', 'cicen', 'hicen', 'hsnon', 'swh',
          'sw', 'lw', 'lw_rad', 'lhf', 'shf', 'us']

# 2d bump yaml (all 2d vars at once)
bumpdir = 'bump'
ufsda.disk_utils.mkdir(os.path.join(anl_dir, bumpdir))
bump_yaml = os.path.join(anl_dir, 'soca_bump2d.yaml')
bump_yaml_template = os.path.join(gdas_home,
                                  'parm',
                                  'soca',
                                  'berror',
                                  'soca_bump2d.yaml')
config = YAMLFile(path=bump_yaml_template)
config = Template.substitute_structure(config, TemplateConstants.DOUBLE_CURLY_BRACES, envconfig.get)
config = Template.substitute_structure(config, TemplateConstants.DOLLAR_PARENTHESES, envconfig.get)
config.save(bump_yaml)

# 3d bump yaml, 1 yaml per variable
# get list of DA variables
soca_vars = os.environ.get("SOCA_VARS").split(",")
for v in soca_vars:
    logging.info(f"creating the yaml to initialize bump for {v}")
    if v in vars2d:
        continue
    else:
        dim = '3d'
    bump_yaml = os.path.join(anl_dir, 'soca_bump'+dim+'_'+v+'.yaml')
    bump_yaml_template = os.path.join(gdas_home,
                                      'parm',
                                      'soca',
                                      'berror',
                                      'soca_bump_split.yaml')
    bumpdir = 'bump'+dim+'_'+v
    os.environ['BUMPDIR'] = bumpdir
    ufsda.disk_utils.mkdir(os.path.join(anl_dir, bumpdir))
    os.environ['CVAR'] = v
    config = YAMLFile(path=bump_yaml_template)
    config = Template.substitute_structure(config, TemplateConstants.DOUBLE_CURLY_BRACES, envconfig.get)
    config = Template.substitute_structure(config, TemplateConstants.DOLLAR_PARENTHESES, envconfig.get)
    config.save(bump_yaml)

################################################################################
# generate yaml for soca_var

var_yaml = os.path.join(anl_dir, 'var.yaml')
var_yaml_template = os.path.join(gdas_home,
                                 'parm',
                                 'soca',
                                 'variational',
                                 '3dvarfgat.yaml')
gen_bkg_list(bkg_path=os.getenv('COMIN_GES'),
             out_path=bkg_dir,
             window_begin=window_begin,
             yaml_name='bkg_list.yaml')
os.environ['BKG_LIST'] = 'bkg_list.yaml'

# select the SABER BLOCKS to use
if 'SABER_BLOCKS_YAML' in os.environ and os.environ['SABER_BLOCKS_YAML']:
    saber_blocks_yaml = os.getenv('SABER_BLOCKS_YAML')
    logging.info(f"using non-default SABER blocks yaml: {saber_blocks_yaml}")
else:
    logging.info(f"using default SABER blocks yaml")
    os.environ['SABER_BLOCKS_YAML'] = os.path.join(gdas_home, 'parm', 'soca', 'berror', 'saber_blocks.yaml')

logging.info(f"{config}")
varconfig = YAMLFile(path=var_yaml_template)
varconfig = Template.substitute_structure(varconfig, TemplateConstants.DOUBLE_CURLY_BRACES, config.get)
varconfig = Template.substitute_structure(varconfig, TemplateConstants.DOLLAR_PARENTHESES, config.get)
varconfig = Template.substitute_structure(varconfig, TemplateConstants.DOUBLE_CURLY_BRACES, envconfig.get)
varconfig = Template.substitute_structure(varconfig, TemplateConstants.DOLLAR_PARENTHESES, envconfig.get)
varconfig.save(var_yaml)

################################################################################
# prepare yaml and CICE restart for soca to cice change of variable

# make a copy of the CICE6 restart
rst_date = fcst_begin.strftime('%Y%m%d.%H%M%S')
ice_rst = os.path.join(os.getenv('COMIN_GES'), '..', 'ice', 'RESTART',
                       rst_date+'.cice_model.res.nc')
ice_rst_ana = os.path.join('Data', rst_date+'.cice_model.res.nc')
ufsda.disk_utils.copyfile(ice_rst, ice_rst_ana)

# write the two seaice analysis to model change of variable yamls
varchgyamls = ['soca_2cice_arctic.yaml', 'soca_2cice_antarctic.yaml']
soca2cice_cfg = {
    "template": "",
    "output": "",
    "config": {
        "OCN_ANA": "./Data/ocn.3dvarfgat_pseudo.an."+window_begin_iso+".nc",
        "ICE_ANA": "./Data/ice.3dvarfgat_pseudo.an."+window_begin_iso+".nc",
        "ICE_RST": ice_rst_ana,
        "FCST_BEGIN": fcst_begin.strftime('%Y-%m-%dT%H:%M:%SZ')
    }
}
varchgyamls = ['soca_2cice_arctic.yaml', 'soca_2cice_antarctic.yaml']
for varchgyaml in varchgyamls:
    soca2cice_cfg['template'] = os.path.join(gdas_home, 'parm', 'soca', 'varchange', varchgyaml)
    f = open('tmp.yaml', 'w')
    yaml.dump(soca2cice_cfg, f, sort_keys=False, default_flow_style=False)
    ufsda.genYAML.genYAML('tmp.yaml', output=varchgyaml)

################################################################################
# links of convenience
mom_ic = glob.glob(os.path.join(bkg_dir, 'gdas.*.ocnf003.nc'))[0]
ufsda.disk_utils.symlink(mom_ic, os.path.join(anl_dir, 'INPUT', 'MOM.res.nc'))

cice_ic = glob.glob(os.path.join(bkg_dir, 'gdas.*.agg_icef003.nc'))[0]
ufsda.disk_utils.symlink(cice_ic, os.path.join(anl_dir, 'INPUT', 'cice.res.nc'))

################################################################################
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
