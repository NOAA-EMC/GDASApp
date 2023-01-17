#!/usr/bin/env python3
import argparse
import datetime as dt
import logging
import os
import re
import subprocess
import sys
import yaml

from pygw.template import Template, TemplateConstants
from pygw.yaml_file import YAMLFile


def export_envar(yamlfile, bashout):

    # open YAML file to get config
    f = open(yamlfile, "r")
    envar_dict = yaml.safe_load(f)

    # open up a file for writing
    f = open(bashout, 'w')
    f.write('#!/bin/bash\n')

    # Loop through variables
    for v in envar_dict:
        batch = f"""export {v}={envar_dict[v]}\n"""
        f.write(batch)


def run_jedi_exe(yamlconfig):
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    # open YAML file to get config
    try:
        with open(yamlconfig, 'r') as yamlconfig_opened:
            all_config_dict = yaml.safe_load(yamlconfig_opened)
        logging.info(f'Loading configuration from {yamlconfig}')
    except Exception as e:
        logging.error(f'Error occurred when attempting to load: {yamlconfig}, error: {e}')

    # check if the specified app mode is valid
    app_mode = all_config_dict['GDASApp mode']
    supported_app_modes = ['hofx', 'variational', 'gw_scripts']
    if app_mode not in supported_app_modes:
        raise KeyError(f"'{app_mode}' not supported. " +
                       "Current GDASApp modes supported are: " +
                       f"{' | '.join(supported_app_modes)}")

    # create working directory
    workdir = all_config_dict['working directory']
    try:
        os.makedirs(workdir, exist_ok=True)
        logging.info(f'Created working directory {workdir}')
    except OSError as error:
        logging.error(f'Error creating {workdir}: {error}')

    # add your ufsda python package to path
    ufsda_path = os.path.join(all_config_dict['GDASApp home'], 'ush')
    sys.path.append(ufsda_path)
    import ufsda
    from ufsda.misc_utils import calc_fcst_steps

    # compute config for YAML for executable
    executable_subconfig = all_config_dict['config']
    valid_time = executable_subconfig['valid_time']
    assim_freq = int(executable_subconfig.get('assim_freq', 6))
    h = re.findall('PT(\\d+)H', executable_subconfig['atm_window_length'])[0]
    prev_cycle = valid_time - dt.timedelta(hours=int(h))
    window_begin = valid_time - dt.timedelta(hours=int(h)/2)
    cyc = valid_time.strftime("%H")
    cdate = valid_time.strftime("%Y%m%d%H")
    gcyc = prev_cycle.strftime("%H")
    gdate = prev_cycle.strftime("%Y%m%d%H")
    pdy = valid_time.strftime("%Y%m%d")
    os.environ['PDY'] = str(pdy)
    os.environ['cyc'] = str(cyc)
    os.environ['assim_freq'] = str(assim_freq)
    oprefix = executable_subconfig['dump'] + ".t" + str(cyc) + "z."
    gprefix = executable_subconfig['dump'] + ".t" + str(gcyc) + "z."

    if app_mode in ['hofx', 'variational']:
        single_exec = True
        var_config = {
            'DATA': os.path.join(workdir),
            'APREFIX': str(oprefix),
            'OPREFIX': str(oprefix),
            'GPREFIX': str(gprefix),
            'BERROR_YAML': executable_subconfig.get('berror_yaml', './'),
            'STATICB_TYPE': executable_subconfig.get('staticb_type', 'gsibec'),
            'OBS_YAML_DIR': executable_subconfig['obs_yaml_dir'],
            'OBS_LIST': executable_subconfig['obs_list'],
            'atm': executable_subconfig.get('atm', False),
            'layout_x': str(executable_subconfig['layout_x']),
            'layout_y': str(executable_subconfig['layout_y']),
            'BKG_DIR': os.path.join(workdir, 'bkg'),
            'fv3jedi_fix_dir': os.path.join(workdir, 'fv3jedi'),
            'fv3jedi_fieldmetadata_dir': os.path.join(workdir, 'fv3jedi'),
            'ANL_DIR': os.path.join(workdir, 'anl'),
            'fv3jedi_staticb_dir': os.path.join(workdir, 'berror'),
            'BIAS_IN_DIR': os.path.join(workdir, 'obs'),
            'BIAS_OUT_DIR': os.path.join(workdir, 'bc'),
            'CRTM_COEFF_DIR': os.path.join(workdir, 'crtm'),
            'BIAS_PREFIX': f"{executable_subconfig['dump']}.t{gcyc}z.",
            'BIAS_DATE': f"{gdate}",
            'DIAG_DIR': os.path.join(workdir, 'diags'),
            'OBS_DIR': os.path.join(workdir, 'obs'),
            'OBS_PREFIX': f"{executable_subconfig['dump']}.t{cyc}z.",
            'OBS_DATE': f"{cdate}",
            'CDATE': f"{cdate}",
            'GDATE': f"{gdate}",
            'valid_time': f"{valid_time.strftime('%Y-%m-%dT%H:%M:%SZ')}",
            'window_begin': f"{window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')}",
            'prev_valid_time': f"{prev_cycle.strftime('%Y-%m-%dT%H:%M:%SZ')}",
            'atm_window_length': executable_subconfig['atm_window_length'],
            'CASE': executable_subconfig['case'],
            'CASE_ANL': executable_subconfig.get('case_anl', executable_subconfig['case']),
            'CASE_ENKF': executable_subconfig.get('case_enkf', executable_subconfig['case']),
            'DOHYBVAR': executable_subconfig.get('dohybvar', False),
            'LEVS': str(executable_subconfig['levs']),
            'NMEM_ENKF': str(executable_subconfig['nmem']),
            'forecast_steps': calc_fcst_steps(executable_subconfig.get('forecast_step', 'PT6H'),
                                              executable_subconfig['atm_window_length']),
            'BKG_TSTEP': executable_subconfig.get('forecast_step', 'PT6H'),
            'INTERP_METHOD': executable_subconfig.get('interp_method', 'barycentric'),
        }
        output_file = os.path.join(workdir, f"gdas_{app_mode}.yaml")
        # set some environment variables
        os.environ['PARMgfs'] = os.path.join(all_config_dict['GDASApp home'], 'parm')
        for key, value in var_config.items():
            os.environ[key] = str(value)
        # generate YAML for executable based on input config
        logging.info(f'Using yamlconfig {yamlconfig}')
        genYAML(yamlconfig, output_file)
        logging.info(f'Wrote YAML file to {output_file}')
        # use R2D2 to stage backgrounds, obs, bias correction files, etc.
        ufsda.stage.gdas_single_cycle(var_config)
        # link additional fix files needed (CRTM, fieldmetadata, etc.)
        gdasfix = executable_subconfig['gdas_fix_root']
        ufsda.stage.gdas_fix(gdasfix, workdir, var_config)
        # link executable
        baseexe = os.path.basename(executable_subconfig['executable'])
        ufsda.disk_utils.symlink(executable_subconfig['executable'], os.path.join(workdir, baseexe))
        # create output directories
        ufsda.disk_utils.mkdir(os.path.join(workdir, 'diags'))
        if app_mode in ['variational']:
            ufsda.disk_utils.mkdir(os.path.join(workdir, 'anl'))
            ufsda.disk_utils.mkdir(os.path.join(workdir, 'bc'))
        baseexe = os.path.join(workdir, baseexe)
    else:
        baseexe = ''
        output_file = ''
        single_exec = False
        gdasapp_home = os.path.join(all_config_dict['GDASApp home'])
        gdasapp_bin = os.path.join(gdasapp_home, 'build', 'bin')
        homegfs = os.path.join(workdir, 'HOMEgfs')
        aprun_socaanal = all_config_dict['job options']['mpiexec']+' '+str(all_config_dict['job options']['ntasks'])
        comin_ges_src = os.path.join(all_config_dict['model backgrounds']['ocn'], 'RESTART')
        ufsda.disk_utils.mkdir(os.path.join(workdir, 'RESTART'))
        ufsda.disk_utils.copytree(comin_ges_src, os.path.join(workdir, 'RESTART'))

        runtime_envar = {
            'CDATE': cdate,
            'GDATE': gdate,
            'gcyc': gcyc,
            'PDY': pdy,
            'cyc': cyc,
            'assim_freq': '6',
            'COMOUT': workdir,
            'DATA': os.path.join(workdir, 'analysis'),
            'COMIN_OBS': all_config_dict['r2d2 options']['root'],
            'COMIN_GES': all_config_dict['model backgrounds']['ocn'],
            'CDUMP': 'gdas',
            'GDUMP': 'gdas',
            'CASE_ANL': "C48",
            'CASE': 'C48',
            'DOHYBVAR': 'False',
            'CASE_ENKF': "C192",
            'LEVS': '75',
            'OBS_YAML_DIR': executable_subconfig['obs_yaml_dir'],
            'OBS_LIST': executable_subconfig['obs_list'],
            'OBS_YAML': executable_subconfig['obs_list'],
            'JEDI_BIN': gdasapp_bin,
            'HOMEgfs': homegfs,
            'SOCA_INPUT_FIX_DIR': all_config_dict['jedi static']['soca']['path'],
            'STATICB_DIR': os.path.join(workdir, 'soca_static'),
            'R2D2_OBS_DB': 'shared',
            'R2D2_OBS_DUMP': all_config_dict['r2d2 options']['obs_dump'],
            'R2D2_OBS_SRC': all_config_dict['r2d2 options']['obs_src'],
            'R2D2_OBS_WINDOW': '24',
            'FV3JEDI_STAGE_YAML': os.path.join(gdasapp_home, 'test', 'soca', 'testinput', 'dumy.yaml'),
            'DOMAIN_STACK_SIZE': all_config_dict['fms']['domain_stack_size'],
            'SOCA_VARS': all_config_dict['jedi options']['soca']['variables'],
            'SOCA_NINNER': all_config_dict['jedi options']['soca']['ninner'],
        }

        # do something to resolve gw env. variables
        runtime_envar_yaml = os.path.join(workdir, 'runtime_envar.yaml')
        f = open(runtime_envar_yaml, 'w')
        yaml.dump(runtime_envar, f, sort_keys=False, default_flow_style=False)
        bashout = os.path.join(workdir, 'load_envar.sh')
        export_envar(runtime_envar_yaml, bashout)

        # link gdas.cd
        ufsda.mkdir(os.path.join(homegfs, 'sorc'))
        ufsda_link = os.path.join(homegfs, 'sorc', 'gdas.cd')
        ufsda.disk_utils.symlink(all_config_dict['GDASApp home'],
                                 ufsda_link)
        ush_link = os.path.join(homegfs, 'ush')
        ufsda.disk_utils.symlink(os.path.join(all_config_dict['GDASApp home'], 'ush'),
                                 ush_link)

    # generate job submission script
    job_script = ufsda.misc_utils.create_batch_job(all_config_dict['job options'],
                                                   workdir,
                                                   baseexe,
                                                   output_file,
                                                   single_exec=single_exec)
    # submit job to queue
    ufsda.misc_utils.submit_batch_job(all_config_dict['job options'], workdir, job_script)


