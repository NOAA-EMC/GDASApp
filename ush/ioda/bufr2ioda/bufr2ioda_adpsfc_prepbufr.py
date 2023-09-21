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


def Compute_dateTime(cycleTimeSinceEpoch, dhr):

    dhr = np.int64(dhr*3600)
    dateTime = dhr + cycleTimeSinceEpoch

    return dateTime


def bufr_to_ioda(config):

    subsets = config["subsets"]

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

    # General informaton
    converter = 'BUFR to IODA Converter'
    platform_description = 'SFCSHP data from prepBUFR format'

    bufrfile = f"{cycle_type}.t{hh}z.{data_format}"
    DATA_PATH = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}",
                             str(hh), bufrfile)

    print("The DATA_PATH is: "+str(DATA_PATH))

    # ============================================
    # Make the QuerySet for all the data we want
    # ============================================
    start_time = time.time()

    print('Making QuerySet ...')
    q = bufr.QuerySet(subsets)

    # MetaData
    q.add('stationIdentification', '*/SID')
    q.add('latitude', '*/YOB')
    q.add('longitude', '*/XOB')
    q.add('obsTimeMinusCycleTime', '*/DHR')
    q.add('stationElevation', '*/ELV')
    q.add('observationType', '*/TYP')
    q.add('pressure', '*/P___INFO/P__EVENT{1}/POB')

#   # Quality Infomation (Quality Indicator)
    q.add('qualityMarkerStationPressure', '*/P___INFO/P__EVENT{1}/PQM')

    # ObsValue
    q.add('stationPressure', '*/P___INFO/P__EVENT{1}/POB')

    end_time = time.time()
    running_time = end_time - start_time
    print('Running time for making QuerySet : ', running_time, 'seconds')

    # ==============================================================
    # Open the BUFR file and execute the QuerySet to get ResultSet
    # Use the ResultSet returned to get numpy arrays of the data
    # ==============================================================
    start_time = time.time()

    print('Executing QuerySet to get ResultSet ...')
    with bufr.File(DATA_PATH) as f:
        r = f.execute(q)

    print(' ... Executing QuerySet: get metadata: basic ...')
    # MetaData
    sid = r.get('stationIdentification')
    lat = r.get('latitude')
    lon = r.get('longitude')
    lon[lon > 180] -= 360
    elv = r.get('stationElevation')
    typ = r.get('observationType')
    pressure = r.get('pressure')
    pressure *= 100

    print(' ... Executing QuerySet: get QualityMarker information ...')
    # Quality Information
    pobqm = r.get('qualityMarkerStationPressure')

    print(' ... Executing QuerySet: get obsvalue: stationPressure ...')
    # ObsValue
    pob = r.get('stationPressure')
    pob *= 100

    print(' ... Executing QuerySet: get datatime: observation time ...')
    # DateTime: seconds since Epoch time
    # IODA has no support for numpy datetime arrays dtype=datetime64[s]
    dhr = r.get('obsTimeMinusCycleTime', type='int64')

    print(' ... Executing QuerySet: Done!')

    print(' ... Executing QuerySet: Check BUFR variable generic
          dimension and type ...')
    # Check BUFR variable generic dimension and type
    print('     sid       shape = ', sid.shape)
    print('     dhr       shape = ', dhr.shape)
    print('     lat       shape = ', lat.shape)
    print('     lon       shape = ', lon.shape)
    print('     elv       shape = ', elv.shape)
    print('     typ       shape = ', typ.shape)
    print('     pressure  shape = ', pressure.shape)

    print('     pobqm     shape = ', pobqm.shape)
    print('     pob       shape = ', pob.shape)

    print('     sid       type  = ', sid.dtype)
    print('     dhr       type  = ', dhr.dtype)
    print('     lat       type  = ', lat.dtype)
    print('     lon       type  = ', lon.dtype)
    print('     elv       type  = ', elv.dtype)
    print('     typ       type  = ', typ.dtype)
    print('     pressure  type  = ', pressure.dtype)

    print('     pobqm     type  = ', pobqm.dtype)
    print('     pob       type  = ', pob.dtype)

    end_time = time.time()
    running_time = end_time - start_time
    print('Running time for executing QuerySet to get ResultSet : ',
          running_time, 'seconds')

    # =========================
    # Create derived variables
    # =========================
    start_time = time.time()

    print('Creating derived variables - dateTime ...')

    cycleTimeSinceEpoch = np.int64(calendar.timegm(time.strptime(
                                   reference_time_full, '%Y%m%d%H%M')))
    dateTime = Compute_dateTime(cycleTimeSinceEpoch, dhr)

    print('     Check derived variables type ... ')
    print('     dateTime shape = ', dateTime.shape)
    print('     dateTime type = ', dateTime.dtype)

    end_time = time.time()
    running_time = end_time - start_time
    print('Running time for creating derived variables : ',
          running_time, 'seconds')

    # =====================================
    # Create IODA ObsSpace
    # Write IODA output
    # =====================================

    # Create the dimensions
    dims = {
             'Location': np.arange(0, lat.shape[0]),
    }

    iodafile = f"{cycle_type}.t{hh}z.{data_type}.{data_format}.nc"
    OUTPUT_PATH = os.path.join(ioda_dir, iodafile)
    print(" ... ... Create OUTPUT file: ", OUTPUT_PATH)

    path, fname = os.path.split(OUTPUT_PATH)
    if path and not os.path.exists(path):
        os.makedirs(path)

    obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)

    # Create Global attributes
    print(' ... ... Create global attributes')

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
    print(' ... ... Create variables: name, type, units, and attributes')
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

    # Observation Type
    obsspace.create_var('MetaData/observationType', dtype=typ.dtype,
                        fillval=typ.fill_value) \
        .write_attr('long_name', 'Observation Type') \
        .write_data(typ)

    # Pressure
    obsspace.create_var('MetaData/pressure', dtype=pressure.dtype,
                        fillval=pressure.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Pressure') \
        .write_data(pressure)

    # Quality: Percent Confidence - Quality Information Without Forecast
    obsspace.create_var('QualityMarker/stationPressure', dtype=pobqm.dtype,
                        fillval=pobqm.fill_value) \
        .write_attr('long_name', 'Station Pressure Quality Marker') \
        .write_data(pobqm)

    # Station Pressure
    obsspace.create_var('ObsValue/pressure', dtype=pob.dtype,
                        fillval=pob.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Station Pressure') \
        .write_data(pob)

    end_time = time.time()
    running_time = end_time - start_time
    print('Running time for splitting and output IODA:', running_time,
          'seconds')

    print("All Done!")


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

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config)

    end_time = time.time()
    running_time = end_time - start_time
    print('Total running time: ', running_time, 'seconds')
