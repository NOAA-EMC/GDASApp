#!/usr/bin/env python3
# (C) Copyright 2023 NOAA/NWS/NCEP/EMC
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

import sys
sys.path.append('/work2/noaa/da/nesposito/GDASApp_20231012/build/lib/python3.7/')
sys.path.append('/work2/noaa/da/nesposito/GDASApp_20231012/build/lib/python3.7/pyioda')
sys.path.append('/work2/noaa/da/nesposito/GDASApp_20231012/build/lib/python3.7/pyiodaconv')
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

def bufr_to_ioda(config, logger):

    subsets = config["subsets"]
    subsets_aircar = config["subsets_aircar"]
    subsets_aircft = config["subsets_aircft"]
    subsets_amdar = config["subsets_amdar"]

    logger.debug(f"Checking subsets = {subsets}")
    logger.debug(f"Checking subsets_aircar = {subsets_aircar}")
    logger.debug(f"Checking subsets_aircft = {subsets_aircft}")
    logger.debug(f"Checking subsets_amdar = {subsets_amdar}")

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
    platform_description = 'aircar and aircft data from BUFR format'

    bufrfile_aircar = f"{cycle_type}.t{hh}z.{data_type[0]}.tm00.{data_format}"
    bufrfile_aircft = f"{cycle_type}.t{hh}z.{data_type[1]}.tm00.{data_format}"
    DATA_PATH_aircar = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}", str(hh),
                                    bufrfile_aircar)
    DATA_PATH_aircft = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}", str(hh),
                                    bufrfile_aircft)

    logger.debug(f"The aircar DATA_PATH is: {DATA_PATH_aircar}")
    logger.debug(f"The aircft DATA_PATH is: {DATA_PATH_aircft}")

    # ============================================
    # Make the QuerySet for all the data we want
    # ============================================
    start_time = time.time()

    logger.debug(f"Making QuerySet ...")
    q = bufr.QuerySet(subsets_aircar) #AIRCAR
    r = bufr.QuerySet(subsets_aircft) #AIRCFT
    s = bufr.QuerySet(subsets_amdar)  #amdar
 
    # Reminder that subsets are the NC digits here:
#    for i in range(len(subsets)):
#       print("hello, ", subsets[i])
    # NC004004 aka AIRCAR

    # MetaData
    q.add("year", "*/YEAR")
    q.add("month", "*/MNTH")
    q.add("day", "*/DAYS")
    q.add("hour", "*/HOUR")
    q.add("minute",  "*/MINU")
    q.add("second", "*/SECO")
    q.add("latitude", "*/CLAT")
    q.add("longitude", "*/CLON")
    q.add("aircraftIdentifier", "*/ACRN")
    q.add("aircraftFlightPhase", "*/POAF")
    q.add("pressure", "*/PRLC")
    q.add("aircraftIndicatedAltitude", "*/IALT")

    # ObsValue
    q.add("airTemperature", "*/TMDB")
    q.add("relativeHumidity", "*/ACMST2/REHU")
#              - scale: .01
    q.add("waterVaporMixingRatio", "*/ACMST2/MIXR")
    q.add("windDirection", "*/WDIR")
    q.add("windSpeed", "*/WSPD")

    #Quality Marker
    q.add("airTemperatureQM", "*/QMAT")
    q.add("waterVaporMixingRatioQM", "*/ACMST2/QMDD")
    q.add("windQM","*/QMWN")

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Running time for making QuerySet: {running_time} seconds")

    # ==============================================================
    # Open the BUFR file and execute the QuerySet to get ResultSet
    # Use the ResultSet returned to get numpy arrays of the data
    # ==============================================================
    start_time = time.time()

    logger.debug(f"Executing QuerySet to get ResultSet ...")
    with bufr.File(DATA_PATH_aircar) as f:
        t = f.execute(q)

    with bufr.File(DATA_PATH_aircft) as f:
        u = f.execute(r)

    with bufr.File(DATA_PATH_aircft) as f:
        v = f.execute(s)

    # MetaData
    year_aircar = t.get('year')
    mnth_aircar = t.get('month')
    days_aircar = t.get('day')
    hour_aircar = t.get('hour')
    minu_aircar = t.get('minute')
    seco_aircar = t.get('second')
    clath_aircar = t.get('latitude')
    clonh_aircar = t.get('longitude')
    acrn_aircar = t.get('aircraftIdentifier')
    poaf_aircar = t.get('aircraftFlightPhase')
    prlc_aircar = t.get('pressure')
    ialt_aircar = t.get('aircraftIndicatedAltitude')

    # ObsValue
    tmdb_aircar = t.get('airTemperature', type='float')
    rehu_aircar = t.get('relativeHumidity', type='float')
    rehu_aircar *= 0.01
    mixr_aircar = t.get('waterVaporMixingRatio', type='float')
    wdir_aircar = t.get('windDirection', type='float')
    wspd_aircar = t.get('windSpeed', type='float')

    # Quality Marker
    qmat_aircar = t.get('airTemperatureQM')
    qmdd_aircar = t.get('waterVaporMixingRatioQM')
    qmwn_aircar = t.get('windQM')


    # Concatenate


    # Derive time/date


    # Derive aircraftFlightLevel


    # =====================================
    # Create IODA ObsSpace
    # Write IODA output
    # =====================================

    # Create the dimensions
    dims = {'Location': np.arange(0, lat.shape[0])}

    iodafile = f"{cycle_type}.t{hh}z.{data_type[0]}_{data_type[1]}.tm00.{data_format}.nc" 
    OUTPUT_PATH = os.path.join(ioda_dir, iodafile)
    logger.debug(f" ... ... Create OUTPUT file: {OUTPUT_PATH}")

    path, fname = os.path.split(OUTPUT_PATH)
    if path and not os.path.exists(path):
        os.makedirs(path)

    obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)

    # Create Global attributes
    logger.debug(f" ... ... Create global attributes")

    obsspace.write_attr('source', source)
    obsspace.write_attr('sourceFiles', bufrfile)
    obsspace.write_attr('dataProviderOrigin', data_provider)
    obsspace.write_attr('description', data_description)
    obsspace.write_attr('datetimeReference', reference_time)
    obsspace.write_attr('datetimeRange',
                        [str(min(dateTime)), str(max(dateTime))])




    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Running time for splitting and output IODA: {running_time} \
                 seconds")

    logger.debug(f"All Done!")


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
    logger = Logger('bufr2ioda_aircar_aircft_bufr.py', level=log_level,
                    colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Total running time: {running_time} seconds")

