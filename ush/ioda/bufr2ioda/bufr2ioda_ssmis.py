#!/usr/bin/env python3
import argparse
import numpy as np
import yaml
import numpy.ma as ma
from pyiodaconv import bufr
import calendar
import json
import time
import math
import datetime
import os
from datetime import datetime
from pyioda import ioda_obs_space as ioda_ospace
from wxflow import Logger

from pprint import pprint

# ====================================================================
# Satellite Winds (AMV) BUFR dump file for AHI/Himawari
# ====================================================================
# All subsets contain all spectral bands: NC005044 NC005045 NC005046
# ====================================================================
# Spectral Band                 | Code (002023) | ObsType
# --------------------------------------------------------------------
# IRLW  (Freq < 5E+13)          |    Method 1   | 252
# VIS                           |    Method 2   | 242
# WV Cloud Top                  |    Method 3   | 250
# WV Clear Sky/ Deep Layer      |    Method 5   | 250
# ====================================================================

# Define and initialize  global variables
global float32_fill_value
global int32_fill_value
global int64_fill_value

float32_fill_value = np.float32(0)
int32_fill_value = np.int32(0)
int64_fill_value = np.int64(0)




def get_config(config, logger):

    subsets = config["subsets"]
    logger.debug(f"Checking subsets = {subsets}")

    # Get parameters from configuration
    subsets = config["subsets"]
    data_format = config["data_format"]
    data_type = config["data_type"]
    data_description = config["data_description"]
    data_provider = config["data_provider"]
    cycle_type = config["cycle_type"]
    dump_dir = config["dump_directory"]
    ioda_dir = config["ioda_directory"]
    cycle = config["cycle_datetime"]
    yyyymmdd = cycle[0:8]
    hh = cycle[8:10]

    satellite_info_array = config["satellite_info"]
    sensor_name = config["sensor_info"]["sensor_name"]
    sensor_full_name = config["sensor_info"]["sensor_full_name"]
    sensor_id = config["sensor_info"]["sensor_id"]

    # Get derived parameters
    yyyymmdd = cycle[0:8]
    hh = cycle[8:10]
    reference_time = datetime.strptime(cycle, "%Y%m%d%H")
    reference_time = reference_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    # General informaton
    converter = 'BUFR to IODA Converter'
    process_level = 'Level-2'
    platform_description = 'Himawari-8'
    sensor_description = 'Advanced Himawari Imager'

    logger.info(f'sensor_name = {sensor_name}')
    logger.info(f'sensor_full_name = {sensor_full_name}')
    logger.info(f'sensor_id = {sensor_id}')
    logger.info(f'reference_time = {reference_time}')

    bufrfile = f"{cycle_type}.t{hh}z.{data_type}.tm00.{data_format}"
    DATA_PATH = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}", str(hh), 'atmos', bufrfile)
    if not os.path.isfile(DATA_PATH):
        logger.info(f"DATA_PATH {DATA_PATH} does not exist")
        return
    logger.debug(f"The DATA_PATH is: {DATA_PATH}")



