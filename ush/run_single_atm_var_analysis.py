#!/usr/bin/env python3
import argparse
import datetime as dt
import logging
import os
import re
import subprocess
import sys
import yaml


def run_atm_var_analysis(yamlconfig):
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    # open YAML file to get config
    try:
        with open(yamlconfig, 'r') as yamlconfig_opened:
            all_config_dict = yaml.safe_load(yamlconfig_opened)
        logging.info(f'Loading configuration from {yamlconfig}')
    except Exception as e:
        logging.error(f'Error occurred when attempting to load: {yamlconfig}, error: {e}')
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
    analysis_subconfig = all_config_dict['analysis options']
    valid_time = analysis_subconfig['valid_time']
    h = re.findall('PT(\\d+)H', analysis_subconfig['atm_window_length'])[0]
    prev_cycle = valid_time - dt.timedelta(hours=int(h))
    cyc = valid_time.strftime("%H")
    cdate = valid_time.strftime("%Y%m%d%H")
    gcyc = prev_cycle.strftime("%H")
    gdate = prev_cycle.strftime("%Y%m%d%H")
    var_config = {
        'paths': analysis_subconfig['paths'],
        'OBS_LIST': analysis_subconfig['obs_list'],
        'atm': analysis_subconfig['atm'],
        'layout_x': str(analysis_subconfig['layout_x']),
        'layout_y': str(analysis_subconfig['layout_y']),
        'BKG_DIR': os.path.join(workdir, 'bkg'),
        'fv3jedi_fix_dir': os.path.join(workdir, 'Data', 'fv3files'),
        'fv3jedi_fieldset_dir': os.path.join(workdir, 'Data', 'fieldsets'),
        'ANL_DIR': os.path.join(workdir, 'anl'),
        'fv3jedi_staticb_dir': os.path.join(workdir, 'berror'),
        'BIAS_DIR': os.path.join(workdir, 'obs'),
        'CRTM_COEFF_DIR': os.path.join(workdir, 'crtm'),
        'BIAS_PREFIX': f"{analysis_subconfig['dump']}.t{gcyc}z",
        'BIAS_DATE': f"{gdate}",
        'DIAG_DIR': os.path.join(workdir, 'diags'),
        'OBS_DIR': os.path.join(workdir, 'obs'),
        'OBS_PREFIX': f"{analysis_subconfig['dump']}.t{cyc}z",
        'OBS_DATE': f"{cdate}",
        'valid_time': f"{valid_time.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        'atm_window_length': analysis_subconfig['atm_window_length'],
        'CASE': analysis_subconfig['case'],
        'CASE_ENKF': analysis_subconfig['case_enkf'],
        'DOHYBVAR': analysis_subconfig['dohybvar'],
        'LEVS': str(analysis_subconfig['levs']),
    }
    template = analysis_subconfig['var_yaml']
    output_file = os.path.join(workdir, 'fv3jedi_var.yaml')
    # set some environment variables
    os.environ['PARMgfs'] = os.path.join(all_config_dict['GDASApp home'], 'parm')
    # generate YAML for executable based on input config
    logging.info(f'Using YAML template {template}')
    ufsda.yamltools.genYAML(var_config, template=template, output=output_file)
    logging.info(f'Wrote Variational DA YAML file to {output_file}')
    # use R2D2 to stage backgrounds, obs, bias correction files, etc.
    # link additional fix files needed (CRTM, fieldsets, etc.)
    gdasfix = analysis_subconfig['gdas_fix_root']
    ufsda.stage.gdas_fix(gdasfix, workdir, var_config)
    # link executable
    varexe = os.path.join(all_config_dict['GDASApp home'], 'build', 'bin', 'fv3jedi_var.x')
    ufsda.disk_utils.symlink(varexe, os.path.join(workdir, 'fv3jedi_var.x'))
    # generate job submission script
    job_script = ufsda.misc_utils.create_batch_job(all_config_dict['job options'],
                                                   workdir,
                                                   os.path.join(workdir, 'fv3jedi_var.x'),
                                                   output_file)
    # submit job to queue
    ufsda.misc_utils.submit_batch_job(all_config_dict['job options'], workdir, job_script)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input YAML Configuration', required=True)
    args = parser.parse_args()
    run_atm_var_analysis(args.config)
