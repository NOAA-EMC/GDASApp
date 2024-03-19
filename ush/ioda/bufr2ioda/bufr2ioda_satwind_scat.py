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

# ==============================================================================================
# Subset    |  Description                                              |  PrepBUFR Report Type
# ----------------------------------------------------------------------------------------------
# NC012122  |  Level-2 ocean surface wind vector retrievals and         |  290
#           |  derived wind components from the Advanced Scatterometer  |
#           |  (ASCAT) on MetOp satellites at 50-km sampling resolution |
# ==============================================================================================


def Compute_WindComponents_from_WindDirection_and_WindSpeed(wdir, wspd):

    # Initialize
    uob = np.full_like(wspd, wspd.fill_value)
    vob = np.full_like(wspd, wspd.fill_value)

    # Compute wind components from wind speed and direction
    uob = -wspd * np.sin(np.radians(wdir))
    vob = -wspd * np.cos(np.radians(wdir))

    return uob, vob


def bufr_to_ioda(config, logger):

    subsets = config['subsets']
    logger.debug(f'Checking subsets = {subsets}')

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
    platform_description = 'EUMETSAT Polar System operaring since 2006 from 837 km altitude in sunsychronous orbits at 09:30'
    sensor_description = 'Active sensor: aperture radar operating at 5.255 GHz (c-band); side looking both left and right; \
                         3 verically polarized antennas on each side'

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

    # Quality
    q.add('qualityFlags', '*/WVCQ')

    # ObsValue
    q.add('windDirectionAt10M', '*/WD10')
    q.add('windSpeedAt10M', '*/WS10')

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

    # Quality Information
    wvcq = r.get('qualityFlags')

    # ObsValue
    # 10-m Wind direction and Speed
    wdir = r.get('windDirectionAt10M', type='float')
    wspd = r.get('windSpeedAt10M')

    # DateTime: seconds since Epoch time
    # IODA has no support for numpy datetime arrays dtype=datetime64[s]
    timestamp = r.get_datetime('year', 'month', 'day', 'hour', 'minute', 'second').astype(np.int64)

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f'Processing time for executing QuerySet to get ResultSet : {running_time} seconds')

    # =========================
    # Create derived variables
    # =========================
    start_time = time.time()

    logger.info('Creating derived variables')
    logger.debug('Creating derived variables - wind components (uob and vob)')

    uob, vob = Compute_WindComponents_from_WindDirection_and_WindSpeed(wdir, wspd)

