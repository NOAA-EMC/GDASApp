#!/usr/bin/env python3
import argparse
import logging
import os
import yaml


def gen_eva_obs_yaml(inputyaml, templateyaml, outputyaml):
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    # open input YAML file to get config
    try:
        with open(inputyaml, 'r') as jediyaml_opened:
            jedi_yaml_dict = yaml.safe_load(jediyaml_opened)
        logging.info(f'Loading configuration from {inputyaml}')
    except Exception as e:
        logging.error(f'Error occurred when attempting to load: {inputyaml}, error: {e}')
    # get just the observations part of the YAML
    jediobs = jedi_yaml_dict['observations']['observers']
    # construct a simplified list of obsspaces for EVA
    evaobs = []
    for obsspace in jediobs:
        tmp_os = obsspace['obs space']
        tmp_dict = {
            'name': tmp_os['name'],
            'diagfile': tmp_os['obsdataout']['obsfile'].replace('.nc4', '_0000.nc4'),
            'vars': tmp_os['simulated variables'],
            'channels': tmp_os.get('channels', None),
        }
        evaobs.append(tmp_dict)
    # read in template YAML file
    try:
        with open(templateyaml, 'r') as templateyaml_opened:
            template_yaml_dict = yaml.safe_load(templateyaml_opened)
        logging.info(f'Loading configuration from {templateyaml}')
    except Exception as e:
        logging.error(f'Error occurred when attempting to load: {templateyaml}, error: {e}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputjediyaml', type=str, help='Input JEDI YAML Configuration', required=True)
    parser.add_argument('-t', '--templateyaml', type=str, help='Template EVA YAML', required=True)
    parser.add_argument('-o', '--outputyaml', type=str, help='Output EVA YAML Configuration', required=True)
    args = parser.parse_args()
    gen_eva_obs_yaml(args.inputjediyaml, args.templateyaml, args.outputyaml)
