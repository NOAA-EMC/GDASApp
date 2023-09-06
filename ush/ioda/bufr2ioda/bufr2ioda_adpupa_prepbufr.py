# (C) Copyright 2023 NOAA/NWS/NCEP/EMC
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
import math
import datetime
import os
from datetime import datetime
from pyioda import ioda_obs_space as ioda_ospace
from wxflow import Logger
from pyiodaconv import bufr
from collections import namedtuple

#|------------------------------------------------------------------------------|
#|            gdas prepbufr file                                                |                    
#|------------------------------------------------------------------------------|
#| MNEMONIC | NUMBER | DESCRIPTION                                              |
#|----------|--------|----------------------------------------------------------|
#|          |        |                                                          |
#| ADPUPA   | A48102 | UPPER-AIR (RAOB, PIBAL, RECCO, DROPS) REPORTS            |
#|------------------------------------------------------------------------------|

# Define and initialize  global variables
#global float32_fill_value
#global int32_fill_value
#global int64_fill_value

#float32_fill_value = np.float32(0)
#int32_fill_value = np.int32(0)
#int64_fill_value = np.int64(0)


def Compute_dateTime(cycleTimeSinceEpoch, hrdr):

    hrdr = np.int64(hrdr*3600)
    hrdr = hrdr+ cycleTimeSinceEpoch

    return hrdr


