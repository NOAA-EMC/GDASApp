#!/usr/bin/env python3
import argparse
import datetime
import logging
import os
import socket
import yaml
import glob

# sets the cmap vmin/vmax for each variable
# TODO: this should probably be in a yaml or something
vminmax = {'seaSurfaceTemperature': {'vmin': -2.0, 'vmax': 2.0},
           'seaIceFraction': {'vmin': -0.2, 'vmax': 0.2},
           'absoluteDynamicTopography': {'vmin': -0.2, 'vmax': 0.2}}


def marine_eva_post(inputyaml, outputdir, diagdir):
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    try:
        with open(inputyaml, 'r') as inputyaml_opened:
            input_yaml_dict = yaml.safe_load(inputyaml_opened)
        logging.info(f'Loading input YAML from {inputyaml}')
    except Exception as e:
        logging.error(f'Error occurred when attempting to load: {inputyaml}, error: {e}')
    for diagnostic in input_yaml_dict['diagnostics']:
        for dataset in diagnostic['data']['datasets']:
            newfilenames = []
            for filename in dataset['filenames']:
                newfilename = os.path.join(diagdir, os.path.basename(filename))
                newfilenames.append(newfilename)
            dataset['filenames'] = newfilenames
        for graphic in diagnostic['graphics']:
            # this assumes that there is only one variable, or that the
            # variables are all the same
            variable = graphic['batch figure']['variables'][0]
            for plot in graphic['plots']:
                for layer in plot['layers']:
                    layer['vmin'] = vminmax[variable]['vmin']
                    layer['vmax'] = vminmax[variable]['vmax']

    # first, let us prepend some comments that tell someone this output YAML was generated
    now = datetime.datetime.now()
    prepend_str = ''.join([
        f'# This YAML file automatically generated by marine_eva_post.py\n',
        f'# on {socket.gethostname()} at {now.strftime("%Y-%m-%dT%H:%M:%SZ")}\n',
    ])

    outputyaml = os.path.join(outputdir, os.path.basename(inputyaml))
    # open output file for writing and start the find/replace process
    try:
        logging.info(f'Writing modified YAML to {outputyaml}')
        with open(outputyaml, 'w') as yaml_out:
            yaml_out.write(prepend_str)
            yaml.dump(input_yaml_dict, yaml_out)
    except Exception as e:
        logging.error(f'Error occurred when attempting to write: {outputyaml}, error: {e}')


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputyaml', type=str, help='Input YAML to modify', required=True)
    parser.add_argument('-o', '--outputdir', type=str, help='Directory to send output YAML', required=True)
    parser.add_argument('-d', '--diagdir', type=str, help='Location of diag files', required=True)
    args = parser.parse_args()
    marine_eva_post(args.inputyaml, args.outputdir, args.diagdir)
