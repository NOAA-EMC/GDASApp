#!/usr/bin/env python3
# (C) Copyright 2023 NOAA/NWS/NCEP/EMC
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

import sys
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
    q = bufr.QuerySet(subsets)

    for i in range(len(subsets)):
        if subsets[i] == "ADPSFC":

            # MetaData
            q.add('stationIdentification', '*/SID')
            q.add('latitude', '*/YOB')
            q.add('longitude', '*/XOB')
            q.add('obsTimeMinusCycleTime', '*/DHR')
            q.add('stationElevation', '*/ELV')
            q.add('observationType', '*/TYP')
            q.add('pressure', '*/P___INFO/P__EVENT{1}/POB')
        
           # Quality Infomation (Quality Indicator)
            q.add('qualityMarkerStationPressure', '*/P___INFO/P__EVENT{1}/PQM')
        
            # ObsValue
            q.add('stationPressure', '*/P___INFO/P__EVENT{1}/POB')
        
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
                r = f.execute(q)
        
            logger.info(" ... Executing QuerySet: get MetaData: basic ...")
            # MetaData
            sid_var1 = r.get('stationIdentification')
            lat_var1 = r.get('latitude')
            lon_var1 = r.get('longitude')
            lon_var1[lon_var1 > 180] -= 360
            elv_var1 = r.get('stationElevation')
            typ_var1 = r.get('observationType')
            pressure_var1 = r.get('pressure')
            pressure_var1 *= 100
        
            logger.info(f" ... Executing QuerySet: get QualityMarker information ...")
            # Quality Information
            pobqm_var1 = r.get('qualityMarkerStationPressure')
        
            logger.info(f" ... Executing QuerySet: get obsvalue: stationPressure ...")
            # ObsValue
            pob_var1 = r.get('stationPressure')
            pob_var1 *= 100
        
            logger.info(f" ... Executing QuerySet: get datatime: observation time ...")
            # DateTime: seconds since Epoch time
            # IODA has no support for numpy datetime arrays dtype=datetime64[s]
            dhr_var1 = r.get('obsTimeMinusCycleTime', type='int64')
        
            logger.info(f" ... Executing QuerySet: Done!")
        
            logger.info(f" ... Executing QuerySet: Check BUFR variable generic \
                        dimension and type ...")
            # Check BUFR variable generic dimension and type
            logger.info(f"     sid       shape = {sid_var1.shape}")
            logger.info(f"     dhr       shape = {dhr_var1.shape}")
            logger.info(f"     lat       shape = {lat_var1.shape}")
            logger.info(f"     lon       shape = {lon_var1.shape}")
            logger.info(f"     elv       shape = {elv_var1.shape}")
            logger.info(f"     typ       shape = {typ_var1.shape}")
            logger.info(f"     pressure  shape = {pressure_var1.shape}")
        
            logger.info(f"     pobqm     shape = {pobqm_var1.shape}")
            logger.info(f"     pob       shape = {pob_var1.shape}")
        
            logger.info(f"     sid       type  = {sid_var1.dtype}")
            logger.info(f"     dhr       type  = {dhr_var1.dtype}")
            logger.info(f"     lat       type  = {lat_var1.dtype}")
            logger.info(f"     lon       type  = {lon_var1.dtype}")
            logger.info(f"     elv       type  = {elv_var1.dtype}")
            logger.info(f"     typ       type  = {typ_var1.dtype}")
            logger.info(f"     pressure  type  = {pressure_var1.dtype}")
        
            logger.info(f"     pobqm     type  = {pobqm_var1.dtype}")
            logger.info(f"     pob       type  = {pob_var1.dtype}")
        
            end_time = time.time()
            running_time = end_time - start_time
            logger.info(f"Running time for executing QuerySet to get ResultSet: \
                        {running_time} seconds")
        
            # =========================
            # Create derived variables
            # =========================
            start_time = time.time()
        
            logger.info(f"Creating derived variables - dateTime ...")
        
            cycleTimeSinceEpoch = np.int64(calendar.timegm(time.strptime(
                                           reference_time_full, '%Y%m%d%H%M')))
            dateTime_var1 = Compute_dateTime(cycleTimeSinceEpoch, dhr)
        
            logger.info(f"     Check derived variables type ... ")
            logger.info(f"     dateTime shape = {dateTime_var1.shape}")
            logger.info(f"     dateTime type = {dateTime_var1.dtype}")
        
        elif subsets[i] == "SFCSHP":
            # MetaData
            sid_var2 = r.get('stationIdentification')
            lat_var2 = r.get('latitude')
            lon_var2 = r.get('longitude')
            lon_var2[lon_var2 > 180] -= 360
            elv_var2 = r.get('stationElevation', type='float')
            typ_var2 = r.get('observationType')
            pressure_var2 = r.get('pressure')
            pressure_var2 *= 100
            tpc_var2 = r.get('temperatureEventCode')
         
            logger.info(f" ... Executing QuerySet: get QualityMarker information ...")
            # Quality Information
            pqm_var2 = r.get('qualityMarkerStationPressure')
            tqm_var2 = r.get('qualityMarkerAirTemperature')
            qqm_var2 = r.get('qualityMarkerSpecificHumidity')
            wqm_var2 = r.get('qualityMarkerWindNorthward')
            sstqm_var2 = r.get('qualityMarkerSeaSurfaceTemperature')
         
            logger.info(f" ... Executing QuerySet: get obsvalue: stationPressure ...")
            # ObsValue
            pob_var2 = r.get('stationPressure')
            pob_var2 *= 100
            tob_var2 = r.get('airTemperature')
            tob_var2 += 273.15
            tvo_var2 = r.get('virtualTemperature')
            tvo_var2 += 273.15
            qob_var2 = r.get('specificHumidity', type='float')
            qob_var2 *= 0.000001
            uob_var2 = r.get('windEastward')
            vob_var2 = r.get('windNorthward')
            sst1_var2 = r.get('seaSurfaceTemperature')
         
            logger.info(f" ... Executing QuerySet: get datatime: observation time ...")
            # DateTime: seconds since Epoch time
            # IODA has no support for numpy datetime arrays dtype=datetime64[s]
            dhr_var2 = r.get('obsTimeMinusCycleTime', type='int64')
         
            logger.info(f" ... Executing QuerySet: Done!")
         
            logger.info(f" ... Executing QuerySet: Check BUFR variable generic  \
                        dimension and type ...")
            # Check BUFR variable generic dimension and type
            logger.info(f"     sid       shape = {sid_var1.shape}")
            logger.info(f"     dhr       shape = {dhr_var1.shape}")
            logger.info(f"     lat       shape = {lat_var1.shape}")
            logger.info(f"     lon       shape = {lon_var1.shape}")
            logger.info(f"     elv       shape = {elv_var1.shape}")
            logger.info(f"     typ       shape = {typ_var1.shape}")
            logger.info(f"     pressure  shape = {pressure_var1.shape}")
            logger.info(f"     tpc       shape = {tpc_var1.shape}")
         
            logger.info(f"     pqm       shape = {pqm_var1.shape}")
            logger.info(f"     tqm       shape = {tqm_var1.shape}")
         
            logger.info(f"     pob       shape = {pob_var1.shape}")
            logger.info(f"     tob       shape = {pob_var1.shape}")
            logger.info(f"     tvo       shape = {tvo_var1.shape}")
         
            logger.info(f"     sid       type  = {sid_var1.dtype}")
            logger.info(f"     dhr       type  = {dhr_var1.dtype}")
            logger.info(f"     lat       type  = {lat_var1.dtype}")
            logger.info(f"     lon       type  = {lon_var1.dtype}")
            logger.info(f"     elv       type  = {elv_var1.dtype}")
            logger.info(f"     typ       type  = {typ_var1.dtype}")
            logger.info(f"     pressure  type  = {pressure_var1.dtype}")
            logger.info(f"     tpc       type  = {tpc_var1.dtype}")
         
            logger.info(f"     pqm       type  = {pqm_var1.dtype}")
            logger.info(f"     tqm       type  = {tqm_var1.dtype}")
         
            logger.info(f"     pob       type  = {pob_var1.dtype}")
            logger.info(f"     tob       type  = {tob_var1.dtype}")
            logger.info(f"     tvo       type  = {tvo_var1.dtype}")

        elif subsets[i] == "ADPUPA":
            q.add('prepbufrDataLevelCategory', '*/PRSLEVEL/CAT')
            q.add('latitude', '*/PRSLEVEL/DRFTINFO/YDR')
            q.add('longitude', '*/PRSLEVEL/DRFTINFO/XDR')
            q.add('stationIdentification', '*/SID')
            q.add('stationElevation', '*/ELV')
            q.add('timeOffset', '*/PRSLEVEL/DRFTINFO/HRDR')
            q.add('temperatureEventCode','*/PRSLEVEL/T___INFO/T__EVENT{1}/TPC')
            q.add('pressure', '*/PRSLEVEL/P___INFO/P__EVENT{1}/POB')
        
            # ObsValue
            q.add('stationPressure', '*/PRSLEVEL/P___INFO/P__EVENT{1}/POB')
            q.add('airTemperature', '*/PRSLEVEL/T___INFO/T__EVENT{1}/TOB')
            #q.add('virtualTemperature', '*/PRSLEVEL/T___INFO/TVO')
            q.add('specificHumidity', '*/PRSLEVEL/Q___INFO/Q__EVENT{1}/QOB')
            q.add('windEastward', '*/PRSLEVEL/W___INFO/W__EVENT{1}/UOB')
            q.add('windNorthward', '*/PRSLEVEL/W___INFO/W__EVENT{1}/VOB')
            q.add('heightOfObservation', '*/PRSLEVEL/Z___INFO/Z__EVENT{1}/ZOB')
        
            # QualityMark
            q.add('pressureQM', '*/PRSLEVEL/P___INFO/P__EVENT{1}/PQM')
            q.add('airTemperatureQM', '*/PRSLEVEL/T___INFO/T__EVENT{1}/TQM')
            q.add('virtualTemperatureQM', '*/PRSLEVEL/T___INFO/T__EVENT{1}/TQM')
            q.add('specificHumidityQM', '*/PRSLEVEL/Q___INFO/Q__EVENT{1}/QQM')
            q.add('windEastwardQM', '*/PRSLEVEL/W___INFO/W__EVENT{1}/WQM')
            q.add('windNorthwardQM', '*/PRSLEVEL/W___INFO/W__EVENT{1}/WQM')
        
            # Use the ResultSet returned to get numpy arrays of the data
            # MetaData
            cat_var3 = r.get('prepbufrDataLevelCategory', 'prepbufrDataLevelCategory')
            lat_var3 = r.get('latitude', 'prepbufrDataLevelCategory')
            lon_var3 = r.get('longitude', 'prepbufrDataLevelCategory')
            lon_var3[lon_var3>180] -= 360  # Convert Longitude from [0,360] to [-180,180]
            sid_var3 = r.get('stationIdentification', 'prepbufrDataLevelCategory')
            elv_var3 = r.get('stationElevation', 'prepbufrDataLevelCategory')
            tpc_var3 = r.get('temperatureEventCode', 'prepbufrDataLevelCategory')
            pob_var3 = r.get('pressure', 'prepbufrDataLevelCategory')
            pob_var3 *= 100
        
            # Time variable
            hrdr_var3 = r.get('timeOffset', 'prepbufrDataLevelCategory')
            cycleTimeSinceEpoch = np.int64(calendar.timegm(time.strptime('2021 08 01 00 00 00', '%Y %m %d %H %M %S')))
            hrdr_var3 = np.int64(hrdr_var3*3600)
            hrdr_var3 += cycleTimeSinceEpoch
        
            # ObsValue
            pob_ps_var3 = np.full(pob.shape[0], pob.fill_value) # Extract stationPressure from pressure, which belongs to CAT=1
            pob_ps_var3 = np.where(cat == 0, pob, pob_ps)
            tob_var3 = r.get('airTemperature', 'prepbufrDataLevelCategory')
            tob_var3 += 273.15
            tsen_var3 = np.full(tob.shape[0], tob.fill_value) # Extract sensible temperature from tob, which belongs to TPC=1
            tsen_var3 = np.where(tpc == 1, tob, tsen)
            tvo_var3 = np.full(tob.shape[0], tob.fill_value) # Extract virtual temperature from tob, which belongs to TPC <= 8 and TPC>1
            tvo_var3 = np.where(((tpc <= 8) & (tpc > 1)), tob, tvo)
            qob_var3 = r.get('specificHumidity', 'prepbufrDataLevelCategory', type='float')
            qob_var3 *= 1.0e-6
            uob_var3 = r.get('windEastward', 'prepbufrDataLevelCategory')
            vob_var3 = r.get('windNorthward', 'prepbufrDataLevelCategory')
        
            # QualityMark
            pobqm_var3 = r.get('pressureQM', 'prepbufrDataLevelCategory')
            pob_psqm_var3 = np.full(pobqm.shape[0], pobqm.fill_value) # Extract stationPressureQM from pressureQM
            pob_psqm_var3 = np.where(cat == 0, pobqm, pob_psqm)
            tobqm_var3 = r.get('airTemperatureQM', 'prepbufrDataLevelCategory')
            tsenqm_var3 = np.full(tobqm.shape[0], tobqm.fill_value) # Extract airTemperature from tobqm, which belongs to TPC=1
            tsenqm_var3 = np.where(tpc == 1, tobqm, tsenqm)
            tvoqm_var3 = np.full(tobqm.shape[0], tobqm.fill_value) # Extract virtual temperature from tob, which belongs to TPC <= 8 and TPC>1
            tvoqm_var3 = np.where(((tpc <= 8) & (tpc > 1)), tobqm, tvoqm)
            qobqm_var3 = r.get('specificHumidityQM', 'prepbufrDataLevelCategory')
            uobqm_var3 = r.get('windEastwardQM', 'prepbufrDataLevelCategory')
            vobqm_var3 = r.get('windNorthwardQM', 'prepbufrDataLevelCategory')


    #Put all the arrays together

    #End

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

    obsspace.write_attr('Converter', converter)
    obsspace.write_attr('source', source)
    obsspace.write_attr('sourceFiles', bufrfile)
    obsspace.write_attr('dataProviderOrigin', data_provider)
    obsspace.write_attr('description', data_description)
    obsspace.write_attr('datetimeReference', reference_time)
    obsspace.write_attr('datetimeRange',
                        [str(min(dateTime)), str(max(dateTime))])
    obsspace.write_attr('platformLongDescription', platform_description)

    # Create IODA variables
    logger.info(f" ... ... Create variables: name, type, units, & attributes")
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
        .write_attr('long_name', 'Station Identification') \
        .write_data(sid)

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

    # Quality: Percent Confidence - Quality Information Without Forecast
    obsspace.create_var('QualityMarker/stationPressure', dtype=pobqm.dtype,
                        fillval=pobqm.fill_value) \
        .write_attr('long_name', 'Station Pressure Quality Marker') \
        .write_data(pobqm)

    # Station Pressure
    obsspace.create_var('ObsValue/pressure', dtype=pob.dtype,
                        fillval=pob.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Station Pressure') \
        .write_data(pob)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Running time for splitting and output IODA: \
                {running_time} seconds")

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
