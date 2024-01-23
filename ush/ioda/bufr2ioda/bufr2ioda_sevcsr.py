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
    sensor_description = 'Spinning Enhanced Visible and InfraRed Imager;12 channels, 1 narrow-bandwidth, 1 high-resolution broad-bandwidth VIS'

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
    q.add('sensorCentralFrequency', '*/RPSEQ7/SCCF')    
    q.add('solarZenithAngle', '*/SOZA')
    q.add('cloudFree', '*/RPSEQ7/NCLDMNT')
    q.add('brightnessTemperature', '*/RPSEQ7/TMBRST')
    q.add('ClearSkyStdDev', '*/RPSEQ7/SDTB')
    

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
  
    nfov=satzenang.shape[0]
    scanpos = np.zeros(nfov, dtype=np.int32)
    scanpos = satzenang.astype(np.int32)  + 1 
  
    cloudAmount=100-cldFree

    sataziang = np.full_like(solzenang, float32_fill_value, dtype=np.float32)
    solaziang = np.full_like(solzenang, float32_fill_value, dtype=np.float32)    
    viewang = np.full_like(solzenang, float32_fill_value, dtype=np.float32)
   # Define Channel dimension for channels 4 to 11 since the other channel values are missing
    channel_start = 4
    channel_end = 11
    channum= np.arange(channel_start, channel_end + 1)
 
    # Define wavenumbers for each satellite ID
    wavenum_values_dict = {
    70: np.array([257301, 159467.6, 136116.2, 114714.5, 103474.5, 92997.55, 83834.94, 74750.95], dtype=np.float32),
    55: np.array([256550.4, 159490.2, 136128.6, 114870.3, 103420.4, 92938.72, 83886.68, 75122.19], dtype=np.float32)}
    wavenum_fill_value = float32_fill_value

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

    # Find nique satellite identifiers in data to process
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
            if satellite_id in wavenum_values_dict:
                # Extract the wavenum values for the current satellite ID
                Wavenum = wavenum_values_dict[satellite_id]
            else:
                # If the satellite ID is not in the dictionary
                logger.debug(f'satellite ID is not in the dictionary {satellite_id}')

            # Define a boolean mask to subset data from the original data object
            satelite_mask = satid == sat
  
            # Define a boolean mask based on the condition 0 < satzenang2 < 80
            satzenang_mask = np.logical_and(0 < satzenang, satzenang < 80)
      
            combined_mask = satzenang_mask * satelite_mask
          
            # MetaData
            lon2 = lon[combined_mask]
            lat2 = lat[combined_mask]
            timestamp2 = timestamp[combined_mask]
            satid2 = satid[combined_mask]
            instid2    = instid[combined_mask]
            satzenang2 = satzenang[combined_mask]
            chanfreq2=chanfreq[3:11]
 
            # Convert scanpos to np.int32 before applying the mask
            scanpos2 = scanpos.astype(np.int32)[combined_mask]
            # Replace masked values with the fill value before writing to IODA variable
            scanpos2 = np.where(scanpos2.mask, int32_fill_value, scanpos2)
            solzenang2 = solzenang[combined_mask]
            cldFree2 = cldFree[combined_mask]
            cldFree2=cldFree2[:, 3:11]
            cloudAmount2 = cloudAmount[combined_mask]
            cloudAmount2= cloudAmount2[:, 3:11]
            BT2= BT[combined_mask]     

            # Extract only channels 4 to 11
            BT2 = BT2[:, 3:11]
            clrStdDev2= clrStdDev[combined_mask]
            viewang2=viewang.flatten()[combined_mask]
            sataziang2=sataziang.flatten()[combined_mask]
            solaziang2=solaziang.flatten()[combined_mask]

            # Timestamp Range
            timestamp2_min = datetime.fromtimestamp(timestamp2.min())
            timestamp2_max = datetime.fromtimestamp(timestamp2.max())

            # Check unique observation time
            unique_timestamp2 = np.unique(timestamp2)
            logger.debug(f'Processing output for satid {sat}')
            
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
 
            # Sensor Channel Number
            obsspace.create_var('MetaData/sensorChannelNumber', dim_list=['Channel'], dtype=np.int32, fillval=int32_fill_value) \
                    .write_attr('long_name', 'Sensor Channel Number') \
                    .write_data(channum)

            # Sensor Central Frequency
            obsspace.create_var('MetaData/sensorCentralFrequency', dim_list=['Channel'],dtype=chanfreq2.dtype, fillval=chanfreq2.fill_value) \
                    .write_attr('units', 'Hz') \
                    .write_attr('long_name', 'Satellite Channel Center Frequency') \
                    .write_data(chanfreq2)

            # Sensor Central Wavenumber
            obsspace.create_var('MetaData/sensorCentralWavenumber',dim_list=['Channel'], dtype=Wavenum.dtype, fillval=wavenum_fill_value) \
                    .write_attr('units', 'm-1') \
                    .write_attr('long_name', 'Sensor Central Wavenumber') \
                    .write_data(Wavenum)


 
            if np.any(combined_mask):
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
                obsspace.create_var('MetaData/sensorScanPosition', dtype=scanpos2.astype(np.int32).dtype, fillval=int32_fill_value) \
                    .write_attr('long_name', 'Sensor Scan Position') \
                    .write_data(scanpos2)
    
                # Sensor Zenith Angle
                obsspace.create_var('MetaData/sensorZenithAngle', dtype=satzenang2.dtype, fillval=satzenang2.fill_value) \
                    .write_attr('units', 'degree') \
                    .write_attr('valid_range', np.array([0, 90], dtype=np.float32)) \
                    .write_attr('long_name', 'Sensor Zenith Angle') \
                    .write_data(satzenang2)
    
    
               # Sensor Azimuth Angle
                obsspace.create_var('MetaData/sensorAzimuthAngle', dtype=np.float32, fillval=sataziang2.fill_value) \
                    .write_attr('units', 'degree') \
                    .write_attr('valid_range', np.array([0, 360], dtype=np.float32)) \
                    .write_attr('long_name', 'Sensor Azimuth Angle') \
                    .write_data(sataziang2)
    
    
               # Solar Azimuth Angle
                obsspace.create_var('MetaData/solarAzimuthAngle', dtype=np.float32, fillval=solaziang2.fill_value) \
                    .write_attr('units', 'degree') \
                    .write_attr('valid_range', np.array([0, 360], dtype=np.float32)) \
                    .write_attr('long_name', 'Solar Azimuth Angle') \
                    .write_data(solaziang2)
    
    
                # Sensor View Angle
                obsspace.create_var('MetaData/sensorViewAngle', dtype=np.float32, fillval=viewang2.fill_value) \
                    .write_attr('units', 'degree') \
                    .write_attr('long_name', 'Sensor View Angle') \
                    .write_data(viewang2)
     
                # Solar Zenith Angle 
                obsspace.create_var('MetaData/solarZenithAngle', dtype=solzenang2.dtype, fillval=solzenang2.fill_value) \
                    .write_attr('units', 'degree') \
                    .write_attr('valid_range', np.array([0, 180], dtype=np.float32)) \
                    .write_attr('long_name', 'Solar Zenith Angle') \
                    .write_data(solzenang2)

               
                # Cloud free 
                obsspace.create_var('MetaData/cloudFree', dtype=cldFree2.dtype, fillval=int32_fill_value) \
                   .write_attr('units', '1') \
                   .write_attr('valid_range', np.array([0, 100], dtype=np.int32)) \
                   .write_attr('long_name', 'Amount Segment Cloud Free') \
                   .write_data(cldFree2)
   

                # Cloud amount based on computation 
                obsspace.create_var('MetaData/cloudAmount', dtype=cloudAmount2.dtype, fillval=cloudAmount2.fill_value) \
                   .write_attr('units', '1') \
                   .write_attr('valid_range', np.array([0, 100], dtype=np.float32)) \
                   .write_attr('long_name', 'Amount of cloud coverage in layer') \
                   .write_data(cloudAmount2)
    
                # ObsType based on computation method/spectral band
                obsspace.create_var('ObsValue/brightnessTemperature', dim_list=['Location','Channel'],dtype=np.float32,fillval=BT2.fill_value) \
                   .write_attr('units', 'k') \
                   .write_attr('long_name', 'Brightness Temperature') \
                   .write_data(BT2)
    
               
                obsspace.create_var('ClearSkyStdDev/brightnessTemperature',  dim_list=['Location','Channel'],dtype=np.float32, fillval=clrStdDev2.fill_value) \
                   .write_attr('long_name', 'Standard Deviation Brightness Temperature') \
                   .write_data(clrStdDev2[:, 3:11])
    
            else:
                logger.debug('No valid values (0<satzenang2 < 80), skipping writing to IODA') 
              
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
