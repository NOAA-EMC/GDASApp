#!/usr/bin/env python3
import argparse
import logging
import os
import pathlib
import sys
from pygw.yaml_file import YAMLFile


def check_valid_yaml(repodir):
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    logging.info(f'Validating YAML files in {repodir}')
    # get recursive list of YAML files to check
    all_yamls = []
    for path in pathlib.Path(os.path.join(repodir, 'test')).rglob('*.yaml'):
        all_yamls.append(os.path.abspath(path))
    for path in pathlib.Path(os.path.join(repodir, 'parm')).rglob('*.yaml'):
        all_yamls.append(os.path.abspath(path))
    for path in pathlib.Path(os.path.join(repodir, 'test')).rglob('*.yml'):
        all_yamls.append(os.path.abspath(path))
    for path in pathlib.Path(os.path.join(repodir, 'parm')).rglob('*.yml'):
        all_yamls.append(os.path.abspath(path))
    nfailed = 0

    for yamlfile in all_yamls:
        logging.info(f'Checking {yamlfile}')
        try:
            config = YAMLFile(path=yamlfile)
        except OSError as e:
            logging.info(f'{yamlfile} warns of error: {e}, but this is fine')
        except Exception as e:
            logging.error(f'Error occurred when attempting to load: {yamlfile}, error: {e}')
            nfailed += 1
    logging.info(f'{nfailed} of {len(all_yamls)} files failed.')
    if nfailed > 0:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('repodir', type=str, help='Path to repository root')
    args = parser.parse_args()
    check_valid_yaml(args.repodir)
