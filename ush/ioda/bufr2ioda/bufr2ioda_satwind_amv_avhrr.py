#!/usr/bin/env python3
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

# ====================================================================
# Satellite Winds (AMV) BUFR dump file for AVHRR
# ====================================================================
# Subset    |  Spectral Band              |  Code (002023) |  ObsType
# --------------------------------------------------------------------
# NC005080  |    IRLW  (Freq < 5E+13)     |    Method 1    |   244
# ====================================================================

# Define and initialize  global variables
global float32_fill_value
global int32_fill_value
global int64_fill_value

float32_fill_value = np.float32(0)
int32_fill_value = np.int32(0)
int64_fill_value = np.int64(0)


def Compute_WindComponents_from_WindDirection_and_WindSpeed(wdir, wspd):

    uob = (-wspd * np.sin(np.radians(wdir))).astype(np.float32)
    vob = (-wspd * np.cos(np.radians(wdir))).astype(np.float32)

    return uob, vob


def Get_ObsType(swcm, chanfreq):

    obstype = swcm.copy()

    # Use numpy vectorized operations
    obstype = np.where(swcm == 1, 244, obstype)  # IRLW

    if not np.any(np.isin(obstype, [244])):
        raise ValueError("Error: Unassigned ObsType found ... ")

    return obstype


def bufr_to_ioda(config, logger):

    subsets = config["subsets"]
    logger.debug(f"Checking subsets = {subsets}")

    # Get parameters from configuration
    subsets = config["subsets"]
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

    # Get derived parameters
    yyyymmdd = cycle[0:8]
    hh = cycle[8:10]
    reference_time = datetime.strptime(cycle, "%Y%m%d%H")
    reference_time = reference_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    # General informaton
    converter = 'BUFR to IODA Converter'
    process_level = 'Level-2'
    platform_description = 'NOAA-15/18/19'
    sensor_description = 'Advanced Very High Resolution Radiometer'

    logger.info(f'sensor_name = {sensor_name}')
    logger.info(f'sensor_full_name = {sensor_full_name}')
    logger.info(f'sensor_id = {sensor_id}')
    logger.info(f'reference_time = {reference_time}')

    bufrfile = f"{cycle_type}.t{hh}z.{data_type}.tm00.{data_format}"
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

    # MetaData
    q.add('latitude', '*/CLAT')
    q.add('longitude', '*/CLON')
    q.add('satelliteId', '*/SAID')
    q.add('year', '*/YEAR')
    q.add('month', '*/MNTH')
    q.add('day', '*/DAYS')
    q.add('hour', '*/HOUR')
    q.add('minute', '*/MINU')
    q.add('second', '*/SECO')
    q.add('satelliteZenithAngle', '*/SAZA')
    q.add('sensorCentralFrequency', '*/SCCF')
    q.add('pressure', '*/PRLC')

    # Processing Center
    q.add('dataProviderOrigin', '*/OGCE')
    q.add('windGeneratingApplication', '*/GQCPRMS[1]/GNAP')

