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
    r = bufr.QuerySet(["SFCSHP"])
    s = bufr.QuerySet(["ADPUPA"])

    for i in range(len(subsets)):
        if subsets[i] == "ADPSFC":
            logger.info("Making QuerySet for ADPSFC")
            # MetaData
            q.add('stationIdentification', '*/SID')
            q.add('prepbufrDataLevelCategory', '*/CAT')
            q.add('temperatureEventCode', "*/T___INFO/T__EVENT{1}/TPC")
            q.add('latitude', '*/YOB')
            q.add('longitude', '*/XOB')
            q.add('obsTimeMinusCycleTime', '*/DHR')
            q.add('stationElevation', '*/ELV')
            q.add('observationType', '*/TYP')
            q.add('pressure', '*/P___INFO/P__EVENT{1}/POB')

            # Quality Infomation (Quality Indicator)
            q.add('qualityMarkerStationPressure', '*/P___INFO/P__EVENT{1}/PQM')
            q.add('qualityMarkerAirTemperature', '*/T___INFO/T__EVENT{1}/TQM')
            q.add('qualityMarkerVirtualTemperature', '*/T___INFO/T__EVENT{1}/TQM')

            # ObsValue
            q.add('stationPressure', '*/P___INFO/P__EVENT{1}/POB')
            q.add('airTemperature', '*/T___INFO/T__EVENT{1}/TOB')
            q.add('virtualTemperature', '*/T___INFO/TVO')

        elif subsets[i] == "SFCSHP":
            logger.info("Making QuerySet for SFCSHP")
            # MetaData
            r.add('stationIdentification', '*/SID')
            r.add('prepbufrDataLevelCategory', '*/CAT')
            r.add('temperatureEventCode', "*/T___INFO/T__EVENT{1}/TPC")
            r.add('latitude', '*/YOB')
            r.add('longitude', '*/XOB')
            r.add('obsTimeMinusCycleTime', '*/DHR')
            r.add('stationElevation', '*/ELV')
            r.add('observationType', '*/TYP')

            # Quality Infomation (Quality Indicator)
            r.add('qualityMarkerStationPressure', '*/P___INFO/P__EVENT{1}/PQM')
            r.add('qualityMarkerAirTemperature', '*/T___INFO/T__EVENT{1}/TQM')
            r.add('qualityMarkerVirtualTemperature', '*/T___INFO/T__EVENT{1}/TQM')

            # ObsValue
            r.add('stationPressure', '*/P___INFO/P__EVENT{1}/POB')
            r.add('airTemperature', '*/T___INFO/T__EVENT{1}/TOB')
            r.add('virtualTemperature', '*/T___INFO/TVO')

        elif subsets[i] == "ADPUPA":
            logger.info("Making QuerySet for ADPUPA")
            # MetaData
            s.add('stationIdentification', 'ADPUPA/SID')
            s.add('prepbufrDataLevelCategory', '*/PRSLEVEL/CAT')
            s.add('temperatureEventCode', "*/PRSLEVEL/T___INFO/T__EVENT{1}/TPC")
            s.add('latitude', '*/PRSLEVEL/DRFTINFO/YDR')
            s.add('longitude', '*/PRSLEVEL/DRFTINFO/XDR')
            s.add('stationElevation', '*/ELV')
            s.add('observationType', '*/TYP')
            s.add('timeOffset', '*/PRSLEVEL/DRFTINFO/HRDR')
            s.add('releaseTime', '*/PRSLEVEL/DRFTINFO/HRDR')
            s.add('pressure', '*/PRSLEVEL/P___INFO/P__EVENT{1}/POB')

            # ObsValue
#            s.add('verticalSignificance', '*/PRSLEVEL/CAT')
            s.add('stationPressure', '*/PRSLEVEL/P___INFO/P__EVENT{1}/POB')
            s.add('airTemperature', '*/PRSLEVEL/T___INFO/T__EVENT{1}/TOB')
            s.add('virtualTemperature', '*/PRSLEVEL/T___INFO/TVO')
