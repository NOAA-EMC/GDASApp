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
            logger.info("Making QuerySet for SFCSHP")
            
            # ObsType
            r.add('ationType', '*/TYP')

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
            logger.info("Making QuerySet for ADPUPA")
            # ObsType
            s.add('ationType', '*/TYP')
            
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
    logger.info(" ... Executing QuerySet for ADPSFC: get ObsType ...")
    # ObsType
    typorig1 = t.get('observationType')

    logger.info(" ... Executing QuerySet for ADPSFC: get MetaData ...")    
    # MetaData
    sidorig1 = t.get('stationIdentification')
    catorig1 = t.get('prepbufrDataLevelCategory')
    tpcorig1 = t.get('temperatureEventCode')
    latorig1 = t.get('latitude')
    lonorig1 = t.get('longitude')
    lonorig1[lonorig1 > 180] -= 360
    dhrorig1 = t.get('obsTimeMinusCycleTime', type='int64')
    zoborig1 = t.get('heightOfStation', type='float')
    pressureorig1 = t.get('pressure')
    pressureorig1 *= 100

    logger.info(f" ... Executing QuerySet: get QualityMarker ...")
    # QualityMarker
    pobqmorig1 = t.get('qualityMarkerStationPressure')
    tobqmorig1 = t.get('qualityMarkerAirTemperature')
    tsenqmorig1 = np.full(tobqmorig1.shape[0], tobqmorig1.fill_value) 
    tsenqmorig1 = np.where(((tpcorig1 >= 1) & (tpcorig1 < 8)), tobqmorig1, tsenqmorig1)
    tvoqmorig1 = np.full(tobqmorig1.shape[0], tobqmorig1.fill_value)
    tvoqmorig1 = np.where((tpcorig1 == 8), tobqmorig1, tvoqmorig1)

    logger.info(f" ... Executing QuerySet: get ObsValues ...")
    # ObsValue
    elvorig1 = t.get('stationElevation', type='float')
    poborig1 = t.get('stationPressure')
    poborig1 *= 100
    toborig1 = t.get('airTemperature')
    toborig1 += 273.15
    tsenorig1 = np.full(toborig1.shape[0], toborig1.fill_value)
    tsenorig1 = np.where(((tpcorig1 >= 1) & (tpcorig1 < 8)), toborig1, tsenorig1)
    tvoorig1 = np.full(toborig1.shape[0], toborig1.fill_value)
    tvoorig1 = np.where((tpcorig1 == 8), toborig1, tvoorig1)

    typ1 = np.array([]) 
    sid1 = np.array([]) 
    cat1 = np.array([])
    tpc1 = np.array([])
    lat1 = np.array([])
    lon1 = np.array([])
    zob1 = np.array([])
    dhr1 = np.array([])
    elv1 = np.array([])
    pressure1 = np.array([])
    pobqm1 = np.array([])
    tobqm1 = np.array([])
    tsenqm1 = np.array([])
    tvoqm1 = np.array([])
    elv1 = np.array([])
    pob1 = np.array([])
    tob1 = np.array([])
    tsen1 = np.array([])
    tvo1 = np.array([])
    
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
            pobqm1 = np.append(pobqm1, pobqmorig1[i])
            tobqm1 = np.append(tobqm1, tobqmorig1[i])
            tsenqm1 = np.append(tsenqm1, tsenqmorig1[i])
            tvoqm1 = np.append(tvoqm1, tvoqmorig1[i])
            elv1 = np.append(elv1, elvorig1[i])
            pob1 = np.append(pob1, poborig1[i])
            tsen1 = np.append(tsen1, tsenorig1[i])
            tvo1 = np.append(tvo1, tvoorig1[i])

    logger.info(" ... QuerySet execution for ADPSFC ... done!")

    # SFCSHP
    logger.info(" ... Executing QuerySet for SFCSHP: get MetaData ...")
    # MetaData
    typorig2 = u.get('observationType')
    sidorig2 = u.get('stationIdentification')
    catorig2 = u.get('prepbufrDataLevelCategory')
    tpcorig2 = u.get('temperatureEventCode')
    latorig2 = u.get('latitude')
    lonorig2 = u.get('longitude')
    lonorig2[lonorig2 > 180] -= 360
    zoborig2 = u.get('heightOfStation', type='float')
    dhrorig2 = u.get('obsTimeMinusCycleTime', type='int64')
    pressureorig2 = u.get('pressure')
    pressureorig2 *= 100

    logger.info(f" ... Executing QuerySet: get QualityMarker information ...")
    # QualityMarker
    pobqmorig2 = u.get('qualityMarkerStationPressure')
    tobqmorig2 = u.get('qualityMarkerAirTemperature')
    tsenqmorig2 = np.full(tobqmorig2.shape[0], tobqmorig2.fill_value)
    tsenqmorig2 = np.where(((tpcorig2 >= 1) & (tpcorig2 < 8)), tobqmorig2, tsenqmorig2)
    tvoqmorig2 = np.full(tobqmorig2.shape[0], tobqmorig2.fill_value)
    tvoqmorig2 = np.where((tpcorig2 == 8), tobqmorig2, tvoqmorig2)

    logger.info(f" ... Executing QuerySet: get ObsValues ...")
    # ObsValue
    elvorig2 = u.get('stationElevation', type='float')
    poborig2 = u.get('stationPressure')
    poborig2 *= 100
    toborig2 = u.get('airTemperature')
    toborig2 += 273.15
    tsenorig2 = np.full(toborig2.shape[0], toborig2.fill_value)
    tsenorig2 = np.where(((tpcorig2 >= 1) & (tpcorig2 < 8)), toborig2, tsenorig2)
    tvoorig2 = np.full(toborig2.shape[0], toborig2.fill_value)
    tvoorig2 = np.where((tpcorig2 == 8), toborig2, tvoorig2)

    typ2 = np.array([]) 
    sid2 = np.array([]) 
    cat2 = np.array([])
    tpc2 = np.array([])
    lat2 = np.array([])
    lon2 = np.array([])
    zob2 = np.array([])
    dhr2 = np.array([])
    pressure2 = np.array([])
    pobqm2 = np.array([])
    tobqm2 = np.array([])
    tsenqm2 = np.array([])
    tvoqm2 = np.array([])
    elv2 = np.array([])
    pob2 = np.array([])
    tob2 = np.array([])
    tsen2 = np.array([])
    tvo2 = np.array([])
    
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
            tsenqm2 = np.append(tsenqm2, tsenqmorig2[i])
            tvoqm2 = np.append(tvoqm2, tvoqmorig2[i])
            elv2 = np.append(elv2, elvorig2[i])
            zob2 = np.append(zob2, zoborig2[i])
            pob2 = np.append(pob2, poborig2[i])
            tsen2 = np.append(tsen2, tsenorig2[i])
            tvo2 = np.append(tvo2, tvoorig2[i])

    logger.info(f" ... QuerySet execution for SFCSHP ... done!")
    
    # ADPUPA
    logger.info(" ... Executing QuerySet for ADPUPA: get MetaData ...")
    # ObsType 
    typ3 = v.get('observationType', 'prepbufrDataLevelCategory')

    # MetaData
    sid3 = v.get('stationIdentification', 'prepbufrDataLevelCategory')
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
    pobqm3 = v.get('qualityMarkerStationPressure', 'prepbufrDataLevelCategory')
    psqm3 = np.full(pobqm3.shape[0], pobqm3.fill_value)
    psqm3 = np.where(cat3 == 0, pobqm3, psqm3)
    tobqm3 = v.get('qualityMarkerAirTemperature', 'prepbufrDataLevelCategory')
    tsenqm3 = np.full(tobqm3.shape[0], tobqm3.fill_value)
    tsenqm3 = np.where(((tpc3 >= 1) & (tpc3 < 8) & (cat3 == 0)), tobqm3, tsenqm3)
    tvoqm3 = np.full(tobqm3.shape[0], tobqm3.fill_value)
    tvoqm3 = np.where(((tpc3 == 8) & (cat3 == 0)), tobqm3, tvoqm3)

    # ObsValue
    elv3 = v.get('stationElevation', 'prepbufrDataLevelCategory', type='float')
    pob3 = v.get('stationPressure', 'prepbufrDataLevelCategory')
    ps3 = np.full(pressure3.shape[0], pressure3.fill_value)
    ps3 = np.where(cat3 == 0, pressure3, ps3)
    tob3 = v.get('airTemperature', 'prepbufrDataLevelCategory')
    tob3 += 273.15
    tsen3 = np.full(tob3.shape[0], tob3.fill_value)
    tsen3 = np.where(((tpc3 >= 1) & (tpc3 < 8) & (cat3 == 0)), tob3, tsen3)
    tvo3 = np.full(tob3.shape[0], tob3.fill_value)
    tvo3 = np.where(((tpc3 == 8) & (cat3 == 0)), tob3, tvo3)

    
    logger.info(f" ... QuerySet execution for ADPSFC ... done!")
    logger.info(f" ... Executing QuerySet: Done!")
    running_time = end_time - start_time
    logger.info(f"Running time for executing QuerySet: {running_time} seconds")

    # Check BUFR variable dimension and type
    logger.info(f"     The shapes and dtypes of all 3 variables")
    logger.info(f"     typ1       shape, type = {typ1.shape}, {typ1.dtype}")
    logger.info(f"     typ2       shape, type = {typ2.shape}, {typ2.dtype}")
    logger.info(f"     typ3       shape, type = {typ3.shape}, {typ3.dtype}")
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
    logger.info(f"     zob1       shape, type = {zob1.shape}, {zob1.dtype}")
    logger.info(f"     zob2       shape, type = {zob2.shape}, {zob2.dtype}")
    logger.info(f"     zob3       shape, type = {zob3.shape}, {zob3.dtype}")
    logger.info(f"     dhr1       shape, type = {dhr1.shape}, {dhr1.dtype}")
    logger.info(f"     dhr2       shape, type = {dhr2.shape}, {dhr2.dtype}")
    logger.info(f"     dhr3       shape, type = {dhr3.shape}, {dhr3.dtype}")
    logger.info(f"     pressure1  shape, type = {pressure1.shape}, {pressure1.dtype}")
    logger.info(f"     pressure2  shape, type = {pressure2.shape}, {pressure2.dtype}")
    logger.info(f"     pressure3  shape, type = {pressure3.shape}, {pressure3.dtype}")
    logger.info(f"     pobqm1     shape, type = {pobqm1.shape}, {pobqm1.dtype}")
    logger.info(f"     pobqm2     shape, type = {pobqm2.shape}, {pobqm2.dtype}")
    logger.info(f"     pobqm3     shape, type = {pobqm3.shape}, {pobqm3.dtype}")
    logger.info(f"     psqm3      shape, type = {psqm3.shape}, {psqm3.dtype}")
    logger.info(f"     tobqm1     shape, type = {tobqm1.shape}, {tobqm1.dtype}")
    logger.info(f"     tobqm2     shape, type = {tobqm2.shape}, {tobqm2.dtype}")
    logger.info(f"     tobqm3     shape, type = {tobqm3.shape}, {tobqm3.dtype}")
    logger.info(f"     tsenqm1    shape, type = {tsenqm1.shape}, {tsenqm1.dtype}")
    logger.info(f"     tsenqm2    shape, type = {tsenqm2.shape}, {tsenqm2.dtype}")
    logger.info(f"     tsenqm3    shape, type = {tsenqm3.shape}, {tsenqm3.dtype}")
    logger.info(f"     tvoqm1     shape, type = {tvoqm1.shape}, {tvoqm1.dtype}")
    logger.info(f"     tvoqm2     shape, type = {tvoqm2.shape}, {tvoqm2.dtype}")
    logger.info(f"     tvoqm3     shape, type = {tvoqm3.shape}, {tvoqm3.dtype}")
    logger.info(f"     elv1       shape, type = {elv1.shape}, {elv1.dtype}")
    logger.info(f"     elv2       shape, type = {elv2.shape}, {elv2.dtype}")
    logger.info(f"     elv3       shape, type = {elv3.shape}, {elv3.dtype}")
    logger.info(f"     pob1       shape, type = {pob1.shape}, {pob1.dtype}")
    logger.info(f"     pob2       shape, type = {pob2.shape}, {pob2.dtype}")
    logger.info(f"     pob3       shape, type = {pob3.shape}, {pob3.dtype}")
    logger.info(f"     tob1       shape, type = {tob1.shape}, {tob1.dtype}")
    logger.info(f"     tob2       shape, type = {tob2.shape}, {tob2.dtype}")
    logger.info(f"     tob3       shape, type = {tob3.shape}, {tob3.dtype}")
    logger.info(f"     tsen1      shape, type = {tsen1.shape}, {tsen1.dtype}")
    logger.info(f"     tsen2      shape, type = {tsen2.shape}, {tsen2.dtype}")
    logger.info(f"     tsen3      shape, type = {tsen3.shape}, {tsen3.dtype}")
    logger.info(f"     tvo1       shape, type = {tvo1.shape}, {tvo1.dtype}")
    logger.info(f"     tvo2       shape, type = {tvo2.shape}, {tvo2.dtype}")
    logger.info(f"     tvo3       shape, type = {tvo3.shape}, {tvo3.dtype}")

    logger.info(f"  ... Concatenate the variables")
    typ = np.concatenate((typ1, typ2, typ3), axis=0)
    sid = np.concatenate((sid1, sid2, sid3), axis=0)
    cat = np.concatenate((cat1, cat2, cat3), axis=0)
    tpc = np.concatenate((tpc1, tpc2, tpc3), axis=0)
    lat = np.concatenate((lat1, lat2, lat3), axis=0)
    lon = np.concatenate((lon1, lon2, lon3), axis=0)
    zob = np.concatenate((zob1, zob2, zob3), axis=0).astype(zob1.dtype)
    dhr = np.concatenate((dhr1, dhr2, dhr3), axis=0).astype(dhr1.dtype)
    pressure = np.concatenate((pressure1, pressure2, pressure3), axis=0)
    pobqm = np.concatenate((pobqm1, pobqm2, pobqm3), axis=0)
    psqm = np.concatenate((pobqm1, pobqm2, psqm3), axis=0)
    tobqm = np.concatenate((tobqm1, tobqm2, tobqm3), axis=0)
    tsenqm = np.concatenate((tsenqm1, tsenqm2, tsenqm3), axis=0)
    tvoqm = np.concatenate((tvoqm1, tvoqm2, tvoqm3), axis=0)
    pob = np.concatenate((pob1, pob2, pob3), axis=0).astype(pob1.dtype)
    ps = np.concatenate((pob1, pob2, ps3), axis=0).astype(pob1.dtype)
    elv = np.concatenate((elv1, elv2, elv3), axis=0)
    tob =  np.concatenate((tob1, tob2, tob3), axis=0).astype(tob1.dtype)
    tsen = np.concatenate((tsen1, tsen2, tsen3), axis=0).astype(tob1.dtype)
    tvo = np.concatenate((tvo1, tvo2, tvo3), axis=0).astype(tvo1.dtype)

    logger.info(f"  ... Concatenated array shapes:")
    logger.info(f"  new typ       shape = {typ.shape}")
    logger.info(f"  new sid       shape = {sid.shape}")
    logger.info(f"  new cat       shape = {cat.shape}")
    logger.info(f"  new tpc       shape = {tpc.shape}")
    logger.info(f"  new lat       shape = {lat.shape}")
    logger.info(f"  new lon       shape = {lon.shape}")
    logger.info(f"  new zob       shape = {zob.shape}")
    logger.info(f"  new dhr       shape = {dhr.shape}")
    logger.info(f"  new pressure  shape = {pressure.shape}")
    logger.info(f"  new pobqm     shape = {pobqm.shape}")
    logger.info(f"  new psqm      shape = {psqm.shape}")
    logger.info(f"  new tobqm     shape = {tobqm.shape}")
    logger.info(f"  new tsenqm    shape = {tsenqm.shape}")
    logger.info(f"  new tvoqm     shape = {tvoqm.shape}")
    logger.info(f"  new pob       shape = {pob.shape}")
    logger.info(f"  new ps        shape = {ps.shape}")
    logger.info(f"  new elv       shape = {elv.shape}")
    logger.info(f"  new tob       shape = {tob.shape}")
    logger.info(f"  new tsen      shape = {tsen.shape}")
    logger.info(f"  new tvo       shape = {tvo.shape}")

    # =========================
    # Create derived variables
    # =========================
    start_time = time.time()

    logger.info(f"Creating derived variables - dateTime ...")

    cycleTimeSinceEpoch = np.int64(calendar.timegm(time.strptime(
                                   reference_time_full, '%Y%m%d%H%M')))
    dateTime1 = Compute_dateTime(cycleTimeSinceEpoch, dhr1)
    dateTime2 = Compute_dateTime(cycleTimeSinceEpoch, dhr2)
    dateTime3 = Compute_dateTime(cycleTimeSinceEpoch, dhr3)

    dateTime = np.concatenate((dateTime1, dateTime2, dateTime3), axis=0).astype(np.int64)

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

    # Observation Type - airTemperature
    obsspace.create_var('ObsType/airTemperature', dtype=typ1.dtype,
                        fillval=typ1.fill_value) \
        .write_attr('long_name', 'Observation Type') \
        .write_data(typ)
    
    # Observation Type - virtualTemperature
    obsspace.create_var('ObsType/virtualTemperature', dtype=typ1.dtype,
                        fillval=typ1.fill_value) \
        .write_attr('long_name', 'Observation Type') \
        .write_data(typ)
    
    # Observation Type - stationPressure
    obsspace.create_var('ObsType/stationPressure', dtype=typ1.dtype,
                        fillval=typ1.fill_value) \
        .write_attr('long_name', 'Observation Type') \
        .write_data(typ)
    
    # Station Identification
    obsspace.create_var('MetaData/stationIdentification', dtype=sid1.dtype,
                        fillval=sid1.fill_value) \
        .write_attr('long_name', 'Station Identification') \
        .write_data(sid)

    # PrepBUFR Data Level Category
    obsspace.create_var('MetaData/prepbufrDataLevelCategory', dtype=cat1.dtype,
                        fillval=cat1.fill_value) \
        .write_attr('long_name', 'prepBUFR Data Level Category') \
        .write_data(cat)

    # Temperature Event Code
    obsspace.create_var('MetaData/temperatureEventCode', dtype=tpc1.dtype,
                        fillval=tpc1.fill_value) \
        .write_attr('long_name', 'temperatureEventCode') \
        .write_data(tpc)

    # Longitude
    obsspace.create_var('MetaData/longitude', dtype=lon1.dtype,
                        fillval=lon1.fill_value) \
        .write_attr('units', 'degrees_east') \
        .write_attr('valid_range', np.array([-180, 180], dtype=np.float32)) \
        .write_attr('long_name', 'Longitude') \
        .write_data(lon)

    # Latitude
    obsspace.create_var('MetaData/latitude', dtype=lat1.dtype,
                        fillval=lat1.fill_value) \
        .write_attr('units', 'degrees_north') \
        .write_attr('valid_range', np.array([-90, 90], dtype=np.float32)) \
        .write_attr('long_name', 'Latitude') \
        .write_data(lat)

    # MetaData: Height Of Station
    obsspace.create_var('MetaData/heightOfStation', dtype=zob1.dtype,
                        fillval=zob1.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Height Of Station') \
        .write_data(zob)
    
    # Datetime
    obsspace.create_var('MetaData/dateTime', dtype=dhr1.dtype,
                        fillval=dhr1.fill_value) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'Datetime') \
        .write_data(dateTime)

    # Pressure
    obsspace.create_var('MetaData/pressure', dtype=pressure1.dtype,
                        fillval=pressure1.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Pressure') \
        .write_data(pressure)

    # Quality Marker: Station Pressure
    obsspace.create_var('QualityMarker/stationPressure', dtype=pobqm1.dtype,
                        fillval=pobqm1.fill_value) \
        .write_attr('long_name', 'Station Pressure Quality Marker') \
        .write_data(psqm)

    # Quality Marker: Air Temperature
    obsspace.create_var('QualityMarker/airTemperature', dtype=tobqm1.dtype,
                        fillval=tobqm1.fill_value) \
        .write_attr('long_name', 'Air Temperature Quality Marker') \
        .write_data(tsenqm)

    # Quality Marker: Virtual Temperature
    obsspace.create_var('QualityMarker/virtualTemperature', dtype=tobqm1.dtype,
                        fillval=tobqm1.fill_value) \
        .write_attr('long_name', 'Virtual Temperature Quality Marker') \
        .write_data(tvoqm)

    # ObsValue: Station Elevation
    obsspace.create_var('ObsValue/stationElevation', dtype=elv1.dtype,
                        fillval=elv1.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Station Elevation') \
        .write_data(elv)
    
    # ObsValue: Station Pressure
    obsspace.create_var('ObsValue/stationPressure', dtype=pob1.dtype,
                        fillval=pob1.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Station Pressure') \
        .write_data(ps)

    # ObsValue: Air Temperature
    obsspace.create_var('ObsValue/airTemperature', dtype=tob1.dtype,
                        fillval=tob1.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Air Temperature') \
        .write_data(tsen)

    # ObsValue: Virtual Temperature
    obsspace.create_var('ObsValue/virtualTemperature', dtype=tvo1.dtype,
                        fillval=tob1.fill_value) \
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
