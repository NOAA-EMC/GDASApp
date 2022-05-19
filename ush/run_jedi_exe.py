#!/usr/bin/env python3
import argparse
import datetime as dt
import logging
import os
import re
import subprocess
import sys
import yaml


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
    supported_app_modes = ['hofx', 'variational']
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
    # compute config for YAML for executable
    executable_subconfig = all_config_dict['executable options']
    valid_time = executable_subconfig['valid_time']
    h = re.findall('PT(\\d+)H', executable_subconfig['atm_window_length'])[0]
    prev_cycle = valid_time - dt.timedelta(hours=int(h))
    window_begin = valid_time - dt.timedelta(hours=int(h)/2)
    cyc = valid_time.strftime("%H")
    cdate = valid_time.strftime("%Y%m%d%H")
    gcyc = prev_cycle.strftime("%H")
    gdate = prev_cycle.strftime("%Y%m%d%H")
    var_config = {
        'BERROR_YAML': executable_subconfig.get('berror_yaml', './'),
        'OBS_YAML_DIR': executable_subconfig['obs_yaml_dir'],
        'OBS_LIST': executable_subconfig['obs_list'],
        'atm': executable_subconfig.get('atm', False),
        'layout_x': str(executable_subconfig['layout_x']),
        'layout_y': str(executable_subconfig['layout_y']),
        'BKG_DIR': os.path.join(workdir, 'bkg'),
        'fv3jedi_fix_dir': os.path.join(workdir, 'Data', 'fv3files'),
        'fv3jedi_fieldset_dir': os.path.join(workdir, 'Data', 'fieldsets'),
        'ANL_DIR': os.path.join(workdir, 'anl'),
        'fv3jedi_staticb_dir': os.path.join(workdir, 'berror'),
        'BIAS_DIR': os.path.join(workdir, 'obs'),
        'CRTM_COEFF_DIR': os.path.join(workdir, 'crtm'),
        'BIAS_PREFIX': f"{executable_subconfig['dump']}.t{gcyc}z",
        'BIAS_DATE': f"{gdate}",
        'DIAG_DIR': os.path.join(workdir, 'diags'),
        'OBS_DIR': os.path.join(workdir, 'obs'),
        'OBS_PREFIX': f"{executable_subconfig['dump']}.t{cyc}z",
        'OBS_DATE': f"{cdate}",
        'valid_time': f"{valid_time.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        'window_begin': f"{window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        'prev_valid_time': f"{prev_cycle.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        'atm_window_length': executable_subconfig['atm_window_length'],
        'CASE': executable_subconfig['case'],
        'CASE_ENKF': executable_subconfig.get('case_enkf', executable_subconfig['case']),
        'DOHYBVAR': executable_subconfig.get('dohybvar', False),
        'LEVS': str(executable_subconfig['levs']),
        'forecast_step': executable_subconfig.get('forecast_step', 'PT6H'),
    }
    template = executable_subconfig['yaml_template']
    output_file = os.path.join(workdir, f"gdas_{app_mode}.yaml")
    # set some environment variables
    os.environ['PARMgfs'] = os.path.join(all_config_dict['GDASApp home'], 'parm')
    # generate YAML for executable based on input config
    logging.info(f'Using YAML template {template}')
    ufsda.yamltools.genYAML(var_config, template=template, output=output_file)
    logging.info(f'Wrote YAML file to {output_file}')
    # use R2D2 to stage backgrounds, obs, bias correction files, etc.
    ufsda.stage.gdas_single_cycle(var_config)
    # link additional fix files needed (CRTM, fieldsets, etc.)
    gdasfix = executable_subconfig['gdas_fix_root']
    ufsda.stage.gdas_fix(gdasfix, workdir, var_config)
    # link executable
    baseexe = os.path.basename(executable_subconfig['executable'])
    ufsda.disk_utils.symlink(executable_subconfig['executable'], os.path.join(workdir, baseexe))
    # create output directories
    ufsda.disk_utils.mkdir(os.path.join(workdir, 'diags'))
    if app_mode in ['variational']:
        ufsda.disk_utils.mkdir(os.path.join(workdir, 'anl'))
    # generate job submission script
    job_script = ufsda.misc_utils.create_batch_job(all_config_dict['job options'],
                                                   workdir,
                                                   os.path.join(workdir, baseexe),
                                                   output_file)
    # submit job to queue
    ufsda.misc_utils.submit_batch_job(all_config_dict['job options'], workdir, job_script)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input YAML Configuration', required=True)
    args = parser.parse_args()
    run_jedi_exe(args.config)