def genYAML(yamlconfig, output_file):
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    # open YAML file to get config
    try:
        with open(yamlconfig, 'r') as yamlconfig_opened:
            all_config_dict = yaml.safe_load(yamlconfig_opened)
        logging.info(f'Loading configuration from {yamlconfig}')
    except Exception as e:
        logging.error(f'Error occurred when attempting to load: {yamlconfig}, error: {e}')
    template = all_config_dict['template']
    config_dict = all_config_dict['config']
    # what if the config_dict has environment variables that need substituted?
    pattern = re.compile(r'.*?\${(\w+)}.*?')
    for key, value in config_dict.items():
        if type(value) == str:
            match = pattern.findall(value)
            if match:
                fullvalue = value
                for g in match:
                    config_dict[key] = fullvalue.replace(
                        f'${{{g}}}', os.environ.get(g, f'${{{g}}}')
                    )
    # NOTE the following is a hack until YAMLFile can take in an input config dict
    # if something in the template is expected to be an env var
    # but it is not defined in the env, problems will arise
    # so we set the env var in this subprocess for the substitution to occur
    for key, value in config_dict.items():
        os.environ[key] = str(value)
    # next we need to compute a few things
    runtime_config = get_runtime_config(dict(os.environ, **config_dict))
    # now run the global-workflow parser
    outconfig = YAMLFile(path=template)
    outconfig = Template.substitute_structure(outconfig, TemplateConstants.DOUBLE_CURLY_BRACES, config_dict.get)
    outconfig = Template.substitute_structure(outconfig, TemplateConstants.DOLLAR_PARENTHESES, config_dict.get)
    outconfig = Template.substitute_structure(outconfig, TemplateConstants.DOUBLE_CURLY_BRACES, runtime_config.get)
    outconfig = Template.substitute_structure(outconfig, TemplateConstants.DOLLAR_PARENTHESES, runtime_config.get)
    outconfig.save(output_file)