#            s.add('height', '*/PRSLEVEL/Z___INFO/Z__EVENT{1}/ZOB')

            # QualityMark
            s.add('pressureQM', '*/PRSLEVEL/P___INFO/P__EVENT{1}/PQM')
            s.add('airTemperatureQM', '*/PRSLEVEL/T___INFO/T__EVENT{1}/TQM')
            s.add('virtualTemperatureQM', '*/PRSLEVEL/T___INFO/T__EVENT{1}/TQM')

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

    with bufr.File(DATA_PATH) as f:
        u = f.execute(r)

    with bufr.File(DATA_PATH) as f:
        v = f.execute(s)

    # ADPSFC
    logger.info(" ... Executing QuerySet for ADPSFC: get MetaData ...")
    # MetaData
    sid1 = t.get('stationIdentification')
    cat1 = t.get('prepbufrDataLevelCategory')
    tpc1 = t.get('temperatureEventCode')
    lat1 = t.get('latitude')
    lon1 = t.get('longitude')
    lon1[lon1 > 180] -= 360
    dhr1 = t.get('obsTimeMinusCycleTime')
    elv1 = t.get('stationElevation')
    typ1 = t.get('observationType')
    pressure1 = t.get('pressure')
    pressure1 *= 100

    logger.info(f" ... Executing QuerySet: get QualityMarker information ...")
    # Quality Information
    pobqm1 = t.get('qualityMarkerStationPressure')
    tobqm1 = t.get('qualityMarkerAirTemperature')
    tvoqm1 = t.get('qualityMarkerVirutalTemperature')

    logger.info(f" ... Executing QuerySet: get ObsValues ...")
    # ObsValue
    pob1 = t.get('stationPressure')
    pob1 *= 100
    tob1 = t.get('airTemperature')
    tob1 += 273.15
    tvo1 = t.get('virtualTemperature')
    tvo1 += 273.15

    # SFCSHP
    logger.info(" ... Executing QuerySet for SFCSHP: get MetaData ...")
    # MetaData
    sid2 = u.get('stationIdentification')
    cat2 = u.get('prepbufrDataLevelCategory')
    tpc2 = u.get('temperatureEventCode')
    lat2 = u.get('latitude')
    lon2 = u.get('longitude')
    lon2[lon2 > 180] -= 360
    dhr2 = u.get('obsTimeMinusCycleTime')
    elv2 = u.get('stationElevation', type='float')
    typ2 = u.get('observationType')
    pressure2 = u.get('pressure')
    pressure2 *= 100

    logger.info(f" ... Executing QuerySet: get QualityMarker information ...")
    # Quality Information
    pobqm2 = u.get('qualityMarkerStationPressure')
    tobqm2 = u.get('qualityMarkerAirTemperature')
    tvoqm2 = u.get('qualityMarkerVirutalTemperature')

    logger.info(f" ... Executing QuerySet: get ObsValues ...")
    # ObsValue
    pob2 = u.get('stationPressure')
    pob2 *= 100
    tob2 = u.get('airTemperature')
    tob2 += 273.15
    tvo2 = u.get('virtualTemperature')
    tvo2 += 273.15

    # ADPUPA
    logger.info(" ... Executing QuerySet for ADPUPA: get MetaData ...")
    # MetaData
    sid3 = v.get('stationIdentification', 'prepbufrDataLevelCategory')
    cat3 = v.get('prepbufrDataLevelCategory', 'prepbufrDataLevelCategory')
    tpc3 = v.get('temperatureEventCode', 'prepbufrDataLevelCategory')
    lat3 = v.get('latitude', 'prepbufrDataLevelCategory')
    lon3 = v.get('longitude', 'prepbufrDataLevelCategory')
    lon3[lon3 > 180] -= 360  # Convert Longitude from [0,360] to [-180,180]
    dhr3 = v.get('timeOffset', 'prepbufrDataLevelCategory')
    elv3 = v.get('stationElevation', 'prepbufrDataLevelCategory', type='float')
    typ3 = v.get('observatoinType', 'prepbufrDataLevelCategory')
    pressure3 = r.get('pressure', 'prepbufrDataLevelCategory')
    pressure3 *= 100

    # ObsValue
    ps3 = np.full(pob3.shape[0], pob3.fill_value)  # Extract stationPressure from pressure, which belongs to CAT=1
    ps3 = np.where(cat3 == 0, pob3, ps3)
    tob3 = v.get('airTemperature', 'prepbufrDataLevelCategory')
    tob3 += 273.15
    tsen3 = np.full(tob3.shape[0], tob3.fill_value)        # Extract sensible temperature from tob, which belongs to TPC=1
    tsen3 = np.where(tpc3 == 1, tob3, tsen3)
    tvo3 = np.full(tob3.shape[0], tob3.fill_value)         # Extract virtual temperature from tob, which belongs to TPC <= 8 and TPC>1
    tvo3 = np.where(((tpc3 <= 8) & (tpc3 > 1)), tob3, tvo3)
    zob = v.get('heightOfObservation', 'prepbufrDataLevelCategory')

    # QualityMark
    pobqm3 = v.get('pressureQM', 'prepbufrDataLevelCategory')
    psqm3 = np.full(pobqm3.shape[0], pobqm3.fill_value)    # Extract stationPressureQM from pressureQM
    psqm3 = np.where(cat3 == 0, pobqm3, psqm3)
    tobqm3 = v.get('airTemperatureQM', 'prepbufrDataLevelCategory')
    tsenqm3 = np.full(tobqm3.shape[0], tobqm3.fill_value)  # Extract airTemperature from tobqm, which belongs to TPC=1
    tsenqm3 = np.where(tpc3 == 1, tobqm3, tsenqm3)
    tvoqm3 = np.full(tobqm3.shape[0], tobqm3.fill_value)  # Extract virtual temperature from tob, which belongs to TPC <= 8 and TPC>1
    tvoqm3 = np.where(((tpc3 <= 8) & (tpc3 > 1)), tobqm3, tvoqm3)

    logger.info(f" ... Executing QuerySet: Done!")
    running_time = end_time - start_time
    logger.info(f"Running time for executing QuerySet: {running_time} seconds")

    # Check BUFR variable dimension and type
    logger.info(f"     The shapes and dtypes of all 3 variables")
    logger.info(f"     sid1       shape, type = {sid1.shape}, {sid1.dtype}")
    logger.info(f"     sid2       shape, type = {sid2.shape}, {sid2.dtype}")
    logger.info(f"     sid3       shape, type = {sid3.shape}, {sid3.dtype}")
    logger.info(f"     cat1       shape, type = {cat1.shape}, {cat1.dtype}")
    logger.info(f"     cat2       shape, type = {cat2.shape}, {cat2.dtype}")
    logger.info(f"     cat3       shape, type = {cat3.shape}, {cat3.dtype}")
    logger.info(f"     tpc1       shape, type = {tpc1.shape}, {tpc1.dtype}")
    logger.info(f"     tpc2       shape, type = {tpc2.shape}, {tpc2.dtype}")
    logger.info(f"     tpc3       shape, type = {tpc3.shape}, {tpc3.dtype}")
    logger.info(f"     lat1       shape, type = {lat1.shape}, {lat1.dtype}")
    logger.info(f"     lat2       shape, type = {lat2.shape}, {lat2.dtype}")
    logger.info(f"     lat3       shape, type = {lat3.shape}, {lat3.dtype}")
    logger.info(f"     lon1       shape, type = {lon1.shape}, {lon1.dtype}")
    logger.info(f"     lon2       shape, type = {lon2.shape}, {lon2.dtype}")
    logger.info(f"     lon3       shape, type = {lon3.shape}, {lon3.dtype}")
    logger.info(f"     dhr1       shape, type = {dhr1.shape}, {dhr1.dtype}")
    logger.info(f"     dhr2       shape, type = {dhr2.shape}, {dhr2.dtype}")
    logger.info(f"     dhr3       shape, type = {dhr3.shape}, {dhr3.dtype}")
    logger.info(f"     elv1       shape, type = {elv1.shape}, {elv1.dtype}")
    logger.info(f"     elv2       shape, type = {elv2.shape}, {elv2.dtype}")
    logger.info(f"     elv3       shape, type = {elv3.shape}, {elv3.dtype}")
    logger.info(f"     typ1       shape, type = {typ1.shape}, {typ1.dtype}")
    logger.info(f"     typ2       shape, type = {typ2.shape}, {typ2.dtype}")
    logger.info(f"     typ3       shape, type = {typ3.shape}, {typ3.dtype}")
    logger.info(f"     pressure1  shape, type = {pressure1.shape}, {pressure1.dtype}")
    logger.info(f"     pressure2  shape, type = {pressure2.shape}, {pressure2.dtype}")
    logger.info(f"     pressure3  shape, type = {pressure3.shape}, {pressure3.dtype}")
    logger.info(f"     pobqm1     shape, type = {pobqm1.shape}, {pobqm1.dtype}")
    logger.info(f"     pobqm2     shape, type = {pobqm2.shape}, {pobqm2.dtype}")
    logger.info(f"     pobqm3     shape, type = {pobqm3.shape}, {pobqm3.dtype}")
    logger.info(f"     tobqm1     shape, type = {tobqm1.shape}, {tobqm1.dtype}")
    logger.info(f"     tobqm2     shape, type = {tobqm2.shape}, {tobqm2.dtype}")
    logger.info(f"     tobqm3     shape, type = {tobqm3.shape}, {tobqm3.dtype}")
    logger.info(f"     tobqm1     shape, type = {tobqm1.shape}, {tobqm1.dtype}")
    logger.info(f"     tobqm2     shape, type = {tobqm2.shape}, {tobqm2.dtype}")
    logger.info(f"     tobqm3     shape, type = {tobqm3.shape}, {tobqm3.dtype}")
    logger.info(f"     tvoqm1     shape, type = {tvoqm1.shape}, {tvoqm1.dtype}")
    logger.info(f"     tvoqm2     shape, type = {tvoqm2.shape}, {tvoqm2.dtype}")
    logger.info(f"     tvoqm3     shape, type = {tvoqm3.shape}, {tvoqm3.dtype}")
    logger.info(f"     pob1       shape, type = {pob1.shape}, {pob1.dtype}")
    logger.info(f"     pob2       shape, type = {pob2.shape}, {pob2.dtype}")
    logger.info(f"     pob3       shape, type = {pob3.shape}, {pob3.dtype}")
    logger.info(f"     tob1       shape, type = {tob1.shape}, {tob1.dtype}")
    logger.info(f"     tob2       shape, type = {tob2.shape}, {tob2.dtype}")
    logger.info(f"     tob3       shape, type = {tob3.shape}, {tob3.dtype}")
    logger.info(f"     tvo1       shape, type = {tvo1.shape}, {tvo1.dtype}")
    logger.info(f"     tvo2       shape, type = {tvo2.shape}, {tvo2.dtype}")
    logger.info(f"     tvo3       shape, type = {tvo3.shape}, {tvo3.dtype}")

    logger.info(f"  ... Concatenate the variables")
    sid = np.concatenate((sid1, sid2, sid3), axis=0)
    cat = np.concatenate((cat1, cat2, cat3), axis=0)
    tpc = np.concatenate((tpc1, tpc2, tpc3), axis=0)
    lat = np.concatenate((lat1, lat2, lat3), axis=0)
    lon = np.concatenate((lon1, lon2, lon3), axis=0)
    dhr = np.concatenate((dhr1, dhr2, dhr3), axis=0)
    elv = np.concatenate((elv1, elv2, elv3), axis=0)
    typ = np.concatenate((typ1, typ2, typ3), axis=0)
    pressure = np.concatenate((pressure1, pressure2, pressure3), axis=0)
    pobqm = np.concatenate((pobqm1, pobqm2, pobqm3), axis=0)
    tobqm = np.concatenate((tobqm1, tobqm2, tobqm3), axis=0)
    tvoqm = np.concatenate((tvoqm1, tvoqm2, tvoqm3), axis=0)
    pob = np.concatenate((pob1, pob2, pob3), axis=0)
    tob = np.concatenate((tob1, tob2, tob3), axis=0)
    tvo = np.concatenate((tvo1, tvo2, tvo3), axis=0)

    logger.info(f"  ... Concatenated array shapes:")
    logger.info(f"  new sid       shape = {sid.shape}")
    logger.info(f"  new cat       shape = {cat.shape}")
    logger.info(f"  new tpc       shape = {tpc.shape}")
    logger.info(f"  new lat       shape = {lat.shape}")
    logger.info(f"  new lon       shape = {lon.shape}")
    logger.info(f"  new dhr       shape = {dhr.shape}")
    logger.info(f"  new elv       shape = {elv.shape}")
    logger.info(f"  new typ       shape = {typ.shape}")
    logger.info(f"  new pressure  shape = {pressure.shape}")
    logger.info(f"  new pobqm     shape = {pobqm.shape}")
    logger.info(f"  new tobqm     shape = {tobqm.shape}")
    logger.info(f"  new tvoqm     shape = {tvoqm.shape}")
    logger.info(f"  new pob       shape = {pob.shape}")
    logger.info(f"  new tob       shape = {tob.shape}")
    logger.info(f"  new tvo       shape = {tvo.shape}")

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

