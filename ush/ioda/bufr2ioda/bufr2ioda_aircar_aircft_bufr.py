#!/usr/bin/env python3
# (C) Copyright 2023 NOAA/NWS/NCEP/EMC
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

import sys
sys.path.append('/work2/noaa/da/nesposito/GDASApp_20231012/build/lib/python3.7/')
sys.path.append('/work2/noaa/da/nesposito/GDASApp_20231012/build/lib/python3.7/pyioda')
sys.path.append('/work2/noaa/da/nesposito/GDASApp_20231012/build/lib/python3.7/pyiodaconv')
import argparse
import numpy as np
import numpy.ma as ma
from pyiodaconv import bufr
import calendar
import json
import time
import math
import datetime
import os
from datetime import datetime
from pyioda import ioda_obs_space as ioda_ospace
from wxflow import Logger

np.set_printoptions(threshold=7000)

global int64_fill_value
int64_fill_value = np.int64(0)


def AircraftFlightLevel(lat, prlc=None, ialt=None, flvl=None, flvlst=None, heit=None, hmsl=None, psal=None):

    AircraftFlightLevel = np.full(lat.shape[0], lat.fill_value)

    for i in range(len(lat)):
        if (prlc is not None) and (not ma.is_masked(prlc[i])):
            print("NE we're doing prlc")
            if (prlc[i]) < 22630:
                print('prlc 1')
            else:
                print('prlc 2')
        elif (ialt is not None) and (not ma.is_masked(ialt[i])):
            AircraftFlightLevel[i] = ialt[i]

        if (psal is not None) and (not ma.is_masked(psal[i])):
            AircraftFlightLevel[i] = psal[i]
        elif (flvl is not None) and (not ma.is_masked(flvl[i])):
            AircraftFlightLevel[i] = flvl[i]
        elif (heit is not None) and (not ma.is_masked(heit[i])):
            AircraftFlightLevel[i] = heit[i]
        elif (hmsl is not None) and (not ma.is_masked(hmsl[i])):
            AircraftFlightLevel[i] = hmsl[i]
        elif (flvlst is not None) and (not ma.is_masked(flvlst[i])):
            AircraftFlightLevel[i] = flvlst[i]

    return AircraftFlightLevel


def QMRKH_to_QMAT_QMWN(qmat_aircft, qmwn_aircft, tmdb_aircft, wspd_aircft, wdir_aircft,
                       qmrkh2_aircft, qmrkh3_aircft, qmrkh4_aircft):
    for i in range(len(qmat_aircft)):
        TQM = np.int32(0)
        if (not ma.is_masked(qmrkh2_aircft[i])) and (qmrkh2_aircft[i] >= 3):
            TQM = np.int32(13)
        else:
            if (not ma.is_masked(qmrkh2_aircft[i])) and (qmrkh2_aircft[i] >= 1):
                TQM = np.int32(3)
            if (not ma.is_masked(qmrkh2_aircft[i])) and (qmrkh2_aircft[i] == 0):
                TQM = np.int32(2)
        if (not ma.is_masked(tmdb_aircft[i]) and (qmat_aircft[i] == 2)):
            qmat_aircft[i] = TQM

        if (not ma.is_masked(wspd_aircft[i])) and (not ma.is_masked(wdir_aircft[i]))
            and (qmwn_aircft[i] == 2):
                WQM = TQM # yes, I meant TQM
#            qmwn_aircft[i] = max(


    print("1")


def PCCF_to_QMDD(qob_aircft, qmdd_aircft, pccf_aircft):
    print("3")
#    for i in range(qmdd_aircft):
#        if (not ma.is_masked(pccf_aircft[i]) and


