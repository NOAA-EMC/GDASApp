#!/usr/bin/env python3
import argparse
import json
import os
from combine_base import Bufr2IodaBase
# from wxflow import Logger
from logging import Logger
from antcorr_application import ACCoeff, apply_ant_corr, remove_ant_corr, R1000, R1000000
from utils import timing_decorator

logger = Logger(os.path.basename(__file__), level='INFO')
AMSUA_TYPE_CHANGE_DATETIME = "2023120000"
BAMUA = '1BAMUA'
ESAMUA = 'ESAMUA'

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
    def re_map_variable(self):
        #  TODO replace this follow that in GSI
        # read_bufrtovs.f90
        # antcorr_application.f90
        # search the keyword “ta2tb” for details

        for sat_id in self.sat_ids:
            logger.info(f'Converting for {sat_id}, ...')
            ta = self.get_container_variable('variables', 'brightnessTemperature', sat_id)
            if ta.shape[0]:
                ifov = self.get_container_variable('variables', 'fieldOfViewNumber', sat_id)
                logger.info(f'ta before correction1: {ta[:100, :]}')
                tb = self.apply_corr(sat_id, ta, ifov)
                logger.info(f'tb after correction1: {tb[:100, :]}')
                self.replace_container_variable('variables', 'brightnessTemperature', tb, sat_id)

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

    convert_bamua = Bufr2IodaAmusa(yaml_order, args.config)
    convert_bamua.set_container()
    convert_esamua = Bufr2IodaAmusaChange(yaml_order, args.config)
    convert_esamua.set_container()
    convert_bamua.encode()
    convert_esamua.encode()
    print(convert_bamua.sat_ids)
    print(convert_esamua.sat_ids)
    # if set(convert_bamua.sat_ids) == set(convert_esamua.sat_ids):
    convert_bamua.container.append(convert_esamua.container)
    convert_bamua.encode()
    # else:
    #    logger.info('Sat ids are different:  {} '.format(set(convert_bamua.sat_ids)))

    logger.info('--Finished--')
