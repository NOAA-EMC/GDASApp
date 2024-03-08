from datetime import datetime, timedelta
import os
import shutil
from dateutil import parser
import ufsda
import logging
import glob
import numpy as np
from wxflow import YAMLFile, parse_yaml, parse_j2yaml, FileHandler

__all__ = ['atm_background', 'atm_obs', 'bias_obs', 'background', 'background_ens', 'fv3jedi', 'obs', 'berror', 'gdas_fix', 'gdas_single_cycle']

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',
                    level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')


def soca_fix(config):
    """
    soca_fix(input_fix_dir, config):
        Stage fix files needed by SOCA for GDAS analyses
        input_fix_dir - path to root fix file directory
        working_dir - path to where files should be linked to
        config - dict containing configuration
    """

    fix_files = []
    # copy Rossby Radius file
    fix_files.append([os.path.join(config['soca_input_fix_dir'], 'rossrad.dat'),
                      os.path.join(config['stage_dir'], 'rossrad.dat')])
    # link name lists
    fix_files.append([os.path.join(config['soca_input_fix_dir'], 'field_table'),
                      os.path.join(config['stage_dir'], 'field_table')])
    fix_files.append([os.path.join(config['soca_input_fix_dir'], 'diag_table'),
                      os.path.join(config['stage_dir'], 'diag_table')])
    fix_files.append([os.path.join(config['soca_input_fix_dir'], 'MOM_input'),
                      os.path.join(config['stage_dir'], 'MOM_input')])
    # link field metadata
    fix_files.append([os.path.join(config['soca_input_fix_dir'], 'fields_metadata.yaml'),
                      os.path.join(config['stage_dir'], 'fields_metadata.yaml')])

    # link ufo <---> soca name variable mapping
    fix_files.append([os.path.join(config['soca_input_fix_dir'], 'obsop_name_map.yaml'),
                      os.path.join(config['stage_dir'], 'obsop_name_map.yaml')])

    # INPUT
    src_input_dir = os.path.join(config['soca_input_fix_dir'], 'INPUT')
    dst_input_dir = os.path.join(config['stage_dir'], 'INPUT')
    FileHandler({'mkdir': [dst_input_dir]}).sync()

    input_files = glob.glob(f'{src_input_dir}/*')
    for input_file in input_files:
        fname = os.path.basename(input_file)
        fix_files.append([os.path.join(src_input_dir, fname),
                          os.path.join(dst_input_dir, fname)])

    FileHandler({'copy': fix_files}).sync()
