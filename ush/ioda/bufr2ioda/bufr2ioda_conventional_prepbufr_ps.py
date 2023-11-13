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
import numpy.ma as ma
import os
import argparse
import math
import calendar
import time
from datetime import datetime
import copy
import json
from pyiodaconv import bufr
from collections import namedtuple
from pyioda import ioda_obs_space as ioda_ospace
from wxflow import Logger


def Compute_dateTime(cycleTimeSinceEpoch, dhr):

    dhr = np.int64(dhr*3600)
    dateTime = dhr + cycleTimeSinceEpoch

    return dateTime


def Mask_typ_for_var(typ, var):

    typ_var = copy.deepcopy(typ)
    for i in range(len(typ_var)):
        if ma.is_masked(var[i]):
            typ_var[i] = typ.fill_value

    return typ_var


def bufr_to_ioda(config, logger):

    subsets = config["subsets"]
    logger.debug(f"Checking subsets = {subsets}")
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
    platform_description = 'Conventional Surface data from prepBUFR format'

    bufrfile = f"{cycle_type}.t{hh}z.{data_format}"
    DATA_PATH = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}",
                             str(hh), bufrfile)

    logger.debug(f"The DATA_PATH is: {DATA_PATH}")

    # ============================================
    # Make the QuerySet for all the data we want
    # ============================================
    start_time = time.time()

    logger.debug('Making QuerySet ...')
    q = bufr.QuerySet(["ADPSFC"])
    r = bufr.QuerySet(["SFCSHP"])
    s = bufr.QuerySet(["ADPUPA"])

    for i in range(len(subsets)):
        if subsets[i] == "ADPSFC":
            logger.debug("Making QuerySet for ADPSFC")

            # ObsType
            q.add('observationType', '*/TYP')

            # MetaData
            q.add('stationIdentification', '*/SID')
            q.add('prepbufrDataLevelCategory', '*/CAT')
            q.add('temperatureEventCode', '*/T___INFO/T__EVENT{1}/TPC')
            q.add('latitude', '*/YOB')
            q.add('longitude', '*/XOB')
            q.add('obsTimeMinusCycleTime', '*/DHR')
            q.add('heightOfStation', '*/Z___INFO/Z__EVENT{1}/ZOB')
            q.add('pressure', '*/P___INFO/P__EVENT{1}/POB')

            # QualityMarker
            q.add('qualityMarkerStationPressure', '*/P___INFO/P__EVENT{1}/PQM')
            q.add('qualityMarkerAirTemperature', '*/T___INFO/T__EVENT{1}/TQM')
            q.add('qualityMarkerVirtualTemperature', '*/T___INFO/T__EVENT{1}/TQM')

            # ObsValue
            q.add('stationElevation', '*/ELV')
            q.add('stationPressure', '*/P___INFO/P__EVENT{1}/POB')
            q.add('airTemperature', '*/T___INFO/T__EVENT{1}/TOB')

        elif subsets[i] == "SFCSHP":
            logger.debug("Making QuerySet for SFCSHP")

            # ObsType
            r.add('observationType', '*/TYP')

            # MetaData
            r.add('stationIdentification', '*/SID')
            r.add('prepbufrDataLevelCategory', '*/CAT')
            r.add('temperatureEventCode', '*/T___INFO/T__EVENT{1}/TPC')
            r.add('latitude', '*/YOB')
            r.add('longitude', '*/XOB')
            r.add('obsTimeMinusCycleTime', '*/DHR')
            r.add('heightOfStation', '*/Z___INFO/Z__EVENT{1}/ZOB')
            r.add('pressure', '*/P___INFO/P__EVENT{1}/POB')

            # QualityMarker
            r.add('qualityMarkerStationPressure', '*/P___INFO/P__EVENT{1}/PQM')
            r.add('qualityMarkerAirTemperature', '*/T___INFO/T__EVENT{1}/TQM')
            r.add('qualityMarkerVirtualTemperature', '*/T___INFO/T__EVENT{1}/TQM')

            # ObsValue
            r.add('stationElevation', '*/ELV')
            r.add('stationPressure', '*/P___INFO/P__EVENT{1}/POB')
            r.add('airTemperature', '*/T___INFO/T__EVENT{1}/TOB')

        elif subsets[i] == "ADPUPA":
            logger.debug("Making QuerySet for ADPUPA")
            # ObsType
            s.add('observationType', '*/TYP')

            # MetaData
            s.add('stationIdentification', 'ADPUPA/SID')
            s.add('prepbufrDataLevelCategory', '*/PRSLEVEL/CAT')
            s.add('temperatureEventCode', '*/PRSLEVEL/T___INFO/T__EVENT{1}/TPC')
            s.add('latitude', '*/PRSLEVEL/DRFTINFO/YDR')
            s.add('longitude', '*/PRSLEVEL/DRFTINFO/XDR')
            s.add('heightOfStation', '*/PRSLEVEL/Z___INFO/Z__EVENT{1}/ZOB')
            s.add('timeOffset', '*/PRSLEVEL/DRFTINFO/HRDR')
            s.add('releaseTime', '*/PRSLEVEL/DRFTINFO/HRDR')
            s.add('pressure', '*/PRSLEVEL/P___INFO/P__EVENT{1}/POB')

            # QualityMarker
            s.add('qualityMarkerStationPressure', '*/PRSLEVEL/P___INFO/P__EVENT{1}/PQM')
            s.add('qualityMarkerAirTemperature', '*/PRSLEVEL/T___INFO/T__EVENT{1}/TQM')
            s.add('qualityMarkerVirtualTemperature', '*/PRSLEVEL/T___INFO/T__EVENT{1}/TQM')

            # ObsValue
            s.add('stationElevation', '*/ELV')
            s.add('stationPressure', '*/PRSLEVEL/P___INFO/P__EVENT{1}/POB')
            s.add('airTemperature', '*/PRSLEVEL/T___INFO/T__EVENT{1}/TOB')

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
        t = f.execute(q)

    with bufr.File(DATA_PATH) as f:
        u = f.execute(r)

    with bufr.File(DATA_PATH) as f:
        v = f.execute(s)

    # ADPSFC
    # ObsType
    logger.debug(" ... Executing QuerySet for ADPSFC: get ObsType ...")
    typorig1 = t.get('observationType', type='int32')

    # MetaData
    logger.debug(" ... Executing QuerySet for ADPSFC: get MetaData ...")
    sidorig1 = t.get('stationIdentification')
    catorig1 = t.get('prepbufrDataLevelCategory')
    tpcorig1 = t.get('temperatureEventCode').astype('int32')
    latorig1 = t.get('latitude')
    lonorig1 = t.get('longitude')
    lonorig1[lonorig1 > 180] -= 360
    dhrorig1 = t.get('obsTimeMinusCycleTime', type='int64')
    zoborig1 = t.get('heightOfStation', type='float')
    pressureorig1 = t.get('pressure')
    pressureorig1 *= 100

    # QualityMarker
    logger.debug(f" ... Executing QuerySet for ADPSFC: get QualityMarker ...")
    pobqmorig1 = t.get('qualityMarkerStationPressure').astype('int32')
    tobqmorig1 = t.get('qualityMarkerAirTemperature').astype('int32')

    # ObsValue
    logger.debug(f" ... Executing QuerySet for ADPSFC: get ObsValues ...")
    elvorig1 = t.get('stationElevation', type='float32')
    poborig1 = t.get('stationPressure')
    poborig1 *= 100
    toborig1 = t.get('airTemperature')
    toborig1 += 273.15

    logger.debug(f" ... Make new arrays for certain Obstypes of ADSPFC")
    typ1 = np.array([], dtype=np.int32)
    sid1 = np.array([]).astype('str')
    cat1 = np.array([], dtype=np.int32)
    tpc1 = np.array([], dtype=np.int32)
    lat1 = np.array([], dtype=np.float32)
    lon1 = np.array([], dtype=np.float32)
    zob1 = np.array([], dtype=np.float32)
    dhr1 = np.array([], dtype=np.int64)
    pressure1 = np.array([], dtype=np.float32)
    pobqm1 = np.array([], dtype=np.int32)
    tobqm1 = np.array([], dtype=np.int32)
    elv1 = np.array([], dtype=np.float32)
    pob1 = np.array([], dtype=np.float32)
    tob1 = np.array([], dtype=np.float32)

    for i in range(len(typorig1)):
        if typorig1[i] < 200:
            typ1 = np.append(typ1, typorig1[i])
            sid1 = np.append(sid1, sidorig1[i])
            cat1 = np.append(cat1, catorig1[i])
            tpc1 = np.append(tpc1, tpcorig1[i])
            lat1 = np.append(lat1, latorig1[i])
            lon1 = np.append(lon1, lonorig1[i])
            zob1 = np.append(zob1, zoborig1[i])
            dhr1 = np.append(dhr1, dhrorig1[i])
            pressure1 = np.append(pressure1, pressureorig1[i])
            pobqm1 = np.append(pobqm1, pobqmorig1[i]).astype('int32')
            tobqm1 = np.append(tobqm1, tobqmorig1[i]).astype('int32')
            elv1 = np.append(elv1, elvorig1[i])
            pob1 = np.append(pob1, poborig1[i])
            tob1 = np.append(tob1, toborig1[i])

    typ1 = ma.array(typ1)
    typ1 = ma.masked_values(typ1, typorig1.fill_value)
    sid1 = ma.array(sid1)
    ma.set_fill_value(sid1, "")
    tpc1 = ma.array(tpc1)
    tpc1 = ma.masked_values(tpc1, tpcorig1.fill_value)
    lat1 = ma.array(lat1)
    lat1 = ma.masked_values(lat1, latorig1.fill_value)
    lon1 = ma.array(lon1)
    lon1 = ma.masked_values(lon1, lonorig1.fill_value)
    zob1 = ma.array(zob1)
    zob1 = ma.masked_values(zob1, zoborig1.fill_value)
    dhr1 = ma.array(dhr1)
    dhr1 = ma.masked_values(dhr1, dhrorig1.fill_value)
    pressure1 = ma.array(pressure1).astype('float32')
    pressure1 = ma.masked_values(pressure1, pressureorig1.fill_value)
    pobqm1 = ma.array(pobqm1).astype('int32')
    pobqm1 = ma.masked_values(pobqm1, pobqmorig1.fill_value)
    tobqm1 = ma.array(tobqm1).astype('int32')
    tobqm1 = ma.masked_values(tobqm1, tobqmorig1.fill_value)
    tsenqm1 = copy.deepcopy(tobqm1)
    tsenqm1f = ma.array(np.full(tobqm1.shape[0], tobqm1.fill_value))
    tsenqm1 = ma.where(((tpc1 >= 1) & (tpc1 < 8)), tobqm1, tsenqm1f)
    tvoqm1 = copy.deepcopy(tobqm1)
    tvoqm1f = ma.array(np.full(tobqm1.shape[0], tobqm1.fill_value))
    tvoqm1 = ma.where((tpc1 == 8), tobqm1, tvoqm1f)
    elv1 = ma.array(elv1).astype('float32')
    elv1 = ma.masked_values(elv1, elvorig1.fill_value)
    pob1 = ma.array(pob1).astype('float32')
    pob1 = ma.masked_values(pob1, poborig1.fill_value)
    tob1 = ma.array(tob1).astype('float32')
    tob1 = ma.masked_values(tob1, toborig1.fill_value)
    tsen1 = copy.deepcopy(tob1)
    tsen1f = ma.array(np.full(tob1.shape[0], tob1.fill_value))
    tsen1 = ma.where(((tpc1 >= 1) & (tpc1 < 8)), tob1, tsen1f)
    tvo1 = ma.array(np.full(tob1.shape[0], tob1.fill_value))
    tvo1f = ma.array(np.full(tob1.shape[0], tob1.fill_value))
    tvo1 = ma.where((tpc1 == 8), tob1, tvo1f)

    logger.debug(" ... QuerySet execution for ADPSFC ... done!")

    # SFCSHP
    # ObsType
    logger.debug(" ... Executing QuerySet for SFCSHP: get ObsType ...")
    typorig2 = u.get('observationType', type='int32')

    # MetaData
    logger.debug(" ... Executing QuerySet for SFCSHP: get MetaData ...")
    sidorig2 = u.get('stationIdentification')
    catorig2 = u.get('prepbufrDataLevelCategory')
    tpcorig2 = u.get('temperatureEventCode').astype('int32')
    latorig2 = u.get('latitude')
    lonorig2 = u.get('longitude')
    lonorig2[lonorig2 > 180] -= 360
    zoborig2 = u.get('heightOfStation', type='float')
    dhrorig2 = u.get('obsTimeMinusCycleTime', type='int64')
    pressureorig2 = u.get('pressure')
    pressureorig2 *= 100

    logger.debug(f" ... Executing QuerySet for SFCSHP: get QualityMarker ...")
    # QualityMarker
    pobqmorig2 = u.get('qualityMarkerStationPressure').astype('int32')
    tobqmorig2 = u.get('qualityMarkerAirTemperature').astype('int32')

    logger.debug(f" ... Executing QuerySet for SFCSHP: get ObsValues ...")
    # ObsValue
    elvorig2 = u.get('stationElevation', type='float32')
    poborig2 = u.get('stationPressure')
    poborig2 *= 100
    toborig2 = u.get('airTemperature')
    toborig2 += 273.15

    logger.debug(f" ... Make new arrays for certain ObsTypes of SFCSHP")
    typ2 = np.array([], dtype=np.int32)
    sid2 = np.array([]).astype('str')
    cat2 = np.array([], dtype=np.int32)
    tpc2 = np.array([], dtype=np.int32)
    lat2 = np.array([], dtype=np.float32)
    lon2 = np.array([], dtype=np.float32)
    zob2 = np.array([], dtype=np.float32)
    dhr2 = np.array([], dtype=np.int64)
    pressure2 = np.array([], dtype=np.float32)
    pobqm2 = np.array([], dtype=np.int32)
    tobqm2 = np.array([], dtype=np.int32)
    elv2 = np.array([], dtype=np.float32)
    pob2 = np.array([], dtype=np.float32)
    tob2 = np.array([], dtype=np.float32)

    for i in range(len(typorig2)):
        if typorig2[i] < 200:
            typ2 = np.append(typ2, typorig2[i])
            sid2 = np.append(sid2, sidorig2[i])
            cat2 = np.append(cat2, catorig2[i])
            tpc2 = np.append(tpc2, tpcorig2[i])
            lat2 = np.append(lat2, latorig2[i])
            lon2 = np.append(lon2, lonorig2[i])
            zob2 = np.append(zob2, zoborig2[i])
            dhr2 = np.append(dhr2, dhrorig2[i])
            pressure2 = np.append(pressure2, pressureorig2[i])
            pobqm2 = np.append(pobqm2, pobqmorig2[i])
            tobqm2 = np.append(tobqm2, tobqmorig2[i])
            elv2 = np.append(elv2, elvorig2[i])
            pob2 = np.append(pob2, poborig2[i])
            tob2 = np.append(tob2, toborig2[i])

    typ2 = ma.array(typ2)
    typ2 = ma.masked_values(typ2, typorig2.fill_value)
    sid2 = ma.array(sid2)
    ma.set_fill_value(sid2, "")
    tpc2 = ma.array(tpc2)
    tpc2 = ma.masked_values(tpc2, tpcorig2.fill_value)
    lat2 = ma.array(lat2)
    lat2 = ma.masked_values(lat2, latorig2.fill_value)
    lon2 = ma.array(lon2)
    lon2 = ma.masked_values(lon2, lonorig2.fill_value)
    zob2 = ma.array(zob2)
    zob2 = ma.masked_values(zob2, zoborig2.fill_value)
    dhr2 = ma.array(dhr2)
    dhr2 = ma.masked_values(dhr2, dhrorig2.fill_value)
    pressure2 = ma.array(pressure2).astype('float32')
    pressure2 = ma.masked_values(pressure2, pressureorig2.fill_value)
    pobqm2 = ma.array(pobqm2).astype('int32')
    pobqm2 = ma.masked_values(pobqm2, pobqmorig2.fill_value)
    tobqm2 = ma.array(tobqm2).astype('int32')
    tobqm2 = ma.masked_values(tobqm2, tobqmorig2.fill_value)
    tsenqm2 = copy.deepcopy(tobqm2)
    tsenqmorig2f = ma.array(np.full(tobqmorig2.shape[0], tobqmorig2.fill_value))
    tsenqmorig2 = ma.where(((tpcorig2 >= 1) & (tpcorig2 < 8)), tobqmorig2, tsenqmorig2f)
    tvoqm2 = copy.deepcopy(tobqm2)
    tvoqmorig2f = ma.array(np.full(tobqmorig2.shape[0], tobqmorig2.fill_value))
    tvoqmorig2 = ma.where((tpcorig2 == 8), tobqmorig2, tvoqmorig2f)
    elv2 = ma.array(elv2).astype('float32')
    elv2 = ma.masked_values(elv2, elvorig2.fill_value)
    pob2 = ma.array(pob2).astype('float32')
    pob2 = ma.masked_values(pob2, poborig2.fill_value)
    tob2 = ma.array(tob2).astype('float32')
    tob2 = ma.masked_values(tob2, toborig2.fill_value)
    tsen2 = copy.deepcopy(tob2)
    tsen2f = ma.array(np.full(tob2.shape[0], tob2.fill_value))
    tsen2 = ma.where(((tpc2 >= 2) & (tpc2 < 8)), tob2, tsen2f)
    tvo2 = ma.array(np.full(tob2.shape[0], tob2.fill_value))
    tvo2f = ma.array(np.full(tob2.shape[0], tob2.fill_value))
    tvo2 = ma.where((tpc2 == 8), tob2, tvo2f)

    logger.debug(f" ... QuerySet execution for SFCSHP ... done!")

    # ADPUPA
    # ObsType
    logger.debug(" ... Executing QuerySet for ADPUPA: get ObsType ...")
    typ3 = v.get('observationType', 'prepbufrDataLevelCategory')

    # MetaData
    logger.debug(" ... Executing QuerySet for ADPUPA: get MetaData ...")
    sid3 = v.get('stationIdentification', 'prepbufrDataLevelCategory').astype('str')

    cat3 = v.get('prepbufrDataLevelCategory', 'prepbufrDataLevelCategory')
    tpc3 = v.get('temperatureEventCode', 'prepbufrDataLevelCategory')
    lat3 = v.get('latitude', 'prepbufrDataLevelCategory')
    lon3 = v.get('longitude', 'prepbufrDataLevelCategory')
    lon3[lon3 > 180] -= 360
    zob3 = v.get('heightOfStation', 'prepbufrDataLevelCategory', type='float')
    dhr3 = v.get('timeOffset', 'prepbufrDataLevelCategory', type='int64')
    pressure3 = v.get('pressure', 'prepbufrDataLevelCategory')
    pressure3 *= 100

    # QualityMark
    logger.debug(" ... Executing QuerySet for ADPUPA: get QualityMarker ...")
    pobqm3 = v.get('qualityMarkerStationPressure', 'prepbufrDataLevelCategory')
    psqm3 = ma.array(np.full(pobqm3.shape[0], pobqm3.fill_value))
    psqm3 = ma.where(cat3 == 0, pobqm3, psqm3)
    tobqm3 = v.get('qualityMarkerAirTemperature', 'prepbufrDataLevelCategory')
    tsenqm3 = copy.deepcopy(tobqm3)
    tsenqm3f = ma.array(np.full(tobqm3.shape[0], tobqm3.fill_value))
    tsenqm3 = ma.where(((tpc3 >= 1) & (tpc3 < 8) & (cat3 == 0)), tobqm3, tsenqm3f)
    tvoqm3 = copy.deepcopy(tobqm3)
    tvoqm3f = ma.array(np.full(tobqm3.shape[0], tobqm3.fill_value))
    tvoqm3 = ma.where(((tpc3 == 8) & (cat3 == 0)), tobqm3, tvoqm3f)

    # ObsValue
    logger.debug(" ... Executing QuerySet for ADPUPA: get ObsValues ...")
    elv3 = v.get('stationElevation', 'prepbufrDataLevelCategory', type='float32')
    pob3 = v.get('stationPressure', 'prepbufrDataLevelCategory', type='float32')
    ps3 = ma.array(np.full(pressure3.shape[0], pressure3.fill_value))
    ps3 = ma.where(cat3 == 0, pressure3, ps3)
    tob3 = v.get('airTemperature', 'prepbufrDataLevelCategory', type='float32')
    tob3 += 273.15
    tsen3 = copy.deepcopy(tob3)
    tsen3f = ma.array(np.full(tob3.shape[0], tob3.fill_value))
    tsen3 = ma.where(((tpc3 >= 1) & (tpc3 < 8) & (cat3 == 0)), tob3, tsen3f)
    tvo3 = copy.deepcopy(tob3)
    tvo3f = ma.array(np.full(tob3.shape[0], tob3.fill_value))
    tvo3 = ma.where(((tpc3 == 8) & (cat3 == 0)), tob3, tvo3f)

    logger.debug(f" ... QuerySet execution for ADPUPA ... done!")
    logger.debug(f" ... Executing QuerySet: Done!")

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Running time for executing QuerySet: {running_time} seconds")

    # Check BUFR variable dimension and type
    logger.debug(f"     The shapes and dtypes of all 3 variables")
    logger.debug(f"     typ1       shape, type = {typ1.shape}, {typ1.dtype}, {typ1.fill_value}")
    logger.debug(f"     typ2       shape, type = {typ2.shape}, {typ2.dtype}, {typ2.fill_value}")
    logger.debug(f"     typ3       shape, type = {typ3.shape}, {typ3.dtype}, {typ3.fill_value}")
    logger.debug(f"     sid1       shape, type = {sid1.shape}, {sid1.dtype}")
    logger.debug(f"     sid2       shape, type = {sid2.shape}, {sid2.dtype}")
    logger.debug(f"     sid3       shape, type = {sid3.shape}, {sid3.dtype}")
    logger.debug(f"     cat1       shape, type = {cat1.shape}, {cat1.dtype}")
    logger.debug(f"     cat2       shape, type = {cat2.shape}, {cat2.dtype}")
    logger.debug(f"     cat3       shape, type = {cat3.shape}, {cat3.dtype}")
    logger.debug(f"     tpc1       shape, type = {tpc1.shape}, {tpc1.dtype}")
    logger.debug(f"     tpc2       shape, type = {tpc2.shape}, {tpc2.dtype}")
    logger.debug(f"     tpc3       shape, type = {tpc3.shape}, {tpc3.dtype}")
    logger.debug(f"     lat1       shape, type = {lat1.shape}, {lat1.dtype}")
    logger.debug(f"     lat2       shape, type = {lat2.shape}, {lat2.dtype}")
    logger.debug(f"     lat3       shape, type = {lat3.shape}, {lat3.dtype}")
    logger.debug(f"     lon1       shape, type = {lon1.shape}, {lon1.dtype}")
    logger.debug(f"     lon2       shape, type = {lon2.shape}, {lon2.dtype}")
    logger.debug(f"     lon3       shape, type = {lon3.shape}, {lon3.dtype}")
    logger.debug(f"     zob1       shape, type = {zob1.shape}, {zob1.dtype}")
    logger.debug(f"     zob2       shape, type = {zob2.shape}, {zob2.dtype}")
    logger.debug(f"     zob3       shape, type = {zob3.shape}, {zob3.dtype}")
    logger.debug(f"     dhr1       shape, type = {dhr1.shape}, {dhr1.dtype}")
    logger.debug(f"     dhr2       shape, type = {dhr2.shape}, {dhr2.dtype}")
    logger.debug(f"     dhr3       shape, type = {dhr3.shape}, {dhr3.dtype}")
    logger.debug(f"     pressure1  shape, type = {pressure1.shape}, {pressure1.dtype}")
    logger.debug(f"     pressure2  shape, type = {pressure2.shape}, {pressure2.dtype}")
    logger.debug(f"     pressure3  shape, type = {pressure3.shape}, {pressure3.dtype}")
    logger.debug(f"     pobqm1     shape, type = {pobqm1.shape}, {pobqm1.dtype}")
    logger.debug(f"     pobqm2     shape, type = {pobqm2.shape}, {pobqm2.dtype}")
    logger.debug(f"     pobqm3     shape, type = {pobqm3.shape}, {pobqm3.dtype}")
    logger.debug(f"     psqm3      shape, type = {psqm3.shape}, {psqm3.dtype}")
    logger.debug(f"     tobqm1     shape, type = {tobqm1.shape}, {tobqm1.dtype}")
    logger.debug(f"     tobqm2     shape, type = {tobqm2.shape}, {tobqm2.dtype}")
    logger.debug(f"     tobqm3     shape, type = {tobqm3.shape}, {tobqm3.dtype}")
    logger.debug(f"     tsenqm1    shape, type = {tsenqm1.shape}, {tsenqm1.dtype}")
    logger.debug(f"     tsenqm2    shape, type = {tsenqm2.shape}, {tsenqm2.dtype}")
    logger.debug(f"     tsenqm3    shape, type = {tsenqm3.shape}, {tsenqm3.dtype}")
    logger.debug(f"     tvoqm1     shape, type = {tvoqm1.shape}, {tvoqm1.dtype}")
    logger.debug(f"     tvoqm2     shape, type = {tvoqm2.shape}, {tvoqm2.dtype}")
    logger.debug(f"     tvoqm3     shape, type = {tvoqm3.shape}, {tvoqm3.dtype}")
    logger.debug(f"     elv1       shape, type = {elv1.shape}, {elv1.dtype}")
    logger.debug(f"     elv2       shape, type = {elv2.shape}, {elv2.dtype}")
    logger.debug(f"     elv3       shape, type = {elv3.shape}, {elv3.dtype}")
    logger.debug(f"     pob1       shape, type = {pob1.shape}, {pob1.dtype}, {pob1.fill_value}")
    logger.debug(f"     pob2       shape, type = {pob2.shape}, {pob2.dtype}, {pob2.fill_value}")
    logger.debug(f"     pob3       shape, type = {pob3.shape}, {pob3.dtype}, {pob3.fill_value}")
    logger.debug(f"     tob1       shape, type = {tob1.shape}, {tob1.dtype}, {tob1.fill_value}")
    logger.debug(f"     tob2       shape, type = {tob2.shape}, {tob2.dtype}, {tob2.fill_value}")
    logger.debug(f"     tob3       shape, type = {tob3.shape}, {tob3.dtype}, {tob3.fill_value}")
    logger.debug(f"     tsen1      shape, type = {tsen1.shape}, {tsen1.dtype}, {tsen1.fill_value}")
    logger.debug(f"     tsen2      shape, type = {tsen2.shape}, {tsen2.dtype}, {tsen2.fill_value}")
    logger.debug(f"     tsen3      shape, type = {tsen3.shape}, {tsen3.dtype}, {tsen3.fill_value}")
    logger.debug(f"     tvo1       shape, type = {tvo1.shape}, {tvo1.dtype}")
    logger.debug(f"     tvo2       shape, type = {tvo2.shape}, {tvo2.dtype}")
    logger.debug(f"     tvo3       shape, type = {tvo3.shape}, {tvo3.dtype}")

    logger.debug(f"  ... Concatenate the variables")
    typ = ma.concatenate((typ1, typ2, typ3), axis=0)
    typ = ma.masked_values(typ, typorig1.fill_value)
    sid = ma.concatenate((sid1, sid2, sid3), axis=0)
    ma.set_fill_value(sid, "")
    cat = ma.concatenate((cat1, cat2, cat3), axis=0)
    cat = ma.masked_values(cat, catorig1.fill_value)
    tpc = ma.concatenate((tpc1, tpc2, tpc3), axis=0)
    tpc = ma.masked_values(tpc, tpcorig1.fill_value)
    lat = ma.concatenate((lat1, lat2, lat3), axis=0)
    lat = ma.masked_values(lat, latorig1.fill_value)
    lon = ma.concatenate((lon1, lon2, lon3), axis=0)
    lon = ma.masked_values(lon, lonorig1.fill_value)
    zob = ma.concatenate((zob1, zob2, zob3), axis=0).astype(zob1.dtype)
    zob = ma.masked_values(zob, zoborig1.fill_value)
    dhr = ma.concatenate((dhr1, dhr2, dhr3), axis=0).astype(dhr1.dtype)
    dhr = ma.masked_values(dhr, dhrorig1.fill_value)
    pressure = ma.concatenate((pressure1, pressure2, pressure3), axis=0)
    pressure = ma.masked_values(pressure, pressureorig1.fill_value)
    pobqm = ma.concatenate((pobqm1, pobqm2, pobqm3), axis=0)
    pobqm = ma.masked_values(pobqm, pobqmorig1.fill_value)
    psqm = ma.concatenate((pobqm1, pobqm2, psqm3), axis=0)
    psqm = ma.masked_values(psqm, pobqmorig1.fill_value)
    tobqm = ma.concatenate((tobqm1, tobqm2, tobqm3), axis=0)
    tobqm = ma.masked_values(tobqm, tobqmorig1.fill_value)
    tsenqm = ma.concatenate((tsenqm1, tsenqm2, tsenqm3), axis=0)
    tsenqm = ma.masked_values(tsenqm, tobqmorig1.fill_value)
    tvoqm = ma.concatenate((tvoqm1, tvoqm2, tvoqm3), axis=0)
    tvoqm = ma.masked_values(tvoqm, tobqmorig1.fill_value)
    pob = ma.concatenate((pob1, pob2, pob3), axis=0).astype(pob1.dtype)
    pob = ma.masked_values(pob, poborig1.fill_value)
    ps = ma.concatenate((pob1, pob2, ps3), axis=0).astype(pob1.dtype)
    ps = ma.masked_values(ps, poborig1.fill_value)
    elv = ma.concatenate((elv1, elv2, elv3), axis=0)
    elv = ma.masked_values(elv, elvorig1.fill_value)
    tob = ma.concatenate((tob1, tob2, tob3), axis=0).astype(tob1.dtype)
    tob = ma.masked_values(tob, toborig1.fill_value)
    tsen = ma.concatenate((tsen1, tsen2, tsen3), axis=0).astype(tob1.dtype)
    tsen = ma.masked_values(tsen, toborig1.fill_value)
    tvo = ma.concatenate((tvo1, tvo2, tvo3), axis=0).astype(tvo1.dtype)
    tvo = ma.masked_values(tvo, toborig1.fill_value)

    logger.debug(f"  ... Concatenated array shapes, dtype and some fill_values:")
    logger.debug(f"  new typ       shape = {typ.shape}, {typ.dtype}, {typ.fill_value}")
    logger.debug(f"  new sid       shape = {sid.shape}, {sid.dtype}")
    logger.debug(f"  new cat       shape = {cat.shape}, {cat.dtype}")
    logger.debug(f"  new tpc       shape = {tpc.shape}, {tpc.dtype}")
    logger.debug(f"  new lat       shape = {lat.shape}, {lat.dtype}")
    logger.debug(f"  new lon       shape = {lon.shape}, {lon.dtype}")
    logger.debug(f"  new zob       shape = {zob.shape}, {zob.dtype}")
    logger.debug(f"  new dhr       shape = {dhr.shape}, {dhr.dtype}")
    logger.debug(f"  new pressure  shape = {pressure.shape}, {pressure.dtype}")
    logger.debug(f"  new pobqm     shape = {pobqm.shape}, {pobqm.dtype}")
    logger.debug(f"  new psqm      shape = {psqm.shape}, {psqm.dtype}")
    logger.debug(f"  new tobqm     shape = {tobqm.shape}, {tobqm.dtype}")
    logger.debug(f"  new tsenqm    shape = {tsenqm.shape}, {tsenqm.dtype}")
    logger.debug(f"  new tvoqm     shape = {tvoqm.shape}, {tvoqm.dtype}")
    logger.debug(f"  new pob       shape = {pob.shape}, {pob.dtype}")
    logger.debug(f"  new ps        shape = {ps.shape}, {ps.dtype}")
    logger.debug(f"  new elv       shape = {elv.shape}, {elv.dtype}")
    logger.debug(f"  new tob       shape = {tob.shape}, {tob.dtype}")
    logger.debug(f"  new tsen      shape = {tsen.shape}, {tsen.dtype}")
    logger.debug(f"  new tvo       shape = {tvo.shape}, {tvo.dtype}")

    # =========================
    # Create derived variables
    # =========================
    start_time = time.time()

    logger.debug(f"Creating derived variables - dateTime ...")

    cycleTimeSinceEpoch = np.int64(calendar.timegm(time.strptime(
                                   reference_time_full, '%Y%m%d%H%M')))
    dateTime1 = Compute_dateTime(cycleTimeSinceEpoch, dhr1)
    dateTime2 = Compute_dateTime(cycleTimeSinceEpoch, dhr2)
    dateTime3 = Compute_dateTime(cycleTimeSinceEpoch, dhr3)

    dateTime = ma.concatenate((dateTime1, dateTime2, dateTime3), axis=0).astype(np.int64)

    logger.debug(f"     Check derived variables type ... ")
    logger.debug(f"     dateTime shape = {dateTime.shape}")
    logger.debug(f"     dateTime type = {dateTime.dtype}")

    typ_ps = Mask_typ_for_var(typ, ps)
    typ_tsen = Mask_typ_for_var(typ, tsen)
    typ_tvo = Mask_typ_for_var(typ, tvo)

    logger.debug(f"     Check drived variables (typ*) shape & type ... ")
    logger.debug(f"     typ_ps shape = {typ_ps.shape}")
    logger.debug(f"     typ_ps type = {typ_ps.dtype}")
    logger.debug(f"     typ_tsen shape = {typ_tsen.shape}")
    logger.debug(f"     typ_tsen type = {typ_tsen.dtype}")
    logger.debug(f"     typ_tvo shape = {typ_tvo.shape}")
    logger.debug(f"     typ_tvo type = {typ_tvo.dtype}")

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

    iodafile = f"{cycle_type}.t{hh}z.{data_description}.{data_format}.nc"
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

    # Create IODA variables
    logger.debug(f" ... ... Create variables: name, type, units, & attributes")

    # Observation Type - airTemperature
    obsspace.create_var('ObsType/airTemperature', dtype=typorig1.dtype,
                        fillval=typorig1.fill_value) \
        .write_attr('long_name', 'Observation Type') \
        .write_data(typ_tsen)

    # Observation Type - virtualTemperature
    obsspace.create_var('ObsType/virtualTemperature', dtype=typorig1.dtype,
                        fillval=typorig1.fill_value) \
        .write_attr('long_name', 'Observation Type') \
        .write_data(typ_tvo)

    # Observation Type - stationPressure
    obsspace.create_var('ObsType/stationPressure', dtype=typorig1.dtype,
                        fillval=typorig1.fill_value) \
        .write_attr('long_name', 'Observation Type') \
        .write_data(typ_ps)

    # Station Identification
    obsspace.create_var('MetaData/stationIdentification', dtype=sidorig1.dtype,
                        fillval=sidorig1.fill_value) \
        .write_attr('long_name', 'Station Identification') \
        .write_data(sid)

    # PrepBUFR Data Level Category
    obsspace.create_var('MetaData/prepbufrDataLevelCategory', dtype=catorig1.dtype,
                        fillval=catorig1.fill_value) \
        .write_attr('long_name', 'prepBUFR Data Level Category') \
        .write_data(cat)

    # Temperature Event Code
    obsspace.create_var('MetaData/temperatureEventCode', dtype=tpcorig1.dtype,
                        fillval=tpcorig1.fill_value) \
        .write_attr('long_name', 'temperatureEventCode') \
        .write_data(tpc)

    # Longitude
    obsspace.create_var('MetaData/longitude', dtype=lonorig1.dtype,
                        fillval=lonorig1.fill_value) \
        .write_attr('units', 'degrees_east') \
        .write_attr('valid_range', np.array([-180, 180], dtype=np.float32)) \
        .write_attr('long_name', 'Longitude') \
        .write_data(lon)

    # Latitude
    obsspace.create_var('MetaData/latitude', dtype=latorig1.dtype,
                        fillval=latorig1.fill_value) \
        .write_attr('units', 'degrees_north') \
        .write_attr('valid_range', np.array([-90, 90], dtype=np.float32)) \
        .write_attr('long_name', 'Latitude') \
        .write_data(lat)

    # MetaData: Height Of Station
    obsspace.create_var('MetaData/heightOfStation', dtype=zoborig1.dtype,
                        fillval=zoborig1.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Height Of Station') \
        .write_data(zob)

    # Datetime
    obsspace.create_var('MetaData/dateTime', dtype=dhrorig1.dtype,
                        fillval=dhrorig1.fill_value) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'Datetime') \
        .write_data(dateTime)

    # Pressure
    obsspace.create_var('MetaData/pressure', dtype=pressureorig1.dtype,
                        fillval=pressureorig1.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Pressure') \
        .write_data(pressure)

    # Quality Marker: Station Pressure
    obsspace.create_var('QualityMarker/stationPressure', dtype=pobqmorig1.dtype,
                        fillval=pobqmorig1.fill_value) \
        .write_attr('long_name', 'Station Pressure Quality Marker') \
        .write_data(psqm)

    # Quality Marker: Air Temperature
    obsspace.create_var('QualityMarker/airTemperature', dtype=tobqmorig1.dtype,
                        fillval=tobqmorig1.fill_value) \
        .write_attr('long_name', 'Air Temperature Quality Marker') \
        .write_data(tsenqm)

    # Quality Marker: Virtual Temperature
    obsspace.create_var('QualityMarker/virtualTemperature', dtype=tobqmorig1.dtype,
                        fillval=tobqmorig1.fill_value) \
        .write_attr('long_name', 'Virtual Temperature Quality Marker') \
        .write_data(tvoqm)

    # ObsValue: Station Elevation
    obsspace.create_var('ObsValue/stationElevation', dtype=elvorig1.dtype,
                        fillval=elvorig1.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Station Elevation') \
        .write_data(elv)

    # ObsValue: Station Pressure
    obsspace.create_var('ObsValue/stationPressure', dtype=poborig1.dtype,
                        fillval=poborig1.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Station Pressure') \
        .write_data(ps)

    # ObsValue: Air Temperature
    obsspace.create_var('ObsValue/airTemperature', dtype=toborig1.dtype,
                        fillval=toborig1.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Air Temperature') \
        .write_data(tsen)

    # ObsValue: Virtual Temperature
    obsspace.create_var('ObsValue/virtualTemperature', dtype=toborig1.dtype,
                        fillval=toborig1.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Virtual Temperature') \
        .write_data(tvo)

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
    logger = Logger('bufr2ioda_conventional_prepbufr_ps.py', level=log_level,
                    colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Total running time: {running_time} seconds")
