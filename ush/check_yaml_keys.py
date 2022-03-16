#!/usr/bin/env python3
# compare keys between two YAML files
import argparse
import logging
import os
import yaml

def check_yaml(YAMLref, YAMLtest, checkValues=False):
    assert os.path.exists(YAMLref), f"File {YAMLref} not found."
    assert os.path.exists(YAMLtest), f"File {YAMLtest} not found."
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    logging.info(f'Comparing {YAMLtest} against {YAMLref}...')
    # load reference file
    try:
        with open(YAMLref, 'r') as YAMLref_opened:
            ref_dict = yaml.safe_load(YAMLref_opened)
    except Exception as e:
        logging.error(f'Error occurred when attempting to load: {YAMLref}, error: {e}')
    # load file to test
    try:
        with open(YAMLtest, 'r') as YAMLtest_opened:
            test_dict = yaml.safe_load(YAMLtest_opened)
    except Exception as e:
        logging.error(f'Error occurred when attempting to load: {YAMLtest}, error: {e}')
    # loop through top level of YAML
    compare_dict('', ref_dict, test_dict, checkValues)

def compare_dict(rootkey, dict1, dict2, checkValues):
    for key, value in dict1.items():
        keypath = f"{rootkey}/{key}"
        if key not in dict2:
            logging.error(f"'{keypath}' not in test file.")
        else:
            if isinstance(value, dict):
                compare_dict(keypath, value, dict2[key], checkValues)
            elif isinstance(value, list):
                compare_list(keypath, value, dict2[key], checkValues)
            else:
                if checkValues:
                    if value != dict2[key]:
                        logging.warning(f"{keypath}: {dict2[key]} != {value}")

def compare_list(rootkey, list1, list2, checkValues):
    if len(list2) != len(list1):
        logging.error(f"{rootkey} len={len(list2)} != {len(list1)}")
    for i, item in enumerate(list1):
        newkey = f"{rootkey}[{i}]"
        if i+1 <= len(list2):
            if isinstance(item, dict) and i+1 <= len(list2):
                compare_dict(newkey, item, list2[i], checkValues)
            elif isinstance(item, list):
                compare_list(newkey, item, list2[i], checkValues)
            else:
                if checkValues:
                    if item != list2[i]:
                        logging.warning(f"{rootkey}/{i}: {list2[i]} != {item}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('YAMLref', type=str, help='Reference YAML file')
    parser.add_argument('YAMLtest', type=str, help='YAML file to compare to reference')
    parser.add_argument("--checkvalues", help="Check values in addition to keys",
                        action="store_true")
    args = parser.parse_args()
    check_yaml(args.YAMLref, args.YAMLtest, args.checkvalues)
