#!/usr/bin/env python3
import os
import datetime as dt
import logging
import subprocess
import csv
import shutil
import glob
import argparse
import yaml

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',
                    level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')


def run_satbias_conv(config):
    # run ioda-converters satbias converter to take GSI satbias file
    # and create UFO compatible input files


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input YAML Configuration', required=True)
    args = parser.parse_args()
    # read YAML for config
    try:
        with open(args.config, 'r') as yaml_opened:
            config = yaml.safe_load(yaml_opened)
    except Exception as e:
        logging.error(f'Error occurred when attempting to load: {args.config}, error: {e}')

    run_satbias_conv(config)
