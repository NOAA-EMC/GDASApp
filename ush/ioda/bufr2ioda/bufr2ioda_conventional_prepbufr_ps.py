#!/usr/bin/env python3
# (C) Copyright 2023 NOAA/NWS/NCEP/EMC
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

import sys
sys.path.append('/work2/noaa/da/nesposito/ioda_bundle_readlc/build/lib/python3.7/')
sys.path.append('/work2/noaa/da/nesposito/ioda_bundle_readlc/build/lib/python3.7/pyioda')
sys.path.append('/work2/noaa/da/nesposito/ioda_bundle_readlc/build/lib/python3.7/pyiodaconv')
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

    subsets1 = config["subsets1"]
    subsets2 = config["subsets2"]
    logger.debug(f"Checking subsets1 = {subsets1}")
    logger.debug(f"Checking subsets2 = {subsets2}")
    logger.info(f"Checking subsets1 = {subsets1}")
    logger.info(f"Checking subsets2 = {subsets2}")

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
#    q = bufr.QuerySet(subsets)   #### A B C works 
    q = bufr.QuerySet()
    r = bufr.QuerySet()
    s = bufr.QuerySet()
   


#    for i in range(len(subsets)):
#        print("NE 0 1 2", subsets[0],subsets[1],subsets[2], len(subsets))
#        if subsets[i] == "ADPSFC":
    logger.info("NE ADPSFC")
    # MetaData
#    q.add('stationIdentification', '*/SID, */SID, */SID')   #### A WORKS
    q.add('stationIdentification1', 'ADPSFC/SID')
    r.add('stationIdentification2', 'SFCSHP/SID')    # B WORKS
    s.add('stationIdentification3', 'ADPUPA/SID')    # B WORKS
    s.add('prepbufrDataLevelCategory', '*/PRSLEVEL/CAT')
#    q.add('temperatureEventCode', '/T___INFO/T__EVENT{1}/TPC')
#    q.add('temperatureEventCode', 'SFCSHP/T___INFO/T__EVENT{1}/TPC') # Cworks
#    q.add('temperatureEventCode', 'ADPUPA/PRSLEVEL/T___INFO/T__EVENT{1}/TPC') # C works
    q.add('temperatureEventCode', "[ADPSFC/T___INFO/T__EVENT{1}/TPC, SFCSHP/T___INFO/T__EVENT{1}/TPC]")
    q.add('temperatureEventCode2', "ADPUPA/PRSLEVEL/T___INFO/T__EVENT{1}/TPC")
#    q.add('temperatureEventCode', "[ADPSFC/T___INFO/T__EVENT{1}/TPC, SFCSHP/T___INFO/T__EVENT{1}/TPC, ADPUPA/PRSLEVEL/T___INFO/T__EVENT{1}/TPC]")


       
    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Running time for making QuerySet: {running_time} seconds")

    # ==============================================================
    # Open the BUFR file and execute the QuerySet to get ResultSet
    # Use the ResultSet returned to get numpy arrays of the data
    # ==============================================================
    start_time = time.time()

#    print("NE q0", q0.dir())
#    print("NE q1", q1.type(), q1.dir())
#    print("NE q2", q2.type(), q2.dir())

    logger.info(f"Executing QuerySet to get ResultSet ...")
    with bufr.File(DATA_PATH) as f:
        t = f.execute(q)
        u = f.execute(r)
        v = f.execute(s)
#        r0 = f.execute(q0)
#        r1 = f.execute(q1)
   
    logger.info(" ... Executing QuerySet for ADPSFC: get MetaData: basic ...")
    # MetaData
    sid1 = t.get('stationIdentification1')
    sid2 = u.get('stationIdentification2')
    sid3 = v.get('stationIdentification3')
    cat = r.get('prepbufrDataLevelCategory')
    tpc = r.get('temperatureEventCode')
    tpc2 = r.get('temperatureEventCode2', 'prepbufrDataLevelCategory')

    logger.info(f" ... Executing QuerySet: Done!")



#            logger.info(f" ... Executing QuerySet: Check BUFR variable generic \
#                        dimension and type ...")
#            # Check BUFR variable generic dimension and type
    logger.info(f"     sid1       shape = {sid1.shape}")
    logger.info(f"     sid2       shape = {sid2.shape}")
    logger.info(f"     sid3       shape = {sid3.shape}")
    logger.info(f"     cat       shape = {cat.shape}")
    logger.info(f"     tpc       shape = {tpc.shape}")
    logger.info(f"     tpc2      shape = {tpc2.shape}")
