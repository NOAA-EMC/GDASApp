#!/usr/bin/env python3
import argparse
import logger
import pathlib
import yaml


def check_valid_yaml(repodir):
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    logging.info(f'Validating YAML files in {repodir}')
    # get recursive list of YAML files to check
    all_yamls = []
    for path in pathlib.Path(os.path.join(repodir, 'test')).rglob('*.yaml'):
        all_yamls.append(path.name)
    for path in pathlib.Path(os.path.join(repodir, 'parm')).rglob('*.yaml'):
        all_yamls.append(path.name)
    for path in pathlib.Path(os.path.join(repodir, 'test')).rglob('*.yml'):
        all_yamls.append(path.name)
    for path in pathlib.Path(os.path.join(repodir, 'parm')).rglob('*.yml'):
        all_yamls.append(path.name)
    for yamlfile in all_yamls:
        print(yamlfile)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('repodir', type=str, help='Path to repository root')
    args = parser.parse_args()
    check_valid_yaml(args.repodir)
