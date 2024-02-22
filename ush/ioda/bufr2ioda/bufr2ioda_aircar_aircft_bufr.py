#!/usr/bin/env python3
# (C) Copyright 2024 NOAA/NWS/NCEP/EMC
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# This code uses the python API to converter aircft and aircar bufr data into IODA.
# The QC done was taken from the prepobs code, specifically iw3unpbf.f
# Some of the rounding / was not done, such as multipying specific humidity by 1000 
# to make the units "g kg-1", or to multiply Temperature by 1000 (I don't know why it
# was done to begin with, but IODA needs them in regular units so they stayed here.
# There is Pressure in the prepbufr file but not in the bufr file and the iw3unpbf code
# explicitly states that P derived from the US standard atmosphere is not used as an
# observation.
#

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
from operator import itemgetter

# NickE I forget why I added this
# np.set_printoptions(threshold=7000)

global int64_fill_value
int64_fill_value = np.int64(0)


# aircraftFlightLevel
def AircraftFlightLevel(lat, prlc=None, ialt=None, flvl=None, flvlst=None, heit=None, hmsl=None, psal=None):

    AircraftFlightLevel = np.full(lat.shape[0], lat.fill_value)

    for i in range(len(lat)):
        if (prlc is not None) and (not ma.is_masked(prlc[i])):
            if (prlc[i]) < 22630:
                AircraftFlightLevel[i] = HGTF_HI(prlc[i])
            else:
                AircraftFlightLevel[i] = HGTF_LO(prlc[i])
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


# stationIdentification
def determine_stationID(rpid, acrn, acid, subset, len_all):
    stationIdentification = ['        '] * len_all
    for i in range(len(subset)):
        if subset[i] == 'NC004004':
            if ma.is_masked(acrn[i]):
                SID = 'ACARS   '
            else:
                SID = acrn[i]
        elif subset[i] == 'NC004006' or subset[i] == 'NC004009' or subset[i] == 'NC004010':
            if ma.is_masked(acrn[i]):
                if subset[i] == 'NC004006':
                    SID = 'E-AMDAR '
                elif subset[i] == 'NC004009':
                    SID = 'CA-AMDAR'
                elif subset[i] == 'NC004010':
                    SID = 'TAMDARB '
            else:
                SID = acrn[i]
        elif subset[i] == 'NC004011' or subset[i] == 'NC004103':
            if ma.is_masked(acrn[i]):
                if ma.is_masked(acid[i]):
                    if subset[i] == 'NC004011':
                        SID = 'K-AMDAR '
                    else:
                        SID = 'AMDAR-BF'
                else:
                    SID = acid[i]
            else:
                SID = acrn[i]
        elif subset[i] == 'NC004008' or subset[i] == 'NC004012' or subset[i] == 'NC004013':
            if ma.is_masked(acid[i]):
                SID = 'TAMDAR-M'
            else:
                SID = acid[i]
        elif subset[i] == 'NC004001' or subset[i] == 'NC004002' or subset[i] == 'NC004003':
            if ma.is_masked(rpid[i]):
                if ma.is_masked(acid[i]):
                    SID = '        '
                else:
                    SID = acid[i]
            else:
                SID = rpid[i]
            if SID == 'A       ' or SID == '        ' or SID[0:3] == 'ARP' or SID[0:3] == 'ARS':
                SID = 'AIRCFT  '
        else:
            logger.debug(f'      WARNING: {subset[i]} should not be in this code')
            SID = '        '

        stationIdentification[i] = SID

    return stationIdentification


def Convert_DPOF_to_POAF(poaf, dpof):
    # Convert the values of DPOF into POAF
    for i in range(len(poaf)):
        if not ma.is_masked(poaf[i]):
            if not ma.is_masked(dpof[i]) and dpof[i] >= 7 and dpof[i] <= 10:
                poaf[i] = 5
            elif not ma.is_masked(dpof[i]) and dpof[i] >= 11 and dpof[i] <= 14:
                poaf[i] = 6


def ES_T(T):
    # Teten's formula. Calculates vapor pressure for a Temperature
    vaporPressure = 6.1078 * math.exp((17.269 * (T - 273.16))/((T - 273.16)+237.3))
    return vaporPressure


def QFRMTP(T, P):
    es_t = ES_T(T)
    # Derives Q from temperature and pressure
    Q = (0.622 * es_t)/(P - (0.378 * es_t))
    return Q


def AS(Q, P):
    # Needed for TFRMQP
    AS = math.log((Q * P) / (6.1078 * ((0.378 * Q) + 0.622)))
    return AS


def TFRMQP(Q, P):
    # Calculates Temperature as a function of Q and P
    term1 = AS(Q, P)
    tfrmqp = ((237.3 * term1) / (17.269 - term1)) + 273.16
    return tfrmqp


