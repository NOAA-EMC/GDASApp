#!/usr/bin/env python3

import argparse
import json
import os
from combine_base import Bufr2IodaBase, CPP
from wxflow import Logger
from antcorr_application import ACCoeff, apply_ant_corr, remove_ant_corr, R1000, R1000000
from utils import timing_decorator, nc_merge

logger = Logger(os.path.basename(__file__), level='INFO')

BACKEND = CPP

AMSUA_TYPE_CHANGE_DATETIME = "2023120000"

BAMUA = '1BAMUA'
ESAMUA  = 'ESAMUA'

YAML_NORMAL = True  # current as normal


class Bufr2IodaAmusa(Bufr2IodaBase):
    def __init__(self, yaml_order, *args, **kwargs):
        self.yaml_order = yaml_order
        super().__init__(*args, **kwargs)

    def get_yaml_file(self):
        if self.yaml_order:
            return self.config['yaml_file'][0]
        else:
            return self.config['yaml_file'][1]


class Bufr2IodaAmusaChange(Bufr2IodaAmusa):
    def get_yaml_file(self):
        if self.yaml_order:
            return self.config['yaml_file'][1]
        else:
            return self.config['yaml_file'][0]

    def get_ac_dir(self):
        return self.config['ac_dir']

    @timing_decorator
    def re_map_variable(self, container):
        #  TODO replace this follow that in GSI
        # read_bufrtovs.f90
        # antcorr_application.f90
        # search the keyword “ta2tb” for details

        for sat_id in self.sat_ids:
            logger.info(f'Converting for {sat_id}, ...')
            ta = self.get_container_variable(container, 'ObsValue', 'brightnessTemperature', sat_id)
            if ta.shape[0]:
                if self.yaml_order:
                    ifov = self.get_container_variable(container, 'MetaData', 'sensorScanPosition', sat_id)
                else:
                    ifov = self.get_container_variable(container, 'MetaData', 'sensorScanPosition', sat_id)
                logger.info(f'ta before correction1: {ta[:100, :]}')
                tb = self.apply_corr(sat_id, ta, ifov)
                logger.info(f'tb after correction1: {tb[:100, :]}')
                self.replace_container_variable(container, 'ObsValue', 'brightnessTemperature', tb, sat_id)

    def apply_corr(self, sat_id, ta, ifov):
        ac = ACCoeff(self.get_ac_dir())  # TODO add later
        llll = 1  # TODO how to set this
        if llll == 1:
            if sat_id not in ['n15', 'n16']:
                # Convert antenna temperature to brightness temperature
                ifov = ifov.astype(int) - 1
                for i in range(ta.shape[1]):
                    logger.info(f'inside loop for allpy ta to tb: i = {i}')
                    x = ta[:, i]
                    # logger.info(f'ta before correction: {x[:100]}')
                    if self.yaml_order:
                        x = apply_ant_corr(i, ac, ifov, x)
                    else:
                        x = remove_ant_corr(i, ac, ifov, x)
                    # logger.info(f'ta after correction: {x[:100]}')
                    x[x >= R1000] = R1000000
                    ta[:, i] = x
        else:
            pass  # TODO after know how to set llll
        return ta


@timing_decorator
def merge(amsua_files, splits):
    ioda_files = [(f'amsua.{x}_ta.tm00.ncc', f'esamua.{x}.tm00.ncc',  f'amsua_{x}.tm00.nc') for x in splits]
    logger.info(f'Ioda files: {ioda_files}')
    file1 = [f for f in amsua_files[0].values()]
    file2 = [f for f in amsua_files[1].values()]
    obs_path_prefix = os.path.commonprefix([file1[0], file2[0]])
    logger.info(f'common prefix: {obs_path_prefix}')
    for ioda_file_0, ioda_file_1, ioda_file_t in ioda_files:
        try:
            nc_merge(obs_path_prefix + ioda_file_0,
                     obs_path_prefix + ioda_file_1,
                     obs_path_prefix + ioda_file_t
                     )
        except FileNotFoundError as e:
            logger.info(f'File not found exception: {e}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input JSON configuration', required=True)
    parser.add_argument('-v', '--verbose', help='print debug logging information',
                        action='store_true')
    args = parser.parse_args()
    log_level = 'DEBUG' if args.verbose else 'INFO'
    logger = Logger(os.path.basename(__file__), level=log_level)
    amsua_files = []
    splits = set()
    json_file_name = args.config
    with open(json_file_name, "r") as json_file:
        config = json.load(json_file)

    cycle_datetime = config["cycle_datetime"]
    if cycle_datetime >= AMSUA_TYPE_CHANGE_DATETIME:
        yaml_order = YAML_NORMAL
    else:
        yaml_order = not YAML_NORMAL
    logger.info(f'yaml order is {yaml_order}')
    BAMUA = '1BAMUA'
    ESAMUA = 'ESAMUA'
    for sat_type in [BAMUA, ESAMUA]:
        logger.info(f'Processing sat type: {sat_type}')
        if sat_type == BAMUA:
            convert = Bufr2IodaAmusa(yaml_order, args.config, backend=BACKEND)
        else:
            convert = Bufr2IodaAmusaChange(yaml_order, args.config, backend=BACKEND)

        convert.execute()
        amsua_files.append(convert.split_files)
        logger.info('Converting amsua type {} done!'.format(sat_type))
        splits.update(set(convert.sat_ids))

    logger.info('--start to merge--')
    merge(amsua_files, splits)
    logger.info('--Finished merge--')