#         IF((QOB(1).LT.BMISS).AND.(QQM(1).EQ.2)) THEN
# ! Always set QQM to 13 if TQM was set to 13 above (regardless of PCCF)
#         IF((RQCD_8.LT.80.0).OR.(RQCD_8.GT.100.0)
#     &      .OR.(TQM(1).EQ.13.0)) THEN
#          QQM(1) = 13.0
#         ELSE
#          QQM(1) = 2.0
#         ENDIF



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

    logger.debug(f"Making QuerySets ...")
    q = bufr.QuerySet(subsets_aircar)  # AIRCAR
    r = bufr.QuerySet(subsets_aircft)  # AIRCFT, no amdar
    s = bufr.QuerySet(subsets_amdar)  # AIRCFT, amdar only


    logger.debug('Making QuerySet for AIRCAR ...')
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
    q.add("waterVaporMixingRatio", "*/ACMST2/MIXR")
    q.add("windDirection", "*/WDIR")
    q.add("windSpeed", "*/WSPD")

    # Quality Marker
    q.add("airTemperatureQM", "*/QMAT")
    q.add("waterVaporMixingRatioQM", "*/ACMST2/QMDD")
    q.add("windQM","*/QMWN")


    logger.debug('Making QuerySet for AIRCAR (no amdar)...')
    # MetaData
    r.add("year", "*/YEAR")
    r.add("month", "*/MNTH")
    r.add("day", "*/DAYS")
    r.add("hour", "*/HOUR")
    r.add("minute",  "*/MINU")
    r.add("latitude", "[*/CLATH, */CLAT]")
    r.add("longitude", "[*/CLON, */CLONH]")
    r.add("seqnum", "*/SEQNUM")
    r.add("aircraftFlightNumber", "*/ACID")
    r.add("aircraftFlightPhase", "*/POAF")
    r.add("aircraftIdentifier", "[*/RPID, */ACRN]")
    r.add("dataProviderRestricted", "*/RSRD")
    r.add("dataRestrictedExpiration", "*/EXPRSRD")
    r.add("dataReceiptTimeHour", "*/RCHR")
    r.add("dataReceiptTimeMinute", "*/RCMI")
    r.add("dataReceiptTimeSignificance", "*/RCTS")

    # MetaData/height
    r.add("flightLevel", "[*/FLVL]")
    r.add("flightLevelST", "[*/FLVLST]")
    r.add("height", "[*/HEIT]")
    r.add("heightOrAltitude", "[*/HMSL]")
    r.add("pressureAltitudeRelativeToMeanSeaLevel", "[*/PSAL]")
    r.add("percentConfidenceRH", "*/PCCF")

    # ObsValue
    r.add("airTemperature", "[*/TMDB, */TMDBST]")
    r.add("relativeHumidity", "[*/AFMST/REHU, */ACMST2/REHU, */RAWHU]")
    r.add("waterVaporMixingRatio", "[*/ACMST2/MIXR, */MIXR]")
    r.add("windDirection", "*/WDIR")
    r.add("windSpeed", "*/WSPD")

    # QualityInformation
    r.add("airTemperatureQualityInformation", "*/QMRKH[2]")
    r.add("windDirectionQualityInformation", "*/QMRKH[3]")
    r.add("windSpeedQualityInformation", "*/QMRKH[4]")

    # QualityMarker
    r.add("airTemperatureQM", "*/QMAT")
    r.add("humidityQM", "[*/AFMST/QMDD, */QMDD]")
