#!/usr/bin/env python3
# genYAML
# generate YAML using ufsda python module,
# current runtime env, and optional input YAML
import argparse
import datetime as dt
import logging
import os
import re
import yaml
from pygw.template import Template, TemplateConstants
from pygw.yaml_file import YAMLFile


def genYAML(yamlconfig, output=None):
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    # open YAML file to get config
    try:
        with open(yamlconfig, 'r') as yamlconfig_opened:
            all_config_dict = yaml.safe_load(yamlconfig_opened)
        logging.info(f'Loading configuration from {yamlconfig}')
    except Exception as e:
        logging.error(f'Error occurred when attempting to load: {yamlconfig}, error: {e}')

    if not output:
        output_file = all_config_dict['output']
    else:
        output_file = output

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
    vpdy = dt.datetime.strptime(config_dict['PDY'], '%Y%m%d')
    vcyc = dt.datetime.strptime(config_dict['cyc'], '%H')
    vdate = int(config_dict.get('PDY'))*100 + int(config_dict.get('cyc'))
    valid_time = dt.datetime.strptime(str(vdate), '%Y%m%d%H')
    assim_freq = int(config_dict.get('assim_freq', 6))
    window_begin = valid_time - dt.timedelta(hours=assim_freq/2)
    window_end = valid_time + dt.timedelta(hours=assim_freq/2)
    bkg_tstep_default = f"PT{assim_freq}H"
    bkg_tstep = str(config_dict.get('BKG_TSTEP', f"PT{assim_freq}H"))
    component_dict = {
        'atmos': 'ATM',
        'chem': 'AERO',
        'ocean': 'SOCA',
        'land': 'land',
    }
    win_begin_var = component_dict[config_dict.get('COMPONENT', 'atmos')] + '_WINDOW_BEGIN'
    win_end_var = component_dict[config_dict.get('COMPONENT', 'atmos')] + '_WINDOW_END'
    win_len_var = component_dict[config_dict.get('COMPONENT', 'atmos')] + '_WINDOW_LENGTH'
    atm_begin_var = 'ATM_BEGIN_YYYYmmddHHMMSS'
    bkg_string_var = 'BKG_YYYYmmddHHMMSS'
    bkg_isotime_var = 'BKG_ISOTIME'
    bkg_tstep_var = 'BKG_TSTEP'
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
        atm_begin_var: f"{window_begin.strftime('%Y%m%d.%H%M%S')}",
        bkg_string_var: f"{valid_time.strftime('%Y%m%d.%H%M%S')}",
        bkg_isotime_var: f"{valid_time.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        bkg_tstep_var: f"{bkg_tstep}",
        npx_ges_var: f"{int(os.environ['CASE'][1:]) + 1}",
        npy_ges_var: f"{int(os.environ['CASE'][1:]) + 1}",
        npz_ges_var: f"{int(os.environ['LEVS']) - 1}",
        npx_anl_var: f"{int(os.environ['CASE_ENKF'][1:]) + 1}",
        npy_anl_var: f"{int(os.environ['CASE_ENKF'][1:]) + 1}",
        npz_anl_var: f"{int(os.environ['LEVS']) - 1}",
    }

    return runtime_config
