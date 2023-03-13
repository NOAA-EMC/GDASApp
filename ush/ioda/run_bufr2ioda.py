#!/usr/bin/env python
import glob
import os
from pygw.template import Template, TemplateConstants
from pygw.yaml_file import YAMLFile

def run_BUFR2IODA(config_path):
    """
    Driver function to:
    - determine list of input BUFR files available
    - generate YAMLs from templates for each BUFR file
    - run BUFR2IODA.x and produce output IODA files
    Parameters
    ----------
    config_path : str
                path to input YAML configuration

    """
    # read input YAML configuration
    config = YAMLFile(path=config_path)

    # get key variables from configuration
    bufr2ioda_exe = config['executable']
    valid_time = config['valid time']
    dump = config['dump']
    bufr_dir = config['BUFR dir']
    yaml_template_dir = config['YAML template dir']
    work_dir = config['working dir']
    out_dir = config['output dir']

    # derived variables
    

    # get list of BUFR files in directory using glob
    bufr_files = os.path.join(bufr_dir, f"{dump}.t{cyc}z.*.bufr_d")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input YAML Configuration', required=True)
    args = parser.parse_args()
    run_BUFR2IODA(args.config)