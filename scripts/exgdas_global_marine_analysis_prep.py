#!/usr/bin/env python3
# Script name:         exufsda_global_marine_analysis_prep.py
# Script description:  Stages files and generates YAML for UFS Global Marine Analysis

# import os to add ush to path
import copy
import os
import glob
import dateutil.parser as dparser
import f90nml
from soca import bkg_utils
from datetime import datetime, timedelta
import pytz
import re
import yaml

from jcb import render
from wxflow import (Logger, Template, TemplateConstants,
                    YAMLFile, FileHandler)

logger = Logger()

# get absolute path of ush/ directory either from env or relative to this file
my_dir = os.path.dirname(__file__)
my_home = os.path.dirname(os.path.dirname(my_dir))
gdas_home = os.path.join(os.getenv('HOMEgfs'), 'sorc', 'gdas.cd')

# import UFSDA utilities
import ufsda
from ufsda.stage import soca_fix


def nearest_date(strings, input_date):
    closest_str = ""
    closest_diff = float("inf")
    for string in strings:
        file_date = dparser.parse(os.path.basename(string), fuzzy=True)
        file_date = file_date.replace(year=input_date.year)
        diff = abs((file_date - input_date).total_seconds())
        if diff < closest_diff:
            closest_str = string
            closest_diff = diff

    return closest_str


def find_bkgerr(input_date, domain):
    """
    Find the std. dev. files that are the closest to the DA window
    """
    bkgerror_dir = os.path.join(os.getenv('SOCA_INPUT_FIX_DIR'), 'bkgerr', 'stddev')
    files = glob.glob(os.path.join(bkgerror_dir, domain+'.ensstddev.fc.*.nc'))

    return nearest_date(files, input_date)


def find_clim_ens(input_date):
    """
    Find the clim. ens. that is the closest to the DA window
    """
    ens_clim_dir = os.path.join(os.getenv('SOCA_INPUT_FIX_DIR'), 'bkgerr', 'ens')
    dirs = glob.glob(os.path.join(ens_clim_dir, '*'))

    return nearest_date(dirs, input_date)


def parse_obs_list_file():
    # Get the list of observation types from the obs_list.yaml
    obs_list_path = os.path.join(gdas_home, 'parm', 'soca', 'obs', 'obs_list.yaml')
    obs_types = []
    with open(obs_list_path, 'r') as file:
        for line in file:
            # Remove leading/trailing whitespace and check if the line is uncommented
            line = line.strip()
            if line.startswith('- !INC') and not line.startswith('#'):
                # Extract the type using regex
                match = re.search(r'\$\{OBS_YAML_DIR\}/(.+)\.yaml', line)
                if match:
                    obs_types.append(str(match.group(1)))
    return obs_types

################################################################################
# runtime environment variables, create directories


logger.info(f"---------------- Setup runtime environement")

anl_dir = os.getenv('DATA')
staticsoca_dir = os.getenv('SOCA_INPUT_FIX_DIR')
nmem_ens = 0
nmem_ens = int(os.getenv('NMEM_ENS'))

# create analysis directories
diags = os.path.join(anl_dir, 'diags')            # output dir for soca DA obs space
obs_in = os.path.join(anl_dir, 'obs')             # input      "           "
bkg_dir = os.path.join(anl_dir, 'bkg')            # ice and ocean backgrounds
anl_out = os.path.join(anl_dir, 'Data')           # output dir for soca DA
static_ens = os.path.join(anl_dir, 'static_ens')  # clim. ens.
FileHandler({'mkdir': [anl_dir, diags, obs_in, bkg_dir, anl_out, static_ens]}).sync()

# Variables of convenience
half_assim_freq = timedelta(hours=int(os.getenv('assim_freq'))/2)
window_middle = datetime.strptime(os.getenv('PDY')+os.getenv('cyc'), '%Y%m%d%H')
window_begin = datetime.strptime(os.getenv('PDY')+os.getenv('cyc'), '%Y%m%d%H') - half_assim_freq
window_begin_iso = window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')
window_middle_iso = window_middle.strftime('%Y-%m-%dT%H:%M:%SZ')
RUN = os.getenv('RUN')
cyc = os.getenv('cyc')
gcyc = os.getenv('gcyc')
PDY = os.getenv('PDY')

# hybrid-envar switch
if os.getenv('DOHYBVAR') == "YES":
    dohybvar = True
else:
    dohybvar = False

# switch for the cycling type
if os.getenv('DOIAU') == "YES":
    # forecast initialized at the begining of the DA window
    fcst_begin = window_begin
