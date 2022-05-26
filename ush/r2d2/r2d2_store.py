#!/usr/bin/env python3
import argparse
from solo.configuration import Configuration
import ufsda.r2d2

if __name__ == "__main__":
    # get input config file
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input YAML Configuration', required=True)
    args = parser.parse_args()
    config = Configuration(args.config)
    ufsda.r2d2.store(config)
