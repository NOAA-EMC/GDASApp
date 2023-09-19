# (C) Copyright 2023 NOAA/NWS/NCEP/EMC
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

import sys

sys.path.append('/work2/noaa/da/nesposito/ioda-bundle_20230712/build/lib/python3.9/')
sys.path.append('/work2/noaa/da/nesposito/ioda-bundle_20230712/build/lib/python3.9/pyiodaconv/')
sys.path.append('/work2/noaa/da/nesposito/ioda-bundle_20230712/build/lib/python3.9/pyioda/')

import os
import argparse
import json
import numpy as np
import numpy.ma as ma
import math
import calendar
import time 
import datetime
from pyiodaconv import bufr
from collections import namedtuple
from pyioda import ioda_obs_space as ioda_ospace

# ====================================================================
# GPS-RO BUFR dump file
#=====================================================================
# NC003010  |    GPS-RO
# ====================================================================

def Derive_stationIdentification(said,ptid,stid):
    stid = stid.astype('str')
    for i in range(len(said)):
       stid[i] = str(said[i]).zfill(4)+str(ptid[i]).zfill(4)

    return stid


def Compute_Grid_Location(degrees):

    for i in range(len(degrees)):
       if degrees[i] < 180 and degrees[i] > -180 :
          degrees[i] = np.deg2rad(degrees[i])
    rad = degrees

    return rad

def Compute_imph(impp, elrc, geodu):

    imph = impp - elrc - geodu

    return imph