def get_runtime_config(config_dict):
    # compute some runtime variables
    # this will probably need pulled out somewhere else eventually
    # a temporary hack to get UFO evaluation stuff and ATM VAR going again
    valid_time = dt.datetime.strptime(config_dict['CDATE'], '%Y%m%d%H')
    assim_freq = int(config_dict.get('assim_freq', 6))
    window_begin = valid_time - dt.timedelta(hours=assim_freq/2)
    window_end = valid_time + dt.timedelta(hours=assim_freq/2)
    component_dict = {
        'atmos': 'ATM',
        'chem': 'AERO',
        'ocean': 'SOCA',
        'land': 'land',
    }
    win_begin_var = component_dict[config_dict.get('COMPONENT', 'atmos')] + '_WINDOW_BEGIN'
    win_end_var = component_dict[config_dict.get('COMPONENT', 'atmos')] + '_WINDOW_END'
    win_len_var = component_dict[config_dict.get('COMPONENT', 'atmos')] + '_WINDOW_LENGTH'
    bkg_string_var = 'BKG_YYYYmmddHHMMSS'
    bkg_isotime_var = 'BKG_ISOTIME'
    npx_ges_var = 'npx_ges'
    npy_ges_var = 'npy_ges'
    npz_ges_var = 'npz_ges'
    npx_anl_var = 'npx_anl'
    npy_anl_var = 'npy_anl'
    npz_anl_var = 'npz_anl'

    runtime_config = {
        win_begin_var: f"{window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        win_end_var: f"{window_end.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        win_len_var: f"PT{assim_freq}H",
        bkg_string_var: f"{valid_time.strftime('%Y%m%d.%H%M%S')}",
        bkg_isotime_var: f"{valid_time.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        npx_ges_var: f"{int(os.environ['CASE'][1:]) + 1}",
        npy_ges_var: f"{int(os.environ['CASE'][1:]) + 1}",
        npz_ges_var: f"{int(os.environ['LEVS']) - 1}",
        npx_anl_var: f"{int(os.environ['CASE_ENKF'][1:]) + 1}",
        npy_anl_var: f"{int(os.environ['CASE_ENKF'][1:]) + 1}",
        npz_anl_var: f"{int(os.environ['LEVS']) - 1}",
    }

    return runtime_config


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input YAML Configuration', required=True)
    args = parser.parse_args()
    run_jedi_exe(args.config)