else:
    # forecast initialized at the middle of the DA window
    fcst_begin = datetime.strptime(os.getenv('PDY')+os.getenv('cyc'), '%Y%m%d%H')

################################################################################
# fetch observations

logger.info(f"---------------- Stage observations")

# create config dict from runtime env
envconfig = {'window_begin': f"{window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')}",
             'ATM_WINDOW_BEGIN': window_begin_iso,
             'ATM_WINDOW_MIDDLE': window_middle_iso,
             'ATM_WINDOW_LENGTH': f"PT{os.getenv('assim_freq')}H",
             'gcyc': gcyc,
             'RUN': RUN}
stage_cfg = YAMLFile(path=os.path.join(gdas_home, 'parm', 'templates', 'stage.yaml'))
stage_cfg = Template.substitute_structure(stage_cfg, TemplateConstants.DOUBLE_CURLY_BRACES, envconfig.get)
stage_cfg = Template.substitute_structure(stage_cfg, TemplateConstants.DOLLAR_PARENTHESES, envconfig.get)

# get the list of observations
obs_files = []
for ob in stage_cfg['observations']['observers']:
    obs_files.append(f"{RUN}.t{cyc}z.{ob['obs space']['name'].lower()}.{PDY}{cyc}.nc4")
obs_list = []

# copy obs from COM_OBS to DATA/obs
for obs_file in obs_files:
    logger.info(f"******* {obs_file}")
    obs_src = os.path.join(os.getenv('COM_OBS'), obs_file)
    obs_dst = os.path.join(os.path.realpath(obs_in), obs_file)
    logger.info(f"******* {obs_src}")
    if os.path.exists(obs_src):
        logger.info(f"******* fetching {obs_file}")
        obs_list.append([obs_src, obs_dst])
    else:
        logger.info(f"******* {obs_file} is not in the database")

FileHandler({'copy': obs_list}).sync()

################################################################################
# stage static files
logger.info(f"---------------- Stage static files")
ufsda.stage.soca_fix(stage_cfg)

# copy obsop_name_map.yaml and fields_metadata.yaml
io_yaml_path = os.path.join(gdas_home, 'parm', 'soca')
io_yaml_list = []
for io_yaml in ['obsop_name_map.yaml', 'fields_metadata.yaml']:
    io_yaml_list.append([os.path.join(io_yaml_path, io_yaml),
                         os.path.join(anl_dir, io_yaml)])
FileHandler({'copy': io_yaml_list}).sync()


################################################################################
# stage ensemble members
if dohybvar or nmem_ens >= 3:
    # TODO: No symlink allowed but this script will be refactored soon
    # Relative path to ensemble perturbations
    ens_perturbations = os.path.join('..', f'gdasmarinebmat.{PDY}{cyc}', 'enspert', 'ens')
    os.symlink(ens_perturbations, 'ens')

################################################################################
# prepare JEDI yamls
os.environ['ENS_SIZE'] = str(nmem_ens)
logger.info(f"---------------- Generate JEDI yaml files")

################################################################################
# Stage the soca grid
src = os.path.join(os.getenv('COMIN_OCEAN_BMATRIX'), 'soca_gridspec.nc')
dst = os.path.join(anl_dir, 'soca_gridspec.nc')
FileHandler({'copy': [[src, dst]]}).sync()

################################################################################
# stage the static B-matrix
bmat_list = []
# Diagonal of the B matrix
bmat_list.append([os.path.join(os.getenv('COMIN_OCEAN_BMATRIX'), f"{RUN}.t{cyc}z.ocean.bkgerr_stddev.nc"),
                  os.path.join(anl_dir, "ocean.bkgerr_stddev.nc")])
bmat_list.append([os.path.join(os.getenv('COMIN_ICE_BMATRIX'), f"{RUN}.t{cyc}z.ice.bkgerr_stddev.nc"),
                  os.path.join(anl_dir, "ice.bkgerr_stddev.nc")])
# Correlation operator
bmat_list.append([os.path.join(os.getenv('COMIN_ICE_BMATRIX'), f"{RUN}.t{cyc}z.hz_ice.nc"),
                  os.path.join(anl_dir, "hz_ice.nc")])
bmat_list.append([os.path.join(os.getenv('COMIN_OCEAN_BMATRIX'), f"{RUN}.t{cyc}z.hz_ocean.nc"),
                  os.path.join(anl_dir, "hz_ocean.nc")])
bmat_list.append([os.path.join(os.getenv('COMIN_OCEAN_BMATRIX'), f"{RUN}.t{cyc}z.vt_ocean.nc"),
                  os.path.join(anl_dir, "vt_ocean.nc")])
