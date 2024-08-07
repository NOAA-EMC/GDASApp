#!/usr/bin/env python3
# (C) Copyright 2023 NOAA/NWS/NCEP/EMC
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

import sys
import numpy as np
import numpy.ma as ma
import os
import argparse
import math
import calendar
import time
from datetime import datetime
import json
from pyiodaconv import bufr
from collections import namedtuple
from pyioda import ioda_obs_space as ioda_ospace
from wxflow import Logger


def Compute_dateTime(cycleTimeSinceEpoch, dhr):

    int64_fill_value = np.int64(0)

    dateTime = np.zeros(dhr.shape, dtype=np.int64)
    for i in range(len(dateTime)):
        if ma.is_masked(dhr[i]):
            continue
        else:
            dateTime[i] = np.int64(dhr[i]*3600) + cycleTimeSinceEpoch

    dateTime = ma.array(dateTime)
    dateTime = ma.masked_values(dateTime, int64_fill_value)

    return dateTime


def bufr_to_ioda(config, logger):

    subsets = config["subsets"]
    logger.debug(f"Checking subsets = {subsets}")

    # Get parameters from configuration
    data_format = config["data_format"]
    source = config["source"]
    data_type = config["data_type"]
    data_description = config["data_description"]
    data_provider = config["data_provider"]
    cycle_type = config["cycle_type"]
    cycle_datetime = config["cycle_datetime"]
    dump_dir = config["dump_directory"]
    ioda_dir = config["ioda_directory"]
    cycle = config["cycle_datetime"]

    # Get derived parameters
    yyyymmdd = cycle[0:8]
    hh = cycle[8:10]

    reference_time = datetime.strptime(cycle, "%Y%m%d%H")
    reference_time = reference_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    reference_time_full = f"{yyyymmdd}{hh}00"

    logger.debug(f"reference_time = {reference_time}")

    # General informaton
    converter = 'BUFR to IODA Converter'
    platform_description = 'SFCSHP data from prepBUFR format'

    bufrfile = f"{cycle_type}.t{hh}z.{data_format}"
    DATA_PATH = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}",
                             str(hh), 'atmos', bufrfile)
    if not os.path.isfile(DATA_PATH):
        logger.info(f"DATA_PATH {DATA_PATH} does not exist")
        return
    logger.debug(f"The DATA_PATH is: {DATA_PATH}")

    # ============================================
    # Make the QuerySet for all the data we want
    # ============================================
    start_time = time.time()

    logger.debug('Making QuerySet ...')
    q = bufr.QuerySet(subsets)

    # ObsType
    q.add('observationType', '*/TYP')

    # MetaData
    q.add('stationIdentification', '*/SID')
    q.add('latitude', '*/YOB')
    q.add('longitude', '*/XOB')
    q.add('obsTimeMinusCycleTime', '*/DHR')
    q.add('height', '*/Z___INFO/Z__EVENT{1}/ZOB')
    q.add('pressure', '*/P___INFO/P__EVENT{1}/POB')

    # Quality Marker
    q.add('qualityMarkerStationPressure', '*/P___INFO/P__EVENT{1}/PQM')
    q.add('qualityMarkerStationElevation', '*/Z___INFO/Z__EVENT{1}/ZQM')

    # ObsError
    q.add('obsErrorStationPressure', '*/P___INFO/P__BACKG{1}/POE')

    # ObsValue
    q.add('stationPressure', '*/P___INFO/P__EVENT{1}/POB')
    q.add('stationElevation', '*/ELV')

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Running time for making QuerySet: {running_time} seconds")

    # ==============================================================
    # Open the BUFR file and execute the QuerySet to get ResultSet
    # Use the ResultSet returned to get numpy arrays of the data
    # ==============================================================
    start_time = time.time()

    logger.debug(f"Executing QuerySet to get ResultSet ...")
    with bufr.File(DATA_PATH) as f:
        try:
            r = f.execute(q)
        except Exception as err:
            logger.info(f'Return with {err}')
            return

    # ObsType
    logger.debug(" ... Executing QuerySet: get ObsType ...")
    typ = r.get('observationType')

    # MetaData
    logger.debug(" ... Executing QuerySet: get MetaData ...")
    sid = r.get('stationIdentification')
    lat = r.get('latitude')
    lon = r.get('longitude')
    lon[lon > 180] -= 360
    zob = r.get('height', type='float')
    pressure = r.get('pressure')
    pressure *= 100

    # Quality Information
    logger.debug(f" ... Executing QuerySet: get QualityMarker ...")
    pobqm = r.get('qualityMarkerStationPressure')
    zobqm = r.get('qualityMarkerStationElevation')

    # ObsError
    logger.debug(f" ... Executing QuerySet: get ObsError ...")
    poboe = r.get('obsErrorStationPressure')
    poboe *= 100

    # ObsValue
    logger.debug(f" ... Executing QuerySet: get ObsValue ...")
    elv = r.get('stationElevation', type='float')
    pob = r.get('stationPressure')
    pob *= 100

    logger.debug(f" ... Executing QuerySet: get dateTime ...")
    # DateTime: seconds since Epoch time
    dhr = r.get('obsTimeMinusCycleTime', type='float')

    logger.debug(f" ... Executing QuerySet: Done!")

    logger.debug(f" ... Executing QuerySet: Check BUFR variable generic \
                dimension and type ...")
    # Check BUFR variable generic dimension and type
    logger.debug(f"     typ       shape = {typ.shape}")
    logger.debug(f"     sid       shape = {sid.shape}")
    logger.debug(f"     dhr       shape = {dhr.shape}")
    logger.debug(f"     lat       shape = {lat.shape}")
    logger.debug(f"     lon       shape = {lon.shape}")
    logger.debug(f"     zob       shape = {zob.shape}")
    logger.debug(f"     pressure  shape = {pressure.shape}")

    logger.debug(f"     pobqm     shape = {pobqm.shape}")
    logger.debug(f"     zobqm     shape = {zobqm.shape}")

    logger.debug(f"     poboe     shape = {poboe.shape}")

    logger.debug(f"     elv       shape = {elv.shape}")
    logger.debug(f"     pob       shape = {pob.shape}")

    logger.debug(f"     dhr       type  = {dhr.shape}")

    logger.debug(f"     sid       type  = {sid.dtype}")
    logger.debug(f"     dhr       type  = {dhr.dtype}")
    logger.debug(f"     lat       type  = {lat.dtype}")
    logger.debug(f"     lon       type  = {lon.dtype}")
    logger.debug(f"     zob       type  = {zob.dtype}")
    logger.debug(f"     typ       type  = {typ.dtype}")
    logger.debug(f"     pressure  type  = {pressure.dtype}")

    logger.debug(f"     pobqm     type  = {pobqm.dtype}")
    logger.debug(f"     zobqm     type  = {zobqm.dtype}")

    logger.debug(f"     poboe     shape = {poboe.dtype}")

    logger.debug(f"     elv       type  = {elv.dtype}")
    logger.debug(f"     pob       type  = {pob.dtype}")

    logger.debug(f"     dhr       type  = {dhr.dtype}")

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Running time for executing QuerySet to get ResultSet: \
                {running_time} seconds")

    # =========================
    # Create derived variables
    # =========================
    start_time = time.time()

    logger.debug(f"Creating derived variables - dateTime ...")

    cycleTimeSinceEpoch = np.int64(calendar.timegm(time.strptime(
                                   reference_time_full, '%Y%m%d%H%M')))
    dateTime = Compute_dateTime(cycleTimeSinceEpoch, dhr)

    logger.debug(f"     Check derived variables type ... ")
    logger.debug(f"     dateTime shape = {dateTime.shape}")
    logger.debug(f"     dateTime type = {dateTime.dtype}")

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Running time for creating derived variables: \
                {running_time} seconds")

    # =====================================
    # Create IODA ObsSpace
    # Write IODA output
    # =====================================

    # Create the dimensions
    dims = {'Location': np.arange(0, lat.shape[0])}

    iodafile = f"{cycle_type}.t{hh}z.{data_type}.tm00.nc"
    OUTPUT_PATH = os.path.join(ioda_dir, iodafile)
    logger.debug(f" ... ... Create OUTPUT file: {OUTPUT_PATH}")

    path, fname = os.path.split(OUTPUT_PATH)
    if path and not os.path.exists(path):
        os.makedirs(path)

    obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)

    # Create Global attributes
    logger.debug(f" ... ... Create global attributes")

    obsspace.write_attr('Converter', converter)
    obsspace.write_attr('source', source)
    obsspace.write_attr('sourceFiles', bufrfile)
    obsspace.write_attr('dataProviderOrigin', data_provider)
    obsspace.write_attr('description', data_description)
    obsspace.write_attr('datetimeReference', reference_time)
    obsspace.write_attr('datetimeRange',
                        [str(min(dateTime)), str(max(dateTime))])
    obsspace.write_attr('platformLongDescription', platform_description)

    # Create IODA variables
    logger.debug(f" ... ... Create variables: name, type, units, & attributes")

    # Observation Type: Station Elevation
    obsspace.create_var('ObsType/stationElevation', dtype=typ.dtype,
                        fillval=typ.fill_value) \
        .write_attr('long_name', 'Station Elevation Observation Type') \
        .write_data(typ)

    # Observation Type: Station Pressure
    obsspace.create_var('ObsType/stationPressure', dtype=typ.dtype,
                        fillval=typ.fill_value) \
        .write_attr('long_name', 'Station Pressure Observation Type') \
        .write_data(typ)

    # Longitude
    obsspace.create_var('MetaData/longitude', dtype=lon.dtype,
                        fillval=lon.fill_value) \
        .write_attr('units', 'degrees_east') \
        .write_attr('valid_range', np.array([-180, 180], dtype=np.float32)) \
        .write_attr('long_name', 'Longitude') \
        .write_data(lon)

    # Latitude
    obsspace.create_var('MetaData/latitude', dtype=lat.dtype,
                        fillval=lat.fill_value) \
        .write_attr('units', 'degrees_north') \
        .write_attr('valid_range', np.array([-90, 90], dtype=np.float32)) \
        .write_attr('long_name', 'Latitude') \
        .write_data(lat)

    # Datetime
    obsspace.create_var('MetaData/dateTime', dtype=dateTime.dtype,
                        fillval=dateTime.fill_value) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'Datetime') \
        .write_data(dateTime)

    # Station Identification
    obsspace.create_var('MetaData/stationIdentification', dtype=sid.dtype,
                        fillval=sid.fill_value) \
        .write_attr('long_name', 'Station Identification') \
        .write_data(sid)

    # Station Elevation
    obsspace.create_var('MetaData/stationElevation', dtype=elv.dtype,
                        fillval=elv.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Station Elevation') \
        .write_data(elv)

    # Height
    obsspace.create_var('MetaData/height', dtype=zob.dtype,
                        fillval=zob.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Height') \
        .write_data(zob)

    # Pressure
    obsspace.create_var('MetaData/pressure', dtype=pressure.dtype,
                        fillval=pressure.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Pressure') \
        .write_data(pressure)

    # QualityMarker: Station Elevation
    obsspace.create_var('QualityMarker/stationElevation', dtype=zobqm.dtype,
                        fillval=zobqm.fill_value) \
        .write_attr('long_name', 'Station Elevation Quality Marker') \
        .write_data(zobqm)

    # QualityMarker: Station Pressure
    obsspace.create_var('QualityMarker/stationPressure', dtype=pobqm.dtype,
                        fillval=pobqm.fill_value) \
        .write_attr('long_name', 'Station Pressure Quality Marker') \
        .write_data(pobqm)

    # ObsError: station Pressure
    obsspace.create_var('ObsError/stationPressure', dtype=poboe.dtype,
                        fillval=poboe.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Station Pressure ObsError') \
        .write_data(poboe)

    # ObsValue: Station Elevation
    obsspace.create_var('ObsValue/stationElevation', dtype=elv.dtype,
                        fillval=elv.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Station Elevation') \
        .write_data(elv)

    # ObsValue: Station Pressure
    obsspace.create_var('ObsValue/stationPressure', dtype=pob.dtype,
                        fillval=pob.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Station Pressure') \
        .write_data(pob)

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Running time for splitting and output IODA: \
                {running_time} seconds")

    logger.debug("All Done!")


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
    logger = Logger('bufr2ioda_adpsfc_prepbufr.py', level=log_level,
                    colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Total running time: {running_time} seconds")
