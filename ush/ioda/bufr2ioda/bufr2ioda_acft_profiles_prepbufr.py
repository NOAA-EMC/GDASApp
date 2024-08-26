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


def Compute_dateTime(cycleTimeSinceEpoch, dhr):

    int64_fill_value = np.int64(0)

    dateTime = np.zeros(dhr.shape, dtype=np.int64)
    for i in range(len(dateTime)):
        if ma.is_masked(dhr[i]):
            continue
        else:
            dateTime[i] = np.int64(dhr[i]*3600) + cycleTimeSinceEpoch

    dateTime = ma.array(dateTime)
    dateTime = ma.masked_values(dateTime, int64_fill_value)

    return dateTime


def Compute_typ_other(typ, var):

    typ_var = copy.deepcopy(typ)
    typ_var[(typ_var > 300) & (typ_var < 400)] -= 200
    typ_var[(typ_var > 400) & (typ_var < 500)] -= 300
    typ_var[(typ_var > 500) & (typ_var < 600)] -= 400

    for i in range(len(typ_var)):
        if ma.is_masked(var[i]):
            typ_var[i] = typ_var.fill_value

    return typ_var


def Compute_typ_uv(typ, var):

    typ_var = copy.deepcopy(typ)
    typ_var[(typ_var > 300) & (typ_var < 400)] -= 100
    typ_var[(typ_var > 400) & (typ_var < 500)] -= 200
    typ_var[(typ_var > 500) & (typ_var < 600)] -= 300

    for i in range(len(typ_var)):
        if ma.is_masked(var[i]):
            typ_var[i] = typ_var.fill_value

    return typ_var


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

    # Get derived parameters
    yyyymmdd = cycle[0:8]
    hh = cycle[8:10]

    reference_time = datetime.strptime(cycle, "%Y%m%d%H")
    reference_time = reference_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    reference_time_full = f"{yyyymmdd}{hh}00"
    logger.debug(f"Reference time = {reference_time}")

    # General informaton
    converter = 'BUFR to IODA Converter'
    platform_description = 'acft_profiles data from prepBUFR format'

    bufrfile = f"{cycle_type}.t{hh}z.{data_format}.acft_profiles"
    DATA_PATH = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}", str(hh),
                             'atmos', bufrfile)
    if not os.path.isfile(DATA_PATH):
        logger.info(f"DATA_PATH {DATA_PATH} does not exist")
        return
    logger.debug(f"The DATA_PATH is: {DATA_PATH}")

    # ============================================
    # Make the QuerySet for all the data we want
    # ============================================
    start_time = time.time()

    logger.debug(f"Making QuerySet ...")
    q = bufr.QuerySet(subsets)

    # ObsType
    q.add('observationType', '*/TYP')

    # MetaData
    q.add('prepbufrDataLevelCategory', '*/PRSLEVLA/CAT')
    q.add('stationIdentification', '*/SID')
    q.add('latitude', '*/PRSLEVLA/DRFTINFO/YDR')
    q.add('longitude', '*/PRSLEVLA/DRFTINFO/XDR')
    q.add('obsTimeMinusCycleTime', '*/PRSLEVLA/DRFTINFO/HRDR')
    q.add('aircraftFlightLevel', '*/PRSLEVLA/Z___INFO/Z__EVENT{1}/ZOB')
    q.add('pressure', '*/PRSLEVLA/P___INFO/P__EVENT{1}/POB')
    q.add('temperatureEventCode', '*/PRSLEVLA/T___INFO/T__EVENT{1}/TPC')
    q.add('instantaneousAltitudeRate', '*/PRSLEVLA/IALR')
    q.add('aircraftFlightPhase', '*/PRSLEVLA/ACFT_SEQ/POAF')

    # QualityMarker
    q.add('qualityMarkerStationElevation', '*/PRSLEVLA/Z___INFO/Z__EVENT{1}/ZQM')
    q.add('qualityMarkerStationPressure', '*/PRSLEVLA/P___INFO/P__EVENT{1}/PQM')
    q.add('qualityMarkerAirTemperature', '*/PRSLEVLA/T___INFO/T__EVENT{1}/TQM')
    q.add('qualityMarkerSpecificHumidity', '*/PRSLEVLA/Q___INFO/Q__EVENT{1}/QQM')
    q.add('qualityMarkerWindNorthward', '*/PRSLEVLA/W___INFO/W__EVENT{1}/WQM')

    # ObsError
    q.add('obsErrorStationPressure', '*/PRSLEVLA/P___INFO/P__BACKG/POE')
    q.add('obsErrorAirTemperature', '*/PRSLEVLA/T___INFO/T__BACKG/TOE')
    q.add('obsErrorSpecificHumidity', '*/PRSLEVLA/Q___INFO/Q__BACKG/QOE')
    q.add('obsErrorWindNorthward', '*/PRSLEVLA/W___INFO/W__BACKG/WOE')

    # ObsValue
    q.add('stationElevation', '*/ELV')
    q.add('stationPressure', '*/PRSLEVLA/P___INFO/P__EVENT{1}/POB')
    q.add('airTemperature', '*/PRSLEVLA/T___INFO/T__EVENT{1}/TOB')
    q.add('virtualTemperature', '*/PRSLEVLA/T___INFO/TVO')
    q.add('specificHumidity', '*/PRSLEVLA/Q___INFO/Q__EVENT{1}/QOB')
    q.add('windNorthward', '*/PRSLEVLA/W___INFO/W__EVENT{1}/VOB')
    q.add('windEastward', '*/PRSLEVLA/W___INFO/W__EVENT{1}/UOB')

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
        try:
            r = f.execute(q)
        except Exception as err:
            logger.info(f'Return with {err}')
            return

    logger.debug(f" ... Executing QuerySet: get MetaData: basic ...")

    # ObsType
    logger.debug(f" ... Executing QuerySet: get ObsType ...")
    typ = r.get('observationType', 'prepbufrDataLevelCategory')

    # MetaData
    logger.debug(f" ... Executing QuerySet: get MetaData ...")
    cat = r.get('prepbufrDataLevelCategory', 'prepbufrDataLevelCategory')
    sid = r.get('stationIdentification', 'prepbufrDataLevelCategory')
    lat = r.get('latitude', 'prepbufrDataLevelCategory')
    lon = r.get('longitude', 'prepbufrDataLevelCategory')
    lon[lon > 180] -= 360
    zob = r.get('aircraftFlightLevel', 'prepbufrDataLevelCategory')
    pressure = r.get('pressure', 'prepbufrDataLevelCategory')
    pressure *= 100
    tpc = r.get('temperatureEventCode', 'prepbufrDataLevelCategory')
    ialr = r.get('instantaneousAltitudeRate', 'prepbufrDataLevelCategory')
    poaf = r.get('aircraftFlightPhase', 'prepbufrDataLevelCategory')

    # QualityMarker
    logger.debug(f" ... Executing QuerySet: get QualityMarker ...")
    zobqm = r.get('qualityMarkerStationElevation', 'prepbufrDataLevelCategory')
    pobqm = r.get('qualityMarkerStationPressure', 'prepbufrDataLevelCategory')
    tobqm = r.get('qualityMarkerAirTemperature', 'prepbufrDataLevelCategory')
    qobqm = r.get('qualityMarkerSpecificHumidity', 'prepbufrDataLevelCategory')
    wobqm = r.get('qualityMarkerWindNorthward', 'prepbufrDataLevelCategory')

    # ObsError
    logger.debug(f" ... Executing QuerySet: get ObsError ...")
    poboe = r.get('obsErrorStationPressure', 'prepbufrDataLevelCategory')
    toboe = r.get('obsErrorAirTemperature', 'prepbufrDataLevelCategory')
    qoboe = r.get('obsErrorSpecificHumidity', 'prepbufrDataLevelCategory')
    qoboe *= 10
    woboe = r.get('obsErrorWindNorthward', 'prepbufrDataLevelCategory')

    # ObsValue
    logger.debug(f" ... Executing QuerySet: get ObsValue ...")
    elv = r.get('stationElevation', 'prepbufrDataLevelCategory', type='float')
    pob = r.get('stationPressure', 'prepbufrDataLevelCategory')
    pob *= 100
    tob = r.get('airTemperature', 'prepbufrDataLevelCategory')
    tob += 273.15
    tvo = r.get('virtualTemperature', 'prepbufrDataLevelCategory')
    tvo += 273.15
    qob = r.get('specificHumidity', 'prepbufrDataLevelCategory', type='float')
    qob *= 0.000001
    uob = r.get('windEastward', 'prepbufrDataLevelCategory')
    vob = r.get('windNorthward', 'prepbufrDataLevelCategory')

    logger.debug(f" ... Executing QuerySet: get datatime: observation time ...")
    # DateTime: seconds since Epoch time
    # IODA has no support for numpy datetime arrays dtype=datetime64[s]
    dhr = r.get('obsTimeMinusCycleTime', 'prepbufrDataLevelCategory',
                type='float')

    logger.debug(f" ... Executing QuerySet: Done!")

    logger.debug(f" ... Executing QuerySet: Check BUFR variable generic \
                dimension and type ...")
    # Check BUFR variable generic dimension and type
    logger.debug(f"     typ       shape = {typ.shape}")
    logger.debug(f"     cat       shape = {cat.shape}")
    logger.debug(f"     sid       shape = {sid.shape}")
    logger.debug(f"     dhr       shape = {dhr.shape}")
    logger.debug(f"     lat       shape = {lat.shape}")
    logger.debug(f"     lon       shape = {lon.shape}")
    logger.debug(f"     zob       shape = {zob.shape}")
    logger.debug(f"     pressure  shape = {pressure.shape}")
    logger.debug(f"     tpc       shape = {tpc.shape}")
    logger.debug(f"     ialr      shape = {ialr.shape}")
    logger.debug(f"     poaf      shape = {poaf.shape}")

    logger.debug(f"     zobqm     shape = {zobqm.shape}")
    logger.debug(f"     pobqm     shape = {pobqm.shape}")
    logger.debug(f"     tobqm     shape = {tobqm.shape}")
    logger.debug(f"     qobqm     shape = {qobqm.shape}")
    logger.debug(f"     wobqm     shape = {wobqm.shape}")

    logger.debug(f"     elv       shape = {elv.shape}")
    logger.debug(f"     pob       shape = {pob.shape}")
    logger.debug(f"     tob       shape = {pob.shape}")
    logger.debug(f"     tvo       shape = {tvo.shape}")
    logger.debug(f"     qob       shape = {qob.shape}")
    logger.debug(f"     uob       shape = {uob.shape}")
    logger.debug(f"     vob       shape = {vob.shape}")

    logger.debug(f"     typ       type  = {typ.dtype}")
    logger.debug(f"     cat       type  = {cat.dtype}")
    logger.debug(f"     sid       type  = {sid.dtype}")
    logger.debug(f"     dhr       type  = {dhr.dtype}")
    logger.debug(f"     lat       type  = {lat.dtype}")
    logger.debug(f"     lon       type  = {lon.dtype}")
    logger.debug(f"     zob       type  = {zob.dtype}")
    logger.debug(f"     pressure  type  = {pressure.dtype}")
    logger.debug(f"     tpc       type  = {tpc.dtype}")
    logger.debug(f"     ialr      type  = {ialr.dtype}")
    logger.debug(f"     poaf      type  = {poaf.dtype}")

    logger.debug(f"     pobqm     type  = {pobqm.dtype}")
    logger.debug(f"     tobqm     type  = {tobqm.dtype}")
    logger.debug(f"     qobqm     type  = {qobqm.dtype}")
    logger.debug(f"     wobqm     type  = {wobqm.dtype}")

    logger.debug(f"     poboe     type  = {poboe.dtype}")
    logger.debug(f"     toboe     type  = {toboe.dtype}")
    logger.debug(f"     qoboe     type  = {qoboe.dtype}")
    logger.debug(f"     woboe     type  = {woboe.dtype}")

    logger.debug(f"     elv       type  = {elv.dtype}")
    logger.debug(f"     pob       type  = {pob.dtype}")
    logger.debug(f"     tob       type  = {tob.dtype}")
    logger.debug(f"     tvo       type  = {tvo.dtype}")
    logger.debug(f"     qob       type  = {qob.dtype}")
    logger.debug(f"     uob       type  = {uob.dtype}")
    logger.debug(f"     vob       type  = {vob.dtype}")

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Running time for executing QuerySet to get ResultSet: \
                {running_time} seconds")

    # =========================
    # Create derived variables
    # =========================
    start_time = time.time()

    logger.debug(f"Creating derived variables - dateTime ...")

    cycleTimeSinceEpoch = np.int64(calendar.timegm(time.strptime(
                                   reference_time_full, '%Y%m%d%H%M')))
    dateTime = Compute_dateTime(cycleTimeSinceEpoch, dhr)
    dateTime_max = ma.MaskedArray.max(dateTime)
    dateTime_min = ma.MaskedArray.min(dateTime)

    logger.debug(f"     Check drived variables (dateTime) shape & type ... ")
    logger.debug(f"     dateTime shape = {dateTime.shape}")
    logger.debug(f"     dateTime type = {dateTime.dtype}")
    logger.debug(f"     dateTime max = {dateTime_max}")
    logger.debug(f"     dateTime min = {dateTime_min}")

    typ_zob = Compute_typ_other(typ, zob)
    typ_pob = Compute_typ_other(typ, pob)
    typ_tob = Compute_typ_other(typ, tob)
    typ_tvo = Compute_typ_other(typ, tvo)
    typ_qob = Compute_typ_other(typ, qob)
    typ_uv = Compute_typ_uv(typ, uob)

    logger.debug(f"     Check drived variables (typ*) shape & type ... ")
    logger.debug(f"     typ_zob shape = {typ_zob.shape}")
    logger.debug(f"     typ_zob type = {typ_zob.dtype}")
    logger.debug(f"     typ_pob shape = {typ_pob.shape}")
    logger.debug(f"     typ_pob type = {typ_pob.dtype}")
    logger.debug(f"     typ_tob shape = {typ_tob.shape}")
    logger.debug(f"     typ_tob type = {typ_tob.dtype}")
    logger.debug(f"     typ_tvo shape = {typ_tvo.shape}")
    logger.debug(f"     typ_tvo type = {typ_tvo.dtype}")
    logger.debug(f"     typ_qob shape = {typ_qob.shape}")
    logger.debug(f"     typ_qob type = {typ_qob.dtype}")
    logger.debug(f"     typ_uv shape = {typ_uv.shape}")
    logger.debug(f"     typ_uv type = {typ_uv.dtype}")

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

    iodafile = f"{cycle_type}.t{hh}z.aircraft.tm00.nc"
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
    obsspace.write_attr('datetimeReference', reference_time)
    obsspace.write_attr('datetimeRange', [str(dateTime_min),
                        str(dateTime_max)])
    obsspace.write_attr('platformLongDescription', platform_description)

    # Create IODA variables
    logger.debug(f" ... ... Create variables: name, type, units, & attributes")
    # ObsType: station Elevation
    obsspace.create_var('ObsType/stationElevation', dtype=typ_zob.dtype,
                        fillval=typ_zob.fill_value) \
        .write_attr('long_name', 'Station Elevation Observation Type') \
        .write_data(typ_zob)

    # ObsType: stationPressure
    obsspace.create_var('ObsType/stationPressure', dtype=typ_pob.dtype,
                        fillval=typ_pob.fill_value) \
        .write_attr('long_name', 'Station Pressure Observation Type') \
        .write_data(typ_pob)

    # ObsType: air Temperature
    obsspace.create_var('ObsType/airTemperature', dtype=typ_tob.dtype,
                        fillval=typ_tob.fill_value) \
        .write_attr('long_name', 'Air Temperature Observation Type') \
        .write_data(typ_tob)

    # ObsType: virtual Temperature
    obsspace.create_var('ObsType/virtualTemperature', dtype=typ_tvo.dtype,
                        fillval=typ_tvo.fill_value) \
        .write_attr('long_name', 'Virtual Temperature Observation Type') \
        .write_data(typ_tvo)

    # ObsType: Specific Humidity
    obsspace.create_var('ObsType/specificHumidity', dtype=typ_qob.dtype,
                        fillval=typ_qob.fill_value) \
        .write_attr('long_name', 'Specific Humidity Observation Type') \
        .write_data(typ_qob)

    # ObsType: wind Eastward
    obsspace.create_var('ObsType/windEastward', dtype=typ_uv.dtype,
                        fillval=typ_uv.fill_value) \
        .write_attr('long_name', 'Wind Eastward Observation Type') \
        .write_data(typ_uv)

    # ObsType: wind Northward
    obsspace.create_var('ObsType/windNorthward', dtype=typ_uv.dtype,
                        fillval=typ_uv.fill_value) \
        .write_attr('long_name', 'Wind Northward Observation Type') \
        .write_data(typ_uv)

    # PrepBUFR Data Level Category
    obsspace.create_var('MetaData/prepbufrDataLevelCategory', dtype=cat.dtype,
                        fillval=cat.fill_value) \
        .write_attr('units', '1') \
        .write_attr('long_name', 'prepBUFR Data Level Category') \
        .write_data(cat)

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
        .write_attr('units', '1') \
        .write_attr('long_name', 'Station Identification') \
        .write_data(sid)

    # AircraftFlightLevel (also known as HeightOfStation)
    obsspace.create_var('MetaData/aircraftFlightLevel', dtype=zob.dtype,
                        fillval=zob.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Aircraft Flight Level') \
        .write_data(zob)

    # Pressure
    obsspace.create_var('MetaData/pressure', dtype=pressure.dtype,
                        fillval=pressure.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Pressure') \
        .write_data(pressure)

    # Temperature Event Code
    obsspace.create_var('MetaData/temperatureEventCode', dtype=tpc.dtype,
                        fillval=tpc.fill_value) \
        .write_attr('long_name', 'Temperature Event Code') \
        .write_data(tpc)

    # Instantaneous Altitude Rate
    obsspace.create_var('MetaData/instantaneousAltitudeRate', dtype=ialr.dtype,
                        fillval=ialr.fill_value) \
        .write_attr('units', 'm s-1') \
        .write_attr('long_name', 'Instantaneous Altitude Rate') \
        .write_data(ialr)

    # Aircraft Flight Phase
    obsspace.create_var('MetaData/aircraftFlightPhase', dtype=poaf.dtype,
                        fillval=poaf.fill_value) \
        .write_attr('long_name', 'Aircraft Flight Phase') \
        .write_data(poaf)

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

    # Quality Marker: Specific Humidity
    obsspace.create_var('QualityMarker/specificHumidity', dtype=qobqm.dtype,
                        fillval=qobqm.fill_value) \
        .write_attr('long_name', 'Specific Humidity Quality Marker') \
        .write_data(qobqm)

    # Quality Marker: Northward Wind
    obsspace.create_var('QualityMarker/windNorthward', dtype=wobqm.dtype,
                        fillval=wobqm.fill_value) \
        .write_attr('long_name', 'Northward Wind Quality Marker') \
        .write_data(wobqm)

    # Quality Marker: Eastward Wind
    obsspace.create_var('QualityMarker/windEastward', dtype=wobqm.dtype,
                        fillval=wobqm.fill_value) \
        .write_attr('long_name', 'Eastward Wind Quality Marker') \
        .write_data(wobqm)

    # ObsError: Station Pressure
    obsspace.create_var('ObsError/stationPressure', dtype=poboe.dtype,
                        fillval=poboe.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Station Pressure ObsError') \
        .write_data(poboe)

    # ObsError: Air Temperature
    obsspace.create_var('ObsError/airTemperature', dtype=toboe.dtype,
                        fillval=toboe.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Air Temperature ObsError') \
        .write_data(toboe)

    # ObsError: Specific Humidity
    obsspace.create_var('ObsError/specificHumidity', dtype=qoboe.dtype,
                        fillval=qoboe.fill_value) \
        .write_attr('long_name', 'Specific Humidity ObsError') \
        .write_data(qoboe)

    # ObsError: Northward Wind
    obsspace.create_var('ObsError/windNorthward', dtype=woboe.dtype,
                        fillval=woboe.fill_value) \
        .write_attr('units', 'm s-1') \
        .write_attr('long_name', 'Northward Wind ObsError') \
        .write_data(woboe)

    # ObsError: Eastward Wind
    obsspace.create_var('ObsError/windEastward', dtype=woboe.dtype,
                        fillval=woboe.fill_value) \
        .write_attr('units', 'm s-1') \
        .write_attr('long_name', 'Eastward Wind ObsError') \
        .write_data(woboe)

    # Station Elevation
    obsspace.create_var('ObsValue/stationElevation', dtype=elv.dtype,
                        fillval=elv.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Station Elevation') \
        .write_data(elv)

    # Station Pressure
    obsspace.create_var('ObsValue/pressure', dtype=pob.dtype,
                        fillval=pob.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Station Pressure') \
        .write_data(pob)

    # Air Temperature
    obsspace.create_var('ObsValue/airTemperature', dtype=tob.dtype,
                        fillval=tob.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Air Temperature') \
        .write_data(tob)

    # Virtual Temperature
    obsspace.create_var('ObsValue/virtualTemperature', dtype=tvo.dtype,
                        fillval=tvo.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Virtual Temperature') \
        .write_data(tvo)

    # Specific Humidity
    obsspace.create_var('ObsValue/specificHumidity', dtype=qob.dtype,
                        fillval=qob.fill_value) \
        .write_attr('units', 'kg kg-1') \
        .write_attr('long_name', 'Specific Humidity') \
        .write_data(qob)

    # Eastward Wind
    obsspace.create_var('ObsValue/windEastward', dtype=uob.dtype,
                        fillval=uob.fill_value) \
        .write_attr('units', 'm s-1') \
        .write_attr('long_name', 'Eastward Wind') \
        .write_data(uob)

    # Northward Wind
    obsspace.create_var('ObsValue/windNorthward', dtype=vob.dtype,
                        fillval=vob.fill_value) \
        .write_attr('units', 'm s-1') \
        .write_attr('long_name', 'Northward Wind') \
        .write_data(vob)

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
    logger = Logger('bufr2ioda_acft_profiles_prepbufr.py', level=log_level,
                    colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Total running time: {running_time} seconds")
