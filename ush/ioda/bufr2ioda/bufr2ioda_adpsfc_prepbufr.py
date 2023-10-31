#!/usr/bin/env python3
# (C) Copyright 2023 NOAA/NWS/NCEP/EMC
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

import sys
import numpy as np
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

    dhr = np.int64(dhr*3600)
    dateTime = dhr + cycleTimeSinceEpoch

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

    logger.info(f"reference_time = {reference_time}")

    # General informaton
    converter = 'BUFR to IODA Converter'
    platform_description = 'SFCSHP data from prepBUFR format'

    bufrfile = f"{cycle_type}.t{hh}z.{data_format}"
    DATA_PATH = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}",
                             str(hh), bufrfile)

    logger.info(f"The DATA_PATH is: {DATA_PATH}")

    # ============================================
    # Make the QuerySet for all the data we want
    # ============================================
    start_time = time.time()

    logger.info('Making QuerySet ...')
    q = bufr.QuerySet(subsets)

    # ObsType
    q.add('observationType', '*/TYP')
    
    # MetaData
    q.add('stationIdentification', '*/SID')
    q.add('latitude', '*/YOB')
    q.add('longitude', '*/XOB')
    q.add('obsTimeMinusCycleTime', '*/DHR')
    q.add('heightOfStation', '*/Z___INFO/Z__EVENT{1}/ZOB')
    q.add('pressure', '*/P___INFO/P__EVENT{1}/POB')

