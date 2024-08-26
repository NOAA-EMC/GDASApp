#!/usr/bin/env python3
# (C) Copyright 2024 NOAA/NWS/NCEP/EM
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
import math
from datetime import datetime
from pyiodaconv import bufr
from collections import namedtuple
from pyioda import ioda_obs_space as ioda_ospace
from wxflow import Logger
import copy
import warnings
# suppress warnings
warnings.filterwarnings('ignore')


def Compute_WindComponents_from_WindDirection_and_WindSpeed(wdir, wspd):

    uob = (-wspd * np.sin(np.radians(wdir))).astype(np.float32)
    vob = (-wspd * np.cos(np.radians(wdir))).astype(np.float32)

    uob = ma.array(uob)
    uob = ma.masked_values(uob, uob.fill_value)
    vob = ma.array(vob)
    vob = ma.masked_values(vob, vob.fill_value)

    return uob, vob


def Compute_SpecificHumidity_from_dewPoint_and_Pressure(tmdp, prlc):

    # est is saturated vapor pressure in Mb
    est = 6.1078 * np.exp((17.269 * (tmdp - 273.16))/((tmdp - 273.16)+237.3))
    # Change est from Mb to Pa
    est = est*100.

    # specificHumidity (qob) is in kg/kg
    qob = (0.622 * est)/(prlc - (0.378 * est))
    qob = ma.array(qob)
    qob = ma.masked_values(qob, qob.fill_value)

    return qob


