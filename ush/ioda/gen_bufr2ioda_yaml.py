#!/usr/bin/env python3
# gen_bufr2ioda_yaml.py
# generate YAML for bufr2ioda.x
# given a template
# and certain configuration parameters
import argparse
from pygw.template import Template, TemplateConstants
from pygw.yaml_file import YAMLFile


def gen_bufr_yaml(config):
    # do stuff here

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(-c, '--config', type=str, help='Input YAML Configuration', required=True)
    args = parser.parse_args()
    gen_bufr_yaml(args.config)