def bufr_to_ioda(config, logger):

    subsets = config["subsets"]
    logger.debug(f"Checking subsets = {subsets}")

    # Get parameters from configuration
    subsets 		= config["subsets"]
    data_format 	= config["data_format"]
    data_type 		= config["data_type"]
    data_description 	= config["data_description"]
    data_provider 	= config["data_provider"]
    cycle_type 		= config["cycle_type"]
    dump_dir 		= config["dump_directory"]
    ioda_dir 		= config["ioda_directory"]
    cycle 		= config["cycle_datetime"]

    # Get derived parameters
    yyyymmdd 		= cycle[0:8]
    hh 			= cycle[8:10]
    reference_time 	= datetime.strptime(cycle, "%Y%m%d%H")
    reference_time 	= reference_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    # General informaton
    converter 			= 'prepBUFR to IODA Converter'
    platform_description 	= 'ADPUPA prepbufr'

    logger.info(f"reference_time = {reference_time}")

    bufrfile 			= f"{cycle_type}.t{hh}z.{data_type}"
    DATA_PATH = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}", str(hh), 'atmos', bufrfile)
    #gdas.t18z.prepbufr  gdas.t18z.satwnd.tm00.bufr_d
    #bufrfile = f"{cycle_type}.t{hh}z.{data_type}.tm00.{data_format}"

    # ============================================
    # Make the QuerySet for all the data we want
    # ============================================
    start_time = time.time()

    logger.info('Making QuerySet')
    q = bufr.QuerySet(subsets)

    # MetaData
    q.add('prepbufrDataLevelCategory', 			'*/PRSLEVEL/CAT')
    q.add('latitude', 					'*/PRSLEVEL/DRFTINFO/YDR')
    q.add('longitude', 					'*/PRSLEVEL/DRFTINFO/XDR')
    q.add('stationIdentification', 			'*/SID')
    q.add('stationElevation', 				'*/ELV')
    q.add('timeOffset', 				'*/PRSLEVEL/DRFTINFO/HRDR')
    q.add('releaseTime', 				'*/PRSLEVEL/DRFTINFO/HRDR')
    q.add('temperatureEventProgramCode',		'*/PRSLEVEL/T___INFO/T__EVENT{1}/TPC')
    q.add('pressure', 					'*/PRSLEVEL/P___INFO/P__EVENT{1}/POB')

    # ObsValue
    q.add('stationPressure', 				'*/PRSLEVEL/P___INFO/P__EVENT{1}/POB')
    q.add('airTemperature', 				'*/PRSLEVEL/T___INFO/T__EVENT{1}/TOB')
    q.add('virtualTemperature', 			'*/PRSLEVEL/T___INFO/TVO')
    q.add('specificHumidity', 				'*/PRSLEVEL/Q___INFO/Q__EVENT{1}/QOB')
    q.add('windEastward', 				'*/PRSLEVEL/W___INFO/W__EVENT{1}/UOB')
    q.add('windNorthward', 				'*/PRSLEVEL/W___INFO/W__EVENT{1}/VOB')
    q.add('heightOfObservation', 			'*/PRSLEVEL/Z___INFO/Z__EVENT{1}/ZOB')

    # QualityMark
    q.add('pressureQM', 				'*/PRSLEVEL/P___INFO/P__EVENT{1}/PQM')
    q.add('airTemperatureQM', 				'*/PRSLEVEL/T___INFO/T__EVENT{1}/TQM')
    q.add('virtualTemperatureQM', 			'*/PRSLEVEL/T___INFO/T__EVENT{1}/TQM')
    q.add('specificHumidityQM', 			'*/PRSLEVEL/Q___INFO/Q__EVENT{1}/QQM')
    q.add('windEastwardQM', 				'*/PRSLEVEL/W___INFO/W__EVENT{1}/WQM')
    q.add('windNorthwardQM', 				'*/PRSLEVEL/W___INFO/W__EVENT{1}/WQM')

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
        r = f.execute(q)

    logger.info('Executing QuerySet: get metadata')
    # MetaData
    cat = r.get('prepbufrDataLevelCategory', 		'prepbufrDataLevelCategory')
    lat = r.get('latitude', 				'prepbufrDataLevelCategory')
    lon = r.get('longitude', 				'prepbufrDataLevelCategory')
    lon[lon>180] -= 360  				# Convert Longitude from [0,360] to [-180,180]
    sid = r.get('stationIdentification', 		'prepbufrDataLevelCategory')
    elv = r.get('stationElevation', 			'prepbufrDataLevelCategory', type='float')
    tpc = r.get('temperatureEventProgramCode', 		'prepbufrDataLevelCategory')
    pob = r.get('pressure', 				'prepbufrDataLevelCategory')
    pob *= 100

    # Time variable
    hrdr = r.get('timeOffset', 				'prepbufrDataLevelCategory')
    ulan = r.get('releaseTime')
    ulan = np.int64(ulan*3600)

    cycleTimeSinceEpoch = np.int64(calendar.timegm(time.strptime(reference_time, '%Y-%m-%dT%H:%M:%SZ')))
    ulan += cycleTimeSinceEpoch
    ulan = np.repeat(ulan[:,0], ulan.shape[1])
    ulan = ulan.reshape(ulan.shape)

    # ObsValue
    ps   = np.full(pob.shape[0], pob.fill_value) 	# Extract stationPressure from pressure, which belongs to CAT=1
    ps   = np.where(cat == 0, pob, ps)
    tob = r.get('airTemperature', 			'prepbufrDataLevelCategory')
    tob += 273.15
    tsen = np.full(tob.shape[0], tob.fill_value) 	# Extract sensible temperature from tob, which belongs to TPC=1
    tsen = np.where(tpc == 1, tob, tsen)
    tvo   = np.full(tob.shape[0], tob.fill_value) 	# Extract virtual temperature from tob, which belongs to TPC <= 8 and TPC>1
    tvo   = np.where(((tpc <= 8) & (tpc > 1)), tob, tvo)
    qob = r.get('specificHumidity', 			'prepbufrDataLevelCategory', type='float')
    qob *= 1.0e-6
    uob = r.get('windEastward', 			'prepbufrDataLevelCategory')
    vob = r.get('windNorthward', 			'prepbufrDataLevelCategory')
    zob = r.get('heightOfObservation', 			'prepbufrDataLevelCategory')

    # QualityMark                    
    pobqm = r.get('pressureQM', 			'prepbufrDataLevelCategory')
    psqm = np.full(pobqm.shape[0], pobqm.fill_value) 	# Extract stationPressureQM from pressureQM
    psqm   = np.where(cat == 0, pobqm, psqm)
    tobqm = r.get('airTemperatureQM', 			'prepbufrDataLevelCategory')
    tsenqm = np.full(tobqm.shape[0], tobqm.fill_value) # Extract airTemperature from tobqm, which belongs to TPC=1
    tsenqm = np.where(tpc == 1, tobqm, tsenqm)
    tvoqm   = np.full(tobqm.shape[0], tobqm.fill_value) # Extract virtual temperature from tob, which belongs to TPC <= 8 and TPC>1
    tvoqm   = np.where(((tpc <= 8) & (tpc > 1)), tobqm, tvoqm)
    qobqm = r.get('specificHumidityQM', 		'prepbufrDataLevelCategory')
    uobqm = r.get('windEastwardQM', 			'prepbufrDataLevelCategory')
    vobqm = r.get('windNorthwardQM', 			'prepbufrDataLevelCategory')

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

    logger.debug(f'     ps    	  shape = {ps.shape}')
    logger.debug(f'     tob       shape = {tob.shape}')
    logger.debug(f'     tsen      shape = {tsen.shape}')
    logger.debug(f'     tvo       shape = {tvo.shape}')
    logger.debug(f'     qob       shape = {qob.shape}')
    logger.debug(f'     uob       shape = {uob.shape}')
    logger.debug(f'     vob       shape = {vob.shape}')
    logger.debug(f'     zob       shape = {zob.shape}')

    logger.debug(f'     pobqm     shape = {pobqm.shape}')
    logger.debug(f'     psqm      shape = {psqm.shape}')
    logger.debug(f'     tobqm     shape = {tobqm.shape}')
    logger.debug(f'     tsenqm    shape = {tsenqm.shape}')
    logger.debug(f'     tvoqm     shape = {tvoqm.shape}')
    logger.debug(f'     qobqm     shape = {qobqm.shape}')
    logger.debug(f'     uobqm     shape = {uobqm.shape}')
    logger.debug(f'     vobqm     shape = {vobqm.shape}')

    logger.debug(f'     cat       type  = {cat.dtype}')
    logger.debug(f'     lat       type  = {lat.dtype}')
    logger.debug(f'     lon       type  = {lon.dtype}')
    logger.debug(f'     sid       type  = {sid.dtype}')
    logger.debug(f'     elv       type  = {elv.dtype}')
    logger.debug(f'     tpc       type  = {tpc.dtype}')
    logger.debug(f'     pob       type  = {pob.dtype}')
    logger.debug(f'     hrdr      type  = {hrdr.dtype}')
    logger.debug(f'     ulan      type  = {ulan.dtype}')

    logger.debug(f'     ps        type = {ps.dtype}')
    logger.debug(f'     tob       type = {tob.dtype}')
    logger.debug(f'     tsen      type = {tsen.dtype}')
    logger.debug(f'     tvo       type = {tvo.dtype}')
    logger.debug(f'     qob       type = {qob.dtype}')
    logger.debug(f'     uob       type = {uob.dtype}')
    logger.debug(f'     vob       type = {vob.dtype}')
    logger.debug(f'     zob       type = {zob.dtype}')

    logger.debug(f'     pobqm     type = {pobqm.dtype}')
    logger.debug(f'     psqm      type = {psqm.dtype}')
    logger.debug(f'     tobqm     type = {tobqm.dtype}')
    logger.debug(f'     tsenqm    type = {tsenqm.dtype}')
    logger.debug(f'     tvoqm     type = {tvoqm.dtype}')
    logger.debug(f'     qobqm     type = {qobqm.dtype}')
    logger.debug(f'     uobqm     type = {uobqm.dtype}')
    logger.debug(f'     vobqm     type = {vobqm.dtype}')

    # Global variables declaration
    # Set global fill values
    #float32_fill_value = lat.fill_value
    #int32_fill_value = tobqm.fill_value
    #int64_fill_value = hrdr.fill_value.astype(np.int64)
    #string_fill_value  = sid.fill_value
    #logger.debug(f'     float32_fill_value  = {float32_fill_value}')
    #logger.debug(f'     int32_fill_value    = {int32_fill_value}')
    #logger.debug(f'     int64_fill_value    = {int64_fill_value}')
    #logger.debug(f'     string_fill_value    = {string_fill_value}')

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Running time for executing QuerySet to get ResultSet : {running_time} seconds")

    # =========================
    # Create derived variables
    # =========================
    start_time = time.time()

    logger.info('Creating derived variables - dateTime from hrdr')

    cycleTimeSinceEpoch = np.int64(calendar.timegm(time.strptime(reference_time, '%Y-%m-%dT%H:%M:%SZ')))
    #cycleTimeSinceEpoch = np.int64(calendar.timegm(time.strptime('2021 08 01 00 00 00', '%Y %m %d %H %M %S')))
    hrdr = Compute_dateTime(cycleTimeSinceEpoch, hrdr)
 

    logger.debug('     Check derived variables type ... ')
    logger.debug(f'     hrdr      type = {hrdr.dtype}')
    #logger.debug(f'     ulan      type = {ulan.dtype}')

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Running time for creating derived variables : {running_time} seconds")


    # Create the dimensions
    dims = {
       'Location': np.arange(0, lat.shape[0])
    }

    # Create IODA ObsSpace
    iodafile = f"{cycle_type}.t{hh}z.{data_type}.nc"
    #iodafile = f"{cycle_type}.t{hh}z.{data_type}.{data_format}.tm00.nc"
    OUTPUT_PATH = os.path.join(ioda_dir, iodafile)
    logger.info(f"Create output file: {OUTPUT_PATH}")
    obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)

    # Create Global attributes
    logger.debug(' ... ... Create global attributes')
    #obsspace.write_attr('Converter', converter)
    obsspace.write_attr('sourceFiles', bufrfile)
    obsspace.write_attr('dataProviderOrigin', data_provider)
    obsspace.write_attr('description', data_description)
    #obsspace.write_attr('datetimeReference', reference_time)
    #obsspace.write_attr('datetimeRange', [ str(hrdr.min()), str(hrdr.max())] )
    #obsspace.write_attr('source', 'UPPER-AIR (RAOB, PIBAL, RECCO, DROPS) REPORTS ')

    # Create IODA variables
    logger.debug(' ... ... Create variables: name, type, units, and attributes')
    # Prepbufr Data Level Category
    obsspace.create_var('MetaData/prepbufrDataLevelCategory', dtype=cat.dtype, fillval=cat.fill_value) \
        .write_attr('units', '1') \
        .write_attr('long_name', 'Prepbufr Data Level Category') \
        .write_data(cat)

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
    obsspace.create_var('MetaData/temperatureEventProgramCode', dtype=tpc.dtype, fillval=tpc.fill_value) \
        .write_attr('units', '1') \
        .write_attr('long_name', 'Temperature Event Program Code') \
        .write_data(tpc)

    # Pressure
    obsspace.create_var('MetaData/pressure', dtype=pob.dtype, fillval=pob.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Pressure') \
        .write_data(pob)

    # Datetime
    obsspace.create_var('MetaData/dateTime', dtype=np.int64, fillval=hrdr.fill_value) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'Datetime') \
        .write_data(hrdr)

    # releaseTime
    obsspace.create_var('MetaData/releaseTime', dtype=np.int64, fillval=hrdr.fill_value) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'Release Time') \
        .write_data(ulan)

    print("Create ObsValue group variables")
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

    # Height of Observation
    obsspace.create_var('ObsValue/heightOfObservation', dtype=zob.dtype, fillval=zob.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Height of Observation') \
        .write_data(zob)

    print("Create QualityMarker group variables")
    # Pressure Quality Marker
    obsspace.create_var('QualityMarker/pressure', dtype=pobqm.dtype, fillval=pobqm.fill_value) \
        .write_attr('units', '1') \
        .write_attr('long_name', 'Pressure Quality Marker') \
        .write_data(pobqm)

    # Station Pressure Quality Marker
    obsspace.create_var('QualityMarker/stationPressure', dtype=pobqm.dtype, fillval=pobqm.fill_value) \
        .write_attr('units', '1') \
        .write_attr('long_name', 'Station Pressure Quality Marker') \
        .write_data(psqm)

    # Air Temperature Quality Marker
    obsspace.create_var('QualityMarker/airTemperature', dtype=tobqm.dtype, fillval=tobqm.fill_value) \
        .write_attr('units', '1') \
        .write_attr('long_name', 'Temperature Quality Marker') \
        .write_data(tobqm)

    # Virtual Temperature Quality Marker
    obsspace.create_var('QualityMarker/virtualTemperature', dtype=tobqm.dtype, fillval=tobqm.fill_value) \
        .write_attr('units', '1') \
        .write_attr('long_name', 'Virtual Temperature Quality Marker') \
        .write_data(tvoqm)

    # Specific Humidity Quality Marker
    obsspace.create_var('QualityMarker/specificHumidity', dtype=qobqm.dtype, fillval=qobqm.fill_value) \
        .write_attr('units', '1') \
        .write_attr('long_name', 'Specific Humidity Quality Marker') \
        .write_data(qobqm)

    # Eastward Wind Quality Marker
    obsspace.create_var('QualityMarker/windEastward', dtype=uobqm.dtype, fillval=uobqm.fill_value) \
        .write_attr('units', '1') \
        .write_attr('long_name', 'Eastward Wind Quality Marker') \
        .write_data(uobqm)

    # Northward Wind Quality Marker
    obsspace.create_var('QualityMarker/windNorthward', dtype=vobqm.dtype, fillval=vobqm.fill_value) \
        .write_attr('units', '1') \
        .write_attr('long_name', 'Northward Wind Quality Marker') \
        .write_data(vobqm)


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