#    obsspace.write_attr('Converter', converter)
    obsspace.write_attr('source', source)
    obsspace.write_attr('sourceFiles', bufrfile)
    obsspace.write_attr('dataProviderOrigin', data_provider)
    obsspace.write_attr('description', data_description)
    obsspace.write_attr('datetimeReference', reference_time)
    obsspace.write_attr('datetimeRange',
                        [str(min(dateTime)), str(max(dateTime))])

    # Create IODA variables
    logger.info(f" ... ... Create variables: name, type, units, & attributes")

    # Station Identification
    obsspace.create_var('MetaData/stationIdentification', dtype=sid.dtype,
                        fillval=sid.fill_value) \
        .write_attr('long_name', 'Station Identification') \
        .write_data(sid)

    # PrepBUFR Data Level Category
    obsspace.create_var('MetaData/prepbufrDataLevelCategory', dtype=cat.dtype,
                        fillval=cat.fill_value) \
        .write_attr('long_name', 'prepBUFR Data Level Category') \
        .write_data(cat)

    # Temperature Event Code
    obsspace.create_var('MetaData/temperatureEventCode', dtype=tpc.dtype,
                        fillval=tpc.fill_value) \
        .write_attr('long_name', 'temperatureEventCode') \
        .write_data(tpc)

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

    # Quality Marker: Station Pressure
    obsspace.create_var('QualityMarker/stationPressure', dtype=pobqm.dtype,
                        fillval=pobqm.fill_value) \
        .write_attr('long_name', 'Station Pressure Quality Marker') \
        .write_data(pobqm)

    # Quality Marker: Air Temperature
    obsspace.create_var('QualityMarker/airTemperature', dtype=tobqm.dtype,
                        fillval=tobqm.fill_value) \
        .write_attr('long_name', 'Air Temperature Quality Marker') \
        .write_data(tobqm)

    # Quality Marker: Virtual Temperature
    obsspace.create_var('QualityMarker/virtualTemperature', dtype=tvoqm.dtype,
                        fillval=tvoqm.fill_value) \
        .write_attr('long_name', 'Virtual Temperature Quality Marker') \
        .write_data(tvoqm)

    # ObsValue: Station Pressure
    obsspace.create_var('ObsValue/stationPressure', dtype=pob.dtype,
                        fillval=pob.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Station Pressure') \
        .write_data(pob)

    # ObsValue: Air Temperature
    obsspace.create_var('ObsValue/airTemperature', dtype=tob.dtype,
                        fillval=tob.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Air Temperature') \
        .write_data(tob)

    # ObsValue: Virtual Temperature
    obsspace.create_var('ObsValue/virtualTemperature', dtype=tvo.dtype,
                        fillval=tvo.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Virtual Temperature') \
        .write_data(tvo)

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
    logger = Logger('bufr2ioda_conventional_prepbufr_ps.py', level=log_level,
                    colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Total running time: {running_time} seconds")