#    r.add("waterVaporMixingRatioQM", "NC004006/QMDD")
    r.add("windQM", "*/QMWN")


    logger.debug('Making QuerySet for AIRCFT (amdar) ...')
    s.add("year", "*/YEAR")
    s.add("month", "*/MNTH")
    s.add("day", "*/DAYS")
    s.add("hour", "*/HOUR")
    s.add("minute",  "*/MINU")
    s.add("latitude", "*/CLATH")
    s.add("longitude", "*/CLONH")
    s.add("latitudeSeq", "*/ADRBLSEQ/CLATH")

    s.add("aircraftFlightNumber", "*/ACID")
    s.add("aircraftNavigationalSystem", "*/ACNS")
    s.add("aircraftIdentifier", "*/ACRN")
    s.add("flightLevelST", "*/ADRBLSEQ/FLVLST")

    # ObsValue
    s.add("airTemperature", "*/ADRBLSEQ/TMDB")
    s.add("dewpointTemperature", "*/ADRBLSEQ/TMDP")
    s.add("waterVaporMixingRatio", "*/ADRBLSEQ/MIXR")
    s.add("windDirection", "*/ADRBLSEQ/WDIR")
    s.add("windSpeed", "*/ADRBLSEQ/WSPD")

    # QualityMarker
    s.add("airTemperatureQM", "*/QMAT")
    s.add("relativeHumidityQM", "*/QMDD")
    s.add("windQM", "*/QMWN")



    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Running time for making QuerySets: {running_time} seconds")

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

    logger.debug(f"Executing QuerySet for AIRCAR ...")
    # MetaData
    year_aircar = t.get('year').astype(np.int64)
    mnth_aircar = t.get('month')
    days_aircar = t.get('day')
    hour_aircar = t.get('hour')
    minu_aircar = t.get('minute')
    lat_aircar = t.get('latitude')
    lon_aircar = t.get('longitude')
    acrn_aircar = t.get('aircraftIdentifier')
    poaf_aircar = t.get('aircraftFlightPhase')
    prlc_aircar = t.get('pressure', type='float')
#    print("NE prlc_aircar")
#    print(prlc_aircar)
    ialt_aircar = t.get('aircraftIndicatedAltitude', type='float')
#    print("NE ialt_aircar")
#    print(ialt_aircar)


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


    logger.debug(f"Executing QuerySet for AIRCFT (no amdar) ...")
    # MetaData
    year_aircft = u.get('year')
    mnth_aircft = u.get('month')
    days_aircft = u.get('day')
    hour_aircft = u.get('hour')
    minu_aircft = u.get('minute')
    lat_aircft = u.get('latitude')
    lon_aircft = u.get('longitude')
    acrn_aircft = u.get('aircraftIdentifier')
    poaf_aircft = u.get('aircraftFlightPhase')
    flvl_aircft = u.get('flightLevel')
    flvlst_aircft = u.get('flightLevelST', type='float')
    heit_aircft = u.get('height', type='float')
    hmsl_aircft = u.get('heightOrAltitude', type='float')
    psal_aircft = u.get('pressureAltitudeRelativeToMeanSeaLevel', type='float')
    pccf_aircft = u.get('percentConfidenceRH', type='int')

    # ObsValue
    tmdb_aircft = u.get('airTemperature', type='float')
    rehu_aircft = u.get('relativeHumidity', type='float')
    rehu_aircft *= 0.01
    mixr_aircft = u.get('waterVaporMixingRatio', type='float')
    wdir_aircft = u.get('windDirection', type='float')
    wspd_aircft = u.get('windSpeed', type='float')

    # Quality Information
    qmrkh2_aircft = u.get('airTemperatureQualityInformation')
    qmrkh3_aircft = u.get('windDirectionQualityInformation')
    qmrkh4_aircft = u.get('windSpeedQualityInformation')

    # Quality Marker
    qmat_aircft = u.get('airTemperatureQM')
    seqnum_aircft = u.get('seqnum')
