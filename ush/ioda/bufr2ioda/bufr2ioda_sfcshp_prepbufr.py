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

    logger.debug(f"Reference time = {reference_time}")

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

    logger.debug("Making QuerySet ...")
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
    q.add('temperatureEventCode', '*/T___INFO/T__EVENT{1}/TPC')

#   # Quality Infomation (Quality Indicator)
    q.add('qualityMarkerStationElevation', '*/Z___INFO/Z__EVENT{1}/ZQM')
    q.add('qualityMarkerStationPressure', '*/P___INFO/P__EVENT{1}/PQM')
    q.add('qualityMarkerAirTemperature', '*/T___INFO/T__EVENT{1}/TQM')
    q.add('qualityMarkerSpecificHumidity', '*/Q___INFO/Q__EVENT{1}/QQM')
    q.add('qualityMarkerWindNorthward', '*/W___INFO/W__EVENT{1}/WQM')
    q.add('qualityMarkerSeaSurfaceTemperature', '*/SST_INFO/SSTEVENT{1}/SSTQM')

    # ObsValue
    q.add('stationElevation', '*/ELV')
    q.add('stationPressure', '*/P___INFO/P__EVENT{1}/POB')
    q.add('airTemperature', '*/T___INFO/T__EVENT{1}/TOB')
    q.add('specificHumidity', '*/Q___INFO/Q__EVENT{1}/QOB')
    q.add('windNorthward', '*/W___INFO/W__EVENT{1}/VOB')
    q.add('windEastward', '*/W___INFO/W__EVENT{1}/UOB')
    q.add('seaSurfaceTemperature', '*/SST_INFO/SSTEVENT{1}/SST1')

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

    logger.debug(f" ... Executing QuerySet: get metadata: basic ...")
    # ObsType
    logger.debug(" ... Executing QuerySet: get ObsType ...")
    typ = r.get('observationType')

    # MetaData
    logger.debug(" ... Executing QuerySet: MetaData ...")
    sid = r.get('stationIdentification')
    lat = r.get('latitude')
    lon = r.get('longitude')
    lon[lon > 180] -= 360
    zob = r.get('heightOfStation', type='float')
    pressure = r.get('pressure')
    pressure *= 100
    tpc = r.get('temperatureEventCode')

    # Quality Information
    logger.debug(f" ... Executing QuerySet: QualityMarker ...")
    zobqm = r.get('qualityMarkerStationElevation')
    pobqm = r.get('qualityMarkerStationPressure')
    tobqm = r.get('qualityMarkerAirTemperature')
    tsenqm = np.full(tobqm.shape[0], tobqm.fill_value)
    tsenqm = np.where(((tpc >= 1) & (tpc < 8)), tobqm, tsenqm)
    tvoqm = np.full(tobqm.shape[0], tobqm.fill_value)
    tvoqm = np.where((tpc == 8), tobqm, tvoqm)
    qobqm = r.get('qualityMarkerSpecificHumidity')
    wobqm = r.get('qualityMarkerWindNorthward')
    sstqm = r.get('qualityMarkerSeaSurfaceTemperature')

    logger.debug(f" ... Executing QuerySet: ObsValue ...")
    # ObsValue
    elv = r.get('stationElevation', type='float')
    pob = r.get('stationPressure')
    pob *= 100
    tob = r.get('airTemperature')
    tob += 273.15
    tsen = np.full(tob.shape[0], tob.fill_value)
    tsen = np.where(((tpc >= 1) & (tpc < 8)), tob, tsen)
    tvo = np.full(tob.shape[0], tob.fill_value)
    tvo = np.where((tpc == 8), tob, tvo)
    qob = r.get('specificHumidity', type='float')
    qob *= 0.000001
    uob = r.get('windEastward')
    vob = r.get('windNorthward')
    sst1 = r.get('seaSurfaceTemperature')

    logger.debug(f" ... Executing QuerySet: get datatime: observation time ...")
    # DateTime: seconds since Epoch time
    # IODA has no support for numpy datetime arrays dtype=datetime64[s]
    dhr = r.get('obsTimeMinusCycleTime', type='int64')

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
    logger.debug(f"     tpc       shape = {tpc.shape}")

    logger.debug(f"     zobqm     shape = {zobqm.shape}")
    logger.debug(f"     pobqm     shape = {pobqm.shape}")
    logger.debug(f"     tobqm     shape = {tobqm.shape}")
    logger.debug(f"     tsenqm    shape = {tsenqm.shape}")
    logger.debug(f"     tvoqm     shape = {tvoqm.shape}")
    logger.debug(f"     qobqm     shape = {qobqm.shape}")
    logger.debug(f"     wobqm     shape = {wobqm.shape}")
    logger.debug(f"     sstqm     shape = {sstqm.shape}")

    logger.debug(f"     elv       shape = {elv.shape}")
    logger.debug(f"     pob       shape = {pob.shape}")
    logger.debug(f"     tob       shape = {tob.shape}")
    logger.debug(f"     tsen      shape = {tsen.shape}")
    logger.debug(f"     tvo       shape = {tvo.shape}")
    logger.debug(f"     qob       shape = {qob.shape}")
    logger.debug(f"     uob       shape = {uob.shape}")
    logger.debug(f"     vob       shape = {vob.shape}")
    logger.debug(f"     sst1      shape = {sst1.shape}")

    logger.debug(f"     typ       type  = {typ.dtype}")
    logger.debug(f"     sid       type  = {sid.dtype}")
    logger.debug(f"     dhr       type  = {dhr.dtype}")
    logger.debug(f"     lat       type  = {lat.dtype}")
    logger.debug(f"     lon       type  = {lon.dtype}")
    logger.debug(f"     zob       type  = {zob.dtype}")
    logger.debug(f"     pressure  type  = {pressure.dtype}")
    logger.debug(f"     tpc       type  = {tpc.dtype}")

    logger.debug(f"     pobqm     type  = {pobqm.dtype}")
    logger.debug(f"     tobqm     type  = {tobqm.dtype}")
    logger.debug(f"     tsenqm    type  = {tsenqm.dtype}")
    logger.debug(f"     tvoqm     type  = {tvoqm.dtype}")
    logger.debug(f"     qobqm     type  = {qobqm.dtype}")
    logger.debug(f"     wobqm     type  = {wobqm.dtype}")
    logger.debug(f"     sstqm     type  = {sstqm.dtype}")

    logger.debug(f"     elv       type  = {elv.dtype}")
    logger.debug(f"     pob       type  = {pob.dtype}")
    logger.debug(f"     tob       type  = {tob.dtype}")
    logger.debug(f"     tsen      type  = {tsen.dtype}")
    logger.debug(f"     tvo       type  = {tvo.dtype}")
    logger.debug(f"     qob       type  = {qob.dtype}")
    logger.debug(f"     uob       type  = {uob.dtype}")
    logger.debug(f"     vob       type  = {vob.dtype}")
    logger.debug(f"     sst1      type  = {sst1.dtype}")

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
    logger.debug(f"Running time for creating derived variables: {running_time} \
                 seconds")

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

    # ObsType: stationElevation
    obsspace.create_var('ObsType/stationElevation', dtype=typ.dtype,
                        fillval=typ.fill_value) \
        .write_attr('long_name', 'Station Elevation Observation Type') \
        .write_data(typ)

    # ObsType: stationPressure
    obsspace.create_var('ObsType/stationPressure', dtype=typ.dtype,
                        fillval=typ.fill_value) \
        .write_attr('long_name', 'Station Pressure Observation Type') \
        .write_data(typ)

    # ObsType: air Temperature
    obsspace.create_var('ObsType/airTemperature', dtype=typ.dtype,
                        fillval=typ.fill_value) \
        .write_attr('long_name', 'Air Temperature Observation Type') \
        .write_data(typ)

    # ObsType: virtual Temperature
    obsspace.create_var('ObsType/virtualTemperature', dtype=typ.dtype,
                        fillval=typ.fill_value) \
        .write_attr('long_name', 'Virtual Temperature Observation Type') \
        .write_data(typ)

    # ObsType: Specific Humidity
    obsspace.create_var('ObsType/specificHumidity', dtype=typ.dtype,
                        fillval=typ.fill_value) \
        .write_attr('long_name', 'Specific Humidity Observation Type') \
        .write_data(typ)

    # ObsType: wind Eastward
    obsspace.create_var('ObsType/windEastward', dtype=typ.dtype,
                        fillval=typ.fill_value) \
        .write_attr('long_name', 'Wind Eastward Observation Type') \
        .write_data(typ)

    # ObsType: wind Northward
    obsspace.create_var('ObsType/windNorthward', dtype=typ.dtype,
                        fillval=typ.fill_value) \
        .write_attr('long_name', 'Wind Northward Observation Type') \
        .write_data(typ)

    # ObsType: Sea Surface Temperature
    obsspace.create_var('ObsType/seaSurfaceTemperature', dtype=typ.dtype,
                        fillval=typ.fill_value) \
        .write_attr('long_name', 'Sea Surface Temperature Observation Type') \
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

    # Temperature Event Code
    obsspace.create_var('MetaData/temperatureEventCode', dtype=tpc.dtype,
                        fillval=tpc.fill_value) \
        .write_attr('long_name', 'Temperature Event Code') \
        .write_data(tpc)

    # Quality Marker: Station Pressure
    obsspace.create_var('QualityMarker/stationPressure', dtype=pobqm.dtype,
                        fillval=pobqm.fill_value) \
        .write_attr('long_name', 'Station Pressure Quality Marker') \
        .write_data(pobqm)

    # Quality Marker: Air Temperature
    obsspace.create_var('QualityMarker/airTemperature', dtype=tobqm.dtype,
                        fillval=tobqm.fill_value) \
        .write_attr('long_name', 'Air Temperature Quality Marker') \
        .write_data(tsenqm)

    # Quality Marker: Virtual Temperature
    obsspace.create_var('QualityMarker/virtualTemperature', dtype=tobqm.dtype,
                        fillval=tobqm.fill_value) \
        .write_attr('long_name', 'Virtual Temperature Quality Marker') \
        .write_data(tvoqm)

    # Quality Marker: Specific Humidity
    obsspace.create_var('QualityMarker/specificHumidity', dtype=qobqm.dtype,
                        fillval=qobqm.fill_value) \
        .write_attr('long_name', 'Specific Humidity Quality Marker') \
        .write_data(qobqm)

    # Quality Marker: Eastward Wind
    obsspace.create_var('QualityMarker/windEastward', dtype=wobqm.dtype,
                        fillval=wobqm.fill_value) \
        .write_attr('long_name', 'Eastward Wind Quality Marker') \
        .write_data(wobqm)

    # Quality Marker: Northward Wind
    obsspace.create_var('QualityMarker/windNorthward', dtype=wobqm.dtype,
                        fillval=wobqm.fill_value) \
        .write_attr('long_name', 'Northward Wind Quality Marker') \
        .write_data(wobqm)

    # Quality Marker: Sea Surface Temperature
    obsspace.create_var('QualityMarker/seaSurfaceTemperature',
                        dtype=sstqm.dtype, fillval=sstqm.fill_value) \
        .write_attr('long_name', 'Sea Surface Temperature Quality Marker') \
        .write_data(sstqm)

    # Station Elevation
    obsspace.create_var('ObsValue/stationElevation', dtype=elv.dtype,
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

    # Air Temperature
    obsspace.create_var('ObsValue/airTemperature', dtype=tob.dtype,
                        fillval=tob.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Air Temperature') \
        .write_data(tsen)

    # Virtual Temperature
    obsspace.create_var('ObsValue/virtualTemperature', dtype=tob.dtype,
                        fillval=tob.fill_value) \
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

    # Sea Surface Temperature
    obsspace.create_var('ObsValue/seaSurfaceTemperature', dtype=sst1.dtype,
                        fillval=sst1.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Sea Surface Temperature') \
        .write_data(sst1)

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
    logger = Logger('bufr2ioda_sfcshp_prepbufr.py', level=log_level,
                    colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Total running time: {running_time} seconds")
