import argparse
import yaml
from pprint import pprint


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input yaml configuration', required=True)
    args = parser.parse_args()
    yaml_file_name = args.config

    with open(yaml_file_name, 'r') as yaml_file:
        yaml_config = yaml.load(yaml_file, Loader=yaml.FullLoader)
        pprint(yaml_config)