#    qmddrehu_aircft = u.get('relativeHumidityQM')
#    qmddmixr_aircft = u.get('waterVaporMixingRatioQM')
    qmdd_aircft = u.get('humidityQM')
    print("NE qmdd check: ")
    for i in range(len(lat_aircft)):
        print(seqnum_aircft[i], lat_aircft[i], lon_aircft[i], qmdd_aircft[i])
    qmwn_aircft = u.get('windQM')


    logger.debug(f"Executing QuerySet for AIRCFT (amdar) ...")
    # MetaData
    year_amdar = v.get('year', 'latitudeSeq')
    mnth_amdar = v.get('month', 'latitudeSeq')
    days_amdar = v.get('day', 'latitudeSeq')
    hour_amdar = v.get('hour', 'latitudeSeq')
    minu_amdar = v.get('minute', 'latitudeSeq')
    lat_amdar = v.get('latitude', 'latitudeSeq')
    lon_amdar = v.get('longitude', 'latitudeSeq')
    latseq_amdar = v.get('latitudeSeq', 'latitudeSeq')
    acid_amdar = v.get('aircraftFlightNumber', 'latitudeSeq')
    acns_amdar = v.get('aircraftNavigationalSystem', 'latitudeSeq')
    acrn_amdar = v.get('aircraftIdentifier', 'latitudeSeq')
    flvlst_amdar = v.get('flightLevelST', 'latitudeSeq', type='float')
