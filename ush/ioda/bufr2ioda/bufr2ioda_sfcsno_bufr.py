#!/usr/bin/env python3
# (C) Copyright 2024 NOAA/NWS/NCEP/EMC
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

import sys
import os
import argparse
import json
import numpy as np
import numpy.ma as ma
import calendar
import time
from datetime import datetime
from pyiodaconv import bufr
from collections import namedtuple
from pyioda import ioda_obs_space as ioda_ospace
from wxflow import Logger


def bufr_to_ioda(config, logger):

    subsets = config["subsets"]
    logger.debug(f"Checking subsets = {subsets}")

    # Get parameters from configuration
    data_format = config["data_format"]
    source = config["source"]
    data_type = config["data_type"]
    cycle_type = config["cycle_type"]
    cycle_datetime = config["cycle_datetime"]
    dump_dir = config["dump_directory"]
    ioda_dir = config["ioda_directory"]
    data_description = config["data_description"]
    data_provider = config["data_provider"]
    cycle = config["cycle_datetime"]

    # Get derived parameters
    yyyymmdd = cycle[0:8]
    hh = cycle[8:10]

    # General informaton
    converter = 'BUFR to IODA Converter'
    platform_description = 'snow depth data from BUFR format'

    bufrfile = f"{cycle_type}.t{hh}z.{data_type}.tm00.{data_format}"
    DATA_PATH = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}", str(hh), 'atmos', bufrfile)
    if not os.path.isfile(DATA_PATH):
        logger.info(f"DATA_PATH {DATA_PATH} does not exist")
        return
    logger.debug(f"The DATA_PATH is: {DATA_PATH}")

    # ============================================
    # Make the QuerySet for all the data we want
    # ============================================
    start_time = time.time()

    logger.debug('Making QuerySet ...')
    q = bufr.QuerySet()

    # MetaData
    q.add('year', '*/YEAR')
    q.add('month', '*/MNTH')
    q.add('day', '*/DAYS')
    q.add('hour', '*/HOUR')
    q.add('minute', '*/MINU')
    q.add('longitude', '[*/CLON, */CLONH]')
    q.add('latitude', '[*/CLAT, */CLATH]')
    q.add('stationElevation', '[*/SELV, */HSMSL]')
    q.add('stationIdentification', '*/RPID')

    # ObsValue
    q.add('totalSnowDepth', '[*/SNWSQ1/TOSD, */MTRMSC/TOSD, */STGDSNDM/TOSD]')
    q.add('groundState', '[*/GRDSQ1/SOGR, */STGDSNDM/SOGR]')

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Running time for making QuerySet: {running_time} seconds")

    # ================================================
    # Open the BUFR file and execute the QuerySet
    # ================================================
    start_time = time.time()

    logger.debug(f" ... Executing QuerySet: get data ...")
    with bufr.File(DATA_PATH) as f:
        try:
            r = f.execute(q)
        except Exception as err:
            logger.info(f'Return with {err}')
            return

    # Use the ResultSet returned to get numpy arrays of the data
    logger.debug(f" ... Executing QuerySet: get MetaData ...")

    lon = r.get('longitude')
    lat = r.get('latitude')
    ele = r.get('stationElevation')
    sid = r.get('stationIdentification')
    sogr = r.get('groundState')

    logger.debug(f" ... Executing QuerySet: get ObsValue ...")
    snod = r.get('totalSnowDepth')

    logger.debug(f" ... Convering snow depth unit from m into mm ...")
    snod *= 1000

    logger.debug(f" ... Create zero snow depth from sogr ...")
    for i in range(len(sogr)):
        if sogr[i] < 10.0 or sogr[i] == 11.0 or sogr[i] == 15.0:
            snod[i] = 0.0

    dateTime = r.get_datetime('year', 'month', 'day', 'hour', 'minute')
    dateTime = dateTime.astype(np.int64)

    logger.debug(f" ... Remove filled/missing snow values ...")
    mask = np.array(snod) < 1000000000
    lon = lon[mask]
    lat = lat[mask]
    ele = ele[mask]
    sid = sid[mask]
    sogr = sogr[mask]
    snod = snod[mask]
    dateTime = dateTime[mask]

    logger.debug(f" ... Remove negative snow values ...")
    mask = snod >= 0.0
    lon = lon[mask]
    lat = lat[mask]
    ele = ele[mask]
    sid = sid[mask]
    sogr = sogr[mask]
    snod = snod[mask]
    dateTime = dateTime[mask]

    logger.debug(f" ... Executing QuerySet: Done! ...")

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Running time for executing QuerySet to get ResultSet: \
                {running_time} seconds")

    # =====================================
    # Create IODA ObsSpace
    # Write IODA output
    # =====================================

    start_time = time.time()
    logger.debug(f" ... executing IODA output ...")
    # Create the dimensions
    dims = {'Location': snod.shape[0]}

    iodafile = f"{cycle_type}.t{hh}z.{data_type}.nc"
    OUTPUT_PATH = os.path.join(ioda_dir, iodafile)
    logger.debug(f" ... ... Create OUTPUT file: {OUTPUT_PATH}")

    path, fname = os.path.split(OUTPUT_PATH)
    if path and not os.path.exists(path):
        os.makedirs(path)

    obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)

    # Create the global attributes
    logger.debug(f" ... ... Create global attributes")

    obsspace.write_attr('Converter', converter)
    obsspace.write_attr('source', source)
    obsspace.write_attr('sourceFiles', bufrfile)
    obsspace.write_attr('dataProviderOrigin', data_provider)
    obsspace.write_attr('description', data_description)
    obsspace.write_attr('datetimeRange', [str(dateTime.min()), str(dateTime.max())])
    obsspace.write_attr('platformLongDescription', platform_description)

    # Create the variables
    logger.debug(f" ... ... Create variables: name, type, units, and attributes")
    obsspace.create_var('MetaData/dateTime', dtype=dateTime.dtype, fillval=dateTime.fill_value) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'Datetime') \
        .write_data(dateTime)

    obsspace.create_var('MetaData/latitude', dtype=lat.dtype, fillval=lat.fill_value) \
        .write_attr('units', 'degrees_north') \
        .write_attr('long_name', 'Latitude') \
        .write_attr('valid_range', [-90.0, 90.0]) \
        .write_data(lat)

    obsspace.create_var('MetaData/longitude', dtype=lon.dtype, fillval=lon.fill_value) \
        .write_attr('units', 'degrees_east') \
        .write_attr('long_name', 'Longitude') \
        .write_attr('valid_range', [-180.0, 180.0]) \
        .write_data(lon)

    obsspace.create_var('MetaData/stationElevation', dtype=ele.dtype, fillval=ele.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Station Elevation') \
        .write_data(ele)

    obsspace.create_var('MetaData/stationIdentification', dtype=sid.dtype, fillval=sid.fill_value) \
        .write_attr('long_name', 'Station Identification') \
        .write_data(sid)

    obsspace.create_var('ObsValue/totalSnowDepth', dtype=snod.dtype,
                        dim_list=['Location'], fillval=snod.fill_value) \
        .write_attr('units', 'mm') \
        .write_attr('long_name', 'Total Snow Depth') \
        .write_data(snod)

    obsspace.create_var('ObsValue/groundState', dtype=sogr.dtype,
                        dim_list=['Location'], fillval=sogr.fill_value) \
        .write_attr('units', 'index') \
        .write_attr('long_name', 'STATE OF THE GROUND') \
        .write_data(sogr)

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Running time for splitting and output IODA: \
                {running_time} seconds")

    logger.debug("IODA output done!")


if __name__ == '__main__':

    start_time = time.time()

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str,
                        help='Input JSON configuration',
                        required=True)
    parser.add_argument('-v', '--verbose',
                        help='print debug logging information',
                        action='store_true')
    args = parser.parse_args()

    log_level = 'DEBUG' if args.verbose else 'INFO'
    logger = Logger('bufr2ioda_sfcsno_bufr.py', level=log_level,
                    colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Total running time: {running_time} seconds")