#   # Quality Infomation (Quality Indicator)
    q.add('qualityMarkerStationPressure', '*/P___INFO/P__EVENT{1}/PQM')
    q.add('qualityMarkerStationElevation', '*/Z___INFO/Z__EVENT{1}/ZQM')
    
    # ObsValue
    q.add('stationPressure', '*/P___INFO/P__EVENT{1}/POB')
    q.add('stationElevation', '*/ELV')

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Running time for making QuerySet: {running_time} seconds")

    # ==============================================================
    # Open the BUFR file and execute the QuerySet to get ResultSet
    # Use the ResultSet returned to get numpy arrays of the data
    # ==============================================================
    start_time = time.time()

    logger.info(f"Executing QuerySet to get ResultSet ...")
    with bufr.File(DATA_PATH) as f:
        r = f.execute(q)
    
    logger.info(" ... Executing QuerySet: get ObsType ...")
    # ObsType
    typ = r.get('observationType')

    logger.info(" ... Executing QuerySet: get MetaData ...")
    # MetaData
    sid = r.get('stationIdentification')
    lat = r.get('latitude')
    lon = r.get('longitude')
    lon[lon > 180] -= 360
    zob = r.get('heightOfStation', type='float')
    pressure = r.get('pressure')
    pressure *= 100

    logger.info(f" ... Executing QuerySet: get QualityMarker information ...")
    # Quality Information
    pobqm = r.get('qualityMarkerStationPressure')
    zobqm = r.get('qualityMarkerStationElevation')
    
    logger.info(f" ... Executing QuerySet: get obsvalue: stationPressure ...")
    # ObsValue
    elv = r.get('stationElevation', type='float')
    pob = r.get('stationPressure')
    pob *= 100

    logger.info(f" ... Executing QuerySet: get datatime: observation time ...")
    # DateTime: seconds since Epoch time
    # IODA has no support for numpy datetime arrays dtype=datetime64[s]
    dhr = r.get('obsTimeMinusCycleTime', type='int64')

    logger.info(f" ... Executing QuerySet: Done!")

    logger.info(f" ... Executing QuerySet: Check BUFR variable generic \
                dimension and type ...")
    # Check BUFR variable generic dimension and type
    logger.info(f"     typ       shape = {typ.shape}")
    logger.info(f"     sid       shape = {sid.shape}")
    logger.info(f"     dhr       shape = {dhr.shape}")
    logger.info(f"     lat       shape = {lat.shape}")
    logger.info(f"     lon       shape = {lon.shape}")
    logger.info(f"     zob       shape = {zob.shape}")
    logger.info(f"     pressure  shape = {pressure.shape}")

    logger.info(f"     pobqm     shape = {pobqm.shape}")
    logger.info(f"     zobqm     shape = {zobqm.shape}")
    logger.info(f"     elv       shape = {elv.shape}")
    logger.info(f"     pob       shape = {pob.shape}")

    logger.info(f"     sid       type  = {sid.dtype}")
    logger.info(f"     dhr       type  = {dhr.dtype}")
    logger.info(f"     lat       type  = {lat.dtype}")
    logger.info(f"     lon       type  = {lon.dtype}")
    logger.info(f"     zob       type  = {zob.dtype}")
    logger.info(f"     typ       type  = {typ.dtype}")
    logger.info(f"     pressure  type  = {pressure.dtype}")

    logger.info(f"     pobqm     type  = {pobqm.dtype}")
    logger.info(f"     zobqm     type  = {zobqm.dtype}")
    logger.info(f"     elv       type  = {elv.dtype}")
    logger.info(f"     pob       type  = {pob.dtype}")

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Running time for executing QuerySet to get ResultSet: \
                {running_time} seconds")

    # =========================
    # Create derived variables
    # =========================
    start_time = time.time()

    logger.info(f"Creating derived variables - dateTime ...")

    cycleTimeSinceEpoch = np.int64(calendar.timegm(time.strptime(
                                   reference_time_full, '%Y%m%d%H%M')))
    dateTime = Compute_dateTime(cycleTimeSinceEpoch, dhr)

    logger.info(f"     Check derived variables type ... ")
    logger.info(f"     dateTime shape = {dateTime.shape}")
    logger.info(f"     dateTime type = {dateTime.dtype}")

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Running time for creating derived variables: \
                {running_time} seconds")

    # =====================================
    # Create IODA ObsSpace
    # Write IODA output
    # =====================================

    # Create the dimensions
    dims = {'Location': np.arange(0, lat.shape[0])}

    iodafile = f"{cycle_type}.t{hh}z.{data_type}.{data_format}.nc"
    OUTPUT_PATH = os.path.join(ioda_dir, iodafile)
    logger.info(f" ... ... Create OUTPUT file: {OUTPUT_PATH}")

    path, fname = os.path.split(OUTPUT_PATH)
    if path and not os.path.exists(path):
        os.makedirs(path)

    obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)

    # Create Global attributes
    logger.info(f" ... ... Create global attributes")

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
    logger.info(f" ... ... Create variables: name, type, units, & attributes")

    # Observation Type - Station Elevation
    obsspace.create_var('ObsType/stationElevation', dtype=typ.dtype,
                        fillval=typ.fill_value) \
        .write_attr('long_name', 'Station Elevation Observation Type') \
        .write_data(typ)

    # Observation Type - Station Pressure
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

    # Height Of Station
    obsspace.create_var('MetaData/heightOfStation', dtype=zob.dtype,
                        fillval=zob.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Height Of Station') \
        .write_data(zob)

    # Pressure
    obsspace.create_var('MetaData/pressure', dtype=pressure.dtype,
                        fillval=pressure.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Pressure') \
        .write_data(pressure)

    # QualityMarker - Station Elevation
    obsspace.create_var('QualityMarker/stationElevation', dtype=zobqm.dtype,
                        fillval=zobqm.fill_value) \
        .write_attr('long_name', 'Station Elevation Quality Marker') \
        .write_data(zobqm)

    # QualityMarker - Station Pressure
    obsspace.create_var('QualityMarker/stationPressure', dtype=pobqm.dtype,
                        fillval=pobqm.fill_value) \
        .write_attr('long_name', 'Station Pressure Quality Marker') \
        .write_data(pobqm)

    # Station Elevation
    obsspace.create_var('ObaValue/stationElevation', dtype=elv.dtype,
                        fillval=elv.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Station Elevation') \
        .write_data(elv)

    # Station Pressure
    obsspace.create_var('ObsValue/stationPressure', dtype=pob.dtype,
                        fillval=pob.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Station Pressure') \
        .write_data(pob)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Running time for splitting and output IODA: \
                {running_time} seconds")

    logger.info("All Done!")


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
    logger.info(f"Total running time: {running_time} seconds")