#    print("NE flvlst_amdar")
#    print(flvlst_amdar)


    # ObsValue
    tmdb_amdar = v.get('airTemperature', 'latitudeSeq', type='float')
    tmdp_amdar = v.get('dewpointTemperature', 'latitudeSeq', type='float')
    mixr_amdar = v.get('waterVaporMixingRatio', 'latitudeSeq', type='float')
    wdir_amdar = v.get('windDirection', 'latitudeSeq', type='float')
    wspd_amdar = v.get('windSpeed', 'latitudeSeq', type='float')

    # Quality Marker
    qmat_amdar = v.get('airTemperatureQM', 'latitudeSeq')
    qmdd_amdar = v.get('relativeHumidityQM', 'latitudeSeq')
    qmwn_amdar = v.get('windQM', 'latitudeSeq')

    # Check Sizes
    logger.debug(f" ... Checking array shapes and sizes ... ")
    logger.debug(f"     year_aircar      shape, type = {year_aircar.shape}, {year_aircar.dtype}")
    logger.debug(f"     mnth_aircar      shape, type = {mnth_aircar.shape}, {mnth_aircar.dtype}")
    logger.debug(f"     days_aircar      shape, type = {days_aircar.shape}, {days_aircar.dtype}")
    logger.debug(f"     hour_aircar      shape, type = {hour_aircar.shape}, {hour_aircar.dtype}")
    logger.debug(f"     minu_aircar      shape, type = {minu_aircar.shape}, {minu_aircar.dtype}")
    logger.debug(f"     lat_aircar       shape, type = {lat_aircar.shape}, {lat_aircar.dtype}")
    logger.debug(f"     lon_aircar       shape, type = {lon_aircar.shape}, {lon_aircar.dtype}")
    logger.debug(f"     acrn_aircar      shape, type = {acrn_aircar.shape}, {acrn_aircar.dtype}")
    logger.debug(f"     poaf_aircar      shape, type = {poaf_aircar.shape}, {poaf_aircar.dtype}")
    logger.debug(f"     prlc_aircar      shape, type = {prlc_aircar.shape}, {prlc_aircar.dtype}")
    logger.debug(f"     ialt_aircar      shape, type = {ialt_aircar.shape}, {ialt_aircar.dtype}")
    logger.debug(f"     tmdb_aircar      shape, type = {tmdb_aircar.shape}, {tmdb_aircar.dtype}")
    logger.debug(f"     rehu_aircar      shape, type = {rehu_aircar.shape}, {rehu_aircar.dtype}")
    logger.debug(f"     mixr_aircar      shape, type = {mixr_aircar.shape}, {mixr_aircar.dtype}")
    logger.debug(f"     wdir_aircar      shape, type = {wdir_aircar.shape}, {wdir_aircar.dtype}")
    logger.debug(f"     wspd_aircar      shape, type = {wspd_aircar.shape}, {wspd_aircar.dtype}")
    logger.debug(f"     qmat_aircar      shape, type = {qmat_aircar.shape}, {qmat_aircar.dtype}")
    logger.debug(f"     qmdd_aircar      shape, type = {qmdd_aircar.shape}, {qmdd_aircar.dtype}")
    logger.debug(f"     qmwn_aircar      shape, type = {qmwn_aircar.shape}, {qmwn_aircar.dtype}")
    logger.debug(f"     year_aircft      shape, type = {year_aircft.shape}, {year_aircft.dtype}")
    logger.debug(f"     mnth_aircft      shape, type = {mnth_aircft.shape}, {mnth_aircft.dtype}")
    logger.debug(f"     days_aircft      shape, type = {days_aircft.shape}, {days_aircft.dtype}")
    logger.debug(f"     hour_aircft      shape, type = {hour_aircft.shape}, {hour_aircft.dtype}")
    logger.debug(f"     minu_aircft      shape, type = {minu_aircft.shape}, {minu_aircft.dtype}")
    logger.debug(f"     lat_aircft       shape, type = {lat_aircft.shape}, {lat_aircft.dtype}")
    logger.debug(f"     lon_aircft       shape, type = {lon_aircft.shape}, {lon_aircft.dtype}")
    logger.debug(f"     acrn_aircft      shape, type = {acrn_aircft.shape}, {acrn_aircft.dtype}")
    logger.debug(f"     poaf_aircft      shape, type = {poaf_aircft.shape}, {poaf_aircft.dtype}")
    logger.debug(f"     flvl_aircft      shape, type = {flvl_aircft.shape}, {flvl_aircft.dtype}")
    logger.debug(f"     flvlst_aircft    shape, type = {flvlst_aircft.shape}, {flvlst_aircft.dtype}")
    logger.debug(f"     heit_aircft      shape, type = {heit_aircft.shape}, {heit_aircft.dtype}")
    logger.debug(f"     hmsl_aircft      shape, type = {hmsl_aircft.shape}, {hmsl_aircft.dtype}")
    logger.debug(f"     psal_aircft      shape, type = {psal_aircft.shape}, {psal_aircft.dtype}")
    logger.debug(f"     pccf_aircft      shape, type = {pccf_aircft.shape}, {pccf_aircft.dtype}")
    logger.debug(f"     tmdb_aircft      shape, type = {tmdb_aircft.shape}, {tmdb_aircft.dtype}")
    logger.debug(f"     rehu_aircft      shape, type = {rehu_aircft.shape}, {rehu_aircft.dtype}")
    logger.debug(f"     mixr_aircft      shape, type = {mixr_aircft.shape}, {mixr_aircft.dtype}")
    logger.debug(f"     wdir_aircft      shape, type = {wdir_aircft.shape}, {wdir_aircft.dtype}")
    logger.debug(f"     wspd_aircft      shape, type = {wspd_aircft.shape}, {wspd_aircft.dtype}")
    logger.debug(f"     qmrkh2_aircft    shape, type = {qmrkh2_aircft.shape}, {qmrkh2_aircft.dtype}")
    logger.debug(f"     qmrkh3_aircft    shape, type = {qmrkh3_aircft.shape}, {qmrkh3_aircft.dtype}")
    logger.debug(f"     qmrkh4_aircft    shape, type = {qmrkh4_aircft.shape}, {qmrkh4_aircft.dtype}")
    logger.debug(f"     qmat_aircft      shape, type = {qmat_aircft.shape}, {qmat_aircft.dtype}")
