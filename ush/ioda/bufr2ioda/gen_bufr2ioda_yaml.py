#!/usr/bin/env python3
# gen_bufr2ioda_yaml.py
# generate YAML for bufr2ioda.x
# given a template
# and certain configuration parameters
import argparse
import os
from wxflow import Logger, parse_j2yaml, cast_strdict_as_dtypedict, save_as_yaml


def gen_bufr_yaml(config, template, output):
    # read in templated YAML and do substitution
    logger.info(f"Using {template} as input")
    bufr_config = parse_j2yaml(template, config)
    save_as_yaml(bufr_config, output)
    logger.info(f"Wrote to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--template', type=str, help='Input YAML template', required=True)
    parser.add_argument('-o', '--output', type=str, help='Output YAML file', required=True)
    args = parser.parse_args()
    # get the config from your environment
    config = cast_strdict_as_dtypedict(os.environ)
    # call the parsing function
    gen_bufr_yaml(config, args.template, args.output)
