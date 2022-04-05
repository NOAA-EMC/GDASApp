#!/usr/bin/env python3
import argparse
import logging
import os
import subprocess
import ufsda
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
        os.makedirs(workdir, exist_ok = True)
        logging.info(f'Created working directory {workdir}')
    except OSError as error:
        logging.error(f'Error creating {workdir}: {error}')
    # use R2D2 to stage backgrounds, obs, bias correction files, etc.
    # link additional fix files needed (CRTM, fieldsets, etc.)
    # link executable
    # generate YAML for executable based on input config
    # generate job submission script
    # submit job to queue


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input YAML Configuration', required=True)
    args = parser.parse_args()
    run_atm_var_analysis(args.config)