FileHandler({'copy': bmat_list}).sync()

################################################################################
# stage the ens B-matrix weights
if dohybvar or nmem_ens >= 3:
    ensbmat_list = []
    ensbmat_list.append([os.path.join(os.getenv('COMIN_OCEAN_BMATRIX'), f"{RUN}.t{cyc}z.ocean.ens_weights.nc"),
                         os.path.join(anl_dir, "ocean.ens_weights.nc")])
    ensbmat_list.append([os.path.join(os.getenv('COMIN_ICE_BMATRIX'), f"{RUN}.t{cyc}z.ice.ens_weights.nc"),
                         os.path.join(anl_dir, "ice.ens_weights.nc")])
    FileHandler({'copy': ensbmat_list}).sync()

################################################################################
# generate yaml for soca_var

logger.info(f"---------------- generate var.yaml")
var_yaml = os.path.join(anl_dir, 'var.yaml')
var_yaml_template = os.path.join(gdas_home,
                                 'parm',
                                 'soca',
                                 'variational',
                                 '3dvarfgat.yaml')
bkg_utils.gen_bkg_list(bkg_path=os.getenv('COM_OCEAN_HISTORY_PREV'),
                       out_path=bkg_dir,
                       window_begin=window_begin,
                       yaml_name='bkg_list.yaml')
os.environ['BKG_LIST'] = 'bkg_list.yaml'

# select the B-matrix to use
if nmem_ens > 3:
    # Use a hybrid static-ensemble B
    os.environ['SABER_BLOCKS_YAML'] = os.path.join(gdas_home, 'parm', 'soca', 'berror', 'soca_hybrid_bmat.yaml')
else:
    # Use a static B
    os.environ['SABER_BLOCKS_YAML'] = os.path.join(gdas_home, 'parm', 'soca', 'berror', 'soca_static_bmat.yaml')

# substitute templated variables in the var config
logger.info(f"{envconfig}")
varconfig = YAMLFile(path=var_yaml_template)
varconfig = Template.substitute_structure(varconfig, TemplateConstants.DOUBLE_CURLY_BRACES, envconfig.get)
varconfig = Template.substitute_structure(varconfig, TemplateConstants.DOLLAR_PARENTHESES, envconfig.get)
varconfig = Template.substitute_structure(varconfig, TemplateConstants.DOUBLE_CURLY_BRACES, envconfig.get)
varconfig = Template.substitute_structure(varconfig, TemplateConstants.DOLLAR_PARENTHESES, envconfig.get)

# Remove empty obs spaces in var_yaml
ufsda.yamltools.save_check(varconfig, target=var_yaml, app='var')

# Produce JEDI YAML file using JCB (for demonstration purposes)
# -------------------------------------------------------------
"""
# Make a copy of the env config before modifying to avoid breaking something else
envconfig_jcb = copy.deepcopy(envconfig)

# Add the things to the envconfig in order to template JCB files
envconfig_jcb['PARMgfs'] = os.getenv('PARMgfs')
envconfig_jcb['nmem_ens'] = nmem_ens
envconfig_jcb['berror_model'] = 'marine_background_error_static_diffusion'
if nmem_ens > 3:
    envconfig_jcb['berror_model'] = 'marine_background_error_hybrid_diffusion_diffusion'
envconfig_jcb['DATA'] = os.getenv('DATA')
envconfig_jcb['OPREFIX'] = os.getenv('OPREFIX')
envconfig_jcb['PDY'] = os.getenv('PDY')
envconfig_jcb['cyc'] = os.getenv('cyc')
envconfig_jcb['SOCA_NINNER'] = os.getenv('SOCA_NINNER')
envconfig_jcb['obs_list'] = ['adt_rads_all']

# Write obs_list_short
with open('obs_list_short.yaml', 'w') as file:
    yaml.dump(parse_obs_list_file(), file, default_flow_style=False)
os.environ['OBS_LIST_SHORT'] = 'obs_list_short.yaml'

# Render the JCB configuration files
jcb_base_yaml = os.path.join(gdas_home, 'parm', 'soca', 'marine-jcb-base.yaml')
jcb_algo_yaml = os.path.join(gdas_home, 'parm', 'soca', 'marine-jcb-3dfgat.yaml.j2')

jcb_base_config = YAMLFile(path=jcb_base_yaml)
jcb_base_config = Template.substitute_structure(jcb_base_config, TemplateConstants.DOUBLE_CURLY_BRACES, envconfig_jcb.get)
jcb_base_config = Template.substitute_structure(jcb_base_config, TemplateConstants.DOLLAR_PARENTHESES, envconfig_jcb.get)
jcb_algo_config = YAMLFile(path=jcb_algo_yaml)
jcb_algo_config = Template.substitute_structure(jcb_algo_config, TemplateConstants.DOUBLE_CURLY_BRACES, envconfig_jcb.get)
jcb_algo_config = Template.substitute_structure(jcb_algo_config, TemplateConstants.DOLLAR_PARENTHESES, envconfig_jcb.get)

# Override base with the application specific config
jcb_config = {**jcb_base_config, **jcb_algo_config}

# Render the full JEDI configuration file using JCB
jedi_config = render(jcb_config)

# Save the JEDI configuration file
var_yaml_jcb = os.path.join(anl_dir, 'var-jcb.yaml')
ufsda.yamltools.save_check(jedi_config, target=var_yaml_jcb, app='var')
"""

