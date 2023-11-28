#!/usr/bin/env python3

import argparse
import os
from bufr2ioda_base import Bufr2IodaBase, CPP
from wxflow import Logger
from antcorr_application import ACCoeff, apply_ant_corr
from utils import timing_decorator, nc_merge

logger = Logger('BUFR2IODA_satwind_amv_goes.py', level='DEBUG')

R1000 = 1000.0
R1000000 = 1000000.0

SPLIT = ('metop-a', 'metop-b', 'metop-c', 'n17', 'n18', 'n19')
ioda_files = [(f'esamua.{x}.tm00.nc', f'amsua.{x}_ta.tm00.nc', f'amsua.{x}.tm00.nc') for x in SPLIT]

BACKEND = CPP


class Bufr2IodaAmusa(Bufr2IodaBase):
    def get_yaml_file(self):
        return self.config['yaml_file'][0]


class Bufr2IodaEbmua(Bufr2IodaBase):

    def get_yaml_file(self):
        return self.config['yaml_file'][1]

    @timing_decorator
    def re_map_variable(self, container):
        #  TODO replace this follow that in GSI
        # read_bufrtovs.f90
        # antcorr_application.f90
        # search the keyword “ta2tb” for details

        for sat_id in self.sat_ids:
            ta = self.get_container_variable(container, 'ObsValue/brightnessTemperature', sat_id)
            if ta.shape[0]:
                ifov = self.get_container_variable(container, 'MetaData/sensorScanPosition', sat_id)
                tb = self.apply_ant_corr(sat_id, ta, ifov)
                self.replace_container_variable(container, 'ObsValue/brightnessTemperature', tb, sat_id)

    def apply_ant_corr(self, sat_id, ta, ifov):
        ac = ACCoeff()  # TODO add later
        llll = 1  # TODO how to set this
        if llll == 1:
            if sat_id not in ['n15', 'n16']:
                # Convert antenna temperature to brightness temperature
                for i in range(ta.shape[0]):
                    x = ta[i, :]
                    apply_ant_corr(ac, ifov[i], x)  # TODO if this is too slow we might need to optimize it
                    x[x > R1000] = R1000000
        else:
            pass  # TODO after know how to set llll
        return ta


@timing_decorator
def merge(amsua_files):
    amsua_0 = amsua_files[0]
    amsua_1 = amsua_files[1]
    obs_Path_prefix = os.path.commonprefix([amsua_files[0][0], amsua_files[1][0]])
    for ioda_file_0, ioda_file_1, ioda_file_t in ioda_files:
        try:
            nc_merge(obs_Path_prefix + ioda_file_0, obs_Path_prefix + ioda_file_1, obs_Path_prefix + ioda_file_t)
        except FileNotFoundError as e:
            print(e)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # parser.add_argument('-t', '--type', type=str, help='Input Satellite type a/e', required=True)
    parser.add_argument('-c', '--config', type=str, help='Input JSON configuration', required=True)
    parser.add_argument('-v', '--verbose', help='print debug logging information',
                        action='store_true')
    args = parser.parse_args()
    log_level = 'DEBUG' if args.verbose else 'INFO'
    logger = Logger('BUFR2IODA_ncep_amsua.py', level=log_level)
    amsua_files = []
    for sat_type in ['a', 'e']:
        print(sat_type)
        if sat_type == 'a':
            convert = Bufr2IodaAmusa(args.config, backend=BACKEND)
        else:
            convert = Bufr2IodaEbmua(args.config, backend=BACKEND)

        convert.execute()
        amsua_files.append(convert.split_files)
        print(amsua_files)
        logger.info('Converting amsua type {} done!'.format(sat_type))

    print('--start to merge--')
    merge(amsua_files)
    print('--Finished merge--')
