#!/usr/bin/env python3
import argparse
import copy
import logging
import yaml


def convert_yaml_ewok_to_gdas(ewokyaml, gdasyaml):
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    # first, read input YAML into memory
    try:
        with open(ewokyaml, 'r') as ewokyaml_opened:
            ob_dict = yaml.safe_load(ewokyaml_opened)
        logging.info(f'Loading configuration from {ewokyaml}')
    except Exception as e:
        logging.error(f'Error occurred when attempting to load: {ewokyaml}, error: {e}')

    # -----------------------------------------
    # replace relevant YAML keys as appropriate

    # obs space input file
    infile = ob_dict['obs space']['obsdatain']['engine']['obsfile']
    obtype = infile.split('/')[2].split('.')[0]
    infile = f"$(OBS_DIR)/$(OBS_PREFIX){obtype}.$(OBS_DATE).nc4"
    ob_dict['obs space']['obsdatain']['engine']['obsfile'] = infile

    # obs space output diag
    outfile = f"$(DIAG_DIR)/diag_{obtype}_$(OBS_DATE).nc4"
    ob_dict['obs space']['obsdataout']['engine']['obsfile'] = outfile

    # io pool to one
    ob_dict['obs space']['io pool'] = {'max pool size': 1}

    # CRTM stuff if appropriate
    if 'obs options' in ob_dict['obs operator'].keys():
        if 'CoefficientPath' in ob_dict['obs operator']['obs options'].keys():
            ob_dict['obs operator']['obs options']['CoefficientPath'] = "$(CRTM_COEFF_DIR)/"
    if 'Absorbers' in ob_dict['obs operator'].keys():
        absorbers = ob_dict['obs operator']['Absorbers']
        # fv3-jedi cannot handle CO2 in the linear obs operator
        if 'CO2' in absorbers:
            linear_absorbers = copy.deepcopy(absorbers)
            linear_absorbers.remove('CO2')
            ob_dict['obs operator']['linear obs operator'] = {'Absorbers': linear_absorbers}

    # obs bias if appropriate
    if 'obs bias' in ob_dict.keys():
        bias_in = f"$(BIAS_IN_DIR)/$(BIAS_PREFIX){obtype}.satbias.$(BIAS_DATE).nc4"
        ob_dict['obs bias']['input file'] = bias_in
        bias_out = f"$(BIAS_OUT_DIR)/$(OBS_PREFIX){obtype}.satbias.$(OBS_DATE).nc4"
        ob_dict['obs bias']['output file'] = bias_out
        for p in ob_dict['obs bias']['variational bc']['predictors']:
            if 'tlapse' in p.keys():
                p['tlapse'] = f"$(BIAS_IN_DIR)/$(BIAS_PREFIX){obtype}.tlapse.$(BIAS_DATE).txt"
        # add a new covariance section with constants by default
        cov_dict = {
            'minimal required obs number': 20,
            'variance range': [1.0e-6, 10.0],
            'step size': 1.0e-4,
            'largest analysis variance': 10000.0,
            'prior': {
                'input file': f"$(BIAS_IN_DIR)/$(BIAS_PREFIX){obtype}.satbias_cov.$(BIAS_DATE).nc4",
                'inflation': {'ratio': 1.1, 'ratio for small dataset': 2.0},
            },
            'output file': f"$(BIAS_OUT_DIR)/$(OBS_PREFIX){obtype}.satbias_cov.$(OBS_DATE).nc4",
        }
        ob_dict['obs bias']['covariance'] = cov_dict

    # write out new YAML file
    try:
        with open(gdasyaml, 'w') as yamlout:
            yaml.dump(ob_dict, yamlout, default_flow_style=False, sort_keys=False)
        logging.info(f'Wrote YAML to {gdasyaml}')
    except Exception as e:
        logging.error(f'Error occurred when attempting to write: {gdasyaml}, error: {e}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('EWOKYAML', type=str, help='Input EWOK UFO YAML file')
    parser.add_argument('GDASYAML', type=str, help='Output GDASApp observation YAML file')
    args = parser.parse_args()
    convert_yaml_ewok_to_gdas(args.EWOKYAML, args.GDASYAML)