################################################################################
# Prepare the yamls for the "checkpoint" jjob
# prepare yaml and CICE restart for soca to cice change of variable

logger.info(f"---------------- generate soca to cice yamls")
# make a copy of the CICE6 restart
rst_date = fcst_begin.strftime('%Y%m%d.%H%M%S')
ice_rst = os.path.join(os.getenv('COM_ICE_RESTART_PREV'), f'{rst_date}.cice_model.res.nc')
ice_rst_ana = os.path.join(anl_out, rst_date+'.cice_model.res.nc')
FileHandler({'copy': [[ice_rst, ice_rst_ana]]}).sync()

# write the two seaice analysis to model change of variable yamls
varchgyamls = ['soca_2cice_arctic.yaml', 'soca_2cice_antarctic.yaml']
soca2cice_cfg = {
    "OCN_ANA": "./Data/ocn.3dvarfgat_pseudo.an."+window_middle_iso+".nc",
    "ICE_ANA": "./Data/ice.3dvarfgat_pseudo.an."+window_middle_iso+".nc",
    "ICE_RST": ice_rst_ana,
    "FCST_BEGIN": fcst_begin.strftime('%Y-%m-%dT%H:%M:%SZ')
}
varchgyamls = ['soca_2cice_arctic.yaml', 'soca_2cice_antarctic.yaml']
for varchgyaml in varchgyamls:
    soca2cice_cfg_template = os.path.join(gdas_home, 'parm', 'soca', 'varchange', varchgyaml)
    outyaml = YAMLFile(path=soca2cice_cfg_template)
    outyaml = Template.substitute_structure(outyaml, TemplateConstants.DOLLAR_PARENTHESES, soca2cice_cfg.get)
    outyaml.save(varchgyaml)

# prepare yaml for soca to MOM6 IAU increment
logger.info(f"---------------- generate soca to MOM6 IAU yaml")
socaincr2mom6_yaml = os.path.join(anl_dir, 'socaincr2mom6.yaml')
socaincr2mom6_yaml_template = os.path.join(gdas_home, 'parm', 'soca', 'variational', 'socaincr2mom6.yaml')
s2mconfig = YAMLFile(path=socaincr2mom6_yaml_template)
s2mconfig = Template.substitute_structure(s2mconfig, TemplateConstants.DOUBLE_CURLY_BRACES, envconfig.get)
s2mconfig.save(socaincr2mom6_yaml)

################################################################################
# Copy initial condition

bkg_utils.stage_ic(bkg_dir, anl_dir, gcyc)

################################################################################
# prepare input.nml
mom_input_nml_src = os.path.join(gdas_home, 'parm', 'soca', 'fms', 'input.nml')
mom_input_nml_tmpl = os.path.join(stage_cfg['stage_dir'], 'mom_input.nml.tmpl')
mom_input_nml = os.path.join(stage_cfg['stage_dir'], 'mom_input.nml')
FileHandler({'copy': [[mom_input_nml_src, mom_input_nml_tmpl]]}).sync()

# swap date and stack size
domain_stack_size = os.getenv('DOMAIN_STACK_SIZE')
ymdhms = [int(s) for s in window_begin.strftime('%Y,%m,%d,%H,%M,%S').split(',')]
with open(mom_input_nml_tmpl, 'r') as nml_file:
    nml = f90nml.read(nml_file)
    nml['ocean_solo_nml']['date_init'] = ymdhms
    nml['fms_nml']['domains_stack_size'] = int(domain_stack_size)
    ufsda.disk_utils.removefile(mom_input_nml)
    nml.write(mom_input_nml)
