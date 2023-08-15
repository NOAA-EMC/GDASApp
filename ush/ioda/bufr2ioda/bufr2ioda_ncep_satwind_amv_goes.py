# (C) Copyright 2023 NOAA/NWS/NCEP/EMC
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

import sys

sys.path.append('/work/noaa/da/eliu/JEDI-iodaconv/ioda-bundle/build/lib/')
sys.path.append('/work/noaa/da/eliu/JEDI-iodaconv/ioda-bundle/build/lib/pyiodaconv/')
sys.path.append('/work/noaa/da/eliu/JEDI-iodaconv/ioda-bundle/build/lib/python3.9/')

import numpy as np
import numpy.ma as ma
from pyiodaconv import bufr
import calendar
import json
import time
import math
import datetime 
from pyioda import ioda_obs_space as ioda_ospace

# ====================================================================
# Satellite Winds (AMV) BUFR dump file for GOES
# =====================================================================
# Subset    |  Spectral Band              |  Code (002023) |  ObsType 
# ---------------------------------------------------------------------
# NC005030  |    IRLW  (Freq < 5E+13)     |    Method 1    |   245
# NC005031  |    WV Clear Sky/ Deep Layer |    Method 5    |   247
# NC005032  |    VIS                      |    Method 2    |   251
# NC005034  |    WV Cloud Top             |    Method 3    |   246
# NC005039  |    IRSW  (Freq > 5E+13 )    |    Method 1    |   240
# ====================================================================

# Define and initialize  global variables
global float32_fill_value
global int32_fill_value
global int64_fill_value

float32_fill_value = np.float32(0)
int32_fill_value   = np.int32(0)
int64_fill_value   = np.int64(0)

def  Compute_WindComponents_from_WindDirection_and_WindSpeed(wdir, wspd):

    uob = (-wspd * np.sin(np.radians(wdir))).astype(np.float32)
    vob = (-wspd * np.cos(np.radians(wdir))).astype(np.float32)

    return uob, vob

def  Get_ObsType(swcm, chanfreq):

    obstype = swcm.copy()

    # Use numpy vectorized operations
    obstype = np.where(swcm == 5, 247, obstype)  # WVCA/DL
    obstype = np.where(swcm == 3, 246, obstype)  # WVCT
    obstype = np.where(swcm == 2, 251, obstype)  # VIS
    obstype = np.where(swcm == 1, 245, obstype)  # IRLW

    condition = np.logical_and(swcm == 1, chanfreq >= 50000000000000.0)  # IRSW
    obstype = np.where(condition, 240, obstype)

    if not np.any(np.isin(obstype, [247, 246, 251, 245, 240])):
        raise ValueError("Error: Unassigned ObsType found ... ")

    return obstype

def bufr_to_ioda(config):


    subsets = config["subsets"]
    print('emily checking subsets = ', subsets)

    # Get parameters from configuration
    data_format = config["data_format"]
    data_type = config["data_type"]
    data_description = config["data_description"]
    data_provider = config["data_provider"]
    cycle_type = config["cycle_type"]
    dump_dir = config["dump_directory"]
    ioda_dir = config["ioda_directory"]
    cycle = config["cycle_datetime"]
    yyyymmdd = cycle[0:8]
    hh = cycle[8:10]

    satellite_info_array = config["satellite_info"]
    sensor_name = config["sensor_info"]["sensor_name"] 
    sensor_full_name = config["sensor_info"]["sensor_full_name"] 
    sensor_id = config["sensor_info"]["sensor_id"] 

    print('sensor_name = ', sensor_name)
    print('sensor_full_name = ', sensor_full_name)
    print('sensor_id = ', sensor_id)

    bufrfile = cycle_type + '.t' + hh + 'z.'+data_type + '.tm00.' + data_format 
    DATA_PATH = dump_dir + '/' + cycle_type + '.' + yyyymmdd  +'/' + hh + '/' + bufrfile

    # ============================================
    # Make the QuerySet for all the data we want
    # ============================================
    start_time = time.time()

    print('Making QuerySet ...')
