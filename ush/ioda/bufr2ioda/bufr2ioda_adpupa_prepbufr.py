#!/usr/bin/env python3
# (C) Copyright 2024 NOAA/NWS/NCEP/EMC
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

import sys
import argparse
import numpy as np
import numpy.ma as ma
import calendar
import json
import time
import copy
import math
import datetime
import os
from datetime import datetime
from pyioda import ioda_obs_space as ioda_ospace
from wxflow import Logger
from pyiodaconv import bufr
from collections import namedtuple
import warnings
# suppress warnings
warnings.filterwarnings('ignore')

# ====================================================================
#            gdas prepbufr file
# ====================================================================
# MNEMONIC | NUMBER | DESCRIPTION
# ---------|--------|-------------------------------------------------
# ADPUPA   | A48102 | UPPER-AIR (RAOB, PIBAL, RECCO, DROPS) REPORTS
# ====================================================================


def Compute_dateTime(cycleTimeSinceEpoch, hrdr):

    int64_fill_value = np.int64(0)
    dateTime = np.zeros(hrdr.shape, dtype=np.int64)
    for i in range(len(dateTime)):
        if ma.is_masked(hrdr[i]):
            continue
        else:
            dateTime[i] = np.int64(hrdr[i]*3600) + cycleTimeSinceEpoch

    dateTime = ma.array(dateTime)
    dateTime = ma.masked_values(dateTime, int64_fill_value)

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

    # Get parameters from configuration
    data_format = config["data_format"]
    data_type = config["data_type"]
    data_description = config["data_description"]
    data_provider = config["data_provider"]
    cycle_type = config["cycle_type"]
    dump_dir = config["dump_directory"]
    ioda_dir = config["ioda_directory"]
    cycle = config["cycle_datetime"]

    # Get derived parameters
    yyyymmdd = cycle[0:8]
    hh = cycle[8:10]
    reference_time = datetime.strptime(cycle, "%Y%m%d%H")
    reference_time = reference_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    # General informaton
    converter = 'prepBUFR to IODA Converter'
    platform_description = 'ADPUPA prepbufr'

    logger.info(f"reference_time = {reference_time}")

    bufrfile = f"{cycle_type}.t{hh}z.{data_format}"
    DATA_PATH = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}", str(hh), 'atmos', bufrfile)
    if not os.path.isfile(DATA_PATH):
        logger.info(f"DATA_PATH {DATA_PATH} does not exist")
        return
    logger.debug(f"The DATA_PATH is: {DATA_PATH}")

    # ============================================
    # Make the QuerySet for all the data we want
    # ============================================
    start_time = time.time()

    logger.info('Making QuerySet')
    q = bufr.QuerySet(subsets)

    # ObsType
    q.add('observationType', '*/TYP')

    # MetaData
    q.add('prepbufrDataLevelCategory', '*/PRSLEVEL/CAT')
    q.add('latitude', '*/PRSLEVEL/DRFTINFO/YDR')
    q.add('longitude', '*/PRSLEVEL/DRFTINFO/XDR')
    q.add('stationIdentification', '*/SID')
    q.add('stationElevation', '*/ELV')
    q.add('timeOffset', '*/PRSLEVEL/DRFTINFO/HRDR')
    q.add('releaseTime', '*/PRSLEVEL/DRFTINFO/HRDR')
    q.add('temperatureEventProgramCode', '*/PRSLEVEL/T___INFO/T__EVENT{1}/TPC')
    q.add('pressure', '*/PRSLEVEL/P___INFO/P__EVENT{1}/POB')
    q.add('height', '*/PRSLEVEL/Z___INFO/Z__EVENT{1}/ZOB')

    # ObsValue
    q.add('stationPressure', '*/PRSLEVEL/P___INFO/P__EVENT{1}/POB')
    q.add('airTemperature', '*/PRSLEVEL/T___INFO/T__EVENT{1}/TOB')
    q.add('virtualTemperature', '*/PRSLEVEL/T___INFO/TVO')
    q.add('specificHumidity', '*/PRSLEVEL/Q___INFO/Q__EVENT{1}/QOB')
    q.add('windEastward', '*/PRSLEVEL/W___INFO/W__EVENT{1}/UOB')
    q.add('windNorthward', '*/PRSLEVEL/W___INFO/W__EVENT{1}/VOB')

    # QualityMark
    q.add('pressureQM', '*/PRSLEVEL/P___INFO/P__EVENT{1}/PQM')
    q.add('airTemperatureQM', '*/PRSLEVEL/T___INFO/T__EVENT{1}/TQM')
    q.add('virtualTemperatureQM', '*/PRSLEVEL/T___INFO/T__EVENT{1}/TQM')
    q.add('specificHumidityQM', '*/PRSLEVEL/Q___INFO/Q__EVENT{1}/QQM')
    q.add('windEastwardQM', '*/PRSLEVEL/W___INFO/W__EVENT{1}/WQM')
    q.add('windNorthwardQM', '*/PRSLEVEL/W___INFO/W__EVENT{1}/WQM')

    # ObsError
    q.add('pressureOE', '*/PRSLEVEL/P___INFO/P__BACKG/POE')
    q.add('airTemperatureOE', '*/PRSLEVEL/T___INFO/T__BACKG/TOE')
    q.add('specificHumidityOE', '*/PRSLEVEL/Q___INFO/Q__BACKG/QOE')
    q.add('windEastwardOE', '*/PRSLEVEL/W___INFO/W__BACKG/WOE')
    q.add('windNorthwardOE', '*/PRSLEVEL/W___INFO/W__BACKG/WOE')

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f'Running time for making QuerySet : {running_time} seconds')

    # ==============================================================
    # Open the BUFR file and execute the QuerySet to get ResultSet
    # Use the ResultSet returned to get numpy arrays of the data
    # ==============================================================
    start_time = time.time()

    logger.info('Executing QuerySet to get ResultSet')
    with bufr.File(DATA_PATH) as f:
        try:
            r = f.execute(q)
        except Exception as err:
            logger.info(f'Return with {err}')
            return

    # ObsType
    logger.debug(" ... Executing QuerySet for ADPUPA: get ObsType ...")
    obstyp = r.get('observationType', 'prepbufrDataLevelCategory', type='int32')
    logger.info('Executing QuerySet: get metadata')

    # MetaData
    cat = r.get('prepbufrDataLevelCategory', 'prepbufrDataLevelCategory')
    lat = r.get('latitude', 'prepbufrDataLevelCategory')
    lon = r.get('longitude', 'prepbufrDataLevelCategory')
    lon[lon > 180] -= 360  # Convert Longitude from [0,360] to [-180,180]
    sid = r.get('stationIdentification', 'prepbufrDataLevelCategory')
    elv = r.get('stationElevation', 'prepbufrDataLevelCategory', type='float')
    tpc = r.get('temperatureEventProgramCode', 'prepbufrDataLevelCategory')
    pob = r.get('pressure', 'prepbufrDataLevelCategory')
    pob *= 100
    zob = r.get('height', 'prepbufrDataLevelCategory', type='float')

    # Time variable
    hrdr = r.get('timeOffset', 'prepbufrDataLevelCategory', type='float')
    ulan = r.get('releaseTime')
    ulan = np.int64(ulan*3600)

    cycleTimeSinceEpoch = np.int64(calendar.timegm(time.strptime(reference_time, '%Y-%m-%dT%H:%M:%SZ')))
    ulan += cycleTimeSinceEpoch
    ulan = np.repeat(ulan[:, 0], ulan.shape[1])
    ulan = ulan.reshape(ulan.shape)

    # ObsValue
    ps = np.full(pob.shape[0], pob.fill_value)  # Extract stationPressure from pressure, which belongs to CAT=1
    ps = np.where(cat == 0, pob, ps)
    tob = r.get('airTemperature', 'prepbufrDataLevelCategory')
    tob += 273.15
    tsen = np.full(tob.shape[0], tob.fill_value)  # Extract sensible temperature from tob, which belongs to TPC=1
    tsen = np.where(((tpc >= 1) & (tpc < 8)), tob, tsen)
    tvo = np.full(tob.shape[0], tob.fill_value) 	# Extract virtual temperature from tob, which belongs to TPC <= 8 and TPC>1
    tvo = np.where((tpc == 8), tob, tvo)
    qob = r.get('specificHumidity', 'prepbufrDataLevelCategory', type='float')
    qob *= 1.0e-6
    uob = r.get('windEastward', 'prepbufrDataLevelCategory')
    vob = r.get('windNorthward', 'prepbufrDataLevelCategory')

    # QualityMark
    pobqm = r.get('pressureQM', 'prepbufrDataLevelCategory')
    psqm = np.full(pobqm.shape[0], pobqm.fill_value) 	# Extract stationPressureQM from pressureQM
    psqm = np.where(cat == 0, pobqm, psqm)
    tobqm = r.get('airTemperatureQM', 'prepbufrDataLevelCategory')
    tsenqm = np.full(tobqm.shape[0], tobqm.fill_value)  # Extract airTemperature from tobqm, which belongs to TPC=1
    tsenqm = np.where(((tpc >= 1) & (tpc < 8)), tobqm, tsenqm)
    tvoqm = np.full(tobqm.shape[0], tobqm.fill_value)  # Extract virtual temperature from tob, which belongs to TPC <= 8 and TPC>1
    tvoqm = np.where((tpc == 8), tobqm, tvoqm)
    qobqm = r.get('specificHumidityQM', 'prepbufrDataLevelCategory')
    uobqm = r.get('windEastwardQM', 'prepbufrDataLevelCategory')
    vobqm = r.get('windNorthwardQM', 'prepbufrDataLevelCategory')

    # ObsError
    poboe = r.get('pressureOE', 'prepbufrDataLevelCategory', type='float32')
    poboe *= 100
    psoe = ma.array(np.full(poboe.shape[0], poboe.fill_value))
    psoe = ma.where(cat == 0, poboe, psoe)
    psoe = ma.masked_values(psoe, 0)
    toboe = r.get('airTemperatureOE', 'prepbufrDataLevelCategory', type='float32')
    toboe = ma.masked_values(toboe, 0)
    tsenoe = copy.deepcopy(toboe)
    tsenoef = ma.array(np.full(toboe.shape[0], toboe.fill_value))
    tsenoe = ma.where(((tpc >= 1) & (tpc < 8)), toboe, tsenoef)
    tsenoe = ma.masked_values(tsenoe, 0)
    tvooe = copy.deepcopy(toboe)
    tvooef = ma.array(np.full(toboe.shape[0], toboe.fill_value))
    tvooe = ma.where(((tpc == 8)), toboe, tvooef)
    tvooe = ma.masked_values(tvooe, 0)
    qoboe = r.get('specificHumidityOE', 'prepbufrDataLevelCategory')
    qoboe *= 10
    uoboe = r.get('windEastwardOE', 'prepbufrDataLevelCategory')
    voboe = r.get('windNorthwardOE', 'prepbufrDataLevelCategory')

    logger.info('Executing QuerySet Done!')

    logger.debug('Executing QuerySet: Check BUFR variable generic dimension and type')
    # Check prepBUFR variable generic dimension and type
    logger.debug(f'     cat       shape = {cat.shape}')
    logger.debug(f'     lat       shape = {lat.shape}')
    logger.debug(f'     lon       shape = {lon.shape}')
    logger.debug(f'     sid       shape = {sid.shape}')
    logger.debug(f'     elv       shape = {elv.shape}')
    logger.debug(f'     tpc       shape = {tpc.shape}')
    logger.debug(f'     pob       shape = {pob.shape}')
    logger.debug(f'     hrdr      shape = {hrdr.shape}')
    logger.debug(f'     ulan      shape = {ulan.shape}')
    logger.debug(f'     zob       shape = {zob.shape}')

    logger.debug(f'     ps    	  shape = {ps.shape}')
    logger.debug(f'     tob       shape = {tob.shape}')
    logger.debug(f'     tsen      shape = {tsen.shape}')
    logger.debug(f'     tvo       shape = {tvo.shape}')
    logger.debug(f'     qob       shape = {qob.shape}')
    logger.debug(f'     uob       shape = {uob.shape}')
    logger.debug(f'     vob       shape = {vob.shape}')

    logger.debug(f'     pobqm     shape = {pobqm.shape}')
    logger.debug(f'     psqm      shape = {psqm.shape}')
    logger.debug(f'     tobqm     shape = {tobqm.shape}')
    logger.debug(f'     tsenqm    shape = {tsenqm.shape}')
    logger.debug(f'     tvoqm     shape = {tvoqm.shape}')
    logger.debug(f'     qobqm     shape = {qobqm.shape}')
    logger.debug(f'     uobqm     shape = {uobqm.shape}')
    logger.debug(f'     vobqm     shape = {vobqm.shape}')

    logger.debug(f"     poboe     shape = {poboe.shape}")
    logger.debug(f"     psoe      shape = {psoe.shape}")
    logger.debug(f"     toboe     shape = {toboe.shape}")
    logger.debug(f"     tsenoe    shape = {tsenoe.shape}")
    logger.debug(f"     tvooe     shape = {tvooe.shape}")
    logger.debug(f"     qoboe     shape = {qoboe.shape}")
    logger.debug(f"     uoboe     shape = {uoboe.shape}")
    logger.debug(f"     voboe     shape = {voboe.shape}")

    logger.debug(f'     cat       type  = {cat.dtype}')
    logger.debug(f'     lat       type  = {lat.dtype}')
    logger.debug(f'     lon       type  = {lon.dtype}')
    logger.debug(f'     sid       type  = {sid.dtype}')
    logger.debug(f'     elv       type  = {elv.dtype}')
    logger.debug(f'     tpc       type  = {tpc.dtype}')
    logger.debug(f'     pob       type  = {pob.dtype}')
    logger.debug(f'     hrdr      type  = {hrdr.dtype}')
    logger.debug(f'     ulan      type  = {ulan.dtype}')
    logger.debug(f'     zob       type = {zob.dtype}')

    logger.debug(f'     ps        type = {ps.dtype}')
    logger.debug(f'     tob       type = {tob.dtype}')
    logger.debug(f'     tsen      type = {tsen.dtype}')
    logger.debug(f'     tvo       type = {tvo.dtype}')
    logger.debug(f'     qob       type = {qob.dtype}')
    logger.debug(f'     uob       type = {uob.dtype}')
    logger.debug(f'     vob       type = {vob.dtype}')

    logger.debug(f'     pobqm     type = {pobqm.dtype}')
    logger.debug(f'     psqm      type = {psqm.dtype}')
    logger.debug(f'     tobqm     type = {tobqm.dtype}')
    logger.debug(f'     tsenqm    type = {tsenqm.dtype}')
    logger.debug(f'     tvoqm     type = {tvoqm.dtype}')
    logger.debug(f'     qobqm     type = {qobqm.dtype}')
    logger.debug(f'     uobqm     type = {uobqm.dtype}')
    logger.debug(f'     vobqm     type = {vobqm.dtype}')

    logger.debug(f"     poboe     type  = {poboe.dtype}")
    logger.debug(f"     psoe      type  = {psoe.dtype}")
    logger.debug(f"     toboe     type  = {toboe.dtype}")
    logger.debug(f"     tsenoe    type  = {tsenoe.dtype}")
    logger.debug(f"     tvooe     type  = {tvooe.dtype}")
    logger.debug(f"     qoboe     type  = {qoboe.dtype}")
    logger.debug(f"     uoboe     type  = {uoboe.dtype}")
    logger.debug(f"     voboe     type  = {voboe.dtype}")

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Running time for executing QuerySet to get ResultSet : {running_time} seconds")

    # =========================
    # Create derived variables
    # =========================
    start_time = time.time()

    logger.info('Creating derived variables - dateTime from hrdr')

    cycleTimeSinceEpoch = np.int64(calendar.timegm(time.strptime(reference_time, '%Y-%m-%dT%H:%M:%SZ')))
    dateTime = Compute_dateTime(cycleTimeSinceEpoch, hrdr)

    logger.debug('     Check derived variables type ... ')
    logger.debug(f'    dateTime      type = {dateTime.dtype}')

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Running time for creating derived variables : {running_time} seconds")

    # Mask Certain Variables
    logger.debug(f"Mask typ for certain variables where data is available...")
    typ_ps = Mask_typ_for_var(obstyp, ps)
    typ_tsen = Mask_typ_for_var(obstyp, tsen)
    typ_tvo = Mask_typ_for_var(obstyp, tvo)
    typ_qob = Mask_typ_for_var(obstyp, qob)
    typ_uob = Mask_typ_for_var(obstyp, uob)
    typ_vob = Mask_typ_for_var(obstyp, vob)

    logger.debug(f"     Check drived variables (typ*) shape & type ... ")
    logger.debug(f"     typ_ps shape, type = {typ_ps.shape}, {typ_ps.dtype}")
    logger.debug(f"     typ_tsen shape, type = {typ_tsen.shape}, {typ_tsen.dtype}")
    logger.debug(f"     typ_tvo shape, type = {typ_tvo.shape}, {typ_tvo.dtype}")
    logger.debug(f"     typ_qob shape, type = {typ_qob.shape}, {typ_qob.dtype}")
    logger.debug(f"     typ_uob shape, type = {typ_uob.shape}, {typ_uob.dtype}")
    logger.debug(f"     typ_vob shape, type = {typ_vob.shape}, {typ_vob.dtype}")

    # Create the dimensions
    dims = {'Location': np.arange(0, lat.shape[0])}

    # Create IODA ObsSpace
    iodafile = f"{cycle_type}.t{hh}z.{data_type}.tm00.nc"
    OUTPUT_PATH = os.path.join(ioda_dir, iodafile)
    logger.info(f"Create output file: {OUTPUT_PATH}")
    obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)

    # Create Global attributes
    logger.debug(' ... ... Create global attributes')
    obsspace.write_attr('sourceFiles', bufrfile)
    obsspace.write_attr('description', data_description)

    # Create IODA variables
    logger.debug(' ... ... Create variables: name, type, units, and attributes')
    # Prepbufr Data Level Category
    obsspace.create_var('MetaData/prepbufrDataLevelCategory', dtype=cat.dtype, fillval=cat.fill_value) \
        .write_attr('units', '1') \
        .write_attr('long_name', 'Prepbufr Data Level Category') \
        .write_data(cat)

    # Observation Type: airTemperature
    obsspace.create_var('ObsType/airTemperature', dtype=obstyp.dtype, fillval=obstyp.fill_value) \
        .write_attr('long_name', 'Observation Type') \
        .write_data(typ_tsen)

    # Observation Type: virtualTemperature
    obsspace.create_var('ObsType/virtualTemperature', dtype=obstyp.dtype, fillval=obstyp.fill_value) \
        .write_attr('long_name', 'Observation Type') \
        .write_data(typ_tvo)

    # Observation Type: stationPressure
    obsspace.create_var('ObsType/stationPressure', dtype=obstyp.dtype, fillval=obstyp.fill_value) \
        .write_attr('long_name', 'Observation Type') \
        .write_data(typ_ps)

    # Observation Type: specificHumidity
    obsspace.create_var('ObsType/specificHumidity', dtype=obstyp.dtype, fillval=obstyp.fill_value) \
        .write_attr('long_name', 'Observation Type') \
        .write_data(typ_qob)

    # Observation Type: windEastward
    obsspace.create_var('ObsType/windEastward', dtype=obstyp.dtype, fillval=obstyp.fill_value) \
        .write_attr('long_name', 'Observation Type') \
        .write_data(typ_uob)

    # Observation Type: windNorthward
    obsspace.create_var('ObsType/windNorthward', dtype=obstyp.dtype, fillval=obstyp.fill_value) \
        .write_attr('long_name', 'Observation Type') \
        .write_data(typ_vob)

    # Latitude
    obsspace.create_var('MetaData/latitude', dtype=lat.dtype, fillval=lat.fill_value) \
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

    # Station Identification
    obsspace.create_var('MetaData/stationIdentification', dtype=sid.dtype, fillval=sid.fill_value) \
        .write_attr('long_name', 'Station Identification') \
        .write_data(sid)

    # Station Elevation
    obsspace.create_var('MetaData/stationElevation', dtype=elv.dtype, fillval=elv.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Station Elevation') \
        .write_data(elv)

    # Temperature Event Program Code
    obsspace.create_var('QCFlags/qualityFlags', dtype=tpc.dtype, fillval=tpc.fill_value) \
        .write_attr('long_name', 'Temperature Event Program Code') \
        .write_data(tpc)

    # Pressure
    obsspace.create_var('MetaData/pressure', dtype=pob.dtype, fillval=pob.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Pressure') \
        .write_data(pob)

    # Height of Observation
    obsspace.create_var('MetaData/height', dtype=zob.dtype, fillval=zob.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Height of Observation') \
        .write_data(zob)

    # Datetime
    obsspace.create_var('MetaData/dateTime', dtype=dateTime.dtype, fillval=dateTime.fill_value) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'Datetime') \
        .write_data(dateTime)

    # releaseTime
    obsspace.create_var('MetaData/releaseTime', dtype=dateTime.dtype, fillval=dateTime.fill_value) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'Release Time') \
        .write_data(ulan)

    # Station Pressure
    obsspace.create_var('ObsValue/stationPressure', dtype=pob.dtype, fillval=pob.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Station Pressure') \
        .write_data(ps)

    # Sensible Temperature
    obsspace.create_var('ObsValue/airTemperature', dtype=tob.dtype, fillval=tob.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Sensible Temperature') \
        .write_data(tsen)

    # Virtual Temperature
    obsspace.create_var('ObsValue/virtualTemperature', dtype=tob.dtype, fillval=tob.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Virtual Temperature') \
        .write_data(tvo)

    # Specific Humidity
    obsspace.create_var('ObsValue/specificHumidity', dtype=qob.dtype, fillval=qob.fill_value) \
        .write_attr('units', 'kg kg-1') \
        .write_attr('long_name', 'Specific Humidity') \
        .write_data(qob)

    # Eastward Wind
    obsspace.create_var('ObsValue/windEastward', dtype=uob.dtype, fillval=uob.fill_value) \
        .write_attr('units', 'm s-1') \
        .write_attr('long_name', 'Eastward Wind') \
        .write_data(uob)

    # Northward Wind
    obsspace.create_var('ObsValue/windNorthward', dtype=vob.dtype, fillval=vob.fill_value) \
        .write_attr('units', 'm s-1') \
        .write_attr('long_name', 'Northward Wind') \
        .write_data(vob)

    # Pressure Quality Marker
    obsspace.create_var('QualityMarker/pressure', dtype=pobqm.dtype, fillval=pobqm.fill_value) \
        .write_attr('long_name', 'Pressure Quality Marker') \
        .write_data(pobqm)

    # Station Pressure Quality Marker
    obsspace.create_var('QualityMarker/stationPressure', dtype=pobqm.dtype, fillval=pobqm.fill_value) \
        .write_attr('long_name', 'Station Pressure Quality Marker') \
        .write_data(psqm)

    # Air Temperature Quality Marker
    obsspace.create_var('QualityMarker/airTemperature', dtype=tobqm.dtype, fillval=tobqm.fill_value) \
        .write_attr('long_name', 'Temperature Quality Marker') \
        .write_data(tobqm)

    # Virtual Temperature Quality Marker
    obsspace.create_var('QualityMarker/virtualTemperature', dtype=tobqm.dtype, fillval=tobqm.fill_value) \
        .write_attr('long_name', 'Virtual Temperature Quality Marker') \
        .write_data(tvoqm)

    # Specific Humidity Quality Marker
    obsspace.create_var('QualityMarker/specificHumidity', dtype=qobqm.dtype, fillval=qobqm.fill_value) \
        .write_attr('long_name', 'Specific Humidity Quality Marker') \
        .write_data(qobqm)

    # Eastward Wind Quality Marker
    obsspace.create_var('QualityMarker/windEastward', dtype=uobqm.dtype, fillval=uobqm.fill_value) \
        .write_attr('long_name', 'Eastward Wind Quality Marker') \
        .write_data(uobqm)

    # Northward Wind Quality Marker
    obsspace.create_var('QualityMarker/windNorthward', dtype=vobqm.dtype, fillval=vobqm.fill_value) \
        .write_attr('long_name', 'Northward Wind Quality Marker') \
        .write_data(vobqm)

    # Pressure Observation Error
    obsspace.create_var('ObsError/pressure', dtype=poboe.dtype, fillval=poboe.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Pressure Observation Error') \
        .write_data(poboe)

    # Station Pressure Observation Error
    obsspace.create_var('ObsError/stationPressure', dtype=psoe.dtype, fillval=psoe.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Station Pressure Observation Error') \
        .write_data(psoe)

    # Air Temperature Observation Error
    obsspace.create_var('ObsError/airTemperature', dtype=toboe.dtype, fillval=toboe.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Air Temperature Observation Error') \
        .write_data(toboe)

    # Sensible Temperature Observation Error
    obsspace.create_var('ObsError/sensibleTemperature', dtype=tsenoe.dtype, fillval=tsenoe.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Sensible Temperature Observation Error') \
        .write_data(tsenoe)

    # Virtual Temperature Observation Error
    obsspace.create_var('ObsError/virtualTemperature', dtype=tvooe.dtype, fillval=tvooe.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Virtual Temperature Observation Error') \
        .write_data(tvooe)

    # Specific Humidity Observation Error
    obsspace.create_var('ObsError/specificHumidity', dtype=qoboe.dtype, fillval=qoboe.fill_value) \
        .write_attr('long_name', 'Specific Humidity Observation Error') \
        .write_data(qoboe)

    # Eastward Wind Observation Error
    obsspace.create_var('ObsError/windEastward', dtype=uoboe.dtype, fillval=uoboe.fill_value) \
        .write_attr('units', 'm s-1') \
        .write_attr('long_name', 'Eastward Wind Observation Error') \
        .write_data(uoboe)

    # Northward Wind Observation Error
    obsspace.create_var('ObsError/windNorthward', dtype=voboe.dtype, fillval=voboe.fill_value) \
        .write_attr('units', 'm s-1') \
        .write_attr('long_name', 'Northward Wind Observation Error') \
        .write_data(voboe)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Running time for splitting and output IODA: {running_time} seconds")

    logger.info("All Done!")


if __name__ == '__main__':

    start_time = time.time()

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input JSON configuration', required=True)
    parser.add_argument('-v', '--verbose', help='print debug logging information',
                        action='store_true')
    args = parser.parse_args()

    log_level = 'DEBUG' if args.verbose else 'INFO'
    logger = Logger('BUFR2IODA_adpupa_prepbufr.py', level=log_level, colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Total running time: {running_time} seconds")
