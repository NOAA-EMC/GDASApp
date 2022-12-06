#!/usr/bin/env python3
import argparse
import logging
import os
import pathlib
import re
import sys
import yaml


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
    # define tags
    envtag = '!ENV'
    inctag = '!INC'
    # pattern for global vars: look for ${word}
    pattern = re.compile(r'.*?\${(\w+)}.*?')
    loader = yaml.SafeLoader

    # the envtag will be used to mark where to start searching for the pattern
    # e.g. somekey: !ENV somestring${MYENVVAR}blah blah blah
    loader.add_implicit_resolver(envtag, pattern, None)
    loader.add_implicit_resolver(inctag, pattern, None)

    def expand_env_variables(line):
        match = pattern.findall(line)  # to find all env variables in line
        if match:
            full_value = line
            for g in match:
                full_value = full_value.replace(
                    f'${{{g}}}', os.environ.get(g, f'${{{g}}}')
                )
            return full_value
        return line

    def constructor_env_variables(loader, node):
        """
        Extracts the environment variable from the node's value
        :param yaml.Loader loader: the yaml loader
        :param node: the current node in the yaml
        :return: the parsed string that contains the value of the environment
        variable
        """
        value = loader.construct_scalar(node)
        return expand_env_variables(value)

    def constructor_include_variables(loader, node):
        """
        Extracts the environment variable from the node's value
        :param yaml.Loader loader: the yaml loader
        :param node: the current node in the yaml
        :return: the content of the file to be included
        """
        value = loader.construct_scalar(node)
        value = expand_env_variables(value)
        expanded = parse_yaml(value)
        return expanded

    loader.add_constructor(envtag, constructor_env_variables)
    loader.add_constructor(inctag, constructor_include_variables)

    for yamlfile in all_yamls:
        logging.info(f'Checking {yamlfile}')
        try:
            with open(yamlfile, 'r') as YAML_opened:
                test_dict = yaml.load(YAML_opened, Loader=loader)
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
