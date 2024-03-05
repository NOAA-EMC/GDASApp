#!/usr/bin/env python3
# Script name:         exufsda_global_marine_analysis_prep.py
# Script description:  Stages files and generates YAML for UFS Global Marine Analysis

# import os to add ush to path
import os
import glob
import dateutil.parser as dparser
import f90nml
from soca import bkg_utils
from datetime import datetime, timedelta
import pytz
from wxflow import (Logger, Template, TemplateConstants, YAMLFile, FileHandler)

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


################################################################################
# runtime environment variables, create directories

logger.info(f"---------------- Setup runtime environement")

comin_obs = os.getenv('COMIN_OBS')
anl_dir = os.getenv('DATA')
staticsoca_dir = os.getenv('SOCA_INPUT_FIX_DIR')
if os.getenv('DOHYBVAR') == "YES":
    dohybvar = True
    nmem_ens = int(os.getenv('NMEM_ENS'))
else:
    dohybvar = False

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
fcst_begin = datetime.strptime(os.getenv('PDY')+os.getenv('cyc'), '%Y%m%d%H')
RUN = os.getenv('RUN')
cyc = os.getenv('cyc')
gcyc = os.getenv('gcyc')
PDY = os.getenv('PDY')

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


################################################################################
# stage ensemble members
if dohybvar:
    logger.info("---------------- Stage ensemble members")
    nmem_ens = int(os.getenv('NMEM_ENS'))
    ens_member_list = []
    for mem in range(1, nmem_ens+1):
        for domain in ['ocean', 'ice']:
            # TODO(Guillaume): make use and define ensemble COM in the j-job
            ensroot = os.getenv('COM_OCEAN_HISTORY_PREV')
            ensdir = os.path.join(os.getenv('COM_OCEAN_HISTORY_PREV'), '..', '..', '..', '..', '..',
                                  f'enkf{RUN}.{PDY}', f'{gcyc}', f'mem{str(mem).zfill(3)}',
                                  'model_data', domain, 'history')
            ensdir_real = os.path.realpath(ensdir)
            f009 = f'enkfgdas.{domain}.t{gcyc}z.inst.f009.nc'

            fname_in = os.path.abspath(os.path.join(ensdir_real, f009))
            fname_out = os.path.realpath(os.path.join(static_ens, domain+"."+str(mem)+".nc"))
            ens_member_list.append([fname_in, fname_out])
    FileHandler({'copy': ens_member_list}).sync()

    # reformat the cice history output
    for mem in range(1, nmem_ens+1):
        cice_fname = os.path.realpath(os.path.join(static_ens, "ice."+str(mem)+".nc"))
        bkg_utils.cice_hist2fms(cice_fname, cice_fname)

# Commented out while testing the parametric diagb
#else:
#    logger.info("---------------- Stage offline ensemble members")
#    ens_member_list = []
#    clim_ens_dir = find_clim_ens(pytz.utc.localize(window_begin, is_dst=None))
#    nmem_ens = len(glob.glob(os.path.abspath(os.path.join(clim_ens_dir, 'ocn.*.nc'))))
#    for domain in ['ocn', 'ice']:
#        for mem in range(1, nmem_ens+1):
#            fname = domain+"."+str(mem)+".nc"
#            fname_in = os.path.abspath(os.path.join(clim_ens_dir, fname))
#            fname_out = os.path.abspath(os.path.join(static_ens, fname))
#            ens_member_list.append([fname_in, fname_out])
#    FileHandler({'copy': ens_member_list}).sync()
os.environ['ENS_SIZE'] = str(nmem_ens)

################################################################################
# prepare JEDI yamls

logger.info(f"---------------- Generate JEDI yaml files")

################################################################################
# copy yaml for grid generation

logger.info(f"---------------- generate gridgen.yaml")
gridgen_yaml_src = os.path.realpath(os.path.join(gdas_home, 'parm', 'soca', 'gridgen', 'gridgen.yaml'))
gridgen_yaml_dst = os.path.realpath(os.path.join(stage_cfg['stage_dir'], 'gridgen.yaml'))
FileHandler({'copy': [[gridgen_yaml_src, gridgen_yaml_dst]]}).sync()

################################################################################
# generate the YAML file for the post processing of the clim. ens. B
berror_yaml_dir = os.path.join(gdas_home, 'parm', 'soca', 'berror')

logger.info(f"---------------- generate soca_diagb.yaml")
diagb_yaml = os.path.join(anl_dir, 'soca_diagb.yaml')
diagb_yaml_template = os.path.join(berror_yaml_dir, 'soca_diagb.yaml')
config = YAMLFile(path=diagb_yaml_template)
config = Template.substitute_structure(config, TemplateConstants.DOUBLE_CURLY_BRACES, envconfig.get)
config = Template.substitute_structure(config, TemplateConstants.DOLLAR_PARENTHESES, envconfig.get)
config.save(diagb_yaml)