#            logger.info(f"     dhr       shape = {dhr_var0.shape}")
#            logger.info(f"     lat       shape = {lat_var0.shape}")
#            logger.info(f"     lon       shape = {lon_var0.shape}")
#            logger.info(f"     elv       shape = {elv_var0.shape}")
#            logger.info(f"     typ       shape = {typ_var0.shape}")
#            logger.info(f"     pressure  shape = {pressure_var0.shape}")
#        
#            logger.info(f"     pobqm     shape = {pobqm_var0.shape}")
#            logger.info(f"     pob       shape = {pob_var0.shape}")
#        
#            logger.info(f"     sid       type  = {sid_var0.dtype}")
#            logger.info(f"     dhr       type  = {dhr_var0.dtype}")
#            logger.info(f"     lat       type  = {lat_var0.dtype}")
#            logger.info(f"     lon       type  = {lon_var0.dtype}")
#            logger.info(f"     elv       type  = {elv_var0.dtype}")
#            logger.info(f"     typ       type  = {typ_var0.dtype}")
#            logger.info(f"     pressure  type  = {pressure_var0.dtype}")
#        
#            logger.info(f"     pobqm     type  = {pobqm_var0.dtype}")
#            logger.info(f"     pob       type  = {pob_var0.dtype}")
#        
#            end_time = time.time()
#            running_time = end_time - start_time
#            logger.info(f"Running time for executing QuerySet to get ResultSet: \
#                        {running_time} seconds")
#######        
#            # =========================
#            # Create derived variables
#            # =========================
#            start_time = time.time()
#        
#            logger.info(f"Creating derived variables - dateTime ...")
#        
#            cycleTimeSinceEpoch = np.int64(calendar.timegm(time.strptime(
#                                           reference_time_full, '%Y%m%d%H%M')))
#            dateTime_var0 = Compute_dateTime(cycleTimeSinceEpoch, dhr_var0)
#        
#            logger.info(f"     Check derived variables type ... ")
#            logger.info(f"     dateTime shape = {dateTime_var0.shape}")
#            logger.info(f"     dateTime type = {dateTime_var0.dtype}")
############        
#        elif subsets[i] == "SFCSHP":
#            logger.info("NE SFCSHP")
#            # MetaData
#            q.add('stationIdentification', 'SFCSHP/SID')
#            q.add('latitude', 'SFCSHP/YOB')
#            q.add('longitude', 'SFCSHP/XOB')
#            q.add('obsTimeMinusCycleTime', 'SFCSHP/DHR')
#            q.add('stationElevation', 'SFCSHP/ELV')
#            q.add('observationType', 'SFCSHP/TYP')
#            q.add('pressure', 'SFCSHP/P___INFO/P__EVENT{1}/POB')
#            q.add('temperatureEventCode', 'SFCSHP/T___INFO/T__EVENT{1}/TPC')
#        
#            # Quality Infomation (Quality Indicator)
#            q.add('qualityMarkerStationPressure', 'SFCSHP/P___INFO/P__EVENT{1}/PQM')
#            q.add('qualityMarkerAirTemperature', 'SFCSHP/T___INFO/T__EVENT{1}/TQM')
#        
#            # ObsValue
#            q.add('stationPressure', 'SFCSHP/P___INFO/P__EVENT{1}/POB')
#            q.add('airTemperature', 'SFCSHP/T___INFO/T__EVENT{1}/TOB')
#            q.add('virtualTemperature', 'SFCSHP/T___INFO/TVO')
#
#            # MetaData
#            sid_var1 = r.get('stationIdentification')
#            lat_var1 = r.get('latitude')
#            lon_var1 = r.get('longitude')
#            lon_var1[lon_var1 > 180] -= 360
#            elv_var1 = r.get('stationElevation', type='float')
#            typ_var1 = r.get('observationType')
#            pressure_var1 = r.get('pressure')
#            pressure_var1 *= 100
#            tpc_var1 = r.get('temperatureEventCode')
#         
#            logger.info(f" ... Executing QuerySet: get QualityMarker information ...")
#            # Quality Information
#            pqm_var1 = r.get('qualityMarkerStationPressure')
#            tqm_var1 = r.get('qualityMarkerAirTemperature')
#            qqm_var1 = r.get('qualityMarkerSpecificHumidity')
#            wqm_var1 = r.get('qualityMarkerWindNorthward')
#            sstqm_var1 = r.get('qualityMarkerSeaSurfaceTemperature')
#         
#            logger.info(f" ... Executing QuerySet: get obsvalue: stationPressure ...")
#            # ObsValue
#            pob_var1 = r.get('stationPressure')
#            pob_var1 *= 100
#            tob_var1 = r.get('airTemperature')
#            tob_var1 += 273.15
#            tvo_var1 = r.get('virtualTemperature')
#            tvo_var1 += 273.15
#            qob_var1 = r.get('specificHumidity', type='float')
#            qob_var1 *= 0.000001
#            uob_var1 = r.get('windEastward')
#            vob_var1 = r.get('windNorthward')
#            sst1_var1 = r.get('seaSurfaceTemperature')
#         
#            logger.info(f" ... Executing QuerySet: get datatime: observation time ...")
#            # DateTime: seconds since Epoch time
#            # IODA has no support for numpy datetime arrays dtype=datetime64[s]
#            dhr_var1 = r.get('obsTimeMinusCycleTime', type='int64')
#         
#            logger.info(f" ... Executing QuerySet: Done!")
#         
#            logger.info(f" ... Executing QuerySet: Check BUFR variable generic  \
#                        dimension and type ...")
#            # Check BUFR variable generic dimension and type
#            logger.info(f"     sid       shape = {sid_var0.shape}")
#            logger.info(f"     dhr       shape = {dhr_var0.shape}")
#            logger.info(f"     lat       shape = {lat_var0.shape}")
#            logger.info(f"     lon       shape = {lon_var0.shape}")
#            logger.info(f"     elv       shape = {elv_var0.shape}")
#            logger.info(f"     typ       shape = {typ_var0.shape}")
#            logger.info(f"     pressure  shape = {pressure_var0.shape}")
#            logger.info(f"     tpc       shape = {tpc_var0.shape}")
#         
#            logger.info(f"     pqm       shape = {pqm_var0.shape}")
#            logger.info(f"     tqm       shape = {tqm_var0.shape}")
#         
#            logger.info(f"     pob       shape = {pob_var0.shape}")
#            logger.info(f"     tob       shape = {pob_var0.shape}")
#            logger.info(f"     tvo       shape = {tvo_var0.shape}")
#         
#            logger.info(f"     sid       type  = {sid_var0.dtype}")
#            logger.info(f"     dhr       type  = {dhr_var0.dtype}")
#            logger.info(f"     lat       type  = {lat_var0.dtype}")
#            logger.info(f"     lon       type  = {lon_var0.dtype}")
#            logger.info(f"     elv       type  = {elv_var0.dtype}")
#            logger.info(f"     typ       type  = {typ_var0.dtype}")
#            logger.info(f"     pressure  type  = {pressure_var0.dtype}")
#            logger.info(f"     tpc       type  = {tpc_var0.dtype}")
#         
#            logger.info(f"     pqm       type  = {pqm_var0.dtype}")
#            logger.info(f"     tqm       type  = {tqm_var0.dtype}")
#         
#            logger.info(f"     pob       type  = {pob_var0.dtype}")
#            logger.info(f"     tob       type  = {tob_var0.dtype}")
#            logger.info(f"     tvo       type  = {tvo_var0.dtype}")
#
#
# ############## put a timer?
#
#
#        elif subsets[i] == "ADPUPA":
#            logger.info("NE ADPUPA")
#
#            q.add('prepbufrDataLevelCategory', 'ADPUPA/PRSLEVEL/CAT')
#            q.add('latitude', 'ADPUPA/PRSLEVEL/DRFTINFO/YDR')
#            q.add('longitude', 'ADPUPA/PRSLEVEL/DRFTINFO/XDR')
#            q.add('stationIdentification', 'ADPUPA/SID')
#            q.add('stationElevation', 'ADPUPA/ELV')
#            q.add('timeOffset', 'ADPUPA/PRSLEVEL/DRFTINFO/HRDR')
#            q.add('temperatureEventCode','ADPUPA/PRSLEVEL/T___INFO/T__EVENT{1}/TPC')
#            q.add('pressure', 'ADPUPA/PRSLEVEL/P___INFO/P__EVENT{1}/POB')
#        
#            # ObsValue
#            q.add('stationPressure', 'ADPUPA/PRSLEVEL/P___INFO/P__EVENT{1}/POB')
#            q.add('airTemperature', 'ADPUPA/PRSLEVEL/T___INFO/T__EVENT{1}/TOB')
#            #q.add('virtualTemperature', 'ADPUPA/PRSLEVEL/T___INFO/TVO')
#            q.add('heightOfObservation', 'ADPUPA/PRSLEVEL/Z___INFO/Z__EVENT{1}/ZOB')
#        
#            # QualityMark
#            q.add('pressureQM', 'ADPUPA/PRSLEVEL/P___INFO/P__EVENT{1}/PQM')
#            q.add('airTemperatureQM', 'ADPUPA/PRSLEVEL/T___INFO/T__EVENT{1}/TQM')
#            q.add('virtualTemperatureQM', 'ADPUPA/PRSLEVEL/T___INFO/T__EVENT{1}/TQM')
#        
#            # Use the ResultSet returned to get numpy arrays of the data
#            # MetaData
#            cat_var2 = r.get('prepbufrDataLevelCategory', 'prepbufrDataLevelCategory')
#            lat_var2 = r.get('latitude', 'prepbufrDataLevelCategory')
#            lon_var2 = r.get('longitude', 'prepbufrDataLevelCategory')
#            lon_var2[lon_var2>180] -= 360  # Convert Longitude from [0,360] to [-180,180]
#            sid_var2 = r.get('stationIdentification', 'prepbufrDataLevelCategory')
#            elv_var2 = r.get('stationElevation', 'prepbufrDataLevelCategory')
#            tpc_var2 = r.get('temperatureEventCode', 'prepbufrDataLevelCategory')
#            pob_var2 = r.get('pressure', 'prepbufrDataLevelCategory')
#            pob_var2 *= 100
#        
#            # Time variable
#            hrdr_var2 = r.get('timeOffset', 'prepbufrDataLevelCategory')
#            cycleTimeSinceEpoch = np.int64(calendar.timegm(time.strptime('2021 08 01 00 00 00', '%Y %m %d %H %M %S')))
#            hrdr_var2 = np.int64(hrdr_var2*3600)
#            hrdr_var2 += cycleTimeSinceEpoch
#        
#            # ObsValue
#            pob_ps_var2 = np.full(pob.shape[0], pob.fill_value) # Extract stationPressure from pressure, which belongs to CAT=1
#            pob_ps_var2 = np.where(cat == 0, pob, pob_ps)
#            tob_var2 = r.get('airTemperature', 'prepbufrDataLevelCategory')
#            tob_var2 += 273.15
#            tsen_var2 = np.full(tob.shape[0], tob.fill_value) # Extract sensible temperature from tob, which belongs to TPC=1
#            tsen_var2 = np.where(tpc == 1, tob, tsen)
#            tvo_var2 = np.full(tob.shape[0], tob.fill_value) # Extract virtual temperature from tob, which belongs to TPC <= 8 and TPC>1
#            tvo_var2 = np.where(((tpc <= 8) & (tpc > 1)), tob, tvo)
#            qob_var2 = r.get('specificHumidity', 'prepbufrDataLevelCategory', type='float')
#            qob_var2 *= 1.0e-6
#            uob_var2 = r.get('windEastward', 'prepbufrDataLevelCategory')
#            vob_var2 = r.get('windNorthward', 'prepbufrDataLevelCategory')
#        
#            # QualityMark
#            pobqm_var2 = r.get('pressureQM', 'prepbufrDataLevelCategory')
#            pob_psqm_var2 = np.full(pobqm.shape[0], pobqm.fill_value) # Extract stationPressureQM from pressureQM
#            pob_psqm_var2 = np.where(cat == 0, pobqm, pob_psqm)
#            tobqm_var2 = r.get('airTemperatureQM', 'prepbufrDataLevelCategory')
#            tsenqm_var2 = np.full(tobqm.shape[0], tobqm.fill_value) # Extract airTemperature from tobqm, which belongs to TPC=1
#            tsenqm_var2 = np.where(tpc == 1, tobqm, tsenqm)
#            tvoqm_var2 = np.full(tobqm.shape[0], tobqm.fill_value) # Extract virtual temperature from tob, which belongs to TPC <= 8 and TPC>1
#            tvoqm_var2 = np.where(((tpc <= 8) & (tpc > 1)), tobqm, tvoqm)
#            qobqm_var2 = r.get('specificHumidityQM', 'prepbufrDataLevelCategory')
#            uobqm_var2 = r.get('windEastwardQM', 'prepbufrDataLevelCategory')
#            vobqm_var2 = r.get('windNorthwardQM', 'prepbufrDataLevelCategory')
#
#            # put a timer ? 
#            #convert time and prob location and whatever else
#
#
#    #Put all the arrays together
#
#    #End
#
#    end_time = time.time()
#    running_time = end_time - start_time
#    logger.info(f"Running time for creating derived variables: \
#                {running_time} seconds")
#
#    # =====================================
#    # Create IODA ObsSpace
#    # Write IODA output
#    # =====================================
#
#    # Create the dimensions
#    dims = {'Location': np.arange(0, lat.shape[0])}
#
#    iodafile = f"{cycle_type}.t{hh}z.{data_type}.{data_format}.nc"
#    OUTPUT_PATH = os.path.join(ioda_dir, iodafile)
#    logger.info(f" ... ... Create OUTPUT file: {OUTPUT_PATH}")
#
#    path, fname = os.path.split(OUTPUT_PATH)
#    if path and not os.path.exists(path):
#        os.makedirs(path)
#
#    obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)
#
#    # Create Global attributes
#    logger.info(f" ... ... Create global attributes")
#
#    obsspace.write_attr('Converter', converter)
#    obsspace.write_attr('source', source)
#    obsspace.write_attr('sourceFiles', bufrfile)
#    obsspace.write_attr('dataProviderOrigin', data_provider)
#    obsspace.write_attr('description', data_description)
#    obsspace.write_attr('datetimeReference', reference_time)
#    obsspace.write_attr('datetimeRange',
#                        [str(min(dateTime)), str(max(dateTime))])
#    obsspace.write_attr('platformLongDescription', platform_description)
#
#    # Create IODA variables
#    logger.info(f" ... ... Create variables: name, type, units, & attributes")
#    # Longitude
#    obsspace.create_var('MetaData/longitude', dtype=lon.dtype,
#                        fillval=lon.fill_value) \
#        .write_attr('units', 'degrees_east') \
#        .write_attr('valid_range', np.array([-180, 180], dtype=np.float32)) \
#        .write_attr('long_name', 'Longitude') \
#        .write_data(lon)
#
#    # Latitude
#    obsspace.create_var('MetaData/latitude', dtype=lat.dtype,
#                        fillval=lat.fill_value) \
#        .write_attr('units', 'degrees_north') \
#        .write_attr('valid_range', np.array([-90, 90], dtype=np.float32)) \
#        .write_attr('long_name', 'Latitude') \
#        .write_data(lat)
#
#    # Datetime
#    obsspace.create_var('MetaData/dateTime', dtype=dateTime.dtype,
#                        fillval=dateTime.fill_value) \
#        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
#        .write_attr('long_name', 'Datetime') \
#        .write_data(dateTime)
#
#    # Station Identification
#    obsspace.create_var('MetaData/stationIdentification', dtype=sid.dtype,
#                        fillval=sid.fill_value) \
#        .write_attr('long_name', 'Station Identification') \
#        .write_data(sid)
#
#    # Station Elevation
#    obsspace.create_var('MetaData/stationElevation', dtype=elv.dtype,
#                        fillval=elv.fill_value) \
#        .write_attr('units', 'm') \
#        .write_attr('long_name', 'Station Elevation') \
#        .write_data(elv)
#
#    # Observation Type
#    obsspace.create_var('MetaData/observationType', dtype=typ.dtype,
#                        fillval=typ.fill_value) \
#        .write_attr('long_name', 'Observation Type') \
#        .write_data(typ)
#
#    # Pressure
#    obsspace.create_var('MetaData/pressure', dtype=pressure.dtype,
#                        fillval=pressure.fill_value) \
#        .write_attr('units', 'Pa') \
#        .write_attr('long_name', 'Pressure') \
#        .write_data(pressure)
#
#    # Quality: Percent Confidence - Quality Information Without Forecast
#    obsspace.create_var('QualityMarker/stationPressure', dtype=pobqm.dtype,
#                        fillval=pobqm.fill_value) \
#        .write_attr('long_name', 'Station Pressure Quality Marker') \
#        .write_data(pobqm)
#
#    # Station Pressure
#    obsspace.create_var('ObsValue/pressure', dtype=pob.dtype,
#                        fillval=pob.fill_value) \
#        .write_attr('units', 'Pa') \
#        .write_attr('long_name', 'Station Pressure') \
#        .write_data(pob)
#
#    end_time = time.time()
#    running_time = end_time - start_time
#    logger.info(f"Running time for splitting and output IODA: \
#                {running_time} seconds")

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
