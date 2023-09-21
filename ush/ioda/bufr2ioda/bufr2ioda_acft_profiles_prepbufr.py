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
    logger.info(f"Reference time = {reference_time}")

    # General informaton
    converter = 'BUFR to IODA Converter'
    platform_description = 'SFCSHP data from prepBUFR format'

    bufrfile = f"{cycle_type}.t{hh}z.{data_format}.acft_profiles"
    DATA_PATH = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}", str(hh),
                             bufrfile)

    # ============================================
    # Make the QuerySet for all the data we want
    # ============================================
    start_time = time.time()

    logger.info(f"Making QuerySet ...")
    q = bufr.QuerySet(subsets)

    # MetaData
    q.add('prepbufrDataLevelCategory', '*/PRSLEVLA/CAT')
    q.add('stationIdentification', '*/SID')
    q.add('latitude', '*/PRSLEVLA/DRFTINFO/YDR')
    q.add('longitude', '*/PRSLEVLA/DRFTINFO/XDR')
    q.add('obsTimeMinusCycleTime', '*/PRSLEVLA/DRFTINFO/HRDR')
    q.add('stationElevation', '*/ELV')
    q.add('aircraftFlightLevel', '*/PRSLEVLA/Z___INFO/Z__EVENT{1}/ZOB')
    q.add('pressure', '*/PRSLEVLA/P___INFO/P__EVENT{1}/POB')
    q.add('temperatureEventCode', '*/PRSLEVLA/T___INFO/T__EVENT{1}/TPC')
    q.add('instantaneousAltitudeRate', '*/PRSLEVLA/IALR')
    q.add('aircraftFlightPhase', '*/PRSLEVLA/ACFT_SEQ/POAF')

