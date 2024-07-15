#!/usr/bin/env python3

import bufr
import netCDF4 as nc
import os
from pyioda.ioda.Engines.Bufr import Encoder
#from wxflow import Logger
import logging
#from bufr2ioda_ncep_1bmusa import Bufr2IodaAmusa
#from bufr2ioda_ncep_esamua import Bufr2IodaEsamusa

# logger = Logger(os.path.basename(__file__), level='INFO', colored_log=True)
logger = logging.getLogger(__name__)
YAML_PATH_ES = './bufr2ioda_esamua_mapping.yaml'
YAML_PATH_1B = './bufr2ioda_1bamua_mapping.yaml'
YAML_NORMAL = True  # current as normal need remap for path2/1bama

R1000 = 1000.0
R1000000 = 1000000.0
INVALID = R1000
# Cosmic background temperature. Taken from Mather,J.C. et. al., 1999, "Calibrator Design for the COBE
# Far-Infrared Absolute Spectrophotometer (FIRAS)"Astrophysical Journal, vol 512, pp 511-520
TSPACE = 2.7253

nc_dir = '/work2/noaa/da/xinjin/gdas-validation/global-workflow/sorc/gdas.cd/ush/ioda/bufr2ioda'


class ACCoeff:
    def __init__(self, ac_dir, sat_id='n19'):
        file_name = os.path.join(ac_dir, 'amsua_' + sat_id + '.ACCoeff.nc')
        nc_file = nc.Dataset(file_name)
        self.n_fovs = len(nc_file.dimensions['n_FOVs'])
        self.n_channels = len(nc_file.dimensions['n_Channels'])
        self.a_earth = nc_file.variables['A_earth'][:]
        self.a_platform = nc_file.variables['A_platform'][:]
        self.a_space = nc_file.variables['A_space'][:]
        self.a_ep = self.a_earth + self.a_platform
        self.a_sp = self.a_space * TSPACE


def remove_ant_corr(i, ac, ifov, t):
    # AC:             Structure containing the antenna correction coefficients for the sensor of interest.
    # iFOV:           The FOV index for a scanline of the sensor of interest.
    # T:              On input, this argument contains the brightness

    # print(f't before corr: {t[:100]}')
    t = ac.a_ep[i, ifov] * t + ac.a_sp[i, ifov]
    # print(f't after corr: {t[:100]}')
    t[(ifov < 1) | (ifov > ac.n_fovs)] = [INVALID]
    return t


def apply_ant_corr(i, ac, ifov, t):
    # t:              on input, this argument contains the antenna temperatures for the sensor channels.
    t = (t - ac.a_sp[i, ifov]) / ac.a_ep[i, ifov]
    t[(ifov < 1) | (ifov > ac.n_fovs)] = [INVALID]
    return t


def get_description(yaml_path):

    description = bufr.encoders.Description(yaml_path)

    return description


def apply_corr(sat_id, ta, ifov):
    # condition to do this? TODO check
    ac = ACCoeff(nc_dir)  # TODO add later
    if sat_id not in ['n15', 'n16']:
        # Convert antenna temperature to brightness temperature
        ifov = ifov.astype(int) - 1
        for i in range(ta.shape[1]):
            logger.info(f'inside loop for allpy ta to tb: i = {i}')
            x = ta[:, i]
            # logger.info(f'ta before correction: {x[:100]}')
            if YAML_NORMAL:
                x = apply_ant_corr(i, ac, ifov, x)
            else:
                x = remove_ant_corr(i, ac, ifov, x)
            # logger.info(f'ta after correction: {x[:100]}')
            x[x >= R1000] = R1000000
            ta[:, i] = x
    return ta


def re_map_variable(container):
    # read_bufrtovs.f90
    # antcorr_application.f90
    # search the keyword “ta2tb” for details
    sat_ids = container.all_sub_categories()
    logger.info(sat_ids)
    for sat_id in sat_ids:
        logger.info(f'Converting for {sat_id}, ...')
        print(f'Converting for {sat_id}, ...')
        ta = container.get('variables/brightnessTemperature', sat_id)
        if ta.shape[0]:
            ifov = container.get('variables/fieldOfViewNumber', sat_id)
            logger.info(f'ta before correction1: {ta[:100, :]}')
            tb = apply_corr(sat_id, ta, ifov)
            logger.info(f'tb after correction1: {tb[:100, :]}')
            container.replace('variables/brightnessTemperature', tb, sat_id)


def get_one_data(input_path, yaml_path, category):
    cache = bufr.DataCache.has(input_path, yaml_path)
    if cache:
        logger.info(f'The cache existed get data container from it')
        container = bufr.DataCache.get(input_path, yaml_path)
        #data = Encoder(get_description(yaml_path)).encode(container)[(category,)]
        #bufr.DataCache.mark_finished(input_path, yaml_path, [category])
    else:
        # If cacache does not exist, get data into cache
        # Get data info container first
        logger.info(f'The cache is not existed')
        container = bufr.Parser(input_path, yaml_path).parse()
        #logger.info(f'add original container list into a cache = {container.list()}')
        #bufr.DataCache.add(input_path, yaml_path, container.all_sub_categories(), container)
        #data = Encoder(get_description(yaml_path)).encode(container)[(category,)]
        #bufr.DataCache.mark_finished(input_path, yaml_path, [category])
    return cache, container


def mark_one_data(cache, input_path, yaml_path, category, container=None):
    if cache:
        logger.info(f'The cache existed get data container from it')
        bufr.DataCache.mark_finished(input_path, yaml_path, [category])
    else:
        logger.info(f'add original container list into a cache = {container.list()}')
        bufr.DataCache.add(input_path, yaml_path, container.all_sub_categories(), container)
        bufr.DataCache.mark_finished(input_path, yaml_path, [category])


def create_obs_group(input_path1, input_path2, category):
    logger.info(f'imput_path: {input_path1}, {input_path2}, and category: {category}')
    logger.info(f'Entering function to create obs group for {category} with yaml path {YAML_PATH_ES} and {YAML_PATH_1B}')
    cache_1, container_1 = get_one_data(input_path1, YAML_PATH_ES, category)
    cache_2, container_2 = get_one_data(input_path2, YAML_PATH_1B, category)

    re_map_variable(container_2)

    print(f'emily checking - Original container list = ', container_1.list())
    print(f'emily checking - Original container list = ', container_2.list())
    container = container_1
    container.append(container_2)

    print('Done')
    data = Encoder(get_description(YAML_PATH_ES)).encode(container)[(category,)]
    mark_one_data(cache_1, input_path1, YAML_PATH_ES, category, container=container_1)
    mark_one_data(cache_2, input_path2, YAML_PATH_1B, category, container=container_2)
    return data

