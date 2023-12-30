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

# ==================================================================================================
# Subset    |  Description (OMPS NP)                                                               |     
# --------------------------------------------------------------------------------------------------
# NC008017  | OMPS NP is the Ozone Nadir Profile derived from the measurements made by the OMPS    |
#           | Nadir Profiler and the OMPS Nadir Mapper sensors on Suomi-NPP and JPSS. The data     |
#           | contains layer ozone amounts derived from the ratio of the observed backscattered    |
#           | spectral radiance to the incoming solar spectral irradiance for all solar zenith     |
#           | angle viewing conditions less than or equal to 80 degrees.                           | 
# ==================================================================================================

def format_element(x):

   field_width    = 15
   decimal_places =  5
   scientific_notation_threshold = 1000

   if abs(x) < scientific_notation_threshold:
      return f"{x:>{field_width}.{decimal_places}f}"
   else:
      return f"{x:>{field_width}.5e}"

def bufr_to_ioda(config, logger):

    # Get parameters from configuration
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
    converter = 'BUFR to IODA Converter'
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
    q.add('hour','*/HOUR')
    q.add('minute', '*/MINU')
    q.add('second', '*/SECO')
    q.add('solarZenithAngle', '*/SOZA')
    q.add('topLevelPressure', '*/OZOPQLSQ/PRLC[2]') 
    q.add('bottomLevelPressure', '*/OZOPQLSQ/PRLC[1]') 

    # Quality
    q.add('totalOzoneQuality', '*/SBUVTOQ')
    q.add('profileOzoneQuality','*/SBUVPOQ')

    # ObsValue
    q.add('ozoneLayer', '*/OZOPQLSQ/OZOP[2]')

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
    satid = r.get('satelliteId', 'ozoneLayer')
    year = r.get('year', 'ozoneLayer')
    month = r.get('month', 'ozoneLayer')
    day = r.get('day', 'ozoneLayer')
    hour = r.get('hour', 'ozoneLayer')
    minute = r.get('minute', 'ozoneLayer')
    second = r.get('second', 'ozoneLayer')
    lat = r.get('latitude', 'ozoneLayer')
    lon = r.get('longitude', 'ozoneLayer')
    solzenang = r.get('solarZenithAngle', 'ozoneLayer')
    ptop = r.get('topLevelPressure', 'ozoneLayer', type='float')
    pbot = r.get('bottomLevelPressure', 'ozoneLayer', type='float')

    # Quality Information 
    poqc = r.get('profileOzoneQuality', 'ozoneLayer')
    toqc = r.get('totalOzoneQuality', 'ozoneLayer')

    # ObsValue
    # Total Ozone 
    o3val= r.get('ozoneLayer', 'ozoneLayer', type='float')

    # DateTime: seconds since Epoch time
    # IODA has no support for numpy datetime arrays dtype=datetime64[s]
    timestamp = r.get_datetime('year','month','day','hour','minute','second', 'ozoneLayer').astype(np.int64)

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f'Processing time for executing QuerySet to get ResultSet : {running_time} seconds')

    # =========================
    # Create derived variables
    # =========================
    start_time = time.time()

    # Set reference pressure
    nlevs = 21
    nprofs = int(len(o3val)/nlevs) 
    pref0 = np.array( [1000.000, 631.000, 398.000, 251.000, 158.000, 100.000, 63.100, \
                         39.800,  25.100,  15.800,  10.000,   6.310,   3.980,  2.510, \
                          1.580,   1.000,   0.631,   0.398,   0.251,   0.158,  0.100] )
    pref0 = pref0 * 100. * 1.01325

    nprofs = int(len(o3val)/nlevs)
    pressure = np.tile(pref0, nprofs).astype(np.float32)

    # Set reference pressure vertices
    prestop = np.array( [    0,         631.000,    398.000,    251.000,    158.000,    100.000,    63.100,  \
                             39.800,      25.100,      15.800,     10.000,      6.310,      3.980,    2.510,  \
                              1.580,       1.000,       0.631,      0.398,      0.251,      0.158,    0.100,   0] )
    presbot = np.array( [ 1000.000,    1000.000,    631.000,    398.000,    251.000,    158.000,    100.000, \
                             63.100,      39.800,     25.100,     15.800,     10.000,      6.310,      3.980, \
                              2.510,       1.580,      1.000,      0.631,      0.398,      0.251,      0.158,  0.100] )
    prestop = prestop * 100. * 1.01325
    presbot = presbot * 100. * 1.01325

    pres = np.zeros((nlevs+1,2), dtype=np.float32)
    pres[:,0] = prestop
    pres[:,1] = presbot
    presv = np.tile(pres, (nprofs, 1)).astype(np.float32)

    # Calculate total column ozone 
    o3tot = np.sum(o3val.reshape(-1, nlevs), axis=1)
    o3tot[o3tot < 1.0e-20] = o3val.fill_value

    # Append total column zoone at the end of each profile    
    # Create a dictionary to store the arrays
    arrays_dict = {
        'o3val'      : o3val,
        'lat'        : lat,
        'lon'        : lon,
        'timestamp'  : timestamp,
        'solzenang'  : solzenang,
        'satid'      : satid,
        'poqc'       : poqc,
        'toqc'       : toqc,
        'pressure'   : pressure,
        'ptop'       : ptop, 
        'pbot'       : pbot, 
    }

    for key in arrays_dict.keys():
        array = arrays_dict[key]

        # Reshape the array (1D to 2D)
        reshaped_array = array.reshape((nprofs, nlevs))

        # Create a temporary array with zeros
