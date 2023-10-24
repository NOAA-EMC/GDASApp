#!/usr/bin/env python3
# (C) Copyright 2023 NOAA/NWS/NCEP/EMC
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

import sys
sys.path.append('/work2/noaa/da/nesposito/ioda_bundle_readlc_20231012/build/lib/python3.7/')
sys.path.append('/work2/noaa/da/nesposito/ioda_bundle_readlc_20231012/build/lib/python3.7/pyioda')
sys.path.append('/work2/noaa/da/nesposito/ioda_bundle_readlc_20231012/build/lib/python3.7/pyiodaconv')
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
    logger.info(f"Checking subsets = {subsets}")

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
    q = bufr.QuerySet(["ADPSFC"])

    for i in range(len(subsets)):
        if subsets[i] == "ADPSFC":
            logger.info("Making QuerySet for ADPSFC")
            # MetaData
            q.add('stationIdentification', '*/SID')
            q.add('observationType', '*/TYP')

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
        t = f.execute(q)


    # ADPSFC
    logger.info(" ... Executing QuerySet for ADPSFC: get MetaData ...")
    # MetaData
    typ1 = t.get('observationType')
    sid1 = t.get('stationIdentification')

    print("NE lentyp1 sid1 ", len(typ1), len(sid1))

    typ2 = np.array([])
    sid2 = np.array([])
    print("NE typ1 1-5", typ1[0], typ1[1], typ1[2], typ1[3], typ1[4], typ1[5])
    print("NE sid1 1-5", sid1[0], sid1[1], sid1[2], sid1[3], sid1[4], sid1[5])

#    for i in range(len(typorig1)):
#        print("FUCK ", typorig1[1])

    for i in range(len(typ1)):
        if typ1[i] < 200:
#            print("NE ", typ1[i])
#            typ2.append(typ1[i])
#            sid2.append(sid1[i])
#            print("NE appending happening?????????", typ1[i], sid1[i])
            typ2 = np.append(typ2, typ1[i])
            sid2 = np.append(sid2, sid1[i])

    print("NE typ2 1-5", typ2[0], typ2[1], typ2[2], typ2[3], typ2[4], typ2[5])
    print("NE sid2 1-5", sid2[0], sid2[1], sid2[2], sid2[3], sid2[4], sid2[5])
#    typ2 = np.array(typ2)
#    sid2 = np.array(sid2)
 

    logger.info(f" ... Executing QuerySet: Done!")
    running_time = end_time - start_time
    logger.info(f"Running time for executing QuerySet: {running_time} seconds")

    # Check BUFR variable dimension and type
    logger.info(f"     The shapes and dtypes of all 3 variables")
    logger.info(f"     sid2       shape, type = {sid2.shape}, {sid2.dtype}")
    logger.info(f"     typ2       shape, type = {typ2.shape}, {typ2.dtype}")

    # =====================================
    # Create IODA ObsSpace
    # Write IODA output
    # =====================================

    # Create the dimensions
    dims = {'Location': np.arange(0, sid1.shape[0])}

    iodafile = f"{cycle_type}.t{hh}z.{data_type}.{data_format}.nc"
    OUTPUT_PATH = os.path.join(ioda_dir, iodafile)
    logger.info(f" ... ... Create OUTPUT file: {OUTPUT_PATH}")

    path, fname = os.path.split(OUTPUT_PATH)
    if path and not os.path.exists(path):
        os.makedirs(path)

    obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)

    # Create Global attributes
    logger.info(f" ... ... Create global attributes")

#    obsspace.write_attr('Converter', converter)
    obsspace.write_attr('source', source)
    obsspace.write_attr('sourceFiles', bufrfile)
    obsspace.write_attr('dataProviderOrigin', data_provider)
    obsspace.write_attr('description', data_description)

    # Create IODA variables
    logger.info(f" ... ... Create variables: name, type, units, & attributes")

    # Station Identification
    obsspace.create_var('MetaData/stationIdentification', dtype=sid1.dtype,
                        fillval=sid1.fill_value) \
        .write_attr('long_name', 'Station Identification') \
        .write_data(sid2)

    obsspace.create_var('MetaData/observationType', dtype=typ1.dtype,
                        fillval=typ1.fill_value) \
        .write_attr('long_name', 'Observation Type') \
        .write_data(typ2)

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
    logger = Logger('bufr2ioda_conventional_prepbufr_ps.py', level=log_level,
                    colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Total running time: {running_time} seconds")
