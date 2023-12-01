#!/usr/bin/env python3

import argparse
import os
from combine_base import Bufr2IodaBase, CPP
from wxflow import Logger
from antcorr_application import ACCoeff, apply_ant_corr
from utils import timing_decorator, nc_merge

logger = Logger(os.path.basename(__file__), level='INFO')

R1000 = 1000.0
R1000000 = 1000000.0

BACKEND = CPP


class Bufr2IodaAmusa(Bufr2IodaBase):
    def get_yaml_file(self):
        return self.config['yaml_file'][0]


class Bufr2IodaEbmua(Bufr2IodaBase):

    def get_yaml_file(self):
        return self.config['yaml_file'][1]

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
               ifov = self.get_container_variable(container, 'MetaData', 'sensorScanPosition', sat_id)
               tb = self.apply_ant_corr(sat_id, ta, ifov)
               self.replace_container_variable(container, 'ObsValue', 'brightnessTemperature', tb, sat_id)

    def apply_ant_corr(self, sat_id, ta, ifov):
        ac = ACCoeff(self.get_ac_dir())  # TODO add later
        llll = 1  # TODO how to set this
        if llll == 1:
            if sat_id not in ['n15', 'n16']:
                # Convert antenna temperature to brightness temperature
                ifov = ifov.astype(int) - 1
                for i in range(ta.shape[1]):
                    x = ta[:, i]
                    apply_ant_corr(i, ac, ifov, x)
                    x[x > R1000] = R1000000
        else:
            pass  # TODO after know how to set llll
        return ta


@timing_decorator
def merge(amsua_files, splits):
    ioda_files = [(f'esamua.{x}.tm00.ncc', f'amsua.{x}_ta.tm00.ncc', f'amsua.{x}.tm00.nc') for x in splits]
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
    for sat_type in ['a', 'e']:
        logger.info(f'Processing sat type: {sat_type}')
        if sat_type == 'a':
            convert = Bufr2IodaAmusa(args.config, backend=BACKEND)
        else:
            convert = Bufr2IodaEbmua(args.config, backend=BACKEND)

        convert.execute()
        amsua_files.append(convert.split_files)
        logger.info('Converting amsua type {} done!'.format(sat_type))
        splits.update(set(convert.sat_ids))

    logger.info('--start to merge--')
    merge(amsua_files, splits)
    logger.info('--Finished merge--')
