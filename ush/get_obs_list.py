#!/usr/bin/env python3
# get_obs_list
# parse YAML file to get list of
# input obs and bias coeff files
# and write to a file for later use
import argparse
import logging
import yaml


def get_obs_list(yamlconfig, outputfile):
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    # open YAML file to get config
    try:
        with open(yamlconfig, 'r') as yamlconfig_opened:
            all_config_dict = yaml.safe_load(yamlconfig_opened)
        logging.info(f'Loading configuration from {yamlconfig}')
    except Exception as e:
        logging.error(f'Error occurred when attempting to load: {yamlconfig}, error: {e}')
    # just grab the observations section
    key = 'cost function'
    if key in all_config_dict.keys():
        obs_list = all_config_dict['cost function']['observations']['observers']
    else:
        obs_list = all_config_dict['observations']['observers']
    with open(outputfile, 'w') as outf:
        for ob in obs_list:
            # get obsdatain
            obsdatain = ob['obs space']['obsdatain']['obsfile']
            outf.write(f"{obsdatain}\n")
            if 'obs bias' in ob.keys():
                biasin = ob['obs bias']['input file']
                satcovin = biasin.replace('satbias', 'satbias_cov')
                lapsein = satcovin.replace('satbias_cov', 'tlapse').replace('nc4', 'txt')
                outf.write(f"{biasin}\n{satcovin}\n{lapsein}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input YAML Configuration', required=True)
    parser.add_argument('-o', '--output', type=str, help='Output text file', required=True)
    args = parser.parse_args()
    get_obs_list(args.config, args.output)
