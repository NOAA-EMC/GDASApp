#!/usr/bin/env python3
import argparse
import datetime
import logging
import os
import socket
import yaml


def gen_eva_obs_yaml(inputyaml, templateyaml, outputdir, group='ObsValue', variable='None', bound=[0, 20]):
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    # open input YAML file to get config
    try:
        with open(inputyaml, 'r') as jediyaml_opened:
            jedi_yaml_dict = yaml.safe_load(jediyaml_opened)
        logging.info(f'Loading configuration from {inputyaml}')
    except Exception as e:
        logging.error(f'Error occurred when attempting to load: {inputyaml}, error: {e}')
    # get just the observations part of the YAML
    if 'observations' in jedi_yaml_dict['cost function']:
        jediobs = jedi_yaml_dict['cost function']['observations']['observers']
    elif 'observers' in jedi_yaml_dict['observations']:
        jediobs = jedi_yaml_dict['observations']['observers']
    else:
        # the unit tests have a different YAML setup
        jediobs = jedi_yaml_dict['observations']
    # construct a simplified list of obsspaces for EVA
    evaobs = []
    for obsspace in jediobs:
        tmp_os = obsspace['obs space']
        if tmp_os['simulated variables'][0] != variable:
            continue
        tmp_dict = {
            'name': tmp_os['name'],
            'diagfile': tmp_os['obsdataout']['engine']['obsfile'].replace('.nc4', '_0000.nc4'),
            'vars': tmp_os['simulated variables'],
            'channels': tmp_os.get('channels', None),
        }
        evaobs.append(tmp_dict)
    # read in template YAML file
    # read it in as a text file and not a YAML file
    # this is so that we can find/replace some things more simply
    try:
        with open(templateyaml, 'r') as templateyaml_opened:
            template_yaml_str = templateyaml_opened.readlines()
        logging.info(f'Loading template from {templateyaml}')
    except Exception as e:
        logging.error(f'Error occurred when attempting to load: {templateyaml}, error: {e}')
    # first, let us prepend some comments that tell someone this output YAML was generated
    now = datetime.datetime.now()
    prepend_str = [
        '# This YAML file automatically generated by gen_eva_obs_yaml.py\n',
        f'# from template YAML file: {templateyaml}\n',
        f'# on {socket.gethostname()} at {now.strftime("%Y-%m-%dT%H:%M:%SZ")}\n',
    ]
    output_temp_str = prepend_str + template_yaml_str
    # make sure the output directory exists and if not, make it
    if not os.path.exists(outputdir):
        logging.info(f'Creating output directory {outputdir}')
        os.makedirs(outputdir)
    # now loop over all observation spaces in input JEDI YAML file
    for obsspace in evaobs:
        name = obsspace['name']
        cycle = obsspace['diagfile'].split('_')[-2]
        logging.info(f'Now processing: {name}')
        # get the dictionary of replacements set up
        replacements = {
            '@FILENAME@': obsspace['diagfile'],
            '@VARIABLES@': obsspace['vars'],
            '@NAME@': name,
            '@CYCLE@': cycle,
        }
        if obsspace['channels'] is not None:
            replacements['@CHANNELS@'] = obsspace['channels']
            replacements['@CHANNELSKEY@'] = f"channels: {obsspace['channels']}"
            replacements['@CHANNELKEY@'] = 'channel: ${channel}'
            replacements['@CHANNELVAR@'] = '${channel}'
        else:
            replacements['@CHANNELS@'] = ''
            replacements['@CHANNELSKEY@'] = ''
            replacements['@CHANNELKEY@'] = ''
            replacements['@CHANNELVAR@'] = ''

        # put the group name and bounds for the colorbar
        replacements['@GRPNAME@'] = group
        replacements['@VMIN@'] = bound[0]
        replacements['@VMAX@'] = bound[1]

        # open output file for writing and start the find/replace process
        outputyaml = os.path.join(outputdir, f'eva_{name}_{cycle}.yaml')
        try:
            logging.info(f'Writing replaced template to {outputyaml}')
            with open(outputyaml, 'w') as yaml_out:
                for line in output_temp_str:
                    for src, target in replacements.items():
                        line = line.replace(src, str(target))
                    yaml_out.write(line)
        except Exception as e:
            logging.error(f'Error occurred when attempting to write: {outputyaml}, error: {e}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputjediyaml', type=str, help='Input JEDI YAML Configuration', required=True)
    parser.add_argument('-t', '--templateyaml', type=str, help='Template EVA YAML', required=True)
    parser.add_argument('-o', '--outputdir', type=str, help='Output directory for EVA YAMLs', required=True)
    parser.add_argument('-g', '--group', type=str, help='ioda groups [ObsValue, ObsError, ombg oman] ', required=False, default='ObsValue')
    parser.add_argument('-v', '--variable', type=str, help='Variable name for the data', required=True)
    parser.add_argument('-b', '--bound', type=str, nargs='+', help='min, max', required=True)
    args = parser.parse_args()
    gen_eva_obs_yaml(args.inputjediyaml, args.templateyaml, args.outputdir, group=args.group, variable=args.variable, bound=args.bound)
