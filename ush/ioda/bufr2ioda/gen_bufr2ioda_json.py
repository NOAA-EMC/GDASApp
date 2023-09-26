#!/usr/bin/env python3
# gen_bufr2ioda_json.py
# generate JSON from a template
# as input to the various
# python BUFR2IODA scripts
import argparse
import json
import os
from wxflow import Logger, parse_j2yaml

# Initialize root logger
logger = Logger('gen_bufr2ioda_json.py', level='INFO', colored_log=True)


def gen_bufr_json(config, template, output):
    # read in templated JSON and do substitution
    logger.info(f"Using {template} as input")
    bufr_config = parse_j2yaml(template, config)
    # write out JSON
    json_object = json.dumps(bufr_config, indent=4)
    with open(output, "w") as outfile:
        outfile.write(json_object)
    logger.info(f"Wrote to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--template', type=str, help='Input JSON template', required=True)
    parser.add_argument('-o', '--output', type=str, help='Output JSON file', required=True)
    args = parser.parse_args()
    gen_bufr_json(config, args.template, args.output)