#    logger.debug(f"     qmddrehu_aircft  shape, type = {qmddrehu_aircft.shape}, {qmddrehu_aircft.dtype}")
#    logger.debug(f"     qmddrehu_aircft  shape, type = {qmddrehu_aircft.shape}, {qmddrehu_aircft.dtype}")
    logger.debug(f"     qmdd_aircft  shape, type = {qmdd_aircft.shape}, {qmdd_aircft.dtype}")
    logger.debug(f"     qmwn_aircft      shape, type = {qmwn_aircft.shape}, {qmwn_aircft.dtype}")
    logger.debug(f"     year_amdar       shape, type = {year_amdar.shape}, {year_amdar.dtype}")
    logger.debug(f"     mnth_amdar       shape, type = {mnth_amdar.shape}, {mnth_amdar.dtype}")
    logger.debug(f"     days_amdar       shape, type = {days_amdar.shape}, {days_amdar.dtype}")
    logger.debug(f"     hour_amdar       shape, type = {hour_amdar.shape}, {hour_amdar.dtype}")
    logger.debug(f"     minu_amdar       shape, type = {minu_amdar.shape}, {minu_amdar.dtype}")
    logger.debug(f"     lat_amdar        shape, type = {lat_amdar.shape}, {lat_amdar.dtype}")
    logger.debug(f"     lon_amdar        shape, type = {lon_amdar.shape}, {lon_amdar.dtype}")
    logger.debug(f"     latseq_amdar     shape, type = {latseq_amdar.shape}, {latseq_amdar.dtype}")
    logger.debug(f"     acid_amdar       shape, type = {acid_amdar.shape}, {acid_amdar.dtype}")
    logger.debug(f"     acns_amdar       shape, type = {acns_amdar.shape}, {acns_amdar.dtype}")
    logger.debug(f"     acrn_amdar       shape, type = {acrn_amdar.shape}, {acrn_amdar.dtype}")
    logger.debug(f"     flvlst_amdar     shape, type = {flvlst_amdar.shape}, {flvlst_amdar.dtype}")
    logger.debug(f"     tmdb_amdar       shape, type = {tmdb_amdar.shape}, {tmdb_amdar.dtype}")
    logger.debug(f"     tmdp_amdar       shape, type = {tmdp_amdar.shape}, {tmdp_amdar.dtype}")
    logger.debug(f"     mixr_amdar       shape, type = {mixr_amdar.shape}, {mixr_amdar.dtype}")
    logger.debug(f"     wdir_amdar       shape, type = {wdir_amdar.shape}, {wdir_amdar.dtype}")
    logger.debug(f"     wspd_amdar       shape, type = {wspd_amdar.shape}, {wspd_amdar.dtype}")
    logger.debug(f"     qmat_amdar       shape, type = {qmat_amdar.shape}, {qmat_amdar.dtype}")
    logger.debug(f"     qmdd_amdar       shape, type = {qmdd_amdar.shape}, {qmdd_amdar.dtype}")
    logger.debug(f"     qmwn_amdar       shape, type = {qmwn_amdar.shape}, {qmwn_amdar.dtype}")

    # Derive QM values in aircft
    logger.debug("Convert variables for QMRKH to QMAT/QMDD/QMWN")
    qmat_aircft, qmwn_aircft = QMRKH_to_QMAT_QMWN(qmat_aircft, qmwn_aircft, tmdb_aircft,
                                                   wspd_aircft, wdir_aircft,
                                                   qmrkh2_aircft, qmrkh3_aircft, qmrkh4_aircft)
    qmdd_aircft = PCCF_to_QMDD(qmdd_aircft, pccf_aircft)

    # Concatenate
    logger.debug("Concatenate the variables ... ")
    lat = ma.concatenate((lat_aircar, lat_aircft, lat_amdar), axis=0).astype(np.float32)
    lat = ma.masked_values(lat, lat_aircar.fill_value)
    lon = ma.concatenate((lat_aircar, lat_aircft, lat_amdar), axis=0).astype(np.float32)
    lon = ma.masked_values(lon, lon_aircar.fill_value)


    logger.debug(f" ... Check the concatenated array shapes, dtypes, some fill_values  ... ")
    logger.debug(f"     concatenated lat size = {lat.shape}, {lat.dtype}, {lat.fill_value}")
    logger.debug(f"     concatenated lon size = {lon.shape}, {lon.dtype}, {lon.fill_value}")


    # Derive time/date   #check to see if this isactually dateTime
    logger.debug(f"     Derive the dateTime variable")
    dateTime_aircar = t.get_datetime('year', 'month', 'day', 'hour', 'minute').astype(np.int64)
    dateTime_aircft = u.get_datetime('year', 'month', 'day', 'hour', 'minute').astype(np.int64)
    dateTime_amdar = v.get_datetime('year', 'month', 'day', 'hour', 'minute', group_by='latitudeSeq').astype(np.int64)

    logger.debug(f"     dateTime_aircar = {dateTime_aircar.shape}, {dateTime_aircar.dtype}")
    logger.debug(f"     dateTime_aircft = {dateTime_aircft.shape}, {dateTime_aircft.dtype}")
    logger.debug(f"     dateTime_amdar = {dateTime_amdar.shape}, {dateTime_amdar.dtype}")

    dateTime = ma.concatenate((dateTime_aircar, dateTime_aircft, dateTime_amdar),axis=0).astype(np.int64)
    dateTime = ma.masked_values(dateTime, dateTime_aircar.fill_value)
    logger.debug(f"     dateTime concatenated info = {dateTime.shape}, {dateTime.dtype}, {dateTime.fill_value}")


    # Derive aircraftFlightLevel
    acftflvl_aircar = AircraftFlightLevel(lat=lat_aircar, prlc=prlc_aircar, ialt=ialt_aircar, flvl=None, flvlst=None,
                                          heit=None, hmsl=None, psal=None)
    acftflvl_aircft = AircraftFlightLevel(lat=lat_aircft, prlc=None, ialt=None, flvl=flvl_aircft, flvlst=flvlst_aircft,
                                          heit=heit_aircft, hmsl=hmsl_aircft, psal=psal_aircft)
    acftflvl_amdar = AircraftFlightLevel(lat=lat_amdar, prlc=None, ialt=None, flvl=None, flvlst=flvlst_amdar,
                                         heit=None, hmsl=None, psal=None)

    aircraftFlightLevel = ma.concatenate((acftflvl_aircar, acftflvl_aircft, acftflvl_amdar), axis=0).astype(np.float32)
    aircraftFlightLevel = ma.masked_values(aircraftFlightLevel, lat.fill_value)
    logger.debug(f"     aircraftFlightLevel concatenated info = {aircraftFlightLevel.shape}, {aircraftFlightLevel.dtype}, {aircraftFlightLevel.fill_value}")


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
    obsspace.write_attr('sourceFiles', [bufrfile_aircar, bufrfile_aircft])
    obsspace.write_attr('dataProviderOrigin', data_provider)
    obsspace.write_attr('description', data_description)
    obsspace.write_attr('datetimeReference', reference_time)
    obsspace.write_attr('datetimeRange',
                        [str(min(dateTime)), str(max(dateTime))])

    # Create IODA variables
    logger.debug(f" ... ... Create variables: name, type, units, & attributes")

    # MetaData
    # Latitude
    obsspace.create_var('MetaData/latitude', dtype=lat.dtype,
                        fillval=lat.fill_value) \
        .write_attr('units', 'degrees_north') \
        .write_attr('valid_range', np.array([-90, 90], dtype=np.float32)) \
        .write_attr('long_name', 'Latitude') \
        .write_data(lat)

    # Longitude
    obsspace.create_var('MetaData/longitude', dtype=lon.dtype, fillval=lon.fill_value) \
        .write_attr('units', 'degrees_east') \
        .write_attr('valid_range', np.array([-180, 180], dtype=np.float32)) \
        .write_attr('long_name', 'Longitude') \
        .write_data(lon)

    # Datetime
    obsspace.create_var('MetaData/dateTime', dtype=dateTime.dtype,
                        fillval=dateTime.fill_value) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'Datetime') \
        .write_data(dateTime)

    # AircraftFlightLevel
    obsspace.create_var('MetaData/aircraftFlightLevel', dtype=aircraftFlightLevel.dtype, fillval=aircraftFlightLevel.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'aircraftFlightLevel') \
        .write_data(aircraftFlightLevel)




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