#   q = bufr.QuerySet()
#   q = bufr.QuerySet(['NC005030', 'NC005031', 'NC005032', 'NC005034', 'NC005039'])
    q = bufr.QuerySet(subsets)

    # MetaData
    q.add('latitude', '*/CLATH')
    q.add('longitude', '*/CLONH')
    q.add('satelliteId', '*/SAID') 
    q.add('year', '*/YEAR') 
    q.add('month', '*/MNTH') 
    q.add('day', '*/DAYS') 
    q.add('hour', '*/HOUR') 
    q.add('minute', '*/MINU') 
    q.add('second', '*/SECO') 
    q.add('sensorZenithAngle', '*/SAZA') 
    q.add('sensorCentralFrequency', '*/SCCF') 
    q.add('pressure', '*/PRLC[1]') 

    # Processing Center
    q.add('dataProviderOrigin', '*/OGCE[1]') 
#   q.add('windGeneratingApplication', '*/AMVQIC/GNAPS') 

#   # Quality Infomation (Quality Inficator and Expecter Error)
#   q.add('windPercentConfidence', '*/AMVQIC/PCCF') 
    q.add('qualityInformationWithoutForecast', '*/AMVQIC{2}/PCCF') 
    q.add('expectedError', '*/AMVQIC{4}/PCCF') 