def bufr_to_ioda(config, logger):

    subsets = config["subsets"]
    logger.debug(f"Checking subsets = {subsets}")

    # Get parameters from configuration
    data_format = config["data_format"]
    data_type = config["data_type"]
    data_description = config["data_description"]
    data_provider = config["data_provider"]
    cycle_type = config["cycle_type"]
    cycle_datetime = config["cycle_datetime"]
    dump_dir = config["dump_directory"]
    ioda_dir = config["ioda_directory"]
    cycle = config["cycle_datetime"]
    source = config["source"]

    # Get derived parameters
    yyyymmdd = cycle[0:8]
    hh = cycle[8:10]

    # General informaton
    converter = 'BUFR to IODA Converter'
    platform_description = 'ADPUPA BUFR Dump'

    bufrfile = f"{cycle_type}.t{hh}z.{data_type}.tm{hh}.{data_format}"
    DATA_PATH = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}", str(hh), f"atmos", bufrfile)
    if not os.path.isfile(DATA_PATH):
        logger.info(f"DATA_PATH {DATA_PATH} does not exist")
        return
    logger.debug(f"The DATA_PATH is: {DATA_PATH}")

    # ============================================
    # Make the QuerySet for all the data we want
    # ============================================
    start_time = time.time()

    logger.info('Making QuerySet')
    q = bufr.QuerySet()

    # MetaData
    q.add('latitude', '*/CLAT')
    q.add('longitude', '*/CLON')
    q.add('stationIdentification', '*/RPID')
    q.add('stationElevation', '*/SELV')
    q.add('pressure', '*/UARLV/PRLC')
    # MetaData/Observation Time
    q.add('year', '*/YEAR')
    q.add('month', '*/MNTH')
    q.add('day', '*/DAYS')
    q.add('hour', '*/HOUR')
    # MetaData/Receipt Time
    q.add('receiptTimeSignificance', '*/RCPTIM{1}/RCTS')
    q.add('receiptYear', '*/RCPTIM{1}/RCYR')
    q.add('receiptMonth', '*/RCPTIM{1}/RCMO')
    q.add('receiptDay', '*/RCPTIM{1}/RCDY')
    q.add('receiptHour', '*/RCPTIM{1}/RCHR')
    q.add('receiptMinute', '*/RCPTIM{1}/RCMI')
    # MetaData/Launch Time
    q.add('launchHour', '*/UASDG/UALNHR')
    q.add('launchMinute', '*/UASDG/UALNMN')

    # ObsValue
    q.add('airTemperature', '*/UARLV/UATMP/TMDB')
    q.add('dewpointTemperature', '*/UARLV/UATMP/TMDP')
    q.add('windDirection', '*/UARLV/UAWND/WDIR')
    q.add('windSpeed', '*/UARLV/UAWND/WSPD')

    # QualityMark
    q.add('pressureQM', '*/UARLV/QMPR')
    q.add('airTemperatureQM', '*/UARLV/UATMP/QMAT')
    q.add('dewpointTemperatureQM', '*/UARLV/UATMP/QMDD')
    q.add('windSpeedQM', '*/UARLV/UAWND/QMWN')

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f'Running time for making QuerySet : {running_time} seconds')

    # ==============================================================
    # Open the BUFR file and execute the QuerySet to get ResultSet
    # Use the ResultSet returned to get numpy arrays of the data
    # ==============================================================
    start_time = time.time()

    logger.info(f"Executing QuerySet for ADPUPA BUFR DUMP to get ResultSet ...")
    with bufr.File(DATA_PATH) as f:
        try:
            r = f.execute(q)
        except Exception as err:
            logger.info(f'Return with {err}')
            return

    # MetaData
    logger.debug(f" ... Executing QuerySet: get MetaData ...")
    clat = r.get('latitude', group_by='pressure')
    clon = r.get('longitude', group_by='pressure')
    rpid = r.get('stationIdentification', group_by='pressure')
    selv = r.get('stationElevation', group_by='pressure', type='float')
    prlc = r.get('pressure', group_by='pressure', type='float')

    # MetaData/Observation Time
    year = r.get('year', group_by='pressure')
    month = r.get('month', group_by='pressure')
    day = r.get('day', group_by='pressure')
    hour = r.get('hour', group_by='pressure')
    # DateTime: seconds since Epoch time
    # IODA has no support for numpy datetime arrays dtype=datetime64[s]
    timestamp = r.get_datetime('year', 'month', 'day', 'hour', group_by='pressure').astype(np.int64)
    int64_fill_value = np.int64(0)
    timestamp = ma.array(timestamp)
    timestamp = ma.masked_values(timestamp, int64_fill_value)

    # MetaData/Receipt Time
    rcts = r.get('receiptTimeSignificance', group_by='pressure')
    receiptYear = r.get('receiptYear', group_by='pressure')
    receiptMonth = r.get('receiptMonth', group_by='pressure')
    receiptDay = r.get('receiptDay', group_by='pressure')
    receiptHour = r.get('receiptHour', group_by='pressure')
    receiptMinute = r.get('receiptMinute', group_by='pressure')
    logger.debug(f" ... Executing QuerySet: get datatime: receipt time ...")
    receipttime1 = r.get_datetime('receiptYear', 'receiptMonth', 'receiptDay', 'receiptHour', 'receiptMinute', group_by='pressure').astype(np.int64)
    # Extract receipttime from receipttime1, which belongs to RCTS=0, i.e. General decoder receipt time
    receipttime = receipttime1
    receipttime = np.where(rcts == 0, receipttime1, receipttime)
    receipttime = ma.array(receipttime)
    receipttime = ma.masked_values(receipttime, int64_fill_value)

    # MetaData/Launch Time
    launchHour = r.get('launchHour', group_by='pressure')
    launchMinute = r.get('launchMinute', group_by='pressure')
    logger.debug(f" ... Executing QuerySet: get datatime: launch time ...")
    launchtime = r.get_datetime('year', 'month', 'day', 'launchHour', 'launchMinute', group_by='pressure').astype(np.int64)
    launchtime = ma.array(launchtime)
    launchtime = ma.masked_values(launchtime, int64_fill_value)

    # ObsValue
    tmdb = r.get('airTemperature', group_by='pressure')
    tmdp = r.get('dewpointTemperature', group_by='pressure')
    wdir = r.get('windDirection', group_by='pressure')
    wspd = r.get('windSpeed', group_by='pressure')

    # QualityMark
    qmpr = r.get('pressureQM', group_by='pressure')
    qmat = r.get('airTemperatureQM', group_by='pressure')
    qmdd = r.get('dewpointTemperatureQM', group_by='pressure')
    qmwn = r.get('windSpeedQM', group_by='pressure')

    # ObsError
    logger.debug(f"Generating ObsError array with missing value...")
    pressureOE = np.float32(np.ma.masked_array(np.full((len(prlc)), 0.0)))
    airTemperaturOE = np.float32(np.ma.masked_array(np.full((len(tmdb)), 0.0)))
    dewpointTemperatureOE = np.float32(np.ma.masked_array(np.full((len(tmdp)), 0.0)))
    windEastwardOE = np.float32(np.ma.masked_array(np.full((len(wspd)), 0.0)))
    windNorthwardOE = np.float32(np.ma.masked_array(np.full((len(wspd)), 0.0)))

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f'Processing time for executing QuerySet to get ResultSet : {running_time} seconds')

    # =========================
    # Create derived variables
    # =========================
    start_time = time.time()

    logger.info('Creating derived variables')
    logger.debug('Creating derived variables - wind components (uob and vob)')

    uob, vob = Compute_WindComponents_from_WindDirection_and_WindSpeed(wdir, wspd)
    logger.debug(f'   uob min/max = {uob.min()} {uob.max()}')
    logger.debug(f'   vob min/max = {vob.min()} {vob.max()}')

    qob = Compute_SpecificHumidity_from_dewPoint_and_Pressure(tmdp, prlc)
    logger.debug(f'   qob min/max = {qob.min()} {qob.max()}')
    specificHumidityOE = np.float32(np.ma.masked_array(np.full((len(qob)), 0.0)))

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f'Processing time for creating derived variables : {running_time} seconds')

    logger.debug('Executing QuerySet for ADPUPA: Check BUFR variable generic dimension and type')
    # Check BUFR variable generic dimension and type
    logger.debug(f'     clat      shape = {clat.shape}')
    logger.debug(f'     clon      shape = {clon.shape}')
    logger.debug(f'     rpid      shape = {rpid.shape}')
    logger.debug(f'     selv      shape = {selv.shape}')
    logger.debug(f'     prlc      shape = {prlc.shape}')

    logger.debug(f'     rcts      shape = {rcts.shape}')
    logger.debug(f'     rcyr      shape = {receiptYear.shape}')
    logger.debug(f'     rcmo      shape = {receiptMonth.shape}')
    logger.debug(f'     rcdy      shape = {receiptDay.shape}')
    logger.debug(f'     rchr      shape = {receiptHour.shape}')
    logger.debug(f'     rcmi      shape = {receiptMinute.shape}')

    logger.debug(f'     ualnhr    shape = {launchHour.shape}')
    logger.debug(f'     ualnmn    shape = {launchMinute.shape}')

    logger.debug(f'     tmdb      shape = {tmdb.shape}')
    logger.debug(f'     tmdp      shape = {tmdp.shape}')
    logger.debug(f'     wdir      shape = {wdir.shape}')
    logger.debug(f'     wspd      shape = {wspd.shape}')
    logger.debug(f'     uob       shape = {uob.shape}')
    logger.debug(f'     vob       shape = {vob.shape}')
    logger.debug(f'     qob       shape = {qob.shape}')

    logger.debug(f'     qmpr      shape = {qmpr.shape}')
    logger.debug(f'     qmat      shape = {qmat.shape}')
    logger.debug(f'     qmdd      shape = {qmdd.shape}')
    logger.debug(f'     qmwn      shape = {qmwn.shape}')

    logger.debug(f'     clat      type  = {clat.dtype}')
    logger.debug(f'     clon      type  = {clon.dtype}')
    logger.debug(f'     rpid      type  = {rpid.dtype}')
    logger.debug(f'     selv      type  = {selv.dtype}')
    logger.debug(f'     prlc      type  = {prlc.dtype}')

    logger.debug(f'     rcts      type  = {rcts.dtype}')
    logger.debug(f'     rcyr      type  = {receiptYear.dtype}')
    logger.debug(f'     rcmo      type  = {receiptMonth.dtype}')
    logger.debug(f'     rcdy      type  = {receiptDay.dtype}')
    logger.debug(f'     rchr      type  = {receiptHour.dtype}')
    logger.debug(f'     rcmi      type  = {receiptMinute.dtype}')

    logger.debug(f'     ualnhr    type  = {launchHour.dtype}')
    logger.debug(f'     ualnmn    type  = {launchMinute.dtype}')

    logger.debug(f'     tmdb      type  = {tmdb.dtype}')
    logger.debug(f'     tmdp      type  = {tmdp.dtype}')
    logger.debug(f'     wdir      type  = {wdir.dtype}')
    logger.debug(f'     wspd      type  = {wspd.dtype}')
    logger.debug(f'     uob       type  = {uob.dtype}')
    logger.debug(f'     vob       type  = {vob.dtype}')
    logger.debug(f'     qob       type  = {qob.dtype}')

    logger.debug(f'     qmpr      type  = {qmpr.dtype}')
    logger.debug(f'     qmat      type  = {qmat.dtype}')
    logger.debug(f'     qmdd      type  = {qmdd.dtype}')
    logger.debug(f'     qmwn      type  = {qmwn.dtype}')

    # =====================================
    # Create IODA ObsSpace
    # Write IODA output
    # =====================================

    # Create the dimensions
    dims = {'Location': np.arange(0, clat.shape[0])}

    # Create IODA ObsSpace
    iodafile = f"{cycle_type}.t{hh}z.{data_type}.tm00.nc"
    OUTPUT_PATH = os.path.join(ioda_dir, iodafile)
    logger.info(f"Create output file: {OUTPUT_PATH}")
    obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)

    # Create Global attributes
    logger.debug(' ... ... Create global attributes')
    obsspace.write_attr('sourceFiles', bufrfile)
    obsspace.write_attr('description', data_description)

    # Create IODA variables
    logger.debug(f" ... ... Create variables: name, type, units, and attributes")

    # Datetime
    obsspace.create_var('MetaData/dateTime', dtype=timestamp.dtype, fillval=timestamp.fill_value) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'Datetime') \
        .write_data(timestamp)

    # Latitude
    obsspace.create_var('MetaData/latitude', dtype=clat.dtype, fillval=clat.fill_value) \
        .write_attr('units', 'degrees_north') \
        .write_attr('valid_range', np.array([-90, 90], dtype=np.float32)) \
        .write_attr('long_name', 'Latitude') \
        .write_data(clat)

    # Longitude
    obsspace.create_var('MetaData/longitude', dtype=clon.dtype, fillval=clon.fill_value) \
        .write_attr('units', 'degrees_east') \
        .write_attr('valid_range', np.array([-180, 180], dtype=np.float32)) \
        .write_attr('long_name', 'Longitude') \
        .write_data(clon)

    # Station Identification
    obsspace.create_var('MetaData/stationIdentification', dtype=rpid.dtype, fillval=rpid.fill_value) \
        .write_attr('long_name', 'Station Identification') \
        .write_data(rpid)

    # Station Elevation
    obsspace.create_var('MetaData/stationElevation', dtype=selv.dtype, fillval=selv.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Station Elevation') \
        .write_data(selv)

    # Pressure
    obsspace.create_var('MetaData/pressure', dtype=prlc.dtype, fillval=prlc.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Pressure') \
        .write_data(prlc)

    # ReceiptTime
    obsspace.create_var('MetaData/receiptTime', dtype=timestamp.dtype, fillval=timestamp.fill_value) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'Receipt Time') \
        .write_data(receipttime)

    # LaunchTime
    obsspace.create_var('MetaData/launchTime', dtype=timestamp.dtype, fillval=timestamp.fill_value) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'Launch Time') \
        .write_data(launchtime)

    # Air Temperature
    obsspace.create_var('ObsValue/airTemperature', dtype=tmdb.dtype, fillval=tmdb.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Air Temperature') \
        .write_data(tmdb)

    # DewPoint Temperature
    obsspace.create_var('ObsValue/dewPointTemperature', dtype=tmdp.dtype, fillval=tmdp.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'DewPoint Temperature') \
        .write_data(tmdp)

    # Eastward Wind
    obsspace.create_var('ObsValue/windEastward', dtype=uob.dtype, fillval=uob.fill_value) \
        .write_attr('units', 'm s-1') \
        .write_attr('long_name', 'Eastward Wind') \
        .write_data(uob)

    # Northward Wind
    obsspace.create_var('ObsValue/windNorthward', dtype=vob.dtype, fillval=vob.fill_value) \
        .write_attr('units', 'm s-1') \
        .write_attr('long_name', 'Northward Wind') \
        .write_data(vob)

    # Specific Humidity
    obsspace.create_var('ObsValue/specificHumidity', dtype=qob.dtype, fillval=qob.fill_value) \
        .write_attr('units', 'kg kg-1') \
        .write_attr('long_name', 'Specific Humidity') \
        .write_data(qob)

    # Pressure Quality Marker
    obsspace.create_var('QualityMarker/pressure', dtype=qmpr.dtype, fillval=qmpr.fill_value) \
        .write_attr('long_name', 'Pressure Quality Marker') \
        .write_data(qmpr)

    # Air Temperature Quality Marker
    obsspace.create_var('QualityMarker/airTemperature', dtype=qmat.dtype, fillval=qmat.fill_value) \
        .write_attr('long_name', 'Temperature Quality Marker') \
        .write_data(qmat)

    # DewPoint Temperature Quality Marker
    obsspace.create_var('QualityMarker/dewPointTemperature', dtype=qmdd.dtype, fillval=qmdd.fill_value) \
        .write_attr('long_name', 'DewPoint Temperature Quality Marker') \
        .write_data(qmdd)

    # Eastward Wind Quality Marker
    obsspace.create_var('QualityMarker/windEastward', dtype=qmwn.dtype, fillval=qmwn.fill_value) \
        .write_attr('long_name', 'Eastward Wind Quality Marker') \
        .write_data(qmwn)

    # Northward Wind Quality Marker
    obsspace.create_var('QualityMarker/windNorthward', dtype=qmwn.dtype, fillval=qmwn.fill_value) \
        .write_attr('long_name', 'Northward Wind Quality Marker') \
        .write_data(qmwn)

    # Pressure Observation Error
    obsspace.create_var('ObsError/pressure', dtype=prlc.dtype, fillval=prlc.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Pressure Observation Error') \
        .write_data(pressureOE)

    # Air Temperature Observation Error
    obsspace.create_var('ObsError/airTemperature', dtype=tmdb.dtype, fillval=tmdb.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Air Temperature Observation Error') \
        .write_data(airTemperaturOE)

    # DewPoint Temperature Observation Error
    obsspace.create_var('ObsError/dewPointTemperature', dtype=tmdp.dtype, fillval=tmdp.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'DewPoint Temperature Observation Error') \
        .write_data(dewpointTemperatureOE)

    # Eastward Wind Observation Error
    obsspace.create_var('ObsError/windEastward', dtype=uob.dtype, fillval=uob.fill_value) \
        .write_attr('units', 'm s-1') \
        .write_attr('long_name', 'Eastward Wind Observation Error') \
        .write_data(windEastwardOE)

    # Northward Wind Observation Error
    obsspace.create_var('ObsError/windNorthward', dtype=vob.dtype, fillval=vob.fill_value) \
        .write_attr('units', 'm s-1') \
        .write_attr('long_name', 'Northward Wind Observation Error') \
        .write_data(windNorthwardOE)

    # Specific Humidity Observation Error
    obsspace.create_var('ObsError/specificHumidity', dtype=qob.dtype, fillval=qob.fill_value) \
        .write_attr('units', 'kg kg-1') \
        .write_attr('long_name', 'Specific Humidity Observation Error') \
        .write_data(specificHumidityOE)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Running time for splitting and output IODA: {running_time} seconds")

    logger.info("All Done!")


if __name__ == '__main__':

    start_time = time.time()

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input JSON configuration', required=True)
    parser.add_argument('-v', '--verbose', help='print debug logging information',
                        action='store_true')
    args = parser.parse_args()

    log_level = 'DEBUG' if args.verbose else 'INFO'
    logger = Logger('BUFR2IODA_adpupa.py', level=log_level, colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Total running time: {running_time} seconds")