def bufr_to_ioda(config):

    subsets = config["subsets"]
    # =========================================
    # Get parameters from configuration
    # =========================================
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

    sensor_satellite_info_array = config["sensor_satellite_info"]

    bufrfile = f"{cycle_type}.t{hh}z.{data_type}.tm00.{data_format}"
    DATA_PATH = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}", str(hh), 'atmos', bufrfile)

    # ============================================
    # Make the QuerySet for all the data we want
    # ============================================
    start_time = time.time()

    print('Making QuerySet ...')
    q = bufr.QuerySet(subsets)

    # MetaData
    q.add('latitude',                      '*/ROSEQ1/CLATH' )
    q.add('longitude',                     '*/ROSEQ1/CLONH' )
    q.add('gridLatitude',                  '*/ROSEQ1/CLATH' )
    q.add('gridLongitude',                 '*/ROSEQ1/CLONH' )
    q.add('year',                          '*/YEAR' )
    q.add('year2',                         '*/YEAR' )
    q.add('month',                         '*/MNTH' )
    q.add('day',                           '*/DAYS' )
    q.add('hour',                          '*/HOUR' )
    q.add('minute',                        '*/MINU' )
    q.add('second',                        '*/SECO' )
    q.add('satelliteIdentifier',           '*/SAID' )
    q.add('satelliteInstrument',           '*/SIID' )
    q.add('satelliteConstellationRO',      '*/SCLF' )
    q.add('satelliteTransmitterId',         '*/PTID' )
    q.add('earthRadiusCurvature',          '*/ELRC' )
    #q.add('observationSequenceNum',        '*/SEQNUM' )
    q.add('geoidUndulation',               '*/GEODU' )
    q.add('height',                        '*/ROSEQ3/HEIT' )
    q.add('impactHeightRO_roseq2repl1',    '*/ROSEQ1/ROSEQ2{1}/IMPP' )
    q.add('impactHeightRO_roseq2repl3',    '*/ROSEQ1/ROSEQ2{3}/IMPP' )
    q.add('impactParameterRO_roseq2repl1', '*/ROSEQ1/ROSEQ2{1}/IMPP' )
    q.add('impactParameterRO_roseq2repl3', '*/ROSEQ1/ROSEQ2{3}/IMPP' )
    q.add('frequency__roseq2repl1',        '*/ROSEQ1/ROSEQ2{1}/MEFR' ) 
    q.add('frequency__roseq2repl3',        '*/ROSEQ1/ROSEQ2{3}/MEFR' )
    q.add('pccf',                          '*/ROSEQ1/PCCF' )
    q.add('percentConfidence',             '*/ROSEQ3/PCCF' )
    q.add('sensorAzimuthAngle',            '*/BEARAZ' )

    # Processing Center
    q.add('dataProviderOrigin',            '*/OGCE' )

    # Quality Information
    q.add('qualityFlags',                  '*/QFRO' )
    q.add('satelliteAscendingFlag',        '*/QFRO' )

    # ObsValue
    q.add('bendingAngle_roseq2repl1',      '*/ROSEQ1/ROSEQ2{1}/BNDA[1]' )
    q.add('bendingAngle_roseq2repl3',      '*/ROSEQ1/ROSEQ2{3}/BNDA[1]' )
    q.add('atmosphericRefractivity',       '*/ROSEQ3/ARFR[1]' )

    # ObsError
    q.add('obsErrorBendingAngle1',           '*/ROSEQ1/ROSEQ2{1}/BNDA[2]')
    q.add('obsErrorBendingAngle3',           '*/ROSEQ1/ROSEQ2{3}/BNDA[2]')
    q.add('obsErrorAtmosphericRefractivity', '*/ROSEQ3/ARFR[2]')

    # ObsType
    q.add('obsTypeBendingAngle',             '*/SAID' )
    q.add('obsTypeAtmosphericRefractivity',  '*/SAID' )

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
    clath      = r.get('latitude',                      'latitude')
    clonh      = r.get('longitude',                     'latitude')
    gclath     = r.get('gridLatitude',                  'latitude')
    gclonh     = r.get('gridLongitude',                 'latitude')
    year       = r.get('year',                          'latitude')
    year2      = r.get('year2')
    mnth       = r.get('month',                         'latitude')
    days       = r.get('day',                           'latitude')
    hour       = r.get('hour',                          'latitude')
    minu       = r.get('minute',                        'latitude')
    seco       = r.get('second',                        'latitude')
    stid       = r.get('satelliteIdentifier',           'latitude')
    said       = r.get('satelliteIdentifier',           'latitude')
    siid       = r.get('satelliteInstrument',           'latitude')
    sclf       = r.get('satelliteConstellationRO',      'latitude')
    ptid       = r.get('satelliteTransmitterId',         'latitude')
    elrc       = r.get('earthRadiusCurvature',          'latitude')
    #seqnum     = r.get('observationSequenceNum')
    geodu      = r.get('geoidUndulation',               'latitude')
    heit       = r.get('height',                        'height', type='float')
    impp1      = r.get('impactParameterRO_roseq2repl1', 'latitude')
    impp3      = r.get('impactParameterRO_roseq2repl3', 'latitude')
    imph1      = r.get('impactHeightRO_roseq2repl1',    'latitude')
    imph3      = r.get('impactHeightRO_roseq2repl3',    'latitude')
    mefr1      = r.get('frequency__roseq2repl1',        'latitude', type='float')
    mefr3      = r.get('frequency__roseq2repl3',        'latitude', type='float')
    pccf       = r.get('pccf',                          'latitude', type='float')
    ref_pccf   = r.get('percentConfidence',             'height' )
    bearaz     = r.get('sensorAzimuthAngle',            'latitude')

    print(' ... Executing QuerySet: get metadata: processing center ...')
    # Processing Center
    ogce       = r.get('dataProviderOrigin',            'latitude')

    print(' ... Executing QuerySet: get metadata: data quality information ...')
    # Quality Information 
    qfro       = r.get('qualityFlags',                  'latitude')
    satasc     = r.get('satelliteAscendingFlag',        'latitude' )

    print(' ... Executing QuerySet: get obsvalue: Bending Angle ...')
    # ObsValue
    # Bending Angle
    bnda1      = r.get('bendingAngle_roseq2repl1',      'latitude')
    bnda3      = r.get('bendingAngle_roseq2repl3',      'latitude')
    arfr       = r.get('atmosphericRefractivity',       'height')

    # ObsError
    # Bending Angle
    bndaoe1    = r.get('obsErrorBendingAngle1',          'latitude')
    bndaoe3    = r.get('obsErrorBendingAngle3',          'latitude')
    arfroe     = r.get('obsErrorAtmosphericRefractivity','height')

    # ObsType
    # Bending Angle
    bndaot     = r.get('obsTypeBendingAngle',           'latitude')
    arfrot     = r.get('obsTypeBendingAngle',           'latitude')

    print(' ... Executing QuerySet: get datatime: observation time ...')
    # DateTime: seconds since Epoch time
    # IODA has no support for numpy datetime arrays dtype=datetime64[s]
    timestamp = r.get_datetime('year','month','day','hour','minute','second','latitude').astype(np.int64)