def get_result_set(data_path, q):
    logger.info('Executing QuerySet to get ResultSet')
    with bufr.File(data_path) as f:
        try:
            r = f.execute(q)
        except Exception as err:
            logger.info(f'Return with {err}')
            return

    # MetaData
    satid = r.get('satelliteId')
    year = r.get('year')
    month = r.get('month')
    day = r.get('day')
    hour = r.get('hour')
    minute = r.get('minute')
    second = r.get('second')
    lat = r.get('latitude')
    lon = r.get('longitude')
    satzenang = r.get('satelliteZenithAngle')
    pressure = r.get('pressure', type='float')
    chanfreq = r.get('sensorCentralFrequency', type='float')

    # Processing Center
    ogce = r.get('dataProviderOrigin')
    ga = r.get('windGeneratingApplication')

    # Quality Information
    qi = r.get('qualityInformationWithoutForecast', type='float')
    # For AHI/Himawari data, qi w/o forecast (qifn) is packaged in same
    # vector where ga == 102. Must conduct a search and extract the
    # correct vector for gnap and qi
    # 1. Find dimension-sizes of ga and qi (should be the same!)
    gDim1, gDim2 = np.shape(ga)
    qDim1, qDim2 = np.shape(qi)
    logger.info(f'Generating Application and Quality Information SEARCH:')
    logger.info(f'Dimension size of GNAP ({gDim1},{gDim2})')
    logger.info(f'Dimension size of PCCF ({qDim1},{qDim2})')
    # 2. Initialize gnap and qifn as None, and search for dimension of
    #    ga with values of 102. If the same column exists for qi, assign
    #    gnap to ga[:,i] and qifn to qi[:,i], else raise warning that no
    #    appropriate GNAP/PCCF combination was found
    gnap = None
    qifn = None
    for i in range(gDim2):
        if np.unique(ga[:, i].squeeze()) == 102:
            if i <= qDim2:
                logger.info(f'GNAP/PCCF found for column {i}')
                gnap = ga[:, i].squeeze()
                qifn = qi[:, i].squeeze()
            else:
                logger.info(f'ERROR: GNAP column {i} outside of PCCF dimension {qDim2}')
    if (gnap is None) & (qifn is None):
        logger.info(f'ERROR: GNAP == 102 NOT FOUND OR OUT OF PCCF DIMENSION-RANGE, WILL FAIL!')

    # Wind Retrieval Method Information
    swcm = r.get('windComputationMethod')

    # ObsValue
    # Wind direction and Speed
    wdir = r.get('windDirection', type='float')
    wspd = r.get('windSpeed')

    # DateTime: seconds since Epoch time
    # IODA has no support for numpy datetime arrays dtype=datetime64[s]
    timestamp = r.get_datetime('year', 'month', 'day', 'hour', 'minute', 'second').astype(np.int64)

    # Check BUFR variable generic dimension and type

    # Global variables declaration
    # Set global fill values
    float32_fill_value = satzenang.fill_value
    int32_fill_value = satid.fill_value
    int64_fill_value = timestamp.fill_value.astype(np.int64)



    # =========================
    # Create derived variables
    # =========================
    start_time = time.time()

    logger.info('Creating derived variables')
    logger.debug('Creating derived variables - wind components (uob and vob)')


    height = np.full_like(pressure, fill_value=pressure.fill_value, dtype=np.float32)
    stnelev = np.full_like(pressure, fill_value=pressure.fill_value, dtype=np.float32)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f'Processing time for creating derived variables : {running_time} seconds')

    # =====================================
    # Split output based on satellite id
    # Create IODA ObsSpace
    # Write IODA output
    # =====================================
    logger.info('Create IODA ObsSpace and Write IODA output based on satellite ID')

    # Find unique satellite identifiers in data to process
    unique_satids = np.unique(satid)
    logger.info(f'Number of Unique satellite identifiers: {len(unique_satids)}')
    logger.info(f'Unique satellite identifiers: {unique_satids}')

    logger.debug(f'Loop through unique satellite identifier {unique_satids}')

    logger.info("All Done!")


def get_yaml_config(yaml_file):
    with open(yaml_file, 'r') as file:
        yaml_config = yaml.load(file, Loader=yaml.FullLoader)
        pprint(yaml_config)
        return yaml_config


if __name__ == '__main__':


    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input JSON configuration', required=True)
    parser.add_argument('-v', '--verbose', help='print debug logging information',
                        action='store_true')
    args = parser.parse_args()

    log_level = 'DEBUG' if args.verbose else 'INFO'
    logger = Logger(os.path.basename(__file__), level=log_level, colored_log=True)

    yaml_config = get_yaml_config(args.config)

    get_config(yaml_config, logger)


