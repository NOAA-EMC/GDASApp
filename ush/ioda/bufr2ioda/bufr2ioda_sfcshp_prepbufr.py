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

def Compute_dateTime(cycleTimeSinceEpoch, dhr):

    dhr = np.int64(dhr*3600)
    dateTime = dhr + cycleTimeSinceEpoch

    return dateTime 

def bufr_to_ioda(config):

    subsets = config["subsets"]

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

    # General informaton
    converter = 'BUFR to IODA Converter'
    platform_description = 'SFCSHP data from prepBUFR format'

    bufrfile = f"{cycle_type}.t{hh}z.{data_format}"
    DATA_PATH = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}", str(hh), bufrfile)

    print("The DATA_PATH is: "+str(DATA_PATH))

    # ============================================
    # Make the QuerySet for all the data we want
    # ============================================
    start_time = time.time()

    print('Making QuerySet ...')
    q = bufr.QuerySet(subsets)

    # MetaData
    q.add('stationIdentification',             '*/SID')
    q.add('latitude',                          '*/YOB')
    q.add('longitude',                         '*/XOB')
    q.add('obsTimeMinusCycleTime',             '*/DHR')
    q.add('stationElevation',                  '*/ELV') 
    q.add('observationType',                   '*/TYP') 
    q.add('pressure',                          '*/P___INFO/P__EVENT{1}/POB')
    q.add('temperatureEventCode',              '*/T___INFO/T__EVENT{1}/TPC')

