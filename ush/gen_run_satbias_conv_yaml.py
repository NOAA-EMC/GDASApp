#!/usr/bin/env python3
# gen_run_satbias_conv_yaml.py
# generate YAML for satbias2ioda.x
# given certain configuration parameters

import argparse
import datetime as dt
import os
from wxflow import Logger, parse_j2yaml, cast_strdict_as_dtypedict, save_as_yaml
from wxflow import add_to_datetime, to_timedelta

# initialize root logger
logger = Logger('gen_run_satbias_conv_yaml.py', level='INFO', colored_log=True)

def gen_run_satbias_conv_yaml(output):
    config = {
        'start time': os.environ['GDATE'], 
        'end time': os.environ['GDATE'], 
        'assim_freq': os.environ['assim_freq'], 
        'gsi_bc_root': os.environ['DATA'],
        'ufo_bc_root': f"{os.environ['DATA']}/output/",
        'work_root': f"{os.environ['DATA']}/tmp/",
        'satbias2ioda': os.environ['EXX'],
        'dump': os.environ['GDUMP'],
    }
    save_as_yaml(config, output)
    logger.info(f"Wrote to {output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', type=str, help='Output YAML File', required=True)
    args = parser.parse_args()
    # call the parsing function
    gen_run_satbias_conv_yaml(args.output)
