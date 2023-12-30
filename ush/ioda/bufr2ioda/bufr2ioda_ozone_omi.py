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

# =======================================================================
# Subset    |  Description                                              |
# -----------------------------------------------------------------------
# NC008013  |  Level-2 total column ozone retrievals from OMI on Earth  |
#           |  Observation System - Aura                                |
# =======================================================================


def bufr_to_ioda(config, logger):

    # ==================================
    # Get parameters from configuration
    # ==================================
    subsets = config["subsets"]
    source = config["source"]
    data_format = config["data_format"]
    data_type = config["data_type"]
    data_description = config["data_description"]
    data_provider = config["data_provider"]
    cycle_type = config["cycle_type"]
    dump_dir = config["dump_directory"]
    ioda_dir = config["ioda_directory"]
    ioda_type = config["ioda_type"]
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

    # General informaton for global attribute
    converter = 'BUFR Converter'
    process_level = config["process_level"]
    platform_description = config["platform_description"]
    sensor_description = config["sensor_description"]

    logger.info(f'Processing {data_description}')
    logger.info(f'reference_time = {reference_time}')

    bufrfile = f"{cycle_type}.t{hh}z.{data_type}.tm00.{data_format}"
    DATA_PATH = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}", str(hh), 'atmos', bufrfile)

    # ============================================
    # Make the QuerySet for all the data we want
    # ============================================
    start_time = time.time()

    logger.info('Making QuerySet')
    q = bufr.QuerySet()

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
    q.add('solarZenithAngle', '*/SOZA')
    q.add('sensorScanPosition', '*/FOVN')

    # Quality
    q.add('bestOzoneAlgorithmFlag', '*/AFBO')
    q.add('totalOzoneQualityFlag', '*/TOQF')
    q.add('totalOzoneQualityCode', '*/TOQC')

    # ObsValue
    q.add('ozoneTotal', '*/OZON')

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
        r = f.execute(q)

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
    solzenang = r.get('solarZenithAngle')
    scanpos = r.get('sensorScanPosition')

    # Quality Information
    toqc = r.get('totalOzoneQualityCode')
    toqf = r.get('totalOzoneQualityFlag')
    afbo = r.get('bestOzoneAlgorithmFlag')

    # ObsValue
    # Total Ozone
    o3val = r.get('ozoneTotal', type='float')

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

    # Create pressure variable and fill in with zeros
    pressure = np.ma.array(np.zeros(lat.shape[0], dtype=np.float32))
    pressure.mask = lat.mask
    pressure.fill_value = lat.fill_value

    end_time = time.time()
    running_time = end_time - start_time
    print('Running time for creating derived variables : ', running_time, 'seconds')

    # =====================================
    # Split output based on satellite id
    # Create IODA ObsSpace
    # Write IODA output
    # =====================================
    logger.info('Split data based on satellite id, Create IODA ObsSpace and Write IODA output')

    # Find unique satellite identifiers in data to process
    unique_satids = np.unique(satid)
    logger.info(f'Number of Unique satellite identifiers : {len(unique_satids)}')
    logger.info(f'Unique satellite identifiers: {unique_satids}')

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
                logger.debug(f'Split data for {satinst} satid = {sat}')

        if matched:

            # Define a boolean mask to subset data from the original data object
            mask = satid == sat
            # MetaData
            lon2 = lon[mask]
            lat2 = lat[mask]
            satid2 = satid[mask]
            solzenang2 = solzenang[mask]
            scanpos2 = scanpos[mask]
            timestamp2 = timestamp[mask]
            pressure2 = pressure[mask]

            # QC Info
            toqc2 = toqc[mask]
            toqf2 = toqf[mask]
            afbo2 = afbo[mask]

            # ObsValue
            o3val2 = o3val[mask]

            timestamp2_min = datetime.fromtimestamp(timestamp2.min())
            timestamp2_max = datetime.fromtimestamp(timestamp2.max())

            # Create the dimensions
            dims = {
                'Location': np.arange(0, lat2.shape[0]),
            }

            # Create IODA ObsSpace
            sat = satellite_name.lower()
            iodafile = f"{cycle_type}.t{hh}z.{ioda_type}_{sat}.tm00.nc"
            OUTPUT_PATH = os.path.join(ioda_dir, iodafile)
            logger.info(f'Create output file : {OUTPUT_PATH}')
            obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)

            # Create Global attributes
            logger.debug('Create global attributes')
            obsspace.write_attr('sourceFiles', bufrfile)
            obsspace.write_attr('source', source)
            obsspace.write_attr('description', data_description)
            obsspace.write_attr('datetimeReference', reference_time)
            obsspace.write_attr('Converter', converter)
            obsspace.write_attr('platformLongDescription', platform_description)
            obsspace.write_attr('platformCommonName', satellite_name)
            obsspace.write_attr('platform', satellite_id)
            obsspace.write_attr('sensorLongDescription', sensor_description)
            obsspace.write_attr('sensorCommonName', sensor_name)
            obsspace.write_attr('sensor', sensor_id)
            obsspace.write_attr('dataProviderOrigin', data_provider)
            obsspace.write_attr('processingLevel', process_level)
            obsspace.write_attr('datetimeRange', [str(timestamp2_min), str(timestamp2_max)])

            # Create IODA variables
            logger.debug('Create variables: name, type, units, and attributes')
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

            # Total Ozone Quality Flag
            obsspace.create_var('MetaData/totalOzoneQualityFlag', dtype=toqf2.dtype, fillval=toqf2.fill_value) \
                .write_attr('long_name', 'Total Ozone Quality Flag  ') \
                .write_data(toqf2)

            # Total Ozone Quality Code
            obsspace.create_var('MetaData/totalOzoneQualityCode', dtype=toqc2.dtype, fillval=toqc2.fill_value) \
                .write_attr('long_name', 'OMI Total Ozone Quality Code') \
                .write_data(toqc2)

            # Pressure
            obsspace.create_var('MetaData/pressure', dtype=pressure2.dtype, fillval=pressure2.fill_value) \
                .write_attr('units', 'pa') \
                .write_attr('long_name', 'Pressure') \
                .write_data(pressure2)

            # Algorithm Flag for Best Ozone
            obsspace.create_var('MetaData/bestOzoneAlgorithmFlag', dtype=afbo2.dtype, fillval=afbo2.fill_value) \
                .write_attr('long_name', 'Algorithm Flag for Best Ozone') \
                .write_data(afbo2)

            # Solar Zenith Angle
            obsspace.create_var('MetaData/solarZenithAngle', dtype=solzenang2.dtype, fillval=solzenang2.fill_value) \
                .write_attr('units', 'm') \
                .write_attr('long_name', 'Solar Zenith Angle') \
                .write_data(solzenang2)

            # Sensor Scan Position
            obsspace.create_var('MetaData/sensorScanPosition', dtype=scanpos2.dtype, fillval=scanpos2.fill_value) \
                .write_attr('long_name', 'Sensor Scan Position') \
                .write_data(scanpos2)

            # Total Ozone
            obsspace.create_var('ObsValue/ozoneTotal', dtype=o3val2.dtype, fillval=o3val2.fill_value) \
                .write_attr('units', 'DU') \
                .write_attr('long_name', 'Total Column Ozone') \
                .write_data(o3val2)

            end_time = time.time()
            running_time = end_time - start_time
            total_ob_processed += len(satid2)
            logger.debug(f'Processing time for splitting and output IODA for {satinst} : {running_time}, seconds')

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
    logger = Logger('BUFR2IODA_ozone_omi.py', level=log_level, colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Total running time : {running_time} seconds")
