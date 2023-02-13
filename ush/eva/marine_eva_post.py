#!/usr/bin/env python3
import argparse
import datetime
import logging
import os
import socket
import yaml
import glob


def marine_eva_post(inputdir, outputdir, diagdir):
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    inputyamls = glob.glob(os.path.join(inputdir, '*.yaml'))
    print(inputyamls)
    for inputyaml in inputyamls:
        try:
            with open(inputyaml, 'r') as inputyaml_opened:
                input_yaml_dict = yaml.safe_load(inputyaml_opened)
            logging.info(f'Loading configuration from {inputyaml}')
        except Exception as e:
            logging.error(f'Error occurred when attempting to load: {inputyaml}, error: {e}')
        for diagnostic in input_yaml_dict['diagnostics']:
            for dataset in diagnostic['data']['datasets']:
                newfilenames = []
                for filename in dataset['filenames']:
                    newfilename = os.path.join(diagdir, os.path.basename(filename))
                    newfilenames.append(newfilename)
                dataset['filenames'] = newfilenames

        # first, let us prepend some comments that tell someone this output YAML was generated
        now = datetime.datetime.now()
        prepend_str = ''.join([
            f'# This YAML file automatically generated by marine_eva_post.py\n',
            f'# on {socket.gethostname()} at {now.strftime("%Y-%m-%dT%H:%M:%SZ")}\n',
        ])

        outputyaml = os.path.join(outputdir, os.path.basename(inputyaml))
        # open output file for writing and start the find/replace process
        try:
            logging.info(f'Writing replaced template to {outputyaml}')
            with open(outputyaml, 'w') as yaml_out:
                yaml_out.write(prepend_str)
                yaml.dump(input_yaml_dict, yaml_out)
        except Exception as e:
            logging.error(f'Error occurred when attempting to write: {outputyaml}, error: {e}')


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputdir', type=str, help='Directory with input YAMLs', required=True)
    parser.add_argument('-o', '--outputdir', type=str, help='Directory to send output YAMLs', required=True)
    parser.add_argument('-d', '--diagdir', type=str, help='Location of diag files', required=True)
    args = parser.parse_args()
    marine_eva_post(args.inputdir, args.outputdir, args.diagdir)