#       tmp = np.zeros((nprofs, 22))
        tmp = np.empty((nprofs, 22), dtype=array.dtype)

        # Assign the reshaped array values to the temporary array
        tmp[:, 1:] = reshaped_array

        if key == 'o3val':
           tmp[:, 0] = o3tot
        elif key == 'pressure':
           tmp[:, 0] = 0.0
        else:
           tmp[:, 0] = tmp[:, 1]

        # Update the array in the dictionary
        arrays_dict[key] = tmp

    # Update the variables with the modified arrays
    lat1 = arrays_dict['lat']
    lon1 = arrays_dict['lon']
    o3val1 = arrays_dict['o3val']
    timestamp1 = arrays_dict['timestamp']
    solzenang1 = arrays_dict['solzenang']
    satid1 = arrays_dict['satid']
    poqc1 = arrays_dict['poqc']
    toqc1 = arrays_dict['toqc']
    pressure1 = arrays_dict['pressure']
    ptop1 = arrays_dict['ptop']
    pbot1 = arrays_dict['pbot']
    presv1 = presv.reshape(nprofs, 22, 2)

#   # Print the profiles for debugging
#   for i in range(o3val1.shape[0]):
#      for k in reversed(range(o3val1.shape[1])):
#         row  = np.array([i+1, k+1, lat1[i,k], lon1[i,k], pressure1[i,k], o3val1[i,k], toqc1[i,k], poqc1[i,k], solzenang1[i,k] ])
#         frow = [format_element(x) for x in row.flatten()]
#         row  = ' '.join(frow)
#         print(row)

    # Print the profiles for debugging
    for i in range(o3val1.shape[0]):
       for k in reversed(range(o3val1.shape[1])):
          row = np.array([i+1, k+1, lat1[i,k], lon1[i,k], ptop1[i,k], pbot1[i,k], pressure1[i,k], presv1[i,k,0], presv1[i,k,1], o3val1[i,k], toqc1[i,k], poqc1[i,k], solzenang1[i,k] ])
          frow = [format_element(x) for x in row.flatten()]
          row = ' '.join(frow)
          print(row)

    # Update the variables with the modified arrays
    lat1 = arrays_dict['lat'].flatten()
    lon1 = arrays_dict['lon'].flatten()
    o3val1 = arrays_dict['o3val'].flatten()
    timestamp1 = arrays_dict['timestamp'].flatten()
    solzenang1 = arrays_dict['solzenang'].flatten()
    satid1 = arrays_dict['satid'].flatten()
    poqc1 = arrays_dict['poqc'].flatten()
    toqc1 = arrays_dict['toqc'].flatten()
    pressure1 = arrays_dict['pressure'].flatten()
    ptop1 = arrays_dict['ptop'].flatten()
    pbot1 = arrays_dict['pbot'].flatten()
    presv1 = presv1.reshape(-1, presv1.shape[-1])

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f'Running time for creating derived variables : {running_time} seconds')

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
            mask       = satid1 == sat
            # MetaData
            lon2 = np.flip(lon1[mask], axis=0)
            lat2 = np.flip(lat1[mask], axis=0)
            satid2 = np.flip(satid1[mask], axis=0)
            solzenang2 = np.flip(solzenang1[mask], axis=0)
            timestamp2 = np.flip(timestamp1[mask], axis=0)
            pressure2 = np.flip(pressure1[mask], axis=0)
            presv2 = np.flip(presv1[mask],     axis=0)
            ptop2 = ptop1[mask]
            pbot2 = pbot1[mask]
            

            # QC Info
            toqc2 = np.flip(toqc1[mask], axis=0)
            poqc2 = np.flip(poqc1[mask], axis=0)

            # ObsValue
            o3val2 = np.flip(o3val1[mask], axis=0)

            timestamp2_min = datetime.fromtimestamp(timestamp1.min())
            timestamp2_max = datetime.fromtimestamp(timestamp1.max())

            # Check unique observation time
            unique_timestamp = np.unique(timestamp1)

            # Create the dimensions
            dims = {
               'Location': np.arange(0, lat2.shape[0]),
               'Vertice': np.array([2, 1])
            }

            # Create IODA ObsSpace 
            sat = satellite_name.lower()
            iodafile = f"{cycle_type}.t{hh}z.{ioda_type}_{sat}.tm00.nc"            
            OUTPUT_PATH = os.path.join(ioda_dir, iodafile)
            obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)
            logger.info(f'Create output file : {OUTPUT_PATH}')

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
            obsspace.write_attr('sensorLongDescription',sensor_description)
            obsspace.write_attr('sensorCommonName', sensor_name)
            obsspace.write_attr('sensor', sensor_id)
            obsspace.write_attr('dataProviderOrigin', data_provider)
            obsspace.write_attr('processingLevel', process_level)
            obsspace.write_attr('datetimeRange', [str(timestamp2_min), str(timestamp2_max)])

            # Create IODA variables
            # Longitude
            obsspace.create_var('MetaData/longitude', dtype=lon2.dtype, fillval=lon.fill_value) \
                .write_attr('units', 'degrees_east') \
                .write_attr('valid_range', np.array([-180, 180], dtype=np.float32)) \
                .write_attr('long_name', 'Longitude') \
                .write_data(lon2)

            # Latitude 
            obsspace.create_var('MetaData/latitude', dtype=lat2.dtype, fillval=lat.fill_value) \
                .write_attr('units', 'degrees_north') \
                .write_attr('valid_range', np.array([-90, 90], dtype=np.float32)) \
                .write_attr('long_name', 'Latitude') \
                .write_data(lat2)
  
            # Datetime
            obsspace.create_var('MetaData/dateTime', dtype=timestamp2.dtype, fillval=timestamp.fill_value) \
                .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
                .write_attr('long_name', 'Unix Epoch') \
                .write_data(timestamp2)

            # Satellite Identifier  
            obsspace.create_var('MetaData/satelliteIdentifier', dtype=satid2.dtype, fillval=satid.fill_value) \
                .write_attr('long_name', 'Satellite Identifier') \
                .write_data(satid2)

            # Quality:
            obsspace.create_var('MetaData/totalOzoneQuality', dtype=toqc2.dtype, fillval=toqc.fill_value) \
                .write_attr('long_name', 'Total Ozone Quality') \
                .write_data(toqc2)

            # Quality:
            obsspace.create_var('MetaData/profileOzoneQuality', dtype=poqc2.dtype, fillval=poqc.fill_value) \
                .write_attr('long_name', 'Layer Ozone Quality') \
                .write_data(poqc2)

            # Pressure 
            obsspace.create_var('MetaData/pressure', dtype=pressure2.dtype, fillval=lat.fill_value) \
                .write_attr('units', 'pa') \
                .write_attr('long_name', 'Pressure') \
                .write_data(pressure2)

            # Pressure vertices 
            obsspace.create_var('RetrievalAncillaryData/pressureVertice', dim_list=['Location','Vertice'], dtype=pbot2.dtype, fillval=lat.fill_value) \
                .write_attr('units', 'pa') \
                .write_attr('long_name', 'Retrieval Pressure Vertices') \
                .write_data(presv2)

            # Pressure 
            obsspace.create_var('MetaData/topLevelPressure', dtype=ptop2.dtype, fillval=lat.fill_value) \
                .write_attr('units', 'pa') \
                .write_attr('long_name', 'Top Level Pressure') \
                .write_data(ptop2)

            # Pressure 
            obsspace.create_var('MetaData/bottomLevelPressure', dtype=pbot2.dtype, fillval=lat.fill_value) \
                .write_attr('units', 'pa') \
                .write_attr('long_name', 'Bottom Level Pressure') \
                .write_data(pbot2)

            # Solar Zenith Angle 
            obsspace.create_var('MetaData/solarZenithAngle', dtype=solzenang2.dtype, fillval=solzenang.fill_value) \
                .write_attr('units', 'degree') \
                .write_attr('valid_range', np.array([0, 180], dtype=np.float32)) \
                .write_attr('long_name', 'Solar Zenith Angle') \
                .write_data(solzenang2)

            # Layer Ozone and Total Ozone 
            obsspace.create_var('ObsValue/ozoneLayer', dtype=o3val2.dtype, fillval=o3val.fill_value) \
                .write_attr('units', 'DU') \
                .write_attr('long_name', 'Layer Ozone') \
                .write_data(o3val2)

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
    logger = Logger('BUFR2IODA_ozone_ompsnp.py', level=log_level, colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Total running time : {running_time} seconds")