#   # Quality Infomation (Quality Indicator)
    q.add('qualityMarkerStationPressure',
          '*/PRSLEVLA/P___INFO/P__EVENT{1}/PQM')
    q.add('qualityMarkerAirTemperature', '*/PRSLEVLA/T___INFO/T__EVENT{1}/TQM')
    q.add('qualityMarkerSpecificHumidity',
          '*/PRSLEVLA/Q___INFO/Q__EVENT{1}/QQM')
    q.add('qualityMarkerWindNorthward', '*/PRSLEVLA/W___INFO/W__EVENT{1}/WQM')

    # ObsValue
    q.add('stationPressure', '*/PRSLEVLA/P___INFO/P__EVENT{1}/POB')
    q.add('airTemperature', '*/PRSLEVLA/T___INFO/T__EVENT{1}/TOB')
    q.add('virtualTemperature', '*/PRSLEVLA/T___INFO/TVO')
    q.add('specificHumidity', '*/PRSLEVLA/Q___INFO/Q__EVENT{1}/QOB')
    q.add('windNorthward', '*/PRSLEVLA/W___INFO/W__EVENT{1}/VOB')
    q.add('windEastward', '*/PRSLEVLA/W___INFO/W__EVENT{1}/UOB')

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

    logger.info(f" ... Executing QuerySet: get MetaData: basic ...")
    # MetaData
    cat = r.get('prepbufrDataLevelCategory', 'prepbufrDataLevelCategory')
    sid = r.get('stationIdentification', 'prepbufrDataLevelCategory')
    lat = r.get('latitude', 'prepbufrDataLevelCategory')
    lon = r.get('longitude', 'prepbufrDataLevelCategory')
    lon[lon > 180] -= 360
    elv = r.get('stationElevation', 'prepbufrDataLevelCategory', type='float')
    zob = r.get('aircraftFlightLevel', 'prepbufrDataLevelCategory')
    pressure = r.get('pressure', 'prepbufrDataLevelCategory')
    pressure *= 100
    tpc = r.get('temperatureEventCode', 'prepbufrDataLevelCategory')
    ialr = r.get('instantaneousAltitudeRate', 'prepbufrDataLevelCategory')
    poaf = r.get('aircraftFlightPhase', 'prepbufrDataLevelCategory')

    logger.info(f" ... Executing QuerySet: get QualityMarker information ...")
    # Quality Information
    pqm = r.get('qualityMarkerStationPressure', 'prepbufrDataLevelCategory')
    tqm = r.get('qualityMarkerAirTemperature', 'prepbufrDataLevelCategory')
    qqm = r.get('qualityMarkerSpecificHumidity', 'prepbufrDataLevelCategory')
    wqm = r.get('qualityMarkerWindNorthward', 'prepbufrDataLevelCategory')

    logger.info(f" ... Executing QuerySet: get ObsValue: stationPressure ...")
    # ObsValue
    pob = r.get('stationPressure', 'prepbufrDataLevelCategory')
    pob *= 100
    tob = r.get('airTemperature', 'prepbufrDataLevelCategory')
    tob += 273.15
    tvo = r.get('virtualTemperature', 'prepbufrDataLevelCategory')
    tvo += 273.15
    qob = r.get('specificHumidity', 'prepbufrDataLevelCategory', type='float')
    qob *= 0.000001
    uob = r.get('windEastward', 'prepbufrDataLevelCategory')
    vob = r.get('windNorthward', 'prepbufrDataLevelCategory')

    logger.info(f" ... Executing QuerySet: get datatime: observation time ...")
    # DateTime: seconds since Epoch time
    # IODA has no support for numpy datetime arrays dtype=datetime64[s]
    dhr = r.get('obsTimeMinusCycleTime', 'prepbufrDataLevelCategory',
                type='int64')

    logger.info(f" ... Executing QuerySet: Done!")

    logger.info(f" ... Executing QuerySet: Check BUFR variable generic \
                dimension and type ...")
    # Check BUFR variable generic dimension and type
    logger.info(f"     cat       shape = {cat.shape}")
    logger.info(f"     sid       shape = {sid.shape}")
    logger.info(f"     dhr       shape = {dhr.shape}")
    logger.info(f"     lat       shape = {lat.shape}")
    logger.info(f"     lon       shape = {lon.shape}")
    logger.info(f"     elv       shape = {elv.shape}")
    logger.info(f"     zob       shape = {zob.shape}")
    logger.info(f"     pressure  shape = {pressure.shape}")
    logger.info(f"     tpc       shape = {tpc.shape}")
    logger.info(f"     ialr      shape = {ialr.shape}")
    logger.info(f"     poaf      shape = {poaf.shape}")

    logger.info(f"     pqm       shape = {pqm.shape}")
    logger.info(f"     tqm       shape = {tqm.shape}")
    logger.info(f"     qqm       shape = {qqm.shape}")
    logger.info(f"     wqm       shape = {wqm.shape}")

    logger.info(f"     pob       shape = {pob.shape}")
    logger.info(f"     tob       shape = {pob.shape}")
    logger.info(f"     tvo       shape = {tvo.shape}")
    logger.info(f"     qob       shape = {qob.shape}")
    logger.info(f"     uob       shape = {uob.shape}")
    logger.info(f"     vob       shape = {vob.shape}")

    logger.info(f"     cat       type  = {cat.dtype}")
    logger.info(f"     sid       type  = {sid.dtype}")
    logger.info(f"     dhr       type  = {dhr.dtype}")
    logger.info(f"     lat       type  = {lat.dtype}")
    logger.info(f"     lon       type  = {lon.dtype}")
    logger.info(f"     elv       type  = {elv.dtype}")
    logger.info(f"     zob       type  = {zob.dtype}")
    logger.info(f"     pressure  type  = {pressure.dtype}")
    logger.info(f"     tpc       type  = {tpc.dtype}")
    logger.info(f"     ialr      type  = {ialr.dtype}")
    logger.info(f"     poaf      type  = {poaf.dtype}")

    logger.info(f"     pqm       type  = {pqm.dtype}")
    logger.info(f"     tqm       type  = {tqm.dtype}")
    logger.info(f"     qqm       type  = {qqm.dtype}")
    logger.info(f"     wqm       type  = {wqm.dtype}")

    logger.info(f"     pob       type  = {pob.dtype}")
    logger.info(f"     tob       type  = {tob.dtype}")
    logger.info(f"     tvo       type  = {tvo.dtype}")
    logger.info(f"     qob       type  = {qob.dtype}")
    logger.info(f"     uob       type  = {uob.dtype}")
    logger.info(f"     vob       type  = {vob.dtype}")

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
    dateTime_max = ma.MaskedArray.max(dateTime)
    dateTime_min = ma.MaskedArray.min(dateTime)

    logger.info(f"     Check drived variables type ... ")
    logger.info(f"     dateTime shape = {dateTime.shape}")
    logger.info(f"     dateTime type = {dateTime.dtype}")
    logger.info(f"     dateTime max = {dateTime_max}")
    logger.info(f"     dateTime min = {dateTime_min}")

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
    obsspace.write_attr('datetimeRange', [str(dateTime_min),
                        str(dateTime_max)])
    obsspace.write_attr('platformLongDescription', platform_description)

    # Create IODA variables
    logger.info(f" ... ... Create variables: name, type, units, & attributes")
    # PrepBUFR Data Level Category
    obsspace.create_var('MetaData/prepbufrDataLevelCategory', dtype=cat.dtype,
                        fillval=cat.fill_value) \
        .write_attr('units', '1') \
        .write_attr('long_name', 'prepBUFR Data Level Category') \
        .write_data(cat)

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
        .write_attr('units', '1') \
        .write_attr('long_name', 'Station Identification') \
        .write_data(sid)

    # Station Elevation
    obsspace.create_var('MetaData/stationElevation', dtype=elv.dtype,
                        fillval=elv.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Station Elevation') \
        .write_data(elv)

    # AircraftFlightLevel
    obsspace.create_var('MetaData/aircraftFlightLevel', dtype=zob.dtype,
                        fillval=zob.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Aircraft Flight Level') \
        .write_data(zob)

    # Pressure
    obsspace.create_var('MetaData/pressure', dtype=pressure.dtype,
                        fillval=pressure.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Pressure') \
        .write_data(pressure)

    # Temperature Event Code
    obsspace.create_var('MetaData/temperatureEventCode', dtype=tpc.dtype,
                        fillval=tpc.fill_value) \
        .write_attr('long_name', 'Temperature Event Code') \
        .write_data(tpc)

    # Instantaneous Altitude Rate
    obsspace.create_var('MetaData/instantaneousAltitudeRate', dtype=ialr.dtype,
                        fillval=ialr.fill_value) \
        .write_attr('long_name', 'Instantaneous Altitude Rate') \
        .write_data(ialr)

    # Aircraft Flight Phase
    obsspace.create_var('MetaData/aircraftFlightPhase', dtype=poaf.dtype,
                        fillval=poaf.fill_value) \
        .write_attr('long_name', 'Aircraft Flight Phase') \
        .write_data(poaf)

    # Quality Marker: Station Pressure
    obsspace.create_var('QualityMarker/stationPressure', dtype=pqm.dtype,
                        fillval=pqm.fill_value) \
        .write_attr('long_name', 'Station Pressure Quality Marker') \
        .write_data(pqm)

    # Quality Marker: Air Temperature
    obsspace.create_var('QualityMarker/airTemperature', dtype=tqm.dtype,
                        fillval=tqm.fill_value) \
        .write_attr('long_name', 'Air Temperature Quality Marker') \
        .write_data(tqm)

    # Quality Marker: Specific Humidity
    obsspace.create_var('QualityMarker/specificHumidity', dtype=qqm.dtype,
                        fillval=qqm.fill_value) \
        .write_attr('long_name', 'Specific Humidity Quality Marker') \
        .write_data(qqm)

    # Quality Marker: Northward Wind
    obsspace.create_var('QualityMarker/windNorthward', dtype=wqm.dtype,
                        fillval=wqm.fill_value) \
        .write_attr('long_name', 'Northward Wind Quality Marker') \
        .write_data(wqm)

    # Station Pressure
    obsspace.create_var('ObsValue/pressure', dtype=pob.dtype,
                        fillval=pob.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Station Pressure') \
        .write_data(pob)

    # Air Temperature
    obsspace.create_var('ObsValue/airTemperature', dtype=tob.dtype,
                        fillval=tob.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Air Temperature') \
        .write_data(tob)

    # Virtual Temperature
    obsspace.create_var('ObsValue/virtualTemperature', dtype=tvo.dtype,
                        fillval=tvo.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Virtual Temperature') \
        .write_data(tvo)

    # Specific Humidity
    obsspace.create_var('ObsValue/specificHumidity', dtype=qob.dtype,
                        fillval=qob.fill_value) \
        .write_attr('units', 'kg kg-1') \
        .write_attr('long_name', 'Specific Humidity') \
        .write_data(qob)

    # Eastward Wind
    obsspace.create_var('ObsValue/windEastward', dtype=uob.dtype,
                        fillval=uob.fill_value) \
        .write_attr('units', 'm s-1') \
        .write_attr('long_name', 'Eastward Wind') \
        .write_data(uob)

    # Northward Wind
    obsspace.create_var('ObsValue/windNorthward', dtype=vob.dtype,
                        fillval=vob.fill_value) \
        .write_attr('units', 'm s-1') \
        .write_attr('long_name', 'Northward Wind') \
        .write_data(vob)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Running time for splitting and output IODA: {running_time} \
                 seconds")

    logger.info(f"All Done!")


if __name__ == '__main__':

    start_time = time.time()

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str,
                        help='Input JSON configuration', required=True)
    parser.add_argument('-v', '--verbose',
                        help='print debug logging information',
                        action='store_true')
    args = parser.parse_args()

    log_level = 'DEBUG' if args.verbose else 'INFO'
    logger = Logger('bufr2ioda_acft_profiles_prepbufr.py', level=log_level,
                    colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Total running time: {running_time} seconds")
