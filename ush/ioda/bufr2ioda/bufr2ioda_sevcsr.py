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

# Define and initialize  global variables
global float32_fill_value
global int32_fill_value
global int64_fill_value

float32_fill_value = np.float32(0)
int32_fill_value = np.int32(0)
int64_fill_value = np.int64(0)


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
    platform_description = 'NOAA Series of Geostationary Operational Environmental Satellites - 3rd generation since 2016'
    sensor_description = '16 channels, balaned visible, near IR, short-wave IR, mid-wave IR, and thermal IR; \
                         central wavelentgh ranges from 470 nm to 13.3 micron'

    logger.info(f'sensor_name = {sensor_name}')
    logger.info(f'sensor_full_name = {sensor_full_name}')
    logger.info(f'sensor_id = {sensor_id}')
    logger.info(f'reference_time = {reference_time}')

    bufrfile = f"{cycle_type}.t{hh}z.{data_type}.tm00.{data_format}"
    DATA_PATH = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}", str(hh), 'atmos', bufrfile)

    # ============================================
    # Make the QuerySet for all the data we want
    # ============================================
    start_time = time.time()

    logger.info('Making QuerySet')
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
    q.add('sensorId', '*/SIID[1]')
    q.add('sensorZenithAngle', '*/SAZA')
    q.add('sensorCentralFrequency', '*/SCCF')    
    q.add('solarZenithAngle', '*/SOZA')
    q.add('cloudFree', '*/NCLDMNT')
    # ObsValue
    q.add('brightnessTemperature', '*/TMBRST')
    # ClearSkyStdDev
    q.add('ClearSkyStdDev', '*/SDTB/TMBRST')
    

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
    instid    = r.get('sensorId')
    year = r.get('year')
    month = r.get('month')
    day = r.get('day')
    hour = r.get('hour')
    minute = r.get('minute')
    second = r.get('second')
    lat = r.get('latitude')
    lon = r.get('longitude')
    satzenang = r.get('sensorZenithAngle')
    chanfreq = r.get('sensorCentralFrequency', type='float')
    BT= r.get('brightnessTemperature')
    clrStdDev= r.get('ClearSkyStdDev')
    cldFree= r.get('cloudFree')
    solzenang=r.get('solarZenithAngle')
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
    if np.ma.is_masked(satzenang[0]):
    # Handle the masked value
        scanpos = np.array([int32_fill_value], dtype=np.int64)

    else:
    # Convert the non-masked value to an integer
        scanpos = np.array([int(satzenang[0]) + 1], dtype=np.int32)

    cloudAmount=1-cldFree
    channum=12

    sataziang=np.array([float32_fill_value], dtype=np.float32)


    logger.info('Creating derived variables')
  
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
            instid2    = instid[mask]
            satzenang2 = satzenang[mask]
            chanfreq2 = chanfreq[mask]
           # obstype2 = obstype[mask]
            solzenang2 = solzenang[mask]
            cldFree2 = cldFree[mask]
            cloudAmount2 = cloudAmount[mask]
            BT2= BT[mask]
            clrStdDev2= clrStdDev[mask]

            # Timestamp Range
            timestamp2_min = datetime.fromtimestamp(timestamp2.min())
            timestamp2_max = datetime.fromtimestamp(timestamp2.max())

            # Check unique observation time
            unique_timestamp2 = np.unique(timestamp2)
            logger.debug(f'Processing output for satid {sat}')

  # Define Channel dimension for channels 4 to 11 since the other channel values are missing.( AZADEH)
            channel_start = 4
            channel_end = 11

            # Create the dimensions
            dims = {
               'Location': np.arange(0, BT2.shape[0]),            
               'Channel' : np.arange(channel_start, channel_end + 1)}

            # Create IODA ObsSpace
            iodafile = f"{cycle_type}.t{hh}z.{satinst}.tm00.nc"
            OUTPUT_PATH = os.path.join(ioda_dir, iodafile)
            logger.info(f'Create output file : {OUTPUT_PATH}')
            obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)

            # Create Global attributes
            logger.debug('Write global attributes')
            obsspace.write_attr('Converter', converter)
            obsspace.write_attr('sourceFiles', bufrfile)
