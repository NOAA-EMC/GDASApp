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
import copy
from datetime import datetime
import json
from pyiodaconv import bufr
from collections import namedtuple
from pyioda import ioda_obs_space as ioda_ospace
from wxflow import Logger


def Compute_sequenceNumber(lon):

    lon_u, seqNum = np.unique(lon, return_inverse=True)
    seqNum = seqNum.astype(np.int64)
    logger.debug(f"Len of Sequence Number: {len(seqNum)}")

    return seqNum


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

    yyyymmdd = cycle[0:8]
    hh = cycle[8:10]

    # General Information
    converter = 'BUFR to IODA Converter'    
    platform_description = 'Surface obs from ALTKOB: temperature and salinity'
    
    bufrfile = f"{cycle_type}.t{hh}z.{data_format}.tm{hh}.bufr_d"
    DATA_PATH = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}", str(hh), f"atmos", bufrfile)
    logger.debug(f"{bufrfile}, {DATA_PATH}")

    # ===========================================
    # Make the QuerySet for all the data we want
    # ===========================================
    start_time = time.time()

    logger.debug(f"Making QuerySet ...")
    q = bufr.QuerySet()

    # MetaData
    q.add('year', '*/YEAR')
    q.add('month', '*/MNTH')
    q.add('day', '*/DAYS')
    q.add('hour', '*/HOUR')
    q.add('minute', '*/MINU')
    q.add('ryear', '*/RCYR')
    q.add('rmonth', '*/RCMO')
    q.add('rday', '*/RCDY')
    q.add('rhour', '*/RCHR')
    q.add('rminute', '*/RCMI')
    q.add('latitude', '*/CLATH')
    q.add('longitude', '*/CLONH')

    # ObsValue
    q.add('temp', '*/SST0')
    q.add('saln', '*/SSS0')

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Running time for making QuerySet: {running_time} seconds")

    # ===============================================================
    # Open the BUFR file and execute the QuerySet
    # Use the ResultSet returned to get numpy arrays of the data
    # ==============================================================
    start_time = time.time()

    logger.debug(f"Executing QuerySet to get ResultSet ...")
    with bufr.File(DATA_PATH) as f:
        r = f.execute(q)

    # MetaData
    logger.debug(f" ... Executing QuerySet: get MetaData ...")
    dateTime = r.get_datetime('year', 'month', 'day', 'hour', 'minute', group_by='depth')
    dateTime = dateTime.astype(np.int64)
    rcptdateTime = r.get_datetime('ryear', 'rmonth', 'rday', 'rhour', 'rminute', group_by='depth')
    rcptdateTime = rcptdateTime.astype(np.int64)
    lat = r.get('latitude', group_by='depth')
    lon = r.get('longitude', group_by='depth')

    # ObsValue
    logger.debug(f" ... Executing QuerySet: get ObsValue ...")
    temp = r.get('temp', group_by='depth')
    temp -= 273.15
    saln = r.get('saln', group_by='depth')

    # Add mask based on min, max values
    mask = ((temp > -10.0) & (temp <= 50.0)) & ((saln >= 0.0) & (saln <= 45.0))
    lat = lat[mask]
    lon = lon[mask]
    dateTime = dateTime[mask]
    rcptdateTime = rcptdateTime[mask]
    temp = temp[mask]
    saln = saln[mask]

    # ObsError
    logger.debug(f"Generating ObsError array with constant value (instrument error)...")
    ObsError_temp = np.float32(np.ma.masked_array(np.full((len(mask)), 0.30)))
    ObsError_saln = np.float32(np.ma.masked_array(np.full((len(mask)), 1.00)))

    # PreQC
    logger.debug(f"Generating PreQC array with 0...")    
    PreQC = (np.ma.masked_array(np.full((len(mask)), 0))).astype(np.int32)

    logger.debug(f" ... Executing QuerySet: Done!")

    logger.debug(f" ... Executing QuerySet: Check BUFR variable generic \
                dimension and type ...")
    # ==================================================
    # Check values of BUFR variables, dimension and type
    # ==================================================
    logger.debug(f" temp          min, max, length, dtype = {temp.min()}, {temp.max()}, {len(temp)}, {temp.dtype}")
    logger.debug(f" saln          min, max, length, dtype = {saln.min()}, {saln.max()}, {len(saln)}, {saln.dtype}")
    logger.debug(f" lon           min, max, length, dtype = {lon.min()}, {lon.max()}, {len(lon)}, {lon.dtype}")
    logger.debug(f" lat           min, max, length, dtype = {lat.min()}, {lat.max()}, {len(lat)}, {lat.dtype}")
    logger.debug(f" depth         min, max, length, dtype = {depth.min()}, {depth.max()}, {len(depth)}, {depth.dtype}")
    logger.debug(f" PreQC         min, max, length, dtype = {PreQC.min()}, {PreQC.max()}, {len(PreQC)}, {PreQC.dtype}")
    logger.debug(f" ObsError_temp min, max, length, dtype = {ObsError_temp.min()}, {ObsError_temp.max()}, {len(ObsError_temp)}, {ObsError_temp.dtype}")
    logger.debug(f" ObsError_saln min, max, length, dtype = {ObsError_saln.min()}, {ObsError_saln.max()}, {len(ObsError_saln)}, {ObsError_saln.dtype}")

    logger.debug(f" stationID                shape, dtype = {stationID.shape}, {stationID.astype(str).dtype}")
    logger.debug(f" dateTime                 shape, dtype = {dateTime.shape}, {dateTime.dtype}")
    logger.debug(f" rcptdateTime             shape, dytpe = {rcptdateTime.shape}, {rcptdateTime.dtype}")

    # =====================================
    # Create IODA ObsSpace
    # Write IODA output
    # =====================================
   
    # Create the dimensions
    dims = {'Location': np.arange(0, lat.shape[0])}

    iodafile = f"{cycle_type}.t{hh}z.{data_type}_profiles.{data_format}.nc"
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
    obsspace.write_attr('datetimeRange', [str(dateTime.min()), str(dateTime.max())])
    obsspace.write_attr('platformLongDescription', platform_description)

    # Create IODA variables
    logger.debug(f" ... ... Create variables: name, type, units, and attributes")

    # Datetime
    obsspace.create_var('MetaData/dateTime', dtype=dateTime.dtype, fillval=dateTime.fill_value) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'Datetime') \
        .write_data(dateTime)

    # rcptDatetime
    obsspace.create_var('MetaData/rcptdateTime', dtype=dateTime.dtype, fillval=dateTime.fill_value) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'receipt Datetime') \
        .write_data(rcptdateTime)

    # Longitude
    obsspace.create_var('MetaData/longitude', dtype=lon.dtype, fillval=lon.fill_value) \
        .write_attr('units', 'degrees_east') \
        .write_attr('valid_range', np.array([-180, 180], dtype=np.float32)) \
        .write_attr('long_name', 'Longitude') \
        .write_data(lon)

    # Latitude 
    obsspace.create_var('MetaData/latitude', dtype=lat.dtype, fillval=lat.fill_value) \
        .write_attr('units', 'degrees_north') \
        .write_attr('valid_range', np.array([-90, 90], dtype=np.float32)) \
        .write_attr('long_name', 'Latitude') \
        .write_data(lat)

    # Station Identification
    obsspace.create_var('MetaData/stationID', dtype=stationID.dtype, fillval=stationID.fill_value) \
        .write_attr('long_name', 'Station Identification') \
        .write_data(stationID)

    # PreQC 
    obsspace.create_var('PreQC/seaSurfaceTemperature', dtype=PreQC.dtype, fillval=PreQC.fill_value) \
        .write_attr('long_name', 'PreQC') \
        .write_data(PreQC)

    obsspace.create_var('PreQC/seaSurfaceSalinity', dtype=PreQC.dtype, fillval=PreQC.fill_value) \
        .write_attr('long_name', 'PreQC') \
        .write_data(PreQC)

    # ObsError 
    obsspace.create_var('ObsError/seaSurfaceTemperature', dtype=ObsError_temp.dtype, fillval=ObsError_temp.fill_value) \
        .write_attr('units', 'degC') \
        .write_attr('long_name', 'ObsError') \
        .write_data(ObsError_temp)

    obsspace.create_var('ObsError/seaSurfaceSalinity', dtype=ObsError_saln.dtype, fillval=ObsError_saln.fill_value) \
        .write_attr('units', 'psu') \
        .write_attr('long_name', 'ObsError') \
        .write_data(ObsError_saln)

    # ObsValue
    obsspace.create_var('ObsValue/seaSurfaceTemperature', dtype=temp.dtype, fillval=temp.fill_value) \
        .write_attr('units', 'degC') \
        .write_attr('valid_range', np.array([-10.0, 50.0], dtype=np.float32)) \
        .write_attr('long_name', 'Sea Surface Temperature') \
        .write_data(temp)

    obsspace.create_var('ObsValue/seaSurfaceSalinity', dtype=saln.dtype, fillval=saln.fill_value) \
        .write_attr('units', 'psu') \
        .write_attr('valid_range', np.array([0.0, 45.0], dtype=np.float32)) \
        .write_attr('long_name', 'Sea Surface Salinity') \
        .write_data(saln)

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Running time for splitting and output IODA: {running_time} \
                 seconds")

    logger.debug(f"All Done!")


if __name__ == '__main__':
    
    start_time = time.time()
    config = "bufr2ioda_trackob_surface.json"

    log_level = 'DEBUG' if args.verbose else 'INFO'
    logger = Logger('bufr2ioda_trackob_surface.py', level=log_level,
                    colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Total running time: {running_time} seconds")