#   # Quality Infomation (Quality Indicator)
    q.add('qualityMarkerStationPressure',      '*/P___INFO/P__EVENT{1}/PQM')
    q.add('qualityMarkerAirTemperature',       '*/T___INFO/T__EVENT{1}/TQM')
    q.add('qualityMarkerSpecificHumidity',     '*/Q___INFO/Q__EVENT{1}/QQM')
    q.add('qualityMarkerWindNorthward',        '*/W___INFO/W__EVENT{1}/WQM')
    q.add('qualityMarkerSeaSurfaceTemperature','*/SST_INFO/SSTEVENT{1}/SSTQM')

    # ObsValue
    q.add('stationPressure',                   '*/P___INFO/P__EVENT{1}/POB') 
    q.add('airTemperature',                    '*/T___INFO/T__EVENT{1}/TOB') 
    q.add('virtualTemperature',                '*/T___INFO/TVO')
    q.add('specificHumidity',                  '*/Q___INFO/Q__EVENT{1}/QOB')
    q.add('windNorthward',                     '*/W___INFO/W__EVENT{1}/VOB')
    q.add('windEastward',                      '*/W___INFO/W__EVENT{1}/UOB')
    q.add('seaSurfaceTemperature',             '*/SST_INFO/SSTEVENT{1}/SST1')

    end_time = time.time()
    running_time = end_time - start_time
    print('Running time for making QuerySet : ', running_time, 'seconds') 

    # ==============================================================
    # Open the BUFR file and execute the QuerySet to get ResultSet
    # Use the ResultSet returned to get numpy arrays of the data
    # ==============================================================
    start_time = time.time()

    print('Executing QuerySet to get ResultSet ...')
    with bufr.File(DATA_PATH) as f:
       r = f.execute(q)
 
    print(' ... Executing QuerySet: get metadata: basic ...')
    # MetaData
    sid       = r.get('stationIdentification')
    lat       = r.get('latitude')
    lon       = r.get('longitude')
    lon[lon>180] -= 360
    elv       = r.get('stationElevation', type='float')
    typ       = r.get('observationType')
    pressure  = r.get('pressure')
    pressure *= 100
    tpc       = r.get('temperatureEventCode')

    print(' ... Executing QuerySet: get QualityMarker information ...')
    # Quality Information 
    pqm       = r.get('qualityMarkerStationPressure')
    tqm       = r.get('qualityMarkerAirTemperature')
    qqm       = r.get('qualityMarkerSpecificHumidity')
    wqm       = r.get('qualityMarkerWindNorthward')
    sstqm     = r.get('qualityMarkerSeaSurfaceTemperature')

    print(' ... Executing QuerySet: get obsvalue: stationPressure ...')
    # ObsValue
    pob       = r.get('stationPressure')
    pob      *= 100
    tob       = r.get('airTemperature')
    tob      += 273.15
    tvo       = r.get('virtualTemperature')
    tvo      += 273.15
    qob       = r.get('specificHumidity', type='float')
    qob      *= 0.000001
    uob       = r.get('windEastward')
    vob       = r.get('windNorthward')
    sst1      = r.get('seaSurfaceTemperature')

    print(' ... Executing QuerySet: get datatime: observation time ...')
    # DateTime: seconds since Epoch time
    # IODA has no support for numpy datetime arrays dtype=datetime64[s]
    dhr       = r.get('obsTimeMinusCycleTime', type='int64')

    print(' ... Executing QuerySet: Done!')

    print(' ... Executing QuerySet: Check BUFR variable generic dimension and type ...')
    # Check BUFR variable generic dimension and type
    print('     sid       shape = ', sid.shape)
    print('     dhr       shape = ', dhr.shape)
    print('     lat       shape = ', lat.shape)
    print('     lon       shape = ', lon.shape)
    print('     elv       shape = ', elv.shape)
    print('     typ       shape = ', typ.shape)
    print('     pressure  shape = ', pressure.shape)
    print('     tpc       shape = ', tpc.shape)

    print('     pqm       shape = ', pqm.shape)
    print('     tqm       shape = ', tqm.shape)
    print('     qqm       shape = ', qqm.shape)
    print('     wqm       shape = ', wqm.shape)
    print('     sstqm     shape = ', sstqm.shape)

    print('     pob       shape = ', pob.shape)
    print('     tob       shape = ', pob.shape)
    print('     tvo       shape = ', tvo.shape)
    print('     qob       shape = ', qob.shape)
    print('     uob       shape = ', uob.shape)
    print('     vob       shape = ', vob.shape)
    print('     sst1      shape = ', sst1.shape)

    print('     sid       type  = ', sid.dtype)  
    print('     dhr       type  = ', dhr.dtype)  
    print('     lat       type  = ', lat.dtype)  
    print('     lon       type  = ', lon.dtype)  
    print('     elv       type  = ', elv.dtype)  
    print('     typ       type  = ', typ.dtype)  
    print('     pressure  type  = ', pressure.dtype)  
    print('     tpc       type  = ', tpc.dtype)  

    print('     pqm       type  = ', pqm.dtype)  
    print('     tqm       type  = ', tqm.dtype)  
    print('     qqm       type  = ', qqm.dtype)  
    print('     wqm       type  = ', wqm.dtype)  
    print('     sstqm     type  = ', sstqm.dtype)  

    print('     pob       type  = ', pob.dtype)  
    print('     tob       type  = ', tob.dtype)  
    print('     tvo       type  = ', tvo.dtype)  
    print('     qob       type  = ', qob.dtype)  
    print('     uob       type  = ', uob.dtype)  
    print('     vob       type  = ', vob.dtype)  
    print('     sst1      type  = ', sst1.dtype)  

    end_time = time.time()
    running_time = end_time - start_time
    print('Running time for executing QuerySet to get ResultSet : ', running_time, 'seconds')

    # =========================
    # Create derived variables
    # =========================
    start_time = time.time()

    print('Creating derived variables - dateTime ...')

    cycleTimeSinceEpoch = np.int64(calendar.timegm(time.strptime(reference_time_full, '%Y%m%d%H%M')))
    dateTime = Compute_dateTime(cycleTimeSinceEpoch, dhr)

    print('     Check derived variables type ... ')
    print('     dateTime shape = ', dateTime.shape)
    print('     dateTime type = ',  dateTime.dtype)

    end_time = time.time()
    running_time = end_time - start_time
    print('Running time for creating derived variables : ', running_time, 'seconds')

    # =====================================
    # Create IODA ObsSpace
    # Write IODA output
    # =====================================

    # Create the dimensions
    dims = {
       'Location'   : np.arange(0, lat.shape[0]),
    }


    iodafile = f"{cycle_type}.t{hh}z.{data_type}.{data_format}.nc"
    OUTPUT_PATH = os.path.join(ioda_dir, iodafile)
    print(" ... ... Create OUTPUT file: ", OUTPUT_PATH)

    path, fname = os.path.split(OUTPUT_PATH)
    if path and not os.path.exists(path):
        os.makedirs(path)

    obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)

    # Create Global attributes
    print(' ... ... Create global attributes')

    obsspace.write_attr('Converter', converter)
    obsspace.write_attr('source', source)
    obsspace.write_attr('sourceFiles', bufrfile)
    obsspace.write_attr('dataProviderOrigin', data_provider)
    obsspace.write_attr('description', data_description)
    obsspace.write_attr('datetimeReference', reference_time)
    obsspace.write_attr('datetimeRange', [str(min(dateTime)), str(max(dateTime))])
    obsspace.write_attr('platformLongDescription', platform_description)

    # Create IODA variables
    print(' ... ... Create variables: name, type, units, and attributes')
    # Longitude
    obsspace.create_var('MetaData/longitude', dtype=lon.dtype, fillval=lon.fill_value) \
        .write_attr('units', 'degrees_east') \
        .write_attr('valid_range', np.array([-180, 180], dtype=np.float32)) \
        .write_attr('long_name', 'Longitude') \
        .write_data(lon)

    # Latitude 
    obsspace.create_var('MetaData/latitude', dtype=lat.dtype, fillval=lat.fill_value) \
        .write_attr('units', 'degrees_north') \
        .write_attr('valid_range', np.array([-90, 90], dtype=np.float32)) \
        .write_attr('long_name', 'Latitude') \
        .write_data(lat)

    # Datetime
    obsspace.create_var('MetaData/dateTime',  dtype=dateTime.dtype, fillval=dateTime.fill_value) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'Datetime') \
        .write_data(dateTime)

    # Station Identification
    obsspace.create_var('MetaData/stationIdentification',  dtype=sid.dtype, fillval=sid.fill_value) \
        .write_attr('units', '1') \
        .write_attr('long_name', 'Station Identification') \
        .write_data(sid)

    # Station Elevation
    obsspace.create_var('MetaData/stationElevation',  dtype=elv.dtype, fillval=elv.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Station Elevation') \
        .write_data(elv)

    # Observation Type 
    obsspace.create_var('MetaData/observationType',  dtype=typ.dtype, fillval=typ.fill_value) \
        .write_attr('long_name', 'Observation Type') \
        .write_data(typ)

    # Pressure
    obsspace.create_var('MetaData/pressure',  dtype=pressure.dtype, fillval=pressure.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Pressure') \
        .write_data(pressure)

    # Temperature Event Code
    obsspace.create_var('MetaData/temperatureEventCode',  dtype=tpc.dtype, fillval=tpc.fill_value) \
        .write_attr('long_name', 'Temperature Event Code') \
        .write_data(typ)

    # Quality Marker: Station Pressure
    obsspace.create_var('QualityMarker/stationPressure',  dtype=pqm.dtype, fillval=pqm.fill_value) \
        .write_attr('long_name', 'Station Pressure Quality Marker') \
        .write_data(pqm)

    # Quality Marker: Air Temperature 
    obsspace.create_var('QualityMarker/airTemperature',  dtype=tqm.dtype, fillval=tqm.fill_value) \
        .write_attr('long_name', 'Air Temperature Quality Marker') \
        .write_data(tqm)

    # Quality Marker: Specific Humidity
    obsspace.create_var('QualityMarker/specificHumidity',  dtype=qqm.dtype, fillval=qqm.fill_value) \
        .write_attr('long_name', 'Specific Humidity Quality Marker') \
        .write_data(qqm)

    # Quality Marker: Northward Wind
    obsspace.create_var('QualityMarker/windNorthward',  dtype=wqm.dtype, fillval=wqm.fill_value) \
        .write_attr('long_name', 'Northward Wind Quality Marker') \
        .write_data(wqm)

    # Quality Marker: Sea Surface Temperature
    obsspace.create_var('QualityMarker/seaSurfaceTemperature',  dtype=sstqm.dtype, fillval=sstqm.fill_value) \
        .write_attr('long_name', 'Sea Surface Temperature Quality Marker') \
        .write_data(sstqm)

    # Station Pressure 
    obsspace.create_var('ObsValue/pressure',  dtype=pob.dtype, fillval=pob.fill_value) \
        .write_attr('units', 'Pa') \
        .write_attr('long_name', 'Station Pressure') \
        .write_data(pob)

    # Air Temperature 
    obsspace.create_var('ObsValue/airTemperature',  dtype=tob.dtype, fillval=tob.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Air Temperature') \
        .write_data(tob)

    # Virtual Temperature
    obsspace.create_var('ObsValue/virtualTemperature',  dtype=tvo.dtype, fillval=tvo.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Virtual Temperature') \
        .write_data(tvo)

    # Specific Humidity
    obsspace.create_var('ObsValue/specificHumidity',  dtype=qob.dtype, fillval=qob.fill_value) \
        .write_attr('units', 'kg kg-1') \
        .write_attr('long_name', 'Specific Humidity') \
        .write_data(qob)

    # Eastward Wind
    obsspace.create_var('ObsValue/windEastward',  dtype=uob.dtype, fillval=uob.fill_value) \
        .write_attr('units', 'm s-1') \
        .write_attr('long_name', 'Eastward Wind') \
        .write_data(uob)

    # Northward Wind
    obsspace.create_var('ObsValue/windNorthward',  dtype=vob.dtype, fillval=vob.fill_value) \
        .write_attr('units', 'm s-1') \
        .write_attr('long_name', 'Northward Wind') \
        .write_data(vob)

    # Sea Surface Temperature
    obsspace.create_var('ObsValue/seaSurfaceTemperature',  dtype=sst1.dtype, fillval=sst1.fill_value) \
        .write_attr('units', 'K') \
        .write_attr('long_name', 'Sea Surface Temperature') \
        .write_data(sst1)


    end_time = time.time()
    running_time = end_time - start_time
    print('Running time for splitting and output IODA:', running_time, 'seconds')

    print("All Done!")

if __name__ == '__main__':

    start_time = time.time()

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input JSON configuration', required=True)
    parser.add_argument('-v', '--verbose', help='print debug logging information',
                        action='store_true')
    args = parser.parse_args()


    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config)

    end_time = time.time()
    running_time = end_time - start_time
    print('Total running time: ', running_time, 'seconds') 