#            obsspace.write_attr('dataProviderOrigin', data_provider)
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

            # Instrument Identifier
            obsspace.create_var('MetaData/instrumentIdentifier', dtype=instid2.dtype, fillval=instid2.fill_value) \
                .write_attr('long_name', 'Satellite Instrument Identifier') \
                .write_data(instid2)


        # Scan Position (derived variable, need to specified fill value explicitly)
            obsspace.create_var('MetaData/sensorScanPosition', dtype=scanpos.dtype, fillval=int32_fill_value) \
               .write_attr('long_name', 'Sensor Scan Position') \
               .write_data(scanpos)


            # Sensor Zenith Angle
            obsspace.create_var('MetaData/sensorZenithAngle', dtype=satzenang2.dtype, fillval=satzenang2.fill_value) \
                .write_attr('units', 'degree') \
                .write_attr('valid_range', np.array([0, 90], dtype=np.float32)) \
                .write_attr('long_name', 'Sensor Zenith Angle') \
                .write_data(satzenang2)


           # Sensor Azimuth Angle
            obsspace.create_var('MetaData/sensorAzimuthAngle', dtype=np.float32, fillval=float32_fill_value) \
                .write_attr('units', 'degree') \
                .write_attr('valid_range', np.array([0, 360], dtype=np.float32)) \
                .write_attr('long_name', 'Sensor Azimuth Angle') \
                .write_data(sataziang)


            # Sensor Centrall Frequency
            obsspace.create_var('MetaData/sensorCentralFrequency', dtype=chanfreq2.dtype, fillval=chanfreq2.fill_value) \
                .write_attr('units', 'Hz') \
                .write_attr('long_name', 'Satellite Channel Center Frequency') \
                .write_data(chanfreq2)

            # Solar Zenith Angle 
            obsspace.create_var('MetaData/solarZenithAngle', dtype=solzenang2.dtype, fillval=solzenang2.fill_value) \
                .write_attr('units', 'degree') \
                .write_attr('valid_range', np.array([0, 180], dtype=np.float32)) \
                .write_attr('long_name', 'Solar Zenith Angle') \
                .write_data(solzenang2)

            # Cloud free 
            obsspace.create_var('MetaData/cloudFree', dtype=cldFree2.dtype, fillval=cldFree2.fill_value) \
               .write_attr('units', '1') \
               .write_attr('valid_range', np.array([0, 1], dtype=np.float32)) \
               .write_attr('long_name', 'Amount Segment Cloud Free') \
               .write_data(cldFree2)


            # Cloud amount based on computation 
            obsspace.create_var('MetaData/cloudAmount', dtype=cloudAmount2.dtype, fillval=cloudAmount2.fill_value) \
               .write_attr('units', '1') \
               .write_attr('valid_range', np.array([0, 1], dtype=np.float32)) \
               .write_attr('long_name', 'Amount of cloud coverage in layer') \
               .write_data(cloudAmount2)

            # ObsType based on computation method/spectral band
            obsspace.create_var('ObsValue/brightnessTemperature', dim_list=['Location','Channel'],dtype=np.float32, fillval=float32_fill_value) \
               .write_attr('units', 'k') \
               .write_attr('long_name', 'Brightness Temperature') \
               .write_data(BT2)

           
            obsspace.create_var('ClearSkyStdDev/brightnessTemperature',  dim_list=['Location','Channel'],dtype=np.float32, fillval=float32_fill_value) \
               .write_attr('long_name', 'Standard Deviation Brightness Temperature') \
               .write_data(clrStdDev2)


          
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
    logger = Logger('bufr2ioda_sevcsr.py', level=log_level, colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Total running time: {running_time} seconds")