logger.info(f"---------------- generate soca_ensb.yaml")
berr_yaml = os.path.join(anl_dir, 'soca_ensb.yaml')
berr_yaml_template = os.path.join(berror_yaml_dir, 'soca_ensb.yaml')
config = YAMLFile(path=berr_yaml_template)
config = Template.substitute_structure(config, TemplateConstants.DOUBLE_CURLY_BRACES, envconfig.get)
config.save(berr_yaml)

logger.info(f"---------------- generate soca_ensweights.yaml")
berr_yaml = os.path.join(anl_dir, 'soca_ensweights.yaml')
berr_yaml_template = os.path.join(berror_yaml_dir, 'soca_ensweights.yaml')
config = YAMLFile(path=berr_yaml_template)
config = Template.substitute_structure(config, TemplateConstants.DOUBLE_CURLY_BRACES, envconfig.get)
config.save(berr_yaml)

################################################################################
# copy yaml for localization length scales

logger.info(f"---------------- generate soca_setlocscales.yaml")
locscales_yaml_src = os.path.join(gdas_home, 'parm', 'soca', 'berror', 'soca_setlocscales.yaml')
locscales_yaml_dst = os.path.join(stage_cfg['stage_dir'], 'soca_setlocscales.yaml')
FileHandler({'copy': [[locscales_yaml_src, locscales_yaml_dst]]}).sync()

################################################################################
# copy yaml for correlation length scales

logger.info(f"---------------- generate soca_setcorscales.yaml")
corscales_yaml_src = os.path.join(gdas_home, 'parm', 'soca', 'berror', 'soca_setcorscales.yaml')
corscales_yaml_dst = os.path.join(stage_cfg['stage_dir'], 'soca_setcorscales.yaml')
FileHandler({'copy': [[corscales_yaml_src, corscales_yaml_dst]]}).sync()

################################################################################
# copy yaml for diffusion initialization

logger.info(f"---------------- generate soca_parameters_diffusion_hz.yaml")
diffu_hz_yaml = os.path.join(anl_dir, 'soca_parameters_diffusion_hz.yaml')
diffu_hz_yaml_dir = os.path.join(gdas_home, 'parm', 'soca', 'berror')
diffu_hz_yaml_template = os.path.join(berror_yaml_dir, 'soca_parameters_diffusion_hz.yaml')
config = YAMLFile(path=diffu_hz_yaml_template)
config = Template.substitute_structure(config, TemplateConstants.DOUBLE_CURLY_BRACES, envconfig.get)
config.save(diffu_hz_yaml)

logger.info(f"---------------- generate soca_parameters_diffusion_vt.yaml")
diffu_vt_yaml = os.path.join(anl_dir, 'soca_parameters_diffusion_vt.yaml')
diffu_vt_yaml_dir = os.path.join(gdas_home, 'parm', 'soca', 'berror')
diffu_vt_yaml_template = os.path.join(berror_yaml_dir, 'soca_parameters_diffusion_vt.yaml')
config = YAMLFile(path=diffu_vt_yaml_template)
config = Template.substitute_structure(config, TemplateConstants.DOUBLE_CURLY_BRACES, envconfig.get)
config.save(diffu_vt_yaml)

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

# select the SABER BLOCKS to use
if 'SABER_BLOCKS_YAML' in os.environ and os.environ['SABER_BLOCKS_YAML']:
    saber_blocks_yaml = os.getenv('SABER_BLOCKS_YAML')
    logger.info(f"using non-default SABER blocks yaml: {saber_blocks_yaml}")
else:
    logger.info(f"using default SABER blocks yaml")
    os.environ['SABER_BLOCKS_YAML'] = os.path.join(gdas_home, 'parm', 'soca', 'berror', 'saber_blocks.yaml')

# substitute templated variables in the var config
logger.info(f"{config}")
varconfig = YAMLFile(path=var_yaml_template)
varconfig = Template.substitute_structure(varconfig, TemplateConstants.DOUBLE_CURLY_BRACES, config.get)
varconfig = Template.substitute_structure(varconfig, TemplateConstants.DOLLAR_PARENTHESES, config.get)
varconfig = Template.substitute_structure(varconfig, TemplateConstants.DOUBLE_CURLY_BRACES, envconfig.get)
varconfig = Template.substitute_structure(varconfig, TemplateConstants.DOLLAR_PARENTHESES, envconfig.get)

# Remove empty obs spaces in var_yaml
ufsda.yamltools.save_check(varconfig.as_dict(), target=var_yaml, app='var')

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
ics_list = []
GDUMP = os.getenv('GDUMP')
# ocean IC's
mom_ic_src = glob.glob(os.path.join(bkg_dir, f'{GDUMP}.ocean.*.inst.f003.nc'))[0]
mom_ic_dst = os.path.join(anl_dir, 'INPUT', 'MOM.res.nc')
ics_list.append([mom_ic_src, mom_ic_dst])

# seaice IC's
cice_ic_src = glob.glob(os.path.join(bkg_dir, f'{GDUMP}.agg_ice.*.inst.f003.nc'))[0]
cice_ic_dst = os.path.join(anl_dir, 'INPUT', 'cice.res.nc')
ics_list.append([cice_ic_src, cice_ic_dst])
FileHandler({'copy': ics_list}).sync()

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