#   # Derived Motion Wind (DMW) Intermediate Vectors - Coefficient of Variation 
#   q.add('coefficientOfVariation', '*/AMVIVR/CVWD') 
    q.add('coefficientOfVariation', '*/AMVIVR{1}/CVWD') 

    # Wind Retrieval Method Information
    q.add('windComputationMethod', '*/SWCM') 
    q.add('windHeightAssignMethod', '*/EHAM') 

    # ObsValue
    q.add('windDirection', '*/WDIR')
    q.add('windSpeed', '*/WSPD')

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
    satid = r.get('satelliteId')
    year = r.get('year')
    month = r.get('month')
    day = r.get('day')
    hour = r.get('hour')
    minute = r.get('minute')
    second = r.get('second')
    lat = r.get('latitude')
    lon = r.get('longitude')
    satzenang = r.get('sensorZenithAngle')
    pressure = r.get('pressure', type='float')
    chanfreq = r.get('sensorCentralFrequency', type='float')

    print(' ... Executing QuerySet: get metadata: processing center ...')
    # Processing Center
    ogce  = r.get('dataProviderOrigin')

    print(' ... Executing QuerySet: get metadata: data quality information ...')
    # Quality Information 
    qifn = r.get('qualityInformationWithoutForecast', type='float')
    ee = r.get('expectedError', type='float')

    print(' ... Executing QuerySet: get metadata: intermediate vector information ...')
    # Derived Motion Wind (DMW) Intermediate Vectors 
    cvwd = r.get('coefficientOfVariation')

    print(' ... Executing QuerySet: get metadata: wind retrieval method ...')
    # Wind Retrieval Method Information
    swcm = r.get('windComputationMethod')
    eham = r.get('windHeightAssignMethod')

    print(' ... Executing QuerySet: get obsvalue: wind direction and speed ...')
    # ObsValue
    # Wind direction and Speed
    wdir = r.get('windDirection', type='float')
    wspd = r.get('windSpeed')

    print(' ... Executing QuerySet: get datatime: observation time ...')
    # DateTime: seconds since Epoch time
    # IODA has no support for numpy datetime arrays dtype=datetime64[s]
    timestamp = r.get_datetime('year', 'month', 'day', 'hour', 'minute', 'second').astype(np.int64)

    print(' ... Executing QuerySet: Done!')

    print(' ... Executing QuerySet: Check BUFR variable generic dimension and type ...')
    # Check BUFR variable generic dimension and type
    print('     timestamp shape = ', timestamp.shape)
    print('     satid     shape = ', satid.shape)
    print('     lon       shape = ', lon.shape)
    print('     chanfreq  shape = ', chanfreq.shape)
    print('     swcm      shape = ', swcm.shape)

    print('     ogce      shape = ', ogce.shape)
    print('     qifn      shape = ', qifn.shape)
    print('     ee        shape = ',   ee.shape)

    print('     cvwd      shape = ', cvwd.shape)

    print('     eham      shape = ', eham.shape)
    print('     pressure  shape = ', pressure.shape)
    print('     wdir      shape = ', wdir.shape)
    print('     wspd      shape = ', wspd.shape)

    print('     timestamp type  = ', timestamp.dtype)
    print('     satid     type  = ', satid.dtype)
    print('     lon       type  = ', lon.dtype)
    print('     chanfreq  type  = ', chanfreq.dtype)
    print('     swcm      type  = ', swcm.dtype)
    print('     satzenang type  = ', satzenang.dtype)

    print('     ogce      type  = ', ogce.dtype)
    print('     qifn      type  = ', qifn.dtype)
    print('     ee        type  = ',   ee.dtype)

    print('     cvwd      type  = ', cvwd.dtype)

    print('     eham      type  = ', eham.dtype)
    print('     pressure  type  = ', pressure.dtype)
    print('     wdir      type  = ', wdir.dtype)
    print('     wspd      type  = ', wspd.dtype)

    # Global variables declaration
    # Set global fill values
    float32_fill_value = satzenang.fill_value
    int32_fill_value = satid.fill_value
    int64_fill_value = timestamp.fill_value.astype(np.int64)
    print('     float32_fill_value  = ', float32_fill_value)
    print('     int32_fill_value    = ', int32_fill_value)
    print('     int64_fill_value    = ', int64_fill_value)

    end_time = time.time()
    running_time = end_time - start_time
    print('Running time for executing QuerySet to get ResultSet : ', running_time, 'seconds')

    # =========================
    # Create derived variables
    # =========================
    start_time = time.time()

    print('Creating derived variables - wind components (uob and vob) ...')

    uob, vob = Compute_WindComponents_from_WindDirection_and_WindSpeed(wdir, wspd)

    print('     uob min/max = ', uob.min(), uob.max())
    print('     vob min/max = ', vob.min(), vob.max())

    obstype = Get_ObsType(swcm, chanfreq)

    print('     obstype min/max = ', obstype.min(), obstype.max())

    print('     Check drived variables type ... ')
    print('     uob      type = ', uob.dtype)
    print('     vob      type = ', vob.dtype)
    print('     obstype  type = ', obstype.dtype)

    height  = np.full_like(pressure, fill_value=pressure.fill_value, dtype=np.float32)
    stnelev = np.full_like(pressure, fill_value=pressure.fill_value, dtype=np.float32)

    end_time = time.time()
    running_time = end_time - start_time
    print('Running time for creating derived variables : ', running_time, 'seconds')

    # =====================================
    # Split output based on satellite id
    # Create IODA ObsSpace
    # Write IODA output
    # =====================================
    print('Split data based on satellite id, Create IODA ObsSpace and Write IODA output')

    # Find unique satellite identifiers in data to process
    unique_satids = np.unique(satid)
    print(' ... Number of Unique satellite identifiers: ', len(unique_satids))
    print(' ... Unique satellite identifiers: ', unique_satids)

    print(' ... Loop through unique satellite identifier ... : ', unique_satids)
    for sat in unique_satids.tolist():
        print(' ... ... Processing output for satid ...  : ', sat)
        start_time = time.time()

        matched = False
        for satellite_info in satellite_info_array:
            if (satellite_info["satellite_id"] == sat):
                matched = True
                satellite_id  = satellite_info["satellite_id"]
                satellite_name = satellite_info["satellite_name"]
                satinst = sensor_name.lower()+'_'+satellite_name.lower()
                print(' ... Split data for', satinst, 'satid = ', sat)

        if matched:

            # Define a boolean mask to subset data from the original data object
            mask = satid == sat
            # MetaData
            lon2 = lon[mask]
            lat2 = lat[mask]
            timestamp2 = timestamp[mask]
            satid2 = satid[mask]
            satzenang2 = satzenang[mask]
            chanfreq2 = chanfreq[mask]
            obstype2 = obstype[mask]
            pressure2 = pressure[mask]
            height2 = height[mask]
            stnelev2 = stnelev[mask]

            # Processing Center
            ogce2 = ogce[mask]

            # QC Info
            cvwd2 = cvwd[mask]
            qifn2 = qifn[mask]
            ee2 = ee[mask]

            # Method
            swcm2 = swcm[mask]
            eham2 = eham[mask]

            # ObsValue
            wdir2 = wdir[mask]
            wspd2 = wspd[mask]
            uob2 = uob[mask]
            vob2 = vob[mask]

            # Check unique observation time
            unique_timestamp2 = np.unique(timestamp2)
            print(' ... Number of Unique observation timestamp: ', len(unique_timestamp2))
            print(' ... Unique observation timestamp: ', unique_timestamp2)

            print(' ... Check drived variables type for subset ... ')
            print('     uob2       type  = ', uob.dtype)
            print('     vob2       type  = ', vob.dtype)
            print('     wdir2      type  = ', wdir2.dtype)
            print('     wspd2      type  = ', wspd2.dtype)
            print('     pressure2  type  = ', pressure2.dtype)
            print('     height2    type  = ', height2.dtype)
            print('     stnelev2   type  = ', stnelev2.dtype)
            print('     qifn2      type  = ', qifn2.dtype)
            print('     ee         type  = ', ee.dtype)
            print('     cvwd2      type  = ', cvwd2.dtype)
            print('     ogce2      type  = ', ogce2.dtype)
            print('     obstype2   type  = ', obstype2.dtype)

            print('     qifn2      shape = ', qifn2.shape)
            print('     ee2        shape = ', ee2.shape)
            print('     cvwd2      shape = ', cvwd2.shape)

            print(' ... Create ObsSpae for', satinst, 'satid = ', sat)
            # Create the dimensions
            dims = {
               'Location'   : np.arange(0, wdir2.shape[0]),
#              'Confidence' : np.arange(0, pccf2.shape[1]),
#              'Vector'     : np.arange(0, tcov2.shape[1]),
            }
    
            # Create IODA ObsSpace
            iodafile = cycle_type + '.t' + hh + 'z.' + data_type + '.'+ satinst + '.tm00.nc'
            OUTPUT_PATH = ioda_dir + '/' + cycle + '/' + iodafile
            print(' ... ... Create output file ...', OUTPUT_PATH)
            obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)

            # Create Global attributes
            print(' ... ... Create global attributes')
            obsspace.write_attr('sensor', sensor_id)
            obsspace.write_attr('platform', satellite_id)
            obsspace.write_attr('dataProviderOrigin', data_provider)
            obsspace.write_attr('description', data_description)

            # Create IODA variables
            print(' ... ... Create variables: name, type, units, and attributes')
            # Longitude
            obsspace.create_var('MetaData/longitude', dtype=lon2.dtype, fillval=lon2.fill_value) \
                .write_attr('units', 'degrees_east') \
                .write_attr('valid_range', np.array([-180, 180], dtype=np.float32)) \
                .write_attr('long_name', 'Longitude') \
                .write_data(lon2)

            # Latitude 
            obsspace.create_var('MetaData/latitude', dtype=lat.dtype, fillval=lat2.fill_value) \
                .write_attr('units', 'degrees_north') \
                .write_attr('valid_range', np.array([-90, 90], dtype=np.float32)) \
                .write_attr('long_name', 'Latitude') \
                .write_data(lat2)

            # Datetime
            obsspace.create_var('MetaData/dateTime', dtype=np.int64, fillval=int64_fill_value) \
                .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
                .write_attr('long_name', 'Datetime') \
                .write_data(timestamp2)

            # Satellite Identifier
            obsspace.create_var('MetaData/satelliteIdentifier', dtype=satid2.dtype, fillval=satid2.fill_value) \
                .write_attr('long_name', 'Satellite Identifier') \
                .write_data(satid2)

            # Sensor Zenith Angle
            obsspace.create_var('MetaData/sensorZenithAngle', dtype=satzenang2.dtype, fillval=satzenang2.fill_value) \
                .write_attr('units', 'degree') \
                .write_attr('valid_range', np.array([0, 90], dtype=np.float32)) \
                .write_attr('long_name', 'Sensor Zenith Angle') \
                .write_data(satzenang2)

            # Sensor Centrall Frequency
            obsspace.create_var('MetaData/sensorCentralFrequency', dtype=chanfreq2.dtype, fillval=chanfreq2.fill_value) \
                .write_attr('units', 'Hz') \
                .write_attr('long_name', 'Satellite Channel Center Frequency') \
                .write_data(chanfreq2)

            # Data Provider
            obsspace.create_var('MetaData/dataProviderOrigin', dtype=ogce2.dtype, fillval=ogce2.fill_value) \
                .write_attr('long_name', 'Identification of Originating/Generating Center') \
                .write_data(ogce2)

            # Quality: Percent Confidence - Quality Information Without Forecast
            obsspace.create_var('MetaData/qualityInformationWithoutForecast', dtype=qifn2.dtype, fillval=qifn2.fill_value) \
                .write_attr('long_name', 'Quality Information Without Forecast') \
                .write_data(qifn2)

            # Quality: Percent Confidence - Expected Error
            obsspace.create_var('MetaData/expectedError', dtype=ee2.dtype, fillval=ee2.fill_value) \
                .write_attr('units', 'm/s') \
                .write_attr('long_name', 'Expected Error') \
                .write_data(ee2)

            # Derived Motion Wind (DMW) Intermediate Vectors - Coefficient of Variation
            obsspace.create_var('MetaData/coefficientOfVariation', dtype=cvwd2.dtype, fillval=cvwd2.fill_value) \
                .write_attr('long_name', 'Coefficient of Variation') \
                .write_data(cvwd2)

            # Wind Computation Method
            obsspace.create_var('MetaData/windComputationMethod', dtype=swcm2.dtype, fillval=swcm2.fill_value) \
                .write_attr('long_name', 'Satellite-derived Wind Computation Method') \
                .write_data(swcm2)

            # Wind Height Assignment Method
            obsspace.create_var('MetaData/windHeightAssignMethod', dtype=eham2.dtype, fillval=eham2.fill_value) \
                .write_attr('long_name', 'Wind Height Assignment Method') \
                .write_data(eham2)

            # ObsType based on computation method/spectral band
            obsspace.create_var('ObsType/windEastward', dtype=obstype2.dtype, fillval=swcm2.fill_value) \
                .write_attr('long_name', 'Observation Type based on Satellite-derived Wind Computation Method and Spectral Band') \
                .write_data(obstype2)

            # ObsType based on computation method/spectral band
            obsspace.create_var('ObsType/windNorthward', dtype=obstype2.dtype, fillval=swcm2.fill_value) \
                .write_attr('long_name', 'Observation Type based on Satellite-derived Wind Computation Method and Spectral Band') \
                .write_data(obstype2)

            # Pressure
            obsspace.create_var('MetaData/pressure', dtype=pressure2.dtype, fillval=pressure2.fill_value) \
                .write_attr('units', 'pa') \
                .write_attr('long_name', 'Pressure') \
                .write_data(pressure2)

            # Height (mimic prepbufr)
            obsspace.create_var('MetaData/height', dtype=height2.dtype, fillval=height2.fill_value) \
                .write_attr('units', 'm') \
                .write_attr('long_name', 'Height of Observation') \
                .write_data(height2)

            # Station Elevation (mimic prepbufr)
            obsspace.create_var('MetaData/stationElevation', dtype=stnelev2.dtype, fillval=stnelev2.fill_value) \
                .write_attr('units', 'm') \
                .write_attr('long_name', 'Station Elevation') \
                .write_data(stnelev2)

            # Wind Speed
            obsspace.create_var('ObsValue/windSpeed', dtype=wspd2.dtype, fillval=wspd2.fill_value) \
                .write_attr('units', 'm s-1') \
                .write_attr('long_name', 'Wind Speed') \
                .write_data(wspd2)

            # Wind Direction
            obsspace.create_var('ObsValue/windDirection', dtype=wdir2.dtype, fillval=wdir2.fill_value) \
                .write_attr('units', 'degrees') \
                .write_attr('long_name', 'Wind Direction') \
                .write_data(wdir2)

            # U-Wind Component
            obsspace.create_var('ObsValue/windEastward', dtype=uob2.dtype, fillval=wspd2.fill_value) \
                .write_attr('units', 'm s-1') \
                .write_attr('long_name', 'Eastward Wind Component') \
                .write_data(uob2)

            # V-Wind Component
            obsspace.create_var('ObsValue/windNorthward', dtype=vob2.dtype, fillval=wspd2.fill_value) \
                .write_attr('units', 'm s-1') \
                .write_attr('long_name', 'Northward Wind Component') \
                .write_data(vob2)

            end_time = time.time()
            running_time = end_time - start_time
            print('Running time for splitting and output IODA for', satinst, running_time, 'seconds')

        else:
            print("Do not find this satellite id in the configuration: satid = ", sat)

    print("All Done!")

if __name__ == '__main__':

    start_time = time.time()

    with open("bufr2ioda_ncep_satwind_amv_goes.json", "r") as json_file:
       config = json.load(json_file)

    print('emily checking config = ', config)

    bufr_to_ioda(config)

    end_time = time.time()
    running_time = end_time -start_time
    print('Total running time: ', running_time, 'seconds')



