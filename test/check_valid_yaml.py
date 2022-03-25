#!/usr/bin/env python3
import argparse
import glob
import logger
import yaml


def check_valid_yaml(repodir):
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    logging.info(f'Validating YAML files in {repodir}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('repodir', type=str, help='Path to repository root')
    args = parser.parse_args()
    check_valid_yaml(args.repodir)