#   logger.debug(f'   uob min/max = {uob.min()}, {uob.max()}')
#   logger.debug(f'   vob min/max = {vob.min()}, {vob.max()}')

    logger.debug('Creating derived variables - GSI ObsType')
    gsi_obstype = 290
    obstype = np.full_like(satid, gsi_obstype)

    logger.debug('Creating derived variables - observation pressure')
    pressure = np.full_like(lat, 101000.)

    logger.debug('Creating derived variables - observation height')
    height = np.full_like(lat, 10.)

    logger.debug('Creating derived variables - station elevation')
    stnelv = np.full_like(lat, 0.)

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f'Processing time for creating derived variables : {running_time} seconds')

    # =====================================
    # Split output based on satellite id
    # Create IODA ObsSpace
    # Write IODA output
    # =====================================
    logger.info('Create IODA ObsSpace and Write IODA output based on satellite ID')

    # Find unique satellite identifiers in data to process
    unique_satids = np.unique(satid)
    logger.info(f'Number of Unique satellite identifiers : {len(unique_satids)}')
    logger.info(f'Unique satellite identifiers : {unique_satids}')

    logger.debug(f'Loop through unique satellite identifier : {unique_satids}')
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

        if matched:

            # Define a boolean mask to subset data from the original data object
            mask = satid == sat
            # MetaData
            lon2 = lon[mask]
            lat2 = lat[mask]
            satid2 = satid[mask]
            timestamp2 = timestamp[mask]
            pressure2 = pressure[mask]
            height2 = height[mask]
            stnelv2 = stnelv[mask]
            obstype2 = obstype[mask]

            # QC Info
            wvcq2 = wvcq[mask]

            # ObsValue
            wdir2 = wdir[mask]
            wspd2 = wspd[mask]
            uob2 = uob[mask]
            vob2 = vob[mask]

            # Timestamp Range
            timestamp2_min = datetime.fromtimestamp(timestamp2.min())
            timestamp2_max = datetime.fromtimestamp(timestamp2.max())

            # Check unique observation time
            unique_timestamp = np.unique(timestamp)
            logger.debug(f"Processing output for satid {sat}")

            # Create the dimensions
            dims = {
                'Location': np.arange(0, wdir2.shape[0]),
            }

            # Create IODA ObsSpace
            iodafile = f"{cycle_type}.t{hh}z.{data_type}.{satinst}.tm00.nc"
            OUTPUT_PATH = os.path.join(ioda_dir, iodafile)
            logger.info(f"Create output file : {OUTPUT_PATH}")
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
            obsspace.create_var('MetaData/latitude', dtype=lat2.dtype, fillval=lat2.fill_value) \
                .write_attr('units', 'degrees_north') \
                .write_attr('valid_range', np.array([-90, 90], dtype=np.float32)) \
                .write_attr('long_name', 'Latitude') \
                .write_data(lat2)

            # Datetime
            obsspace.create_var('MetaData/dateTime', dtype=timestamp2.dtype, fillval=timestamp2.fill_value) \
                .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
                .write_attr('long_name', 'Unix Epoch') \
                .write_data(timestamp2)

            # Satellite Identifier
            obsspace.create_var('MetaData/satelliteIdentifier', dtype=satid2.dtype, fillval=satid2.fill_value) \
                .write_attr('long_name', 'Satellite Identifier') \
                .write_data(satid2)

            # Quality: Wind Vector Cell Quality
            obsspace.create_var('MetaData/qualityFlags', dtype=wvcq2.dtype, fillval=wvcq2.fill_value) \
                .write_attr('long_name', 'Wind Vector Cell Quality') \
                .write_data(wvcq2)

            # Pressure
            obsspace.create_var('MetaData/pressure', dtype=pressure2.dtype, fillval=pressure2.fill_value) \
                .write_attr('units', 'pa') \
                .write_attr('long_name', 'Pressure') \
                .write_data(pressure2)

            # Height
            obsspace.create_var('MetaData/height', dtype=height2.dtype, fillval=height2.fill_value) \
                .write_attr('units', 'm') \
                .write_attr('long_name', 'Height of Observation') \
                .write_data(height2)

            # Station Elevation
            obsspace.create_var('MetaData/stationElevation', dtype=stnelv2.dtype, fillval=stnelv2.fill_value) \
                .write_attr('units', 'm') \
                .write_attr('long_name', 'Station Elevation') \
                .write_data(stnelv2)

            # ObsType based on sensor type
            obsspace.create_var('ObsType/windEastward', dtype=obstype2.dtype, fillval=obstype2.fill_value) \
                .write_attr('long_name', 'PrepBUFR Report Type') \
                .write_data(obstype2)

            # ObsType based on sensor type
            obsspace.create_var('ObsType/windNorthward', dtype=obstype2.dtype, fillval=obstype2.fill_value) \
                .write_attr('long_name', 'PrepBUFR Report Type') \
                .write_data(obstype2)

            # U-Wind Component
            obsspace.create_var('ObsValue/windEastward', dtype=uob2.dtype, fillval=uob2.fill_value) \
                .write_attr('units', 'm s-1') \
                .write_attr('long_name', 'Eastward Wind Component at 10 Meters') \
                .write_data(uob2)

            # V-Wind Component
            obsspace.create_var('ObsValue/windNorthward', dtype=vob2.dtype, fillval=vob2.fill_value) \
                .write_attr('units', 'm s-1') \
                .write_attr('long_name', 'Northward Wind Component at 10 Meters') \
                .write_data(vob2)

            end_time = time.time()
            running_time = end_time - start_time
            total_ob_processed += len(satid2)
            logger.debug(f'Number of observation processed : {len(satid2)}')
            logger.debug(f'Processing time for splitting and output IODA for {satinst} : {running_time} seconds')

        else:
            logger.info(f'Do not find this satellite id in the configuration: satid = {sat}')

    logger.info('All Done!')
    logger.info(f'Total number of observation processed : {total_ob_processed}')


if __name__ == '__main__':

    start_time = time.time()

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input JSON configuration', required=True)
    parser.add_argument('-v', '--verbose', help='print debug logging information',
                        action='store_true')
    args = parser.parse_args()

    log_level = 'DEBUG' if args.verbose else 'INFO'
    logger = Logger('BUFR2IODA_satwind_scat.py', level=log_level, colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f'Total processing time : {running_time} seconds')