#   # Quality Infomation (Quality Indicator w/o forecast)
    q.add('qualityInformationWithoutForecast', '*/GQCPRMS[1]/PCCF')

    # Wind Retrieval Method Information
    q.add('windComputationMethod', '*/SWCM')

    # ObsValue
    q.add('windDirection', '*/WDIR')
    q.add('windSpeed', '*/WSPD')

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f'Processing time for making QuerySet : {running_time} seconds')

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
    satzenang = r.get('satelliteZenithAngle')
    pressure = r.get('pressure', type='float')
    chanfreq = r.get('sensorCentralFrequency', type='float')

    # Processing Center
    ogce = r.get('dataProviderOrigin')
    ga = r.get('windGeneratingApplication')

    # Quality Information
    qi = r.get('qualityInformationWithoutForecast', type='float')
    # For NOAA-15/18/19 AVHRR data, qi w/o forecast (qifn) is packaged in same
    # vector of qi with ga = 1 (EUMETSAT QI without forecast), and EE is
    # packaged in same vector of qi with ga=4 (Estimated Error (EE) in m/s
    # converted to a percent confidence)shape (4,nobs). Must conduct a
    # search and extract the correct vector for gnap and qi
    # 1. Find dimension-sizes of ga and qi (should be the same!)
    gDim1, gDim2 = np.shape(ga)
    qDim1, qDim2 = np.shape(qi)
    logger.info(f'Generating Application and Quality Information SEARCH:')
    logger.info(f'Dimension size of GNAP ({gDim1},{gDim2})')
    logger.info(f'Dimension size of PCCF ({qDim1},{qDim2})')
    # 2. Initialize gnap and qifn as None, and search for dimension of
    #    ga with values of 1. If the same column exists for qi, assign
    #    gnap to ga[:,i] and qifn to qi[:,i], else raise warning that no
    #    appropriate GNAP/PCCF combination was found
    gnap = None
    qifn = None
    for i in range(gDim2):
        if np.unique(ga[:, i].squeeze()) == 1:
            if i <= qDim2:
                logger.info(f'GNAP/PCCF found for column {i}')
                gnap = ga[:, i].squeeze()
                qifn = qi[:, i].squeeze()
            else:
                logger.info(f'ERROR: GNAP column {i} outside of PCCF dimension {qDim2}')
    if (gnap is None) & (qifn is None):
        logger.info(f'ERROR: GNAP == 1 NOT FOUND OR OUT OF PCCF DIMENSION-RANGE, WILL FAIL!')
    # If EE is needed, key search on np.unique(ga[:,i].squeeze()) == 4 instead

    # Wind Retrieval Method Information
    swcm = r.get('windComputationMethod')

    # ObsValue
    # Wind direction and Speed
    wdir = r.get('windDirection', type='float')
    wspd = r.get('windSpeed')

    # DateTime: seconds since Epoch time
    # IODA has no support for numpy datetime arrays dtype=datetime64[s]
    timestamp = r.get_datetime('year', 'month', 'day', 'hour', 'minute', 'second').astype(np.int64)

    # Check BUFR variable generic dimension and type

    # Global variables declaration
    # Set global fill values
    float32_fill_value = satzenang.fill_value
    int32_fill_value = satid.fill_value
    int64_fill_value = timestamp.fill_value.astype(np.int64)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f'Processing time for executing QuerySet to get ResultSet : {running_time} seconds')

    # =========================
    # Create derived variables
    # =========================
    start_time = time.time()

    logger.info('Creating derived variables')
    logger.debug('Creating derived variables - wind components (uob and vob)')

    uob, vob = Compute_WindComponents_from_WindDirection_and_WindSpeed(wdir, wspd)

    logger.debug(f'   uob min/max = {uob.min()} {uob.max()}')
    logger.debug(f'   vob min/max = {vob.min()} {vob.max()}')

    obstype = Get_ObsType(swcm, chanfreq)

    height = np.full_like(pressure, fill_value=pressure.fill_value, dtype=np.float32)
    stnelev = np.full_like(pressure, fill_value=pressure.fill_value, dtype=np.float32)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f'Processing time for creating derived variables : {running_time} seconds')

    # =====================================
    # Split output based on satellite id
    # Create IODA ObsSpace
    # Write IODA output
    # =====================================
    logger.info('Create IODA ObsSpace and Write IODA output based on satellite ID')

    # Find unique satellite identifiers in data to process
    unique_satids = np.unique(satid)
    logger.info(f'Number of Unique satellite identifiers: {len(unique_satids)}')
    logger.info(f'Unique satellite identifiers: {unique_satids}')

    logger.debug(f'Loop through unique satellite identifier {unique_satids}')
    total_ob_processed = 0
    for sat in unique_satids.tolist():
        start_time = time.time()

        matched = False
        for satellite_info in satellite_info_array:
            if (satellite_info["satellite_id"] == sat):
                matched = True
                satellite_id = satellite_info["satellite_id"]
                satellite_name = satellite_info["satellite_name"]
                satinst = sensor_name.lower()+'_'+satellite_name.lower()
                logger.debug(f'Split data for {satinst} satid = {sat}')

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
            qifn2 = qifn[mask]

            # Method
            swcm2 = swcm[mask]

            # ObsValue
            wdir2 = wdir[mask]
            wspd2 = wspd[mask]
            uob2 = uob[mask]
            vob2 = vob[mask]

            # Timestamp Range
            timestamp2_min = datetime.fromtimestamp(timestamp2.min())
            timestamp2_max = datetime.fromtimestamp(timestamp2.max())

            # Check unique observation time
            unique_timestamp2 = np.unique(timestamp2)
            logger.debug(f'Processing output for satid {sat}')

            # Create the dimensions
            dims = {
                'Location': np.arange(0, wdir2.shape[0])
            }

            # Create IODA ObsSpace
            iodafile = f"{cycle_type}.t{hh}z.{data_type}.{satinst}.tm00.nc"
            OUTPUT_PATH = os.path.join(ioda_dir, iodafile)
            logger.info(f'Create output file : {OUTPUT_PATH}')
            obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)

            # Create Global attributes
            logger.debug('Write global attributes')
            obsspace.write_attr('Converter', converter)
            obsspace.write_attr('sourceFiles', bufrfile)
            obsspace.write_attr('dataProviderOrigin', data_provider)
            obsspace.write_attr('description', data_description)
            obsspace.write_attr('datetimeReference', reference_time)
            obsspace.write_attr('datetimeRange', [str(timestamp2_min), str(timestamp2_max)])
            obsspace.write_attr('sensor', sensor_id)
            obsspace.write_attr('platform', satellite_id)
            obsspace.write_attr('platformCommonName', satellite_name)
            obsspace.write_attr('sensorCommonName', sensor_name)
            obsspace.write_attr('processingLevel', process_level)
            obsspace.write_attr('platformLongDescription', platform_description)
            obsspace.write_attr('sensorLongDescription', sensor_description)

            # Create IODA variables
            logger.debug('Write variables: name, type, units, and attributes')
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
            obsspace.create_var('MetaData/satelliteZenithAngle', dtype=satzenang2.dtype, fillval=satzenang2.fill_value) \
                .write_attr('units', 'degree') \
                .write_attr('valid_range', np.array([0, 90], dtype=np.float32)) \
                .write_attr('long_name', 'Satellite Zenith Angle') \
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

            # Wind Computation Method
            obsspace.create_var('MetaData/windComputationMethod', dtype=swcm2.dtype, fillval=swcm2.fill_value) \
                .write_attr('long_name', 'Satellite-derived Wind Computation Method') \
                .write_data(swcm2)

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

            # U-Wind Component
            obsspace.create_var('ObsValue/windEastward', dtype=uob2.dtype, fillval=uob2.fill_value) \
                .write_attr('units', 'm s-1') \
                .write_attr('long_name', 'Eastward Wind Component') \
                .write_data(uob2)

            # V-Wind Component
            obsspace.create_var('ObsValue/windNorthward', dtype=vob2.dtype, fillval=vob2.fill_value) \
                .write_attr('units', 'm s-1') \
                .write_attr('long_name', 'Northward Wind Component') \
                .write_data(vob2)

            end_time = time.time()
            running_time = end_time - start_time
            total_ob_processed += len(satid2)
            logger.debug(f'Number of observation processed : {len(satid2)}')
            logger.debug(f'Processing time for splitting and output IODA for {satinst} : {running_time} seconds')

        else:
            logger.info(f"Do not find this satellite id in the configuration: satid = {sat}")

    logger.info("All Done!")
    logger.info(f'Total number of observation processed : {total_ob_processed}')


if __name__ == '__main__':

    start_time = time.time()

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input JSON configuration', required=True)
    parser.add_argument('-v', '--verbose', help='print debug logging information',
                        action='store_true')
    args = parser.parse_args()

    log_level = 'DEBUG' if args.verbose else 'INFO'
    logger = Logger('BUFR2IODA_satwind_amv_ahi.py', level=log_level, colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Total running time: {running_time} seconds")