def HGTF_HI(P):
    # Calculate Z from P < 22630 Pa
    height = 11000 - math.log(p / 226.3) / 0.001576106
    return height


def HGTF_LO(P):
    # Calculate Z from P > 22630 Pa
    height = (1. - (p / 1013.25) ** (1. / 5.256)) * (288.15 / 0.0065)
    return height


def PR_Z(Z):
    # Estimate pressure in mb using indicated altitude via US std atmosphere where Z < 11000 m
    pr_z = 1013.25 * (((288.15 - (.0065 * Z))/288.15)**5.256)
    return pr_z


def PRS_Z(Z):
    # Estimate pressure in mb using indicated altitude via US std atmosphere where Z > 11000 m
    prs_z = pressure = 226.3 * math.exp(1.576106E-4 * (11000. - Z))
    return prs_z


def Derive_ObsValues(prlc, tmdb, mixr, rehu, mstq, aircraftFlightLevel, dateTime, subset):
    pob = ma.array([prlc.fill_value] * len(prlc)).astype(np.float32)
    tob = ma.array([tmdb.fill_value] * len(tmdb)).astype(np.float32)
    qob = ma.array([mixr.fill_value] * len(mixr)).astype(np.float32)
    for i in range(len(prlc)):
        ITMP = 0
        if not ma.is_masked(prlc[i]):
            pob[i] = round(prlc[i] * 0.1)
        if not ma.is_masked(tmdb[i]):
            ITMP = tmdb[i] * 100.0
            tob[i] = np.float32(tmdb[i])
            if (mstq[i] == 0 or subset[i] == 'NC004006' or subset[i] == 'NC004008' or subset[i] == 'NC004010' or
                    subset[i] == 'NC004012' or subset[i] == 'NC004013' or subset[i] == 'NC004103'):
                if pob[i] >= prlc.fill_value:
                    if aircraftFlightLevel[i] <= 11000.0:
                        p = PR_Z(aircraftFlightLevel[i])
                    else:
                        p = PRS_Z(aircraftFlightLevel[i])
                else:
                    p = pob[i]*0.1
                QQ = mixr.fill_value
                if (subset[i] == 'NC004004'):
                    # 20061001000000 -> 1159675200
                    # 20061031235959 -> 1162357199
                    # 20071002000000 -> 1191297600
                    # 20071002235959 -> 1191383999
                    if ((dateTime[i] >= 1159675200 and dateTime[i] <= 1162357199) or
                            (dateTime[i] >= 1191297600 and dateTime[i] <= 1191383999)):
                        # During these dates, mixr was scaled incorrectly
                        mixr[i] = mixr.fill_value
                if (mixr[i] < mixr.fill_value):
                    if (subset[i] == 'NC004004'):
                        # 20061101000000 -> 1162357200
                        # 20071001235959 -> 1191297599
                        if (dateTime[i] >= 1162357200 and dateTime[i] <= 1191297599):
                            # During these dates, mixr was scaled incorrectly
                            mixr[i] *= 0.1
                    QQ = mixr[i]/(1.0 + mixr[i])
                elif (rehu[i] < rehu.fill_value):
                    QQSAT = QFRMTP(tmdb[i], p)
                    QQ = (rehu[i] * 0.01) * QQSAT
                if (QQ > 0.0):
                    TD = TFRMQP(QQ, p)
                    if (round(TD * 10) <= round(tmdb[i] * 10)):
                        qob[i] = QQ

    return pob, tob, qob


def QMRKH_to_QM(qmat, qmwn, qmdd, tob, wspd, wdir, qob, qmrkh2, qmrkh3, qmrkh4, pccf, subset):

    for i in range(len(qmat)):
        TQM1 = np.int32(0)
        if (not ma.is_masked(qmrkh2[i])) and (qmrkh2[i] >= 3):
            TQM1 = np.int32(13)
        else:
            if (not ma.is_masked(qmrkh2[i])) and (qmrkh2[i] >= 1):
                TQM1 = np.int32(3)
            if (not ma.is_masked(qmrkh2[i])) and (qmrkh2[i] == 0):
                TQM1 = np.int32(2)
        if (not ma.is_masked(tob[i]) and (qmat[i] == 2)):
            qmat[i] = TQM1

        WDIRQM1 = np.int32(0)
        if (qmrkh3[i] >= 3):
            WDIRQM1 = np.int32(13)
        else:
            if (not ma.is_masked(qmrkh3[i])) and (qmrkh3[i] >= 1):
                WDIRQM1 = np.int32(3)
            if (not ma.is_masked(qmrkh3[i])) and (qmrkh3[i] == 0):
                WDIRQM1 = np.int32(2)
        if ((not ma.is_masked(wspd[i])) and (not ma.is_masked(wdir[i])) and qmwn[i] == 2):
            WQM1 = WDIRQM1

        WQM2 = np.int32(0)
        if (qmrkh4[i] >= 3):
            WQM2 = np.int32(13)
        else:
            if (not ma.is_masked(qmrkh4[i])) and (qmrkh4[i] >= 1):
                WQM2 = np.int32(3)
            if (not ma.is_masked(qmrkh4[i])) and (qmrkh4[i] == 0):
                WQM2 = np.int32(2)
        if ((not ma.is_masked(wspd[i])) and (not ma.is_masked(wdir[i])) and qmwn[i] == 2):
            qmwn[i] = max(WQM1, WQM2)

        QQM1 = np.int32(0)
        if (not ma.is_masked(qob[i])) and (qmdd[i] == 2):
            if pccf[i] < 80.0 or pccf[i] > 100.0:
                qmdd[i] = np.int32(13)
            else:
                qmdd[i] = np.int32(2)

    for i in range(len(qmwn)):
        if qmwn[i] == 14:
            qmat[i] == 14


