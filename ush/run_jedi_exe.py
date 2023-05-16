#!/usr/bin/env python3
import argparse
import datetime as dt
import logging
import os
import re
import subprocess
import sys
import yaml
import pygw
from pygw.yaml_file import parse_j2yaml, save_as_yaml


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
    supported_app_modes = ['hofx', 'variational', 'letkf']
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
    from ufsda.stage import gdas_single_cycle, gdas_fix, background_ens, atm_obs, bias_obs
    from ufsda.genYAML import genYAML

    # compute config for YAML for executable
    executable_subconfig = all_config_dict['config']
    valid_time = executable_subconfig['valid_time']
    assim_freq = int(executable_subconfig.get('assim_freq', 6))
    h = re.findall('PT(\\d+)H', executable_subconfig['atm_window_length'])[0]
    prev_cycle = valid_time - dt.timedelta(hours=int(h))
    window_begin = valid_time - dt.timedelta(hours=int(h)/2)
    cyc = valid_time.strftime("%H")
    gcyc = prev_cycle.strftime("%H")
    gPDY = prev_cycle.strftime("%Y%m%d")
    pdy = valid_time.strftime("%Y%m%d")
    os.environ['PDY'] = str(pdy)
    os.environ['cyc'] = str(cyc)
    os.environ['assim_freq'] = str(assim_freq)
    oprefix = executable_subconfig['dump'] + ".t" + str(cyc) + "z."
    gprefix = executable_subconfig['dump'] + ".t" + str(gcyc) + "z."
    comin = executable_subconfig.get('gdas_fix_root', './')
    comin_ges_ens = os.path.join(comin, 'cases', 'enkfgdas.' + str(gPDY), str(gcyc))
    dump = executable_subconfig['dump']
    output_file = os.path.join(workdir, f"gdas_{app_mode}.yaml")

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
        'BIAS_DATE': f"{gPDY}{gcyc}",
        'DIAG_DIR': os.path.join(workdir, 'diags'),
        'OBS_DIR': os.path.join(workdir, 'obs'),
        'OBS_PREFIX': f"{executable_subconfig['dump']}.t{cyc}z.",
        'OBS_DATE': f"{pdy}{cyc}",
        'PDY': f"{pdy}",
        'cyc': f"{cyc}",
        'gPDY': f"{gPDY}",
        'gcyc': f"{gcyc}",
        'valid_time': f"{valid_time.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        'window_begin': f"{window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        'prev_valid_time': f"{prev_cycle.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        'previous_cycle': f"{prev_cycle}",
        'current_cycle': f"{valid_time}",
        'atm_window_length': executable_subconfig['atm_window_length'],
        'ATM_WINDOW_LENGTH': f"PT{assim_freq}H",
        'ATM_WINDOW_BEGIN': f"{window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        'COMOUT': os.path.join(workdir, 'obs'),
        'CASE': executable_subconfig['case'],
        'CASE_ANL': executable_subconfig.get('case_anl', executable_subconfig['case']),
        'CASE_ENS': executable_subconfig.get('case_enkf', executable_subconfig['case']),
        'DOHYBVAR': executable_subconfig.get('dohybvar', False),
        'LEVS': str(executable_subconfig['levs']),
        'NMEM_ENS': executable_subconfig.get('nmem', 0),
        'COMIN_GES_ENS': f"{comin_ges_ens}",
        'forecast_steps': calc_fcst_steps(executable_subconfig.get('forecast_step', 'PT6H'),
                                          executable_subconfig['atm_window_length']),
        'BKG_TSTEP': executable_subconfig.get('forecast_step', 'PT6H'),
        'INTERP_METHOD': executable_subconfig.get('interp_method', 'barycentric'),
        'output_file': os.path.join(workdir, f"gdas_{app_mode}.yaml"),
        'dump': f"{dump}",
        'output_file': f"{output_file}",
    }

    # set some environment variables
    os.environ['PARMgfs'] = os.path.join(all_config_dict['GDASApp home'], 'parm')
    for key, value in var_config.items():
        os.environ[key] = str(value)
    # generate YAML for executable based on input config
    logging.info(f'Using yamlconfig {yamlconfig}')

    local_dict = {
        'npx_ges': f"{int(os.environ['CASE'][1:]) + 1}",
        'npy_ges': f"{int(os.environ['CASE'][1:]) + 1}",
        'npz_ges': f"{int(os.environ['LEVS']) - 1}",
        'npz': f"{int(os.environ['LEVS']) - 1}",
        'npx_anl': f"{int(os.environ['CASE_ANL'][1:]) + 1}",
        'npy_anl': f"{int(os.environ['CASE_ANL'][1:]) + 1}",
        'npz_anl': f"{int(os.environ['LEVS']) - 1}",
        'NMEM_ENS': f"{int(os.environ['NMEM_ENS'])}",
        'ATM_WINDOW_BEGIN': window_begin,
        'ATM_WINDOW_LENGTH': f"PT{assim_freq}H",
        'BKG_TSTEP': executable_subconfig.get('forecast_step', 'PT6H'),
        'OPREFIX': f"{dump}.t{cyc}z.",  # TODO: CDUMP is being replaced by RUN
        'APREFIX': f"{dump}.t{cyc}z.",  # TODO: CDUMP is being replaced by RUN
        'GPREFIX': f"gdas.t{gcyc}z.",
        'DATA': os.path.join(workdir),
        'layout_x': str(executable_subconfig['layout_x']),
        'layout_y': str(executable_subconfig['layout_y']),
        'previous_cycle': prev_cycle,
        'current_cycle': valid_time,
    }

    varda_yaml = parse_j2yaml(all_config_dict['template'], local_dict)
    save_as_yaml(varda_yaml, output_file)

    logging.info(f'Wrote YAML file to {output_file}')
    # use R2D2 to stage backgrounds, obs, bias correction files, etc.
    if app_mode in ['variational', 'hofx']:
        ufsda.stage.gdas_single_cycle(var_config, local_dict)
    # stage ensemble backgrouns for letkf
    if app_mode in ['letkf']:
        ufsda.stage.background_ens(var_config)
        ufsda.stage.atm_obs(var_config, local_dict)
        ufsda.stage.bias_obs(var_config, local_dict)

    # link additional fix files needed (CRTM, fieldmetadata, etc.)
    gdasfix = executable_subconfig['gdas_fix_root']
    ufsda.stage.gdas_fix(gdasfix, workdir, var_config)
    # link executable
    baseexe = os.path.basename(executable_subconfig['executable'])
    ufsda.disk_utils.symlink(executable_subconfig['executable'], os.path.join(workdir, baseexe))
    # create output directories
    ufsda.disk_utils.mkdir(os.path.join(workdir, 'diags'))
    if app_mode in ['variational', 'letkf']:
        ufsda.disk_utils.mkdir(os.path.join(workdir, 'anl'))
        ufsda.disk_utils.mkdir(os.path.join(workdir, 'bc'))
    baseexe = os.path.join(workdir, baseexe)

    # generate job submission script
    job_script = ufsda.misc_utils.create_batch_job(all_config_dict['job options'],
                                                   workdir,
                                                   baseexe,
                                                   output_file,
                                                   single_exec=single_exec)
    # submit job to queue
    ufsda.misc_utils.submit_batch_job(all_config_dict['job options'], workdir, job_script)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input YAML Configuration', required=True)
    args = parser.parse_args()
    run_jedi_exe(args.config)
