#!/usr/bin/env python3
# gen_bufr2ioda_yaml.py
# generate YAML for bufr2ioda.x
# given a template
# and certain configuration parameters
import argparse
import os
from wxflow import Template, TemplateConstants, YAMLFile


# list of satellite radiance BUFR files that need split by SatId
sat_list = [
    'atms',
    '1bamua',
    '1bmhs',
    'crisf4',
    'iasidb',
]


def gen_bufr_yaml(config):
    # open the template input file
    bufr_yaml = YAMLFile(path=config['template yaml'])
    # determine if splits need in the output file path
    obtype = config['obtype']
    if obtype in sat_list:
        # split by satellite platform
        obtype_out = f"{obtype}_{{splits/satId}}"
    else:
        obtype_out = obtype
    # construct the output IODA file path
    output_ioda = [
        config['run'],
        f"t{config['cyc']:02}z",
        obtype_out,
        'nc',
    ]
    output_ioda_str = '.'.join(output_ioda)
    output_ioda_file = os.path.join(config['output dir'], output_ioda_str)
    # construct the template substitution dict
    substitutions = {
        'BUFR_in': config['input file'],
        'IODA_out': output_ioda_file,
    }
    # substitue templates
    bufr_yaml = Template.substitute_structure(bufr_yaml, TemplateConstants.DOLLAR_PARENTHESES, substitutions.get)
    # write out BUFR converter YAML file
    bufr_yaml.save(config['output yaml file'])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input YAML Configuration', required=True)
    args = parser.parse_args()
    config = YAMLFile(path=args.config)
    gen_bufr_yaml(config)