###NICKE SEQNUM would happen around here
#For seqnum
#    seqnum=[]
#    qq=1
#    for i in range(len(elrc)):
#       if elrc[i] != elrc[i+1]:
#          qq = qq+1
#          seqnum.append(qq[i])
# check length. should be 666000
##### SOMEHTING LIKE THAT


    print(' ... Executing QuerySet: Done!')

    print(' ... Executing QuerySet: Check BUFR variable generic dimension and type ...')
    # Check BUFR variable generic dimension and type
    print('     clath     shape,type = ', clath.shape,  clath.dtype)
    print('     clonh     shape,type = ', clonh.shape,  clonh.dtype)
    print('     gclath    shape,type = ', gclath.shape, gclath.dtype)
    print('     gclonh    shape,type = ', gclonh.shape, gclonh.dtype)
    print('     year      shape,type = ', year.shape,   year.dtype)
    print('     mnth      shape,type = ', mnth.shape,   mnth.dtype)
    print('     days      shape,type = ', days.shape,   days.dtype)
    print('     hour      shape,type = ', hour.shape,   hour.dtype)
    print('     minu      shape,type = ', minu.shape,   minu.dtype)
    print('     seco      shape,type = ', seco.shape,   seco.dtype)
    print('     stid      shape,type = ', stid.shape,   stid.dtype)
    print('     said      shape,type = ', said.shape,   said.dtype)
    print('     siid      shape,type = ', siid.shape,   siid.dtype)
    print('     sclf      shape,type = ', sclf.shape,   sclf.dtype)
    print('     ptid      shape,type = ', ptid.shape,   ptid.dtype)
    print('     elrc      shape,type = ', elrc.shape,   elrc.dtype)
    print('     geodu     shape,type = ', geodu.shape,  geodu.dtype)
    print('     heit      shape,type = ', heit.shape,   heit.dtype)
    print('     impp1     shape,type = ', impp1.shape,   impp1.dtype)
    print('     impp3     shape,type = ', impp3.shape,   impp3.dtype)
    print('     imph1     shape,type = ', imph1.shape,   imph1.dtype)
    print('     imph3     shape,type = ', imph3.shape,   imph3.dtype)
    print('     mefr1     shape,type = ', mefr1.shape,   mefr1.dtype)
    print('     mefr3     shape,type = ', mefr3.shape,   mefr3.dtype)
    print('     pccf      shape,type = ', pccf.shape,   pccf.dtype)
    print('     ref_pccf  shape,type = ', ref_pccf.shape,   ref_pccf.dtype)
    print('     bearaz    shape,type = ', bearaz.shape,   bearaz.dtype)

    print('     ogce      shape,type = ', ogce.shape,   ogce.dtype)

    print('     qfro      shape,type = ', qfro.shape,   qfro.dtype)
    print('     satasc    shape,type = ', satasc.shape, satasc.dtype)

    print('     bnda1     shape,type = ', bnda1.shape,   bnda1.dtype)
    print('     bnda3     shape,type = ', bnda3.shape,   bnda3.dtype)
    print('     arfr      shape,type = ', arfr.shape,    arfr.dtype)

    print('     bndaoe1   shape,type = ', bndaoe1.shape,   bndaoe1.dtype)
    print('     bndaoe3   shape,type = ', bndaoe3.shape,   bndaoe3.dtype)
    print('     arfroe    shape,type = ', arfr.shape,   arfr.dtype)

    print('     bndaot    shape,type = ', bndaot.shape, bndaot.dtype)

    end_time = time.time()
    running_time = end_time - start_time
    print('Running time for executing QuerySet to get ResultSet : ', running_time, 'seconds')

    # =========================
    # Create derived variables
    # =========================
    start_time = time.time()

    print('Creating derived variables - stationIdentification')
    stid = Derive_stationIdentification(said,ptid,stid)

    print('     stid shape,type = ', stid.shape, stid.dtype)

    print('Creating derived variables - Grid Latitude / Longitude ...')
    gclonh = Compute_Grid_Location(gclonh)
    gclath = Compute_Grid_Location(gclath)

    print('     gclonh shape,type = ', gclonh.shape, gclonh.dtype)
    print('     gclath shape,type = ', gclath.shape, gclath.dtype)
    print('     gclonh min/max = ', gclonh.min(), gclonh.max())
    print('     gclath min/max = ', gclath.min(), gclath.max())

    print('Creating derived variables - imph ...')
    imph1 = Compute_imph(impp1, elrc, geodu)
    imph3 = Compute_imph(impp3, elrc, geodu)

    print('     imph1 shape,type = ', imph1.shape, imph1.dtype)
    print('     imph3 shape,type = ', imph3.shape, imph3.dtype)
    print('     imph1 min/max = ', imph1.min(), imph1.max())
    print('     imph3 min/max = ', imph3.min(), imph3.max())

    end_time = time.time()
    running_time = end_time - start_time
    print('Running time for creating derived variables : ', running_time, 'seconds')

    # =====================================
    # Create IODA ObsSpace
    # Write IODA output
    # =====================================
    
    print('Split data based on satellite id, Create IODA ObsSpace and Write IODA output')

    # Find unique satellite identifiers in data to process
    unique_satids = np.unique(said)
    print(' ... Number of Unique satellite identifiers: ', len(unique_satids))
    print(' ... Unique satellite identifiers: ', unique_satids)

    print(' ... Loop through unique satellite identifier ... : ', unique_satids)
    for sat in unique_satids.tolist():
        print("Processing output for said: ", sat)
        start_time = time.time()

        # Find matched sensor_satellite_info from sensor_satellite_info namedtuple
        matched = False
        for sensor_satellite_info in sensor_satellite_info_array:
            if (sensor_satellite_info["satellite_id"] == sat):
               matched = True
               sensor_id = sensor_satellite_info["sensor_id"]
               sensor_full_name = sensor_satellite_info["sensor_full_name"]
               sensor_name = sensor_satellite_info["sensor_name"]
               satellite_id = sensor_satellite_info["satellite_id"]
               satellite_full_name = sensor_satellite_info["satellite_full_name"]
               satellite_name = sensor_satellite_info["satellite_name"]

        
        if matched:    

           print(' ... Split data for satid = ', sat)
   
           # Define a boolean mask to subset data from the original data object
           mask       = said == sat
           # MetaData
           clonh2     = clonh[mask]
           clath2     = clath[mask]
           gclonh2    = gclonh[mask]
           gclath2    = gclath[mask]
           timestamp2 = timestamp[mask]
           stid2      = stid[mask]
           said2      = said[mask]
           siid2      = siid[mask]
           sclf2      = sclf[mask]
           ptid2      = ptid[mask]
           elrc2      = elrc[mask]
           geodu2     = geodu[mask]
           heit2      = heit[mask]
           impp1_2    = impp1[mask]
           impp3_2    = impp3[mask]
           imph1_2    = imph1[mask]
           imph3_2    = imph3[mask]
           mefr1_2    = mefr1[mask]
           mefr3_2    = mefr3[mask]
           pccf2      = pccf[mask]
           ref_pccf2  = ref_pccf[mask]
           bearaz2    = bearaz[mask]
   
           # Processing Center
           ogce2      = ogce[mask]
   
           # QC Info
           qfro2      = qfro[mask]
           satasc2    = satasc[mask]
   
           # ObsValue
           bnda1_2      = bnda1[mask]
           bnda3_2      = bnda3[mask]
           arfr2        = arfr[mask]
   
           # ObsError
           bndaoe1_2  = bndaoe1[mask]
           bndaoe3_2  = bndaoe3[mask]
           arfroe2    = arfr[mask]
   
           # ObsType
           bndaot2    = bndaot[mask]
           arfrot2    = arfrot[mask]
    
           # Choose bnda, mefr, impp, imph
           if ((sat == 44) or (sat == 825)):
             bnda2    = bnda1_2
             mefr2    = mefr1_2
             impp2    = impp1_2
             imph2    = imph1_2
             bndaoe2  = bndaoe1_2
           else:
             bnda2    = bnda3_2
             mefr2    = mefr3_2
             impp2    = impp3_2
             imph2    = imph3_2 
             bndaoe2  = bndaoe3_2
    
           # Check unique observation time
           unique_timestamp2 = np.unique(timestamp2)
           print(' ... Number of Unique observation timestamp: ', len(unique_timestamp2))
           print(' ... Unique observation timestamp: ', unique_timestamp2)
   
           print(' ... Create ObsSpae for satid = ', sat)
    
           # =====================================
           # Create IODA ObsSpace
           # Write IODA output
           # =====================================
    
           # Write the data to an IODA file
           OUTPUT_PATH = '/work2/noaa/da/nesposito/NewConv/api_convert/json/json_gdasapp/gdas.t00z.gpsro_'+str(sat)+'.tm00.nc'
           path, fname = os.path.split(OUTPUT_PATH)
           if path and not os.path.exists(path):
               os.makedirs(path)
   
           # Create the dimensions
           dims = {
              'Location'   : np.arange(0, clath2.shape[0]),
           }
       
           # Create IODA ObsSpace 
           obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)
   
           # Create Global attributes
           print(' ... ... Create global attributes')
           obsspace.write_attr('data_format', data_format)
           obsspace.write_attr('data_type', data_type)
           obsspace.write_attr('subsets', subsets)
           obsspace.write_attr('cycle_type', cycle_type)
           obsspace.write_attr('cycle_datetime', cycle)
           obsspace.write_attr('dataProviderOrigin', data_provider)
           obsspace.write_attr('converter', os.path.basename(__file__))

           obsspace.write_attr('description', data_description)
           obsspace.write_attr('sensor', sensor_id)
           obsspace.write_attr('satellite', satellite_id)
           obsspace.write_attr('sensorName', sensor_name)
           obsspace.write_attr('satelliteName', satellite_name)
           obsspace.write_attr('sensorFullName', sensor_full_name)
           obsspace.write_attr('satelliteFullName', satellite_full_name)
   
           # Create IODA variables
           print(' ... ... Create variables: name, type, units, and attributes')
           # Longitude
           obsspace.create_var('MetaData/longitude', dtype=clonh2.dtype, fillval=clonh2.fill_value) \
               .write_attr('units', 'degrees_east') \
               .write_attr('valid_range', np.array([-180, 180], dtype=np.float32)) \
               .write_attr('long_name', 'Longitude') \
               .write_data(clonh2)
   
           # Latitude 
           obsspace.create_var('MetaData/latitude', dtype=clath.dtype, fillval=clath2.fill_value) \
               .write_attr('units', 'degrees_north') \
               .write_attr('valid_range', np.array([-90, 90], dtype=np.float32)) \
               .write_attr('long_name', 'Latitude') \
               .write_data(clath2)
   
           # Grid Longitude
           obsspace.create_var('MetaData/gridLongitude', dtype=gclonh2.dtype, fillval=gclonh2.fill_value) \
               .write_attr('units', 'radians') \
               .write_attr('valid_range', np.array([-3.14159265, 3.14159265], dtype=np.float32)) \
               .write_attr('long_name', 'Grid Longitude') \
               .write_data(gclonh2)
   
           # Grid Latitude
           obsspace.create_var('MetaData/gridLatitude', dtype=gclath.dtype, fillval=gclath2.fill_value) \
               .write_attr('units', 'radians') \
               .write_attr('valid_range', np.array([-1.570796325, 1.570796325], dtype=np.float32)) \
               .write_attr('long_name', 'Grid Latitude') \
               .write_data(gclath2)
   
           # Datetime
           obsspace.create_var('MetaData/dateTime', dtype=np.int64, fillval=timestamp2.fill_value) \
               .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
               .write_attr('long_name', 'Datetime') \
               .write_data(timestamp2)
   
           # Satellite Identifier
           obsspace.create_var('MetaData/stationIdentification', dtype=stid2.dtype, fillval=stid2.fill_value) \
               .write_attr('long_name', 'Station Identification') \
               .write_data(stid2)

           # Satellite Identifier  
           obsspace.create_var('MetaData/satelliteIdentifier', dtype=said2.dtype, fillval=said2.fill_value) \
               .write_attr('long_name', 'Satellite Identifier') \
               .write_data(said2)
   
           # Satellite Instrument
           obsspace.create_var('MetaData/satelliteInstrument', dtype=siid2.dtype, fillval=siid2.fill_value) \
               .write_attr('long_name', 'Satellite Instrument') \
               .write_data(siid2)
   
           # Satellite Constellation RO
           obsspace.create_var('MetaData/satelliteConstellationRO', dtype=sclf2.dtype, fillval=sclf2.fill_value) \
               .write_attr('long_name', 'Satellite Constellation RO') \
               .write_data(sclf2)
   
           # Satellite Transmitter ID
           obsspace.create_var('MetaData/satelliteTransmitterId', dtype=ptid2.dtype, fillval=ptid2.fill_value) \
               .write_attr('long_name', 'Satellite Transmitter Id') \
               .write_data(ptid2)
   
           # Earth Radius Curvature
           obsspace.create_var('MetaData/earthRadiusCurvature', dtype=elrc2.dtype, fillval=elrc2.fill_value) \
               .write_attr('units', 'm') \
               .write_attr('long_name', 'Earth Radius of Curvature') \
               .write_data(elrc2)
   
           # Geoid Undulation
           obsspace.create_var('MetaData/geoidUndulation', dtype=geodu2.dtype, fillval=geodu2.fill_value) \
               .write_attr('units', 'm') \
               .write_attr('long_name', 'Geoid Undulation') \
               .write_data(geodu2)
   
           # Height
           obsspace.create_var('MetaData/height', dtype=heit2.dtype, fillval=heit2.fill_value) \
               .write_attr('units', 'm') \
               .write_attr('long_name', 'Height' ) \
               .write_data(heit2) 
   
          # Impact Parameter RO
           obsspace.create_var('MetaData/impactParameterRO', dtype=impp2.dtype, fillval=impp2.fill_value) \
               .write_attr('units', 'm') \
               .write_attr('long_name', 'Impact Parameter RO') \
               .write_data(impp2)
   
           # Impact Height RO
           obsspace.create_var('MetaData/impactHeightRO', dtype=imph2.dtype, fillval=imph2.fill_value) \
               .write_attr('units', 'm') \
               .write_attr('long_name', 'Impact Height RO') \
               .write_data(imph2)
   
           # Impact Height RO
           obsspace.create_var('MetaData/frequency', dtype=mefr2.dtype, fillval=mefr2.fill_value) \
               .write_attr('units', 'Hz') \
               .write_attr('long_name', 'Frequency') \
               .write_data(mefr2)
   
           # PCCF Percent Confidence
           obsspace.create_var('MetaData/pccf', dtype=pccf2.dtype, fillval=pccf2.fill_value) \
               .write_attr('units', '%') \
               .write_attr('long_name', 'Percent Confidence') \
               .write_data(pccf2)
   
           # PCCF Ref Percent Confidence
           obsspace.create_var('MetaData/percentConfidence', dtype=ref_pccf2.dtype, fillval=ref_pccf2.fill_value) \
               .write_attr('units', '%') \
               .write_attr('long_name', 'Ref Percent Confidence') \
               .write_data(ref_pccf2)
   
           # Azimuth Angle
           obsspace.create_var('MetaData/sensorAzimuthAngle', dtype=bearaz2.dtype, fillval=bearaz2.fill_value) \
               .write_attr('units', 'degree') \
               .write_attr('long_name', 'Percent Confidence') \
               .write_data(bearaz2)
   
           # Data Provider 
           obsspace.create_var('MetaData/dataProviderOrigin', dtype=ogce2.dtype, fillval=ogce2.fill_value) \
               .write_attr('long_name', 'Identification of Originating/Generating Center') \
               .write_data(ogce2)
   
           # Quality: Quality Flags
           obsspace.create_var('MetaData/qualityFlags', dtype=qfro2.dtype, fillval=qfro2.fill_value) \
               .write_attr('long_name', 'Quality Flags') \
               .write_data(qfro2)
   
           # Quality: Satellite Ascending Flag
           obsspace.create_var('MetaData/satelliteAscendingFlag', dtype=satasc2.dtype, fillval=satasc2.fill_value) \
               .write_attr('long_name', 'Satellite Ascending Flag') \
               .write_data(satasc2)
   
           # ObsValue: Bending Angle
           obsspace.create_var('ObsValue/bendingAngle', dtype=bnda2.dtype, fillval=bnda2.fill_value) \
               .write_attr('units', 'radians') \
               .write_attr('long_name', 'Bending Angle') \
               .write_data(bnda2)
   
           # ObsValue: Atmospheric Refractivity 
           obsspace.create_var('ObsValue/atmosphericRefractivity', dtype=arfr2.dtype, fillval=arfr2.fill_value) \
               .write_attr('units', 'N-units') \
               .write_attr('long_name', 'Atmospheric Refractivity ObsError') \
               .write_data(arfr2)
   
           # ObsError: Bending Angle
           obsspace.create_var('ObsError/bendingAngle', dtype=bndaoe2.dtype, fillval=bndaoe2.fill_value) \
               .write_attr('units', 'radians') \
               .write_attr('long_name', 'Bending Angle Obs Error') \
               .write_data(bndaoe2)
   
           # ObsError: Atmospheric Refractivity
           obsspace.create_var('ObsError/atmosphericRefractivity', dtype=arfroe2.dtype, fillval=arfroe2.fill_value) \
               .write_attr('units', 'N-units') \
               .write_attr('long_name', 'Atmospheric Refractivity ObsError') \
               .write_data(arfroe2)
   
           # ObsType
           obsspace.create_var('ObsType/BendingAngle', dtype=bndaot2.dtype, fillval=bndaot2.fill_value) \
               .write_attr('long_name', 'Bending Angle ObsType') \
               .write_data(bndaot2)
  
           # ObsType: Atmospheric Refractivity
           obsspace.create_var('ObsType/atmosphericRefractivity', dtype=arfrot2.dtype, fillval=arfrot2.fill_value) \
               .write_attr('long_name', 'Atmospheric Refractivity ObsType') \
               .write_data(arfrot2) 
   
           end_time = time.time()
           running_time = end_time - start_time
           print('Running time for splitting and output IODA for', str(sat), running_time, 'seconds')

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