def Derive_SequenceNumber(stationIdentification1):
    seqNum = np.array([], dtype=int)
    num = 0
    for i in range(len(stationIdentification1)):
        if i == 0:
            num += 1
            seqNum = np.append(seqNum, num)
        elif (stationIdentification1[i-1] != stationIdentification1[i]):
            num += 1
            seqNum = np.append(seqNum, [num])
        else:
            seqNum = np.append(seqNum, [num])
    return seqNum


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
    r001 = bufr.QuerySet(["NC004001"])  # individual for subset
    r002 = bufr.QuerySet(["NC004002"])
    r003 = bufr.QuerySet(["NC004003"])
    r005 = bufr.QuerySet(["NC004005"])
    r006 = bufr.QuerySet(["NC004006"])
    r009 = bufr.QuerySet(["NC004009"])
    r010 = bufr.QuerySet(["NC004010"])
    r011 = bufr.QuerySet(["NC004011"])
    r015 = bufr.QuerySet(["NC004015"])
    s = bufr.QuerySet(subsets_amdar)  # AIRCFT, amdar only

    logger.debug('Making QuerySet for AIRCAR ...')
    # MetaData
    q.add("year", "*/YEAR")
    q.add("month", "*/MNTH")
    q.add("day", "*/DAYS")
    q.add("hour", "*/HOUR")
    q.add("minute", "*/MINU")
    q.add("second", "*/SECO")
    q.add("latitude", "*/CLAT")
    q.add("longitude", "*/CLON")
    q.add("aircraftIdentifier", "*/ACRN")
    q.add("aircraftFlightPhase", "*/POAF")
    q.add("moistureQuality", "*/MSTQ")
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
    q.add("windQM", "*/QMWN")

    logger.debug('Making QuerySet for AIRCAR (no amdar)...')
    # MetaData
    r.add("year", "*/YEAR")
    r001.add("year", "*/YEAR")
    r002.add("year", "*/YEAR")
    r003.add("year", "*/YEAR")
    r005.add("year", "*/YEAR")
    r006.add("year", "*/YEAR")
    r009.add("year", "*/YEAR")
    r010.add("year", "*/YEAR")
    r011.add("year", "*/YEAR")
    r015.add("year", "*/YEAR")
    r.add("month", "*/MNTH")
    r.add("day", "*/DAYS")
    r.add("hour", "*/HOUR")
    r.add("minute", "*/MINU")
    r.add("latitude", "[*/CLAT, */CLATH]")
    r.add("longitude", "[*/CLON, */CLONH]")
    r.add("aircraftFlightNumber", "*/ACID")
    r.add("aircraftFlightPhase", "*/POAF")
    r.add("detailedPhaseOfFlight", "*/DPOF")
    r.add("reportIdentifier", "*/RPID")
    r.add("aircraftIdentifier", "*/ACRN]")
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
    r.add("windQM", "*/QMWN")

    logger.debug('Making QuerySet for AIRCFT (amdar) ...')
    s.add("year", "*/YEAR")
    s.add("month", "*/MNTH")
    s.add("day", "*/DAYS")
    s.add("hour", "*/HOUR")
    s.add("minute", "*/MINU")
    s.add("latitude", "*/CLATH")
    s.add("longitude", "*/CLONH")
    s.add("latitudeSeq", "*/ADRBLSEQ/CLATH")

    s.add("aircraftFlightNumber", "*/ACID")
    s.add("aircraftNavigationalSystem", "*/ACNS")
    s.add("aircraftIdentifier", "*/ACRN")
    s.add("detailedPhaseOfFlight", "*/DPOF")
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
        f.rewind()
        try:
            u001 = f.execute(r001)
        except RuntimeError:
            u001_try = False
        else:
            u001_try = True
        f.rewind()
        try:
            u002 = f.execute(r002)
        except RuntimeError:
            u002_try = False
        else:
            u002_try = True
        f.rewind()
        try:
            u003 = f.execute(r003)
        except RuntimeError:
            u003_try = False
        else:
            u003_try = True
        f.rewind()
        try:
            u005 = f.execute(r005)
        except RuntimeError:
            u005_try = False
        else:
            u005_try = True
        f.rewind()
        try:
            u006 = f.execute(r006)
        except RuntimeError:
            u006_try = False
        else:
            u006_try = True
        f.rewind()
        try:
            u009 = f.execute(r009)
        except RuntimeError:
            u009_try = False
        else:
            u009_try = True
        f.rewind()
        try:
            u010 = f.execute(r010)
        except RuntimeError:
            u010_try = False
        else:
            u010_try = True
        f.rewind()
        try:
            u011 = f.execute(r011)
        except RuntimeError:
            u011_try = False
        else:
            u011_try = True
        f.rewind()
        try:
            u015 = f.execute(r015)
        except RuntimeError:
            u015_try = False
        else:
            u015_try = True
        f.rewind()

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
    mstq_aircar = t.get('moistureQuality')
    prlc_aircar = t.get('pressure', type='float')
    ialt_aircar = t.get('aircraftIndicatedAltitude', type='float')

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
    rpid_aircft = u.get('reportIdentifier')
    acrn_aircft = u.get('aircraftIdentifier')
    poaf_aircft = u.get('aircraftFlightPhase')
    dpof_aircft = u.get('detailedPhaseOfFlight')
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
    qmdd_aircft = u.get('humidityQM')
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
    dpof_amdar = v.get('detailedPhaseOfFlight', 'latitudeSeq')
    flvlst_amdar = v.get('flightLevelST', 'latitudeSeq', type='float')

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
    logger.debug(f"     rpid_aircft      shape, type = {rpid_aircft.shape}, {rpid_aircft.dtype}")
    logger.debug(f"     acrn_aircft      shape, type = {acrn_aircft.shape}, {acrn_aircft.dtype}")
    logger.debug(f"     poaf_aircft      shape, type = {poaf_aircft.shape}, {poaf_aircft.dtype}")
    logger.debug(f"     dpof_aircft      shape, type = {dpof_aircft.shape}, {dpof_aircft.dtype}")
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
    logger.debug(f"     dpof_amdar       shape, type = {dpof_amdar.shape}, {dpof_amdar.dtype}")
    logger.debug(f"     flvlst_amdar     shape, type = {flvlst_amdar.shape}, {flvlst_amdar.dtype}")
    logger.debug(f"     tmdb_amdar       shape, type = {tmdb_amdar.shape}, {tmdb_amdar.dtype}")
    logger.debug(f"     tmdp_amdar       shape, type = {tmdp_amdar.shape}, {tmdp_amdar.dtype}")
    logger.debug(f"     mixr_amdar       shape, type = {mixr_amdar.shape}, {mixr_amdar.dtype}")
    logger.debug(f"     wdir_amdar       shape, type = {wdir_amdar.shape}, {wdir_amdar.dtype}")
    logger.debug(f"     wspd_amdar       shape, type = {wspd_amdar.shape}, {wspd_amdar.dtype}")
    logger.debug(f"     qmat_amdar       shape, type = {qmat_amdar.shape}, {qmat_amdar.dtype}")
    logger.debug(f"     qmdd_amdar       shape, type = {qmdd_amdar.shape}, {qmdd_amdar.dtype}")
    logger.debug(f"     qmwn_amdar       shape, type = {qmwn_amdar.shape}, {qmwn_amdar.dtype}")

    logger.debug("  Retrieve *_aircar and *_amdar lengths")
    len_aircar = len(year_aircar)
    len_amdar = len(year_amdar)

    logger.debug("  Retrieve *_aircft lengths")
    if u001_try:
        len001 = len(u001.get('year'))
        print(len001)
    else:
        len001 = 0
    if u002_try:
        len002 = len(u002.get('year'))
        print(len002)
    else:
        len001 = 0
    if u003_try:
        len003 = len(u003.get('year'))
        print(len003)
    else:
        len005 = 0
    if u005_try:
        len005 = len(u005.get('year'))
        print(len005)
    else:
        len005 = 0
    if u006_try:
        len006 = len(u006.get('year'))
        print(len006)
    else:
        len006 = 0
    if u009_try:
        len009 = len(u009.get('year'))
        print(len009)
    else:
        len009 = 0
    if u010_try:
        len010 = len(u010.get('year'))
        print(len010)
    else:
        len010 = 0
    if u011_try:
        len011 = len(u011.get('year'))
        print(len011)
    else:
        len011 = 0
    if u015_try:
        len015 = len(u015.get('year'))
        print(len015)
    else:
        len015 = 0

    len_aircft = len001 + len002 + len003 + len005 + len006 + len009 + len010 + len011 + len015
    len_all = len_aircar + len_aircft + len_amdar
    logger.debug(f"   lengths of aircar, aircft amdar, total: {len_aircar}, {len_aircft}, {len_amdar}, {len_all}")

    logger.debug("Generate subset variable")
    subset_aircar = ['NC004004'] * len(year_aircar)
    subset_aircft = (['NC004001'] * len001 + ['NC004002'] * len002 + ['NC004003'] * len003 +
                     ['NC004005'] * len005 + ['NC004006'] * len006 + ['NC004009'] * len009 +
                     ['NC004010'] * len010 + ['NC004011'] * len011 + ['NC004015'] * len015)
    subset_amdar = ['NC004103'] * len(year_amdar)

    subset = ma.array(subset_aircar + subset_aircft + subset_amdar)
    logger.debug(f"       subset shape = {subset.shape}")
    print("subset len is ", len(subset))

    if len_all != len(subset):
        print(f" PROBLEM. len_aircft != len(subset), {len_aircft} != {len(subset)}")

    # Concatenate
    logger.debug("Concatenate the variables ... ")
    lat = ma.concatenate((lat_aircar, lat_aircft, lat_amdar), axis=0).astype(np.float32)
    lat = ma.masked_values(lat, lat_aircar.fill_value)
    lon = ma.concatenate((lon_aircar, lon_aircft, lon_amdar), axis=0).astype(np.float32)
    lon = ma.masked_values(lon, lon_aircar.fill_value)
    acid = ma.concatenate((['        '] * len_aircar, ['        '] * len_aircft, acid_amdar), axis=0)
    acid = ma.masked_values(acid, acid_amdar.fill_value)
    rpid = ma.concatenate((['        '] * len_aircar, rpid_aircft, ['        '] * len_amdar), axis=0)
    rpid = ma.masked_values(rpid, rpid_aircft.fill_value)
    acrn = ma.concatenate((acrn_aircar, acrn_aircft, acrn_amdar), axis=0)
    acrn = ma.masked_values(acrn, acrn_aircar.fill_value)
    poaf = ma.concatenate((poaf_aircar, poaf_aircft, [poaf_aircar.fill_value] * len_amdar), axis=0).astype(np.int32)
    poaf = ma.masked_values(poaf, poaf_aircar.fill_value)
    dpof = ma.concatenate(([dpof_aircft.fill_value] * len_amdar, dpof_aircft, dpof_amdar), axis=0).astype(np.int32)
    dpof = ma.masked_values(dpof, dpof_aircft.fill_value)
    pccf = ma.concatenate(([pccf_aircft.fill_value] * len_aircar, pccf_aircft, [pccf_aircft.fill_value] * len_amdar), axis=0).astype(np.int32)
    pccf = ma.masked_values(pccf, pccf_aircft.fill_value)
    mstq = ma.concatenate((mstq_aircar, [mstq_aircar.fill_value] * len_aircft, [mstq_aircar.fill_value] * len_amdar), axis=0).astype(np.int32)
    mstq = ma.masked_values(mstq, mstq_aircar.fill_value)
    prlc = ma.concatenate((prlc_aircar, [prlc_aircar.fill_value] * len_aircft, [prlc_aircar.fill_value] * len_amdar), axis=0).astype(np.float32)
    prlc = ma.masked_values(prlc, prlc_aircar.fill_value)
    tmdb = ma.concatenate((tmdb_aircar, tmdb_aircft, tmdb_amdar), axis=0).astype(np.float32)
    tmdb = ma.masked_values(tmdb, tmdb_aircar.fill_value)
    tmdp = ma.concatenate(([tmdp_amdar.fill_value] * len_aircar, [tmdp_amdar.fill_value] * len_aircft, tmdp_amdar), axis=0).astype(np.float32)
    tmdp = ma.masked_values(tmdp, tmdp_amdar.fill_value)
    rehu = ma.concatenate((rehu_aircar, rehu_aircft, [rehu_aircft.fill_value] * len_amdar), axis=0).astype(np.float32)
    rehu = ma.masked_values(rehu, rehu_aircft.fill_value)
    mixr = ma.concatenate((mixr_aircar, mixr_aircft, mixr_amdar), axis=0).astype(np.float32)
    mixr = ma.masked_values(mixr, mixr_aircar.fill_value)
    wdir = ma.concatenate((wdir_aircar, wdir_aircft, wdir_amdar), axis=0).astype(np.float32)
    wdir = ma.masked_values(wdir, wdir_aircft.fill_value)
    wspd = ma.concatenate((wspd_aircar, wspd_aircft, wspd_amdar), axis=0).astype(np.float32)
    wspd = ma.masked_values(wspd, wspd_aircft.fill_value)
    qmat = ma.concatenate((qmat_aircar, qmat_aircft, qmat_amdar), axis=0).astype(np.int32)
    qmat = ma.masked_values(qmat, qmat_aircft.fill_value)
    qmdd = ma.concatenate((qmdd_aircar, qmdd_aircft, qmdd_amdar), axis=0).astype(np.int32)
    qmdd = ma.masked_values(qmdd, qmdd_aircft.fill_value)
    qmwn = ma.concatenate((qmwn_aircar, qmwn_aircft, qmwn_amdar), axis=0).astype(np.int32)
    qmwn = ma.masked_values(qmwn, qmwn_aircft.fill_value)
    qmrkh2 = ma.concatenate(([qmrkh2_aircft.fill_value] * len_aircar, qmrkh2_aircft, [qmrkh2_aircft.fill_value] * len_amdar), axis=0).astype(np.int32)
    qmrkh2 = ma.masked_values(qmrkh2, qmrkh2_aircft.fill_value)
    qmrkh3 = ma.concatenate(([qmrkh3_aircft.fill_value] * len_aircar, qmrkh3_aircft, [qmrkh3_aircft.fill_value] * len_amdar), axis=0).astype(np.int32)
    qmrkh3 = ma.masked_values(qmrkh3, qmrkh3_aircft.fill_value)
    qmrkh4 = ma.concatenate(([qmrkh4_aircft.fill_value] * len_aircar, qmrkh4_aircft, [qmrkh4_aircft.fill_value] * len_amdar), axis=0).astype(np.int32)
    qmrkh4 = ma.masked_values(qmrkh4, qmrkh4_aircft.fill_value)

    logger.debug(f" ... Check the concatenated array shapes, dtypes, some fill_values  ... ")
    logger.debug(f"     concatenated lat size = {lat.shape}, {lat.dtype}, {lat.fill_value}")
    logger.debug(f"     concatenated lon size = {lon.shape}, {lon.dtype}, {lon.fill_value}")
    logger.debug(f"     concatenated acid size = {acid.shape}, {acid.dtype}, {acid.fill_value}")
    logger.debug(f"     concatenated acrn size = {acrn.shape}, {acrn.dtype}, {acrn.fill_value}")
    logger.debug(f"     concatenated poaf size = {poaf.shape}, {poaf.dtype}, {poaf.fill_value}")
    logger.debug(f"     concatenated dpof size = {dpof.shape}, {dpof.dtype}, {dpof.fill_value}")
    logger.debug(f"     concatenated pccf size = {pccf.shape}, {pccf.dtype}, {pccf.fill_value}")
    logger.debug(f"     concatenated tmdb size = {tmdb.shape}, {tmdb.dtype}, {tmdb.fill_value}")
    logger.debug(f"     concatenated tmdp size = {tmdp.shape}, {tmdp.dtype}, {tmdp.fill_value}")
    logger.debug(f"     concatenated rehu size = {rehu.shape}, {rehu.dtype}, {rehu.fill_value}")
    logger.debug(f"     concatenated mixr size = {mixr.shape}, {mixr.dtype}, {mixr.fill_value}")
    logger.debug(f"     concatenated wdir size = {wdir.shape}, {wdir.dtype}, {wdir.fill_value}")
    logger.debug(f"     concatenated wspd size = {wspd.shape}, {wspd.dtype}, {wspd.fill_value}")
    logger.debug(f"     concatenated qmat size = {qmat.shape}, {qmat.dtype}, {qmat.fill_value}")
    logger.debug(f"     concatenated qmdd size = {qmdd.shape}, {qmdd.dtype}, {qmdd.fill_value}")
    logger.debug(f"     concatenated qmwn size = {qmwn.shape}, {qmwn.dtype}, {qmwn.fill_value}")
    logger.debug(f"     concatenated qmrkh2 size = {qmrkh2.shape}, {qmrkh2.dtype}, {qmrkh2.fill_value}")
    logger.debug(f"     concatenated qmrkh3 size = {qmrkh3.shape}, {qmrkh3.dtype}, {qmrkh3.fill_value}")
    logger.debug(f"     concatenated qmrkh4 size = {qmrkh4.shape}, {qmrkh4.dtype}, {qmrkh4.fill_value}")

    # Derive time/date   #check to see if this isactually dateTime
    logger.debug(f"     Derive the dateTime variable")
    dateTime_aircar = t.get_datetime('year', 'month', 'day', 'hour', 'minute').astype(np.int64)
    dateTime_aircft = u.get_datetime('year', 'month', 'day', 'hour', 'minute').astype(np.int64)
    dateTime_amdar = v.get_datetime('year', 'month', 'day', 'hour', 'minute', group_by='latitudeSeq').astype(np.int64)

    logger.debug(f"     dateTime_aircar = {dateTime_aircar.shape}, {dateTime_aircar.dtype}")
    logger.debug(f"     dateTime_aircft = {dateTime_aircft.shape}, {dateTime_aircft.dtype}")
    logger.debug(f"     dateTime_amdar = {dateTime_amdar.shape}, {dateTime_amdar.dtype}")

    dateTime = ma.concatenate((dateTime_aircar, dateTime_aircft, dateTime_amdar), axis=0).astype(np.int64)
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

    # Derive stationIdentification
    logger.debug('      Derive stationIdentification')
    stationIdentification = ma.array(determine_stationID(rpid, acrn, acid, subset, len_all))

    # Convert DPOF to POAF values
    logger.debug('      Convert DPOF to POAF')
    Convert_DPOF_to_POAF(poaf, dpof)

    # Derive ObsValues
    logger.debug('      Derive ObsValues (P, T, Q)')
    pob, tob, qob = Derive_ObsValues(prlc, tmdb, mixr, rehu, mstq, aircraftFlightLevel, dateTime, subset)

    pob = ma.masked_values(pob, prlc.fill_value)
    tob = ma.masked_values(tob, tmdb.fill_value)
    qob = ma.masked_values(qob, mixr.fill_value)

    # Convert QMRKH values (NC004010) in aircft to QMAT / QMDD / QMWN
    logger.debug("      Convert QMRKH to QMAT/QMDD/QMWN")
    QMRKH_to_QM(qmat, qmwn, qmdd, tob, wspd, wdir, qob, qmrkh2, qmrkh3, qmrkh4, pccf, subset)

    # Sort the data by stationIdentification (so we can get sequence number (seqNum) and dateTime)
    logger.debug("      Sort the data by stationIdentification and dateTime")
    tuple_merged = list(zip(stationIdentification, dateTime, lat, lon, pob, tob, qob, wspd, wdir, qmat,
                            qmwn, qmdd, subset, aircraftFlightLevel, poaf))
    tuple_sorted = sorted(tuple_merged, key=itemgetter(0, 1))

    # Pull the tuples apart
    logger.debug("      Pull the tuples apart into their associated variables")
    stationIdentification1 = ma.array([t[0] for t in tuple_sorted])
    dateTime1 = ma.array([t[1] for t in tuple_sorted]).astype(np.int64)
    dateTime1 = ma.masked_values(dateTime1, dateTime.fill_value)
    lat1 = ma.array([t[2] for t in tuple_sorted]).astype(np.float32)
    lat1 = ma.masked_values(lat1, lat.fill_value)
    lon1 = ma.array([t[3] for t in tuple_sorted]).astype(np.float32)
    lon1 = ma.masked_values(lon1, lon.fill_value)
    pob1 = ma.array([t[4] for t in tuple_sorted]).astype(np.float32)
    pob1 = ma.masked_values(pob1, pob.fill_value)
    tob1 = ma.array([t[5] for t in tuple_sorted]).astype(np.float32)
    tob1 = ma.masked_values(tob1, tob.fill_value)
    qob1 = ma.array([t[6] for t in tuple_sorted]).astype(np.float32)
    qob1 = ma.masked_values(qob1, qob.fill_value)
    wspd1 = ma.array([t[7] for t in tuple_sorted]).astype(np.float32)
    wspd1 = ma.masked_values(wspd1, wspd.fill_value)
    wdir1 = ma.array([t[8] for t in tuple_sorted]).astype(np.float32)
    wdir1 = ma.masked_values(wdir1, wdir.fill_value)
    qmat1 = ma.array([t[9] for t in tuple_sorted]).astype(np.int32)
    qmat1 = ma.masked_values(qmat1, qmat.fill_value)
    qmwn1 = ma.array([t[10] for t in tuple_sorted]).astype(np.int32)
    qmwn1 = ma.masked_values(qmwn1, qmwn.fill_value)
    qmdd1 = ma.array([t[11] for t in tuple_sorted]).astype(np.int32)
    qmdd1 = ma.masked_values(qmdd1, qmdd.fill_value)
    subset1 = ma.array([t[12] for t in tuple_sorted])
    aircraftFlightLevel1 = ma.array([t[13] for t in tuple_sorted]).astype(np.float32)
    aircraftFlightLevel1 = ma.masked_values(aircraftFlightLevel1, aircraftFlightLevel.fill_value)
    poaf1 = ma.array([t[14] for t in tuple_sorted]).astype(np.int32)
    poaf1 = ma.masked_values(poaf1, poaf.fill_value)

    # Derive Sequence Number
    logger.debug('      Derive Sequence Number (seqNum)')
    seqNum = Derive_SequenceNumber(stationIdentification1)

    logger.debug(f"     seqNum shape, size, max = {seqNum.shape}, {seqNum.dtype}, {seqNum.max()}")

    # =====================================
    # Create IODA ObsSpace
    # Write IODA output
    # =====================================

    # Create the dimensions
    dims = {'Location': np.arange(0, lat1.shape[0])}

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
    # stationIdentification
    obsspace.create_var('MetaData/stationIdentification', dtype=stationIdentification.dtype) \
        .write_attr('long_name', 'Station Identification') \
        .write_data(stationIdentification1)

    # Latitude
    obsspace.create_var('MetaData/latitude', dtype=lat.dtype,
                        fillval=lat.fill_value) \
        .write_attr('units', 'degrees_north') \
        .write_attr('valid_range', np.array([-90, 90], dtype=np.float32)) \
        .write_attr('long_name', 'Latitude') \
        .write_data(lat1)

    # Longitude
    obsspace.create_var('MetaData/longitude', dtype=lon.dtype, fillval=lon.fill_value) \
        .write_attr('units', 'degrees_east') \
        .write_attr('valid_range', np.array([-180, 180], dtype=np.float32)) \
        .write_attr('long_name', 'Longitude') \
        .write_data(lon1)

    # Datetime
    obsspace.create_var('MetaData/dateTime', dtype=dateTime.dtype,
                        fillval=dateTime.fill_value) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'Datetime') \
        .write_data(dateTime1)

    # sequenceNumber
    obsspace.create_var('MetaData/sequenceNumber', dtype=seqNum.dtype,
                        fillval=qmat.fill_value) \
        .write_attr('long_name', 'Sequence Number') \
        .write_data(seqNum)

    # subset
    obsspace.create_var('MetaData/subset', dtype=subset.dtype) \
        .write_attr('long_name', 'Subset') \
        .write_data(subset1)

    # aircraftFlightPhase
    obsspace.create_var('MetaData/aircraftFlightPhase', dtype=poaf.dtype,
                        fillval=poaf.fill_value) \
        .write_attr('long_name', 'Aircraft Flight Phase') \
        .write_data(poaf1)

    # AircraftFlightLevel
    obsspace.create_var('MetaData/aircraftFlightLevel', dtype=aircraftFlightLevel.dtype, fillval=aircraftFlightLevel.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'aircraftFlightLevel') \
        .write_data(aircraftFlightLevel1)

    # Pressure
    obsspace.create_var('MetaData/pressure', dtype=pob.dtype, fillval=pob.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'pressure') \
        .write_data(pob1)

    # QualityMarker
    # airTemperature
    obsspace.create_var('QualityMarker/airTemperature', dtype=qmat.dtype, fillval=qmat.fill_value) \
        .write_attr('long_name', 'Air Temperature Quality Marker') \
        .write_data(qmat1)

    # specificHumidity
    obsspace.create_var('QualityMarker/specificHumidity', dtype=qmdd.dtype, fillval=qmdd.fill_value) \
        .write_attr('long_name', 'Specific Humidity Quality Marker') \
        .write_data(qmdd1)

    # windSpeed
    obsspace.create_var('QualityMarker/windSpeed', dtype=qmwn.dtype, fillval=qmwn.fill_value) \
        .write_attr('long_name', 'Wind Speed Quality Marker') \
        .write_data(qmwn1)

    # windDirection
    obsspace.create_var('QualityMarker/windDirection', dtype=qmwn.dtype, fillval=qmwn.fill_value) \
        .write_attr('long_name', 'Wind Direction Quality Marker') \
        .write_data(qmwn1)

    # ObsValue
    # airTemperature
    obsspace.create_var('ObsValue/airTemperature', dtype=tob.dtype, fillval=tob.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Air Temperature') \
        .write_data(tob1)

    # specificHumidity
    obsspace.create_var('ObsValue/specificHumidity', dtype=qob.dtype, fillval=qob.fill_value) \
        .write_attr('units', 'kg kg-1') \
        .write_attr('long_name', 'Specific Humidity') \
        .write_data(qob1)

    # windSpeed
    obsspace.create_var('ObsValue/windSpeed', dtype=wspd.dtype, fillval=wspd.fill_value) \
        .write_attr('units', 'm s-1') \
        .write_attr('long_name', 'Wind Speed') \
        .write_data(wspd1)

    # windDirection
    obsspace.create_var('ObsValue/windDirection', dtype=wdir.dtype, fillval=wdir.fill_value) \
        .write_attr('units', 'degree') \
        .write_attr('long_name', 'Wind Direction') \
        .write_data(wdir1)

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